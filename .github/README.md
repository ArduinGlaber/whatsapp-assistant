# GitHub Actions Configuration

## Required Secrets

Configure these secrets in your repository settings at `Settings → Secrets and variables → Actions`:

| Secret Name | Description |
|-------------|-------------|
| `FACEBOOK_EMAIL` | Email address for Facebook account |
| `FACEBOOK_PASSWORD` | Password for Facebook account |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token (optional, for notifications) |

### Adding Secrets

```bash
# Using GitHub CLI
gh secret set FACEBOOK_EMAIL --body "your-email@example.com"
gh secret set FACEBOOK_PASSWORD --body "your-password"
gh secret set TELEGRAM_BOT_TOKEN --body "your-bot-token"

# Or via Web UI:
# Repository → Settings → Secrets and variables → Actions → New repository secret
```

## Workflow Behavior

### Schedule
- Runs at **8:00 AM** and **8:00 PM Cuba time** (UTC-5)
- This equals **13:00** and **21:00 UTC**

### Manual Trigger
- Go to **Actions** tab → **Scrape Facebook Marketplace** → **Run workflow**

### Process Flow
1. Checkout latest code
2. Set up Python 3.11
3. Install dependencies from `scraper/requirements.txt`
4. Run scraper with credentials from secrets
5. Create/update `v1.0.0` release with `listings.db`

### Error Handling
- If Facebook login fails → workflow exits with error
- If no database is created → no release is published
- Release is only created/updated when database exists

## Troubleshooting

### Login Failures
If the scraper fails to login:
1. Check that credentials are correct in secrets
2. Facebook may require additional verification
3. Consider using app passwords for 2FA-enabled accounts

### No Posts Scraped
- Verify the group ID is correct
- Check if the group is still accessible with the account
- Facebook may have rate-limited the account

### Database Not Uploaded
The workflow checks for database existence before creating a release. If the database file doesn't exist, no release will be created.
