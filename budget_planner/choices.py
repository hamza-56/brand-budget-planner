from django.db import models


class CampaignStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    PAUSED = "paused", "Paused"
    BUDGET_EXCEEDED = "budget_exceeded", "Budget Exceeded"
    DAYPARTING_PAUSED = "dayparting_paused", "Dayparting Paused"
    INACTIVE = "inactive", "Inactive"
