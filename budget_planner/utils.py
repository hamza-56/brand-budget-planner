import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, TypedDict, Union

from django.db.models import QuerySet
from django.utils import timezone

from .models import AdSpend, Brand, Campaign


class BudgetStatusSummary(TypedDict):
    total_brands: int
    active_brands: int
    daily_budget_exceeded: int
    monthly_budget_exceeded: int
    total_daily_spend: float
    total_monthly_spend: float
    total_daily_budget: float
    total_monthly_budget: float


def record_ad_spend(campaign_id: int, amount: Union[str, int, float, Decimal], description: str = "") -> AdSpend:
    """
    Helper function to record ad spend
    """
    try:
        campaign: Campaign = Campaign.objects.get(id=campaign_id)
        spend: AdSpend = AdSpend.objects.create(campaign=campaign, amount=Decimal(str(amount)), description=description)

        # Check if this spend causes budget to be exceeded
        campaign.refresh_from_db()
        campaign.update_status()

        return spend
    except Campaign.DoesNotExist:
        raise ValueError(f"Campaign with id {campaign_id} does not exist")


def get_active_campaigns() -> QuerySet[Campaign]:
    """
    Get all currently active campaigns
    """
    return Campaign.objects.filter(status="active", brand__is_active=True).select_related("brand")


def get_budget_status_summary() -> BudgetStatusSummary:
    """
    Get summary of budget status across all brands
    """
    brands: QuerySet[Brand] = Brand.objects.all()
    summary: BudgetStatusSummary = {
        "total_brands": brands.count(),
        "active_brands": brands.filter(is_active=True).count(),
        "daily_budget_exceeded": 0,
        "monthly_budget_exceeded": 0,
        "total_daily_spend": 0.0,
        "total_monthly_spend": 0.0,
        "total_daily_budget": 0.0,
        "total_monthly_budget": 0.0,
    }

    for brand in brands:
        if brand.daily_budget_exceeded:
            summary["daily_budget_exceeded"] += 1
        if brand.monthly_budget_exceeded:
            summary["monthly_budget_exceeded"] += 1

        summary["total_daily_spend"] += float(brand.daily_spend)
        summary["total_monthly_spend"] += float(brand.monthly_spend)
        summary["total_daily_budget"] += float(brand.daily_budget)
        summary["total_monthly_budget"] += float(brand.monthly_budget)

    return summary
