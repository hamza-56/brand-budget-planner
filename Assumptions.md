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