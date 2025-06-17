from __future__ import annotations

import datetime

from django.db import models


class CampaignQuerySet(models.QuerySet["Campaign"]):
    def active(self) -> CampaignQuerySet:
        return self.filter(status="active", brand__is_active=True)

    def with_brand(self) -> CampaignQuerySet:
        return self.select_related("brand")


class CampaignManager(models.Manager["Campaign"]):
    def get_queryset(self) -> CampaignQuerySet:
        return CampaignQuerySet(self.model, using=self._db)

    def active(self) -> CampaignQuerySet:
        return self.get_queryset().active()


class AdSpendQuerySet(models.QuerySet["AdSpend"]):
    def for_date(self, date: datetime.date) -> AdSpendQuerySet:
        return self.filter(timestamp__date=date)

    def for_month(self, month_start: datetime.date) -> AdSpendQuerySet:
        return self.filter(timestamp__date__gte=month_start)


class AdSpendManager(models.Manager["AdSpend"]):
    def get_queryset(self) -> AdSpendQuerySet:
        return AdSpendQuerySet(self.model, using=self._db)
