import datetime
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, TypedDict

from celery import shared_task
from django.core.management import call_command
from django.db.models import QuerySet, Sum
from django.utils import timezone

from .models import AdSpend, Brand, Campaign

logger: logging.Logger = logging.getLogger(__name__)


class StatusChanges(TypedDict):
    activated: int
    budget_paused: int
    dayparting_paused: int
    deactivated: int


class BudgetAlert(TypedDict):
    type: str
    brand: str
    percent_used: float
    spend: float
    budget: float


@shared_task
def check_and_update_campaign_statuses() -> StatusChanges:
    """Check all campaigns and update their statuses based on budgets and dayparting"""
    campaigns: QuerySet[Campaign] = Campaign.objects.select_related("brand").all()

    status_changes: StatusChanges = {"activated": 0, "budget_paused": 0, "dayparting_paused": 0, "deactivated": 0}

    for campaign in campaigns:
        old_status: str = campaign.status
        campaign.update_status()

        # Track status changes for reporting
        if old_status != campaign.status:
            if campaign.status == Campaign.STATUS_ACTIVE:
                status_changes["activated"] += 1
            elif campaign.status == Campaign.STATUS_BUDGET_EXCEEDED:
                status_changes["budget_paused"] += 1
            elif campaign.status == Campaign.STATUS_DAYPARTING_PAUSED:
                status_changes["dayparting_paused"] += 1
            elif campaign.status == Campaign.STATUS_INACTIVE:
                status_changes["deactivated"] += 1

    logger.info(f"Campaign status update completed: {status_changes}")
    return status_changes


@shared_task
def recalculate_spend_totals() -> str:
    """
    Recalculate daily and monthly spend totals for all brands and campaigns
    """
    today: datetime.date = timezone.now().date()
    current_month: datetime.date = timezone.now().replace(day=1).date()

    # Update campaign totals
    campaigns: QuerySet[Campaign] = Campaign.objects.all()
    for campaign in campaigns:
        daily_total: Optional[Decimal] = AdSpend.objects.filter(campaign=campaign, timestamp__date=today).aggregate(
            total=Sum("amount")
        )["total"]
        daily_total = daily_total or Decimal("0")

        monthly_total: Optional[Decimal] = AdSpend.objects.filter(
            campaign=campaign, timestamp__date__gte=current_month
        ).aggregate(total=Sum("amount"))["total"]
        monthly_total = monthly_total or Decimal("0")

        campaign.daily_spend = daily_total
        campaign.monthly_spend = monthly_total
        campaign.save(update_fields=["daily_spend", "monthly_spend", "updated_at"])

    # Update brand totals
    brands: QuerySet[Brand] = Brand.objects.all()
    for brand in brands:
        daily_total: Optional[Decimal] = AdSpend.objects.filter(campaign__brand=brand, timestamp__date=today).aggregate(
            total=Sum("amount")
        )["total"]
        daily_total = daily_total or Decimal("0")

        monthly_total: Optional[Decimal] = AdSpend.objects.filter(
            campaign__brand=brand, timestamp__date__gte=current_month
        ).aggregate(total=Sum("amount"))["total"]
        monthly_total = monthly_total or Decimal("0")

        brand.daily_spend = daily_total
        brand.monthly_spend = monthly_total
        brand.save(update_fields=["daily_spend", "monthly_spend", "updated_at"])

    logger.info("Spend totals recalculation completed")
    return "Spend totals recalculation completed"


@shared_task
def reset_daily_budgets() -> str:
    """
    Reset daily budgets at start of new day
    """
    try:
        call_command("reset_daily_budgets")
        logger.info("Daily budget reset completed successfully")
        return "Daily budget reset completed"
    except Exception as e:
        logger.error(f"Daily budget reset failed: {str(e)}")
        raise


@shared_task
def reset_monthly_budgets() -> str:
    """
    Reset monthly budgets at start of new month
    """
    try:
        call_command("reset_monthly_budgets")
        logger.info("Monthly budget reset completed successfully")
        return "Monthly budget reset completed"
    except Exception as e:
        logger.error(f"Monthly budget reset failed: {str(e)}")
        raise


@shared_task
def monitor_budget_limits() -> List[BudgetAlert]:
    """
    Monitor and alert on budget limits
    """
    today: datetime.date = timezone.now().date()
    alerts: List[BudgetAlert] = []

    # Check brands approaching daily limits (90% threshold)
    brands: QuerySet[Brand] = Brand.objects.filter(is_active=True)
    for brand in brands:
        if brand.daily_spend >= brand.daily_budget * Decimal("0.9"):
            percent_used: float = float(brand.daily_spend / brand.daily_budget * 100) if brand.daily_budget > 0 else 0
            alerts.append(
                {
                    "type": "daily_budget_warning",
                    "brand": brand.name,
                    "percent_used": percent_used,
                    "spend": float(brand.daily_spend),
                    "budget": float(brand.daily_budget),
                }
            )

    # Check brands approaching monthly limits (90% threshold)
    for brand in brands:
        if brand.monthly_spend >= brand.monthly_budget * Decimal("0.9"):
            percent_used: float = (
                float(brand.monthly_spend / brand.monthly_budget * 100) if brand.monthly_budget > 0 else 0
            )
            alerts.append(
                {
                    "type": "monthly_budget_warning",
                    "brand": brand.name,
                    "percent_used": percent_used,
                    "spend": float(brand.monthly_spend),
                    "budget": float(brand.monthly_budget),
                }
            )

    if alerts:
        logger.warning(f"Budget alerts generated: {alerts}")

    return alerts
