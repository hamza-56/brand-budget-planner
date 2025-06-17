from __future__ import annotations

import datetime
import json
from decimal import Decimal
from typing import Any, Dict, List, Optional, TypedDict, Union

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import QuerySet, Sum
from django.utils import timezone

from .choices import CampaignStatus
from .managers import AdSpendManager, CampaignManager
from core.models import TimeStampedUUIDModel

class DaypartingWindow(TypedDict):
    start: str
    end: str


class DaypartingSchedule(TypedDict, total=False):
    monday: List[DaypartingWindow]
    tuesday: List[DaypartingWindow]
    wednesday: List[DaypartingWindow]
    thursday: List[DaypartingWindow]
    friday: List[DaypartingWindow]
    saturday: List[DaypartingWindow]
    sunday: List[DaypartingWindow]


class Brand(TimeStampedUUIDModel):
    name: str = models.CharField(max_length=100, unique=True)
    daily_budget: Decimal = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    monthly_budget: Decimal = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    daily_spend: Decimal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    monthly_spend: Decimal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active: bool = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name

    @property
    def daily_budget_remaining(self) -> Decimal:
        return max(Decimal("0"), self.daily_budget - self.daily_spend)

    @property
    def monthly_budget_remaining(self) -> Decimal:
        return max(Decimal("0"), self.monthly_budget - self.monthly_spend)

    @property
    def daily_budget_exceeded(self) -> bool:
        return self.daily_spend >= self.daily_budget

    @property
    def monthly_budget_exceeded(self) -> bool:
        return self.monthly_spend >= self.monthly_budget

    class Meta:
        ordering: List[str] = ["name"]


class Campaign(TimeStampedUUIDModel):
    brand: Brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="campaigns")
    name: str = models.CharField(max_length=200)
    status: CampaignStatus = models.CharField(
        max_length=20, choices=CampaignStatus.choices, default=CampaignStatus.ACTIVE
    )
    daily_spend: Decimal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    monthly_spend: Decimal = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    dayparting_enabled: bool = models.BooleanField(default=False)
    dayparting_schedule: DaypartingSchedule = models.JSONField(default=dict, blank=True)

    objects: CampaignManager = CampaignManager()

    def __str__(self) -> str:
        return f"{self.brand.name} - {self.name}"

    def is_within_dayparting_window(self) -> bool:
        """
        Check if current time is within allowed dayparting window
        """
        if not self.dayparting_enabled:
            return True

        now: datetime.datetime = timezone.now()
        current_day: str = now.strftime("%A").lower()
        current_time: str = now.strftime("%H:%M")

        day_schedule: List[DaypartingWindow] = self.dayparting_schedule.get(current_day, [])

        for window in day_schedule:
            if window["start"] <= current_time <= window["end"]:
                return True

        return False

    def should_be_active(self) -> bool:
        """
        Determine if campaign should be active based on all conditions
        """
        if not self.brand.is_active:
            return False

        if self.brand.daily_budget_exceeded or self.brand.monthly_budget_exceeded:
            return False

        if self.dayparting_enabled and not self.is_within_dayparting_window():
            return False

        return self.status not in [CampaignStatus.INACTIVE, CampaignStatus.PAUSED]

    def update_status(self) -> None:
        """
        Update campaign status based on current conditions
        """
        if not self.brand.is_active:
            self.status = CampaignStatus.INACTIVE
        elif self.brand.daily_budget_exceeded or self.brand.monthly_budget_exceeded:
            self.status = CampaignStatus.BUDGET_EXCEEDED
        elif self.dayparting_enabled and not self.is_within_dayparting_window():
            self.status = CampaignStatus.DAYPARTING_PAUSED
        elif self.status in [CampaignStatus.BUDGET_EXCEEDED, CampaignStatus.DAYPARTING_PAUSED]:
            self.status = CampaignStatus.ACTIVE

        self.save(update_fields=["status", "updated_at"])

    class Meta:
        ordering: List[str] = ["brand__name", "name"]
        unique_together: List[tuple[str, str]] = [("brand", "name")]


class AdSpend(models.Model):
    campaign: Campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="spends")
    amount: Decimal = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    timestamp: datetime.datetime = models.DateTimeField(auto_now_add=True)
    description: str = models.CharField(max_length=500, blank=True)

    objects: AdSpendManager = AdSpendManager()

    def save(self, *args: Any, **kwargs: Any) -> None:
        is_new: bool = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            self.update_spend_totals()

    def update_spend_totals(self) -> None:
        """
        Update daily and monthly spend totals for campaign and brand
        """
        today: datetime.date = timezone.now().date()
        current_month: datetime.date = timezone.now().replace(day=1).date()

        daily_total: Optional[Decimal] = AdSpend.objects.filter(
            campaign=self.campaign, timestamp__date=today
        ).aggregate(total=Sum("amount"))["total"]
        daily_total = daily_total or Decimal("0")

        monthly_total: Optional[Decimal] = AdSpend.objects.filter(
            campaign=self.campaign, timestamp__date__gte=current_month
        ).aggregate(total=Sum("amount"))["total"]
        monthly_total = monthly_total or Decimal("0")

        self.campaign.daily_spend = daily_total
        self.campaign.monthly_spend = monthly_total
        self.campaign.save(update_fields=["daily_spend", "monthly_spend", "updated_at"])

        brand_daily_total: Optional[Decimal] = AdSpend.objects.filter(
            campaign__brand=self.campaign.brand, timestamp__date=today
        ).aggregate(total=Sum("amount"))["total"]
        brand_daily_total = brand_daily_total or Decimal("0")

        brand_monthly_total: Optional[Decimal] = AdSpend.objects.filter(
            campaign__brand=self.campaign.brand, timestamp__date__gte=current_month
        ).aggregate(total=Sum("amount"))["total"]
        brand_monthly_total = brand_monthly_total or Decimal("0")

        self.campaign.brand.daily_spend = brand_daily_total
        self.campaign.brand.monthly_spend = brand_monthly_total
        self.campaign.brand.save(update_fields=["daily_spend", "monthly_spend", "updated_at"])

    def __str__(self) -> str:
        return f"{self.campaign} - ${self.amount} on {self.timestamp.date()}"

    class Meta:
        ordering: List[str] = ["-timestamp"]
