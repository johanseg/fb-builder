# Railway deployment and reporting runbook

Production reporting is read-only against Meta: it stores daily ad Insights and produces KILL, SCALE, or OBSERVE recommendations. It never changes a campaign, budget, ad set, or ad status.

## Required variables

- `FACEBOOK_ACCESS_TOKEN` stays server-side; never expose Facebook credentials in frontend build variables.
- `ALLOWED_FB_ACCOUNTS` is a comma-separated list of normalized `act_` IDs. The database mapping cannot extend this list.
- Configure R2 completely before running `backend/scripts/migrate_local_uploads_to_r2.py --apply`.

## Release order

1. Apply the reporting Alembic migration in the controlled Railway pre-deploy phase. Web and worker startup must not mutate schema or run `init_db.py` schema checks.
2. Set the staging allowlist and map only its account as an admin in Settings. Mapping verifies the configured server token can read the account.
3. Create a Railway Cron service from `backend/railway.reporting.toml`. The initial successful sync collects 90 completed account-local days; later runs use the brand policy, defaulting to 35 completed days. Admins and managers may also use the authenticated manual sync control.
4. Reconcile the sync-run account totals to stored ad-day totals before using recommendations. Any failed or mismatched mapped account makes the report partial and suppresses recommendations.
5. Repeat on production with a separately confirmed production allowlist. Verify the deployed SHA, service logs, migration revision, and health endpoint before declaring it ready.

Manual post-deploy verification requires the exact deployed SHA; the workflow rejects a healthy instance whose `/health` `commit_sha` does not match it.

## Legacy media migration

`python backend/scripts/migrate_local_uploads_to_r2.py` is dry-run only. It inventories only managed `/uploads/...` references from generated ads, Facebook ads, winning ads, AI personas, brand-scrape media, and product shots; external landing-page and website fields are intentionally excluded. It reports source size/SHA-256, verified R2 size/SHA-256 when configured, and a separate exception manifest. `--apply` copies verified files to configured R2 and updates their references only after verification, but never deletes local files. Review the JSON manifest before any separately authorized cleanup.
