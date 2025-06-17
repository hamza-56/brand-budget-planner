from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import SafeString

from .models import AdSpend, Brand, Campaign


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display: List[str] = [
        "name",
        "daily_budget",
        "daily_spend",
        "daily_remaining",
        "monthly_budget",
        "monthly_spend",
        "monthly_remaining",
        "is_active",
    ]
    list_filter: List[str] = ["is_active", "created_at"]
    search_fields: List[str] = ["name"]
    readonly_fields: List[str] = ["daily_spend", "monthly_spend", "created_at", "updated_at"]

    def daily_remaining(self, obj: Brand) -> SafeString:
        remaining: Decimal = obj.daily_budget_remaining
        color: str = "red" if remaining <= 0 else "green"
        return format_html(f'<span style="color: {color};">${remaining}</span>')

    daily_remaining.short_description = "Daily Remaining"

    def monthly_remaining(self, obj: Brand) -> SafeString:
        remaining: Decimal = obj.monthly_budget_remaining
        color: str = "red" if remaining <= 0 else "green"
        return format_html(f'<span style="color: {color};">${remaining}</span>')

    monthly_remaining.short_description = "Monthly Remaining"


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display: List[str] = [
        "name",
        "brand",
        "status",
        "daily_spend",
        "monthly_spend",
        "dayparting_enabled",
        "within_dayparting",
    ]
    list_filter: List[str] = ["status", "dayparting_enabled", "brand", "created_at"]
    search_fields: List[str] = ["name", "brand__name"]
    readonly_fields: List[str] = ["daily_spend", "monthly_spend", "created_at", "updated_at"]

    fieldsets: tuple[tuple[Optional[str], Dict[str, Any]], ...] = (
        (None, {"fields": ("brand", "name", "status")}),
        ("Spend Information", {"fields": ("daily_spend", "monthly_spend"), "classes": ("collapse",)}),
        (
            "Dayparting",
            {
                "fields": ("dayparting_enabled", "dayparting_schedule"),
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def within_dayparting(self, obj: Campaign) -> Union[str, SafeString]:
        if not obj.dayparting_enabled:
            return "N/A"
        within: bool = obj.is_within_dayparting_window()
        color: str = "green" if within else "red"
        return format_html(f'<span style="color: {color};">{"Yes" if within else "No"}</span>')

    within_dayparting.short_description = "Within Dayparting Window"


@admin.register(AdSpend)
class AdSpendAdmin(admin.ModelAdmin):
    list_display: List[str] = ["campaign", "amount", "timestamp", "description"]
    list_filter: List[str] = ["campaign__brand", "campaign", "timestamp"]
    search_fields: List[str] = ["campaign__name", "campaign__brand__name", "description"]
    date_hierarchy: str = "timestamp"
    readonly_fields: List[str] = ["timestamp"]
