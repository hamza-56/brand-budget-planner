# Ad Campaign Budget Management System

A Django-based backend system for managing advertising campaign budgets with automatic budget enforcement, dayparting schedules, and spend tracking.

## Features

- **Budget Management**: Track daily and monthly spend limits for brands and campaigns
- **Automatic Campaign Control**: Pause/resume campaigns based on budget constraints
- **Dayparting**: Schedule campaigns to run only during specified time windows
- **Real-time Monitoring**: Celery-based periodic tasks for budget enforcement
- **Admin Interface**: Django admin panel for managing brands, campaigns, and spend records

## System Architecture

### Data Models

#### Brand

- Represents an advertising client/brand
- Has daily and monthly budget limits
- Tracks current spend totals
- Can be activated/deactivated

#### Campaign

- Belongs to a Brand (many-to-one relationship)
- Has status (active, paused, budget_exceeded, dayparting_paused, inactive)
- Supports dayparting schedules stored as JSON
- Tracks daily and monthly spend

#### AdSpend

- Individual spend transactions
- Belongs to a Campaign (many-to-one relationship)
- Automatically updates campaign and brand spend totals on creation

### System Workflow

```
AdSpend Created → Update Campaign/Brand Totals → Check Budget Limits → Update Campaign Status
     ↓
Celery Tasks (Every 5-15 minutes):
- check_and_update_campaign_statuses()
- recalculate_spend_totals()
- monitor_budget_limits()

Daily (00:00 UTC):
- reset_daily_budgets()

Monthly (1st day, 00:00 UTC):
- reset_monthly_budgets()
```

## Setup Instructions

### Prerequisites

- Python 3.8+
- PostgreSQL (recommended) or SQLite for development
- Redis (for Celery broker)

### Installation

1. **Clone the repository**

```bash
git clone <repository-url>
cd ad-campaign-system
```

2. **Create virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Environment Configuration**
   Create a `.env` file in the project root:

```env
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:password@localhost/ad_campaign_db
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

5. **Database Setup**

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### Running the Application

1. **Start Django Development Server**

```bash
python manage.py runserver
```

2. **Start Celery Worker**

```bash
celery -A brand_budget_planner worker --loglevel=info
```

3. **Start Celery Beat (Scheduler)**

```bash
celery -A brand_budget_planner beat --loglevel=info
```

4. **Access the Application**

- Django Admin: http://localhost:8000/admin/

## Management Commands

### Reset Daily Budgets

```bash
python manage.py reset_daily_budgets
python manage.py reset_daily_budgets --dry-run  # Preview changes
```

### Reset Monthly Budgets

```bash
python manage.py reset_monthly_budgets
python manage.py reset_monthly_budgets --dry-run  # Preview changes
```

## Celery Tasks

The system includes several automated tasks:

- **check_and_update_campaign_statuses**: Runs every 5 minutes to update campaign statuses based on budgets and dayparting
- **recalculate_spend_totals**: Runs every 10 minutes to ensure spend totals are accurate
- **reset_daily_budgets**: Runs daily at midnight to reset daily spend counters
- **reset_monthly_budgets**: Runs on the 1st of each month to reset monthly spend counters
- **monitor_budget_limits**: Runs every 15 minutes to generate budget alerts

## Dayparting Configuration

Dayparting schedules are stored as JSON in the following format:

```json
{
    "monday": [
        {"start": "09:00", "end": "17:00"},
        {"start": "19:00", "end": "22:00"}
    ],
    "tuesday": [
        {"start": "09:00", "end": "17:00"}
    ],
    "wednesday": [],
    "thursday": [
        {"start": "10:00", "end": "16:00"}
    ],
    "friday": [
        {"start": "09:00", "end": "17:00"}
    ],
    "saturday": [
        {"start": "10:00", "end": "14:00"}
    ],
    "sunday": []
}
```

## System States and Transitions

### Campaign Status States

- **active**: Campaign is running normally
- **paused**: Manually paused by user
- **budget_exceeded**: Paused due to budget limits
- **dayparting_paused**: Paused due to dayparting schedule
- **inactive**: Brand is inactive

### Status Transition Logic

```
active → budget_exceeded (when budget exceeded)
active → dayparting_paused (when outside dayparting window)
budget_exceeded → active (when budgets reset)
dayparting_paused → active (when entering dayparting window)
```

## Monitoring and Alerts

The system provides budget monitoring with configurable thresholds:

- **Daily Budget Warning**: Triggered at 90% of daily budget
- **Monthly Budget Warning**: Triggered at 90% of monthly budget
- **Campaign Status Changes**: Logged for audit purposes

## Assumptions and Simplifications

### 1. Front-End and API

- No front-end or API is required for interacting with the system.
- Brands and Campaigns are added and managed via the Django admin interface.

### 2. Time Zone Handling

- All times are stored and processed in UTC
- Dayparting windows are assumed to be in the same timezone as the server
- No support for brand-specific timezones

### 3. Budget Enforcement

- Budgets are enforced at the brand level, not individual campaigns
- Spend tracking is based on when transactions are recorded, not actual ad delivery time
- No support for budget rollover between periods

### 4. Data Consistency

- AdSpend records are immutable once created
- Spend totals are recalculated periodically via Celery tasks
- Race conditions during high-volume spend recording are handled through database transactions

### 5. Dayparting

- Dayparting schedules support multiple windows per day
- No support for different schedules for different campaigns under the same brand
- Timezone considerations are simplified (server timezone only)

### 6. Performance

- System is optimized for moderate scale (hundreds of brands, thousands of campaigns)
- Database queries use select_related() for common operations
- Spend calculations are cached in model fields for performance

### 7. Error Handling

- Failed Celery tasks are logged but don't stop the system
- Invalid spend records are rejected with appropriate error messages
- System gracefully handles missing or corrupted dayparting data

### 8. Testing
- No test cases are required at this stage of development.

### Common Issues

1. **Celery tasks not running**

   - Check Redis connection
   - Verify beat schedule configuration
   - Check worker logs for errors

2. **Spend totals incorrect**

   - Run `recalculate_spend_totals` task manually
   - Check for AdSpend records with invalid amounts
   - Verify time zone settings

3. **Campaigns not activating after budget reset**
   - Check brand active status
   - Verify dayparting configuration
   - Check campaign status update logic

### Debug Commands

```bash
# Check Celery task status
celery -A brand_budget_planner inspect active

# Manually run budget recalculation
python manage.py shell -c "from brand_budget_planner.tasks import recalculate_spend_totals; recalculate_spend_totals()"

# Check campaign statuses
python manage.py shell -c "from brand_budget_planner.models import Campaign; print([(c.name, c.status) for c in Campaign.objects.all()])"
```
