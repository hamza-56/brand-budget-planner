import datetime
from decimal import Decimal
from typing import Any, Dict

from django.core.management.base import BaseCommand, CommandParser
from django.db.models import QuerySet, Sum
from django.utils import timezone

from brand_budget_planner.choices import CampaignStatus
from brand_budget_planner.models import Brand, Campaign


class Command(BaseCommand):
    help: str = "Reset monthly budgets and reactivate eligible campaigns"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be reset without making changes",
        )

    def handle(self, *args: Any, **options: Dict[str, Any]) -> None:
        current_month: datetime.date = timezone.now().replace(day=1).date()
        dry_run: bool = options.get("dry_run", False)

        if dry_run:
            self.stdout.write("DRY RUN MODE - No changes will be made")

        if not dry_run:
            brands_updated: int = Brand.objects.update(monthly_spend=Decimal("0"))
            campaigns_updated: int = Campaign.objects.update(monthly_spend=Decimal("0"))
        else:
            brands_updated = Brand.objects.count()
            campaigns_updated = Campaign.objects.count()

        self.stdout.write(
            f"{'Would reset' if dry_run else 'Reset'} monthly spend for "
            f"{brands_updated} brands and {campaigns_updated} campaigns"
        )

        campaigns: QuerySet[Campaign] = Campaign.objects.all()
        reactivated_count: int = 0

        for campaign in campaigns:
            old_status: str = campaign.status
            if not dry_run:
                campaign.update_status()

            if old_status == CampaignStatus.BUDGET_EXCEEDED and (
                not dry_run and campaign.status == CampaignStatus.ACTIVE or dry_run and campaign.should_be_active()
            ):
                reactivated_count += 1

        self.stdout.write(f"{'Would reactivate' if dry_run else 'Reactivated'} {reactivated_count} campaigns")

        if not dry_run:
            self.stdout.write(self.style.SUCCESS("Monthly budget reset completed successfully"))
        else:
            self.stdout.write(self.style.WARNING("DRY RUN completed - no changes made"))
