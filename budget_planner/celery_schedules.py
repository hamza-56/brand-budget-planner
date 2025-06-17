from typing import Any, Dict

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE: Dict[str, Dict[str, Any]] = {
    # Check campaign statuses every 5 minutes
    "check-campaign-statuses": {
        "task": "brand_budget_planner.tasks.check_and_update_campaign_statuses",
        "schedule": crontab(minute="*/5"),
    },
    # Recalculate spend totals every 10 minutes
    "recalculate-spend-totals": {
        "task": "brand_budget_planner.tasks.recalculate_spend_totals",
        "schedule": crontab(minute="*/10"),
    },
    # Reset daily budgets at midnight
    "reset-daily-budgets": {
        "task": "brand_budget_planner.tasks.reset_daily_budgets",
        "schedule": crontab(minute=0, hour=0),
    },
    # Reset monthly budgets on the 1st of each month at midnight
    "reset-monthly-budgets": {
        "task": "brand_budget_planner.tasks.reset_monthly_budgets",
        "schedule": crontab(minute=0, hour=0, day_of_month=1),
    },
    # Monitor budget limits every 15 minutes
    "monitor-budget-limits": {
        "task": "brand_budget_planner.tasks.monitor_budget_limits",
        "schedule": crontab(minute="*/15"),
    },
}

CELERY_TIMEZONE: str = "UTC"
