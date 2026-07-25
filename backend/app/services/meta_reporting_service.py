"""Read-only Meta Insights sync and reporting helpers."""

from __future__ import annotations

import os
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Brand, BrandAdAccount, MetaInsightDaily, MetaSyncRun
if TYPE_CHECKING:
    from app.services.facebook_service import FacebookService


DEFAULT_LOOKBACK_DAYS = 35
INITIAL_LOOKBACK_DAYS = 90
logger = logging.getLogger(__name__)


def decimal(value) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def normalized_account_id(value: str) -> str:
    return value if value.startswith("act_") else f"act_{value}"


def allowed_account_ids() -> set[str]:
    raw = os.getenv("ALLOWED_FB_ACCOUNTS", "")
    return {normalized_account_id(value.strip()) for value in raw.split(",") if value.strip()}


def _action_total(actions, action_types: set[str]) -> Decimal:
    return sum(
        (decimal(action.get("value")) for action in (actions or []) if action.get("action_type") in action_types),
        Decimal("0"),
    )


class MetaReportingService:
    """Persist daily ad insight rows and derive read-only recommendations."""

    def __init__(self, db: Session, facebook_service: Any = None):
        self.db = db
        self.facebook = facebook_service

    def _facebook(self) -> Any:
        if self.facebook is None:
            from app.services.facebook_service import FacebookService
            self.facebook = FacebookService()
        return self.facebook

    def accessible_account(self, meta_account_id: str) -> dict:
        """Confirm the server token can read an allowlisted account before mapping it."""
        account_id = normalized_account_id(meta_account_id)
        if account_id not in allowed_account_ids():
            raise ValueError("Account is not present in ALLOWED_FB_ACCOUNTS")
        for account in self._facebook().get_ad_accounts():
            if normalized_account_id(account.get("id", "")) == account_id:
                return account
        raise ValueError("Account is not accessible with the configured Meta token")

    def _window(self, account: BrandAdAccount, brand: Brand) -> tuple[date, date, int]:
        try:
            today = datetime.now(ZoneInfo(account.timezone or "UTC")).date()
        except ZoneInfoNotFoundError:
            today = datetime.now(timezone.utc).date()
        latest = self.db.query(func.max(MetaInsightDaily.date_start)).filter(
            MetaInsightDaily.brand_ad_account_id == account.id
        ).scalar()
        lookback = INITIAL_LOOKBACK_DAYS if latest is None else (brand.lookback_days or DEFAULT_LOOKBACK_DAYS)
        lookback = max(1, int(lookback))
        end = today - timedelta(days=1)  # completed account-local days only
        return end - timedelta(days=lookback - 1), end, lookback

    def sync_account(self, account: BrandAdAccount) -> MetaSyncRun:
        """Use Meta GET Insights only; the SDK cursor paginates every result page."""
        allowed = allowed_account_ids()
        meta_account_id = normalized_account_id(account.meta_account_id)
        if not allowed or meta_account_id not in allowed:
            raise ValueError("Account is not present in ALLOWED_FB_ACCOUNTS")
        brand = self.db.query(Brand).filter(Brand.id == account.brand_id).one()
        start, end, lookback = self._window(account, brand)
        run = MetaSyncRun(
            brand_ad_account_id=account.id,
            status="running",
            started_at=datetime.now(timezone.utc),
            scope="ad_daily",
            lookback_days=lookback,
            totals={},
        )
        self.db.add(run)
        self.db.commit()
        try:
            ad_rows = list(self._get_ad_rows(meta_account_id, start, end))
            account_rows = list(self._get_account_rows(meta_account_id, start, end))
            stored = self._store_rows(account, run, ad_rows)
            reconciliation = self._reconcile(ad_rows, account_rows)
            run.status = "completed" if reconciliation["matched"] else "partial"
            run.completed_at = datetime.now(timezone.utc)
            run.totals = {"ad_rows": stored, "reconciliation": reconciliation}
            self.db.commit()
            return run
        except Exception as error:
            self.db.rollback()
            run.status = "failed"
            run.completed_at = datetime.now(timezone.utc)
            run.error = str(error)
            self.db.add(run)
            self.db.commit()
            raise

    def sync_enabled_accounts(self) -> list[MetaSyncRun]:
        runs = []
        for account in self.db.query(BrandAdAccount).filter(BrandAdAccount.enabled.is_(True)).all():
            try:
                runs.append(self.sync_account(account))
            except Exception:
                logger.exception("Meta reporting sync failed for account %s", account.id)
                runs.append(self.db.query(MetaSyncRun).filter_by(brand_ad_account_id=account.id).order_by(MetaSyncRun.started_at.desc()).first())
        return runs

    def sync_brand(self, brand_id: str) -> list[MetaSyncRun]:
        accounts = self.db.query(BrandAdAccount).filter_by(brand_id=brand_id, enabled=True).all()
        if not accounts:
            raise ValueError("Brand has no enabled Meta account mappings")
        runs = []
        for account in accounts:
            try:
                runs.append(self.sync_account(account))
            except Exception:
                logger.exception("Meta reporting sync failed for account %s", account.id)
                runs.append(self.db.query(MetaSyncRun).filter_by(brand_ad_account_id=account.id).order_by(MetaSyncRun.started_at.desc()).first())
        return runs

    def _get_ad_rows(self, meta_account_id: str, start: date, end: date):
        account = self._facebook()._get_account(meta_account_id)
        return account.get_insights(
            fields=[
                "ad_id", "ad_name", "campaign_id", "campaign_name", "adset_id", "adset_name", "date_start", "spend",
                "impressions", "clicks", "actions", "action_values",
            ],
            params={"level": "ad", "time_increment": 1, "time_range": {"since": str(start), "until": str(end)}, "limit": 500},
        )

    def _get_account_rows(self, meta_account_id: str, start: date, end: date):
        account = self._facebook()._get_account(meta_account_id)
        return account.get_insights(
            fields=["date_start", "spend", "impressions", "clicks", "actions", "action_values"],
            params={"level": "account", "time_increment": 1, "time_range": {"since": str(start), "until": str(end)}, "limit": 500},
        )

    def _store_rows(self, account: BrandAdAccount, run: MetaSyncRun, rows) -> int:
        count = 0
        for value in rows:
            row = dict(value)
            if not row.get("ad_id") or not row.get("date_start"):
                continue
            insight = self.db.query(MetaInsightDaily).filter_by(
                brand_ad_account_id=account.id, meta_ad_id=row["ad_id"], date_start=date.fromisoformat(row["date_start"]),
            ).one_or_none()
            if insight is None:
                insight = MetaInsightDaily(
                    brand_ad_account_id=account.id, meta_ad_id=row["ad_id"], date_start=date.fromisoformat(row["date_start"]),
                )
                self.db.add(insight)
            actions = row.get("actions") or []
            values = row.get("action_values") or []
            insight.meta_sync_run_id = run.id
            insight.currency = account.currency
            insight.spend = decimal(row.get("spend"))
            insight.impressions = int(row.get("impressions") or 0)
            insight.clicks = int(row.get("clicks") or 0)
            insight.actions = actions
            insight.purchase_value = _action_total(values, {"purchase", "omni_purchase", "offsite_conversion.fb_pixel_purchase"})
            insight.meta_campaign_id = row.get("campaign_id")
            insight.meta_adset_id = row.get("adset_id")
            insight.campaign_name = row.get("campaign_name")
            insight.adset_name = row.get("adset_name")
            insight.ad_name = row.get("ad_name")
            insight.raw = row
            count += 1
        self.db.flush()
        return count

    def _reconcile(self, ad_rows, account_rows) -> dict:
        def totals(rows):
            return {
                "spend": sum((decimal(dict(row).get("spend")) for row in rows), Decimal("0")),
                "impressions": sum((int(dict(row).get("impressions") or 0) for row in rows), 0),
                "clicks": sum((int(dict(row).get("clicks") or 0) for row in rows), 0),
            }
        ads, accounts = totals(ad_rows), totals(account_rows)
        matched = ads == accounts
        return {"matched": matched, "ads": {key: str(value) for key, value in ads.items()}, "account": {key: str(value) for key, value in accounts.items()}}

    def report(self, brand_id: str, start: date, end: date) -> dict:
        brand = self.db.query(Brand).filter(Brand.id == brand_id).one()
        accounts = self.db.query(BrandAdAccount).filter_by(brand_id=brand_id, enabled=True).all()
        rows = self.db.query(MetaInsightDaily).join(BrandAdAccount).filter(
            BrandAdAccount.brand_id == brand_id,
            BrandAdAccount.enabled.is_(True),
            MetaInsightDaily.date_start >= start,
            MetaInsightDaily.date_start <= end,
        ).all()
        latest = {account.id: self.db.query(MetaSyncRun).filter_by(brand_ad_account_id=account.id).order_by(MetaSyncRun.started_at.desc()).first() for account in accounts}
        partial = not accounts or any(run is None or run.status != "completed" for run in latest.values())
        summaries = self._summaries(rows)
        recommendations = self._recommend(rows, brand, partial)
        return {
            "brand_id": brand_id, "date_from": start, "date_to": end, "partial": partial,
            "coverage": {"mapped_accounts": len(accounts), "completed_accounts": sum(run is not None and run.status == "completed" for run in latest.values()), "runs": {str(key): run.status if run else "missing" for key, run in latest.items()}},
            "summaries": summaries, "recommendations": recommendations,
        }

    def _summaries(self, rows):
        grouped = defaultdict(list)
        for row in rows:
            grouped[row.currency].append(row)
        output = []
        for currency, values in grouped.items():
            spend = sum((decimal(row.spend) for row in values), Decimal("0"))
            impressions = sum(row.impressions or 0 for row in values)
            clicks = sum(row.clicks or 0 for row in values)
            purchases = sum((_action_total(row.actions, {"purchase", "omni_purchase", "offsite_conversion.fb_pixel_purchase"}) for row in values), Decimal("0"))
            purchase_value = sum((decimal(row.purchase_value) for row in values), Decimal("0"))
            output.append({"currency": currency, "spend": spend, "impressions": impressions, "clicks": clicks, "purchases": purchases, "purchase_value": purchase_value, "ctr": (Decimal("100") * clicks / impressions if impressions else None), "cpm": (Decimal("1000") * spend / impressions if impressions else None), "roas": (purchase_value / spend if spend else None)})
        return output

    def _recommend(self, rows, brand: Brand, partial: bool):
        grouped = defaultdict(list)
        for row in rows:
            grouped[(row.meta_ad_id, row.currency, row.ad_name, row.campaign_name, row.adset_name)].append(row)
        results = []
        for (meta_ad_id, currency, ad_name, campaign_name, adset_name), values in grouped.items():
            spend = sum((decimal(row.spend) for row in values), Decimal("0"))
            purchases = sum((_action_total(row.actions, {"purchase", "omni_purchase", "offsite_conversion.fb_pixel_purchase"}) for row in values), Decimal("0"))
            purchase_value = sum((decimal(row.purchase_value) for row in values), Decimal("0"))
            roas = purchase_value / spend if spend else None
            minimum = decimal(brand.min_spend)
            if partial:
                status, reason = "OBSERVE", "Recommendations suppressed until every mapped account reconciles."
            elif spend < minimum:
                status, reason = "OBSERVE", "Below the brand minimum-spend threshold."
            elif purchases < int(brand.min_purchases or 0) or (roas is not None and roas < decimal(brand.break_even_roas)):
                status, reason = "KILL", "Below the brand purchase or break-even threshold."
            elif roas is not None and purchases >= int(brand.min_purchases or 0) and roas >= decimal(brand.scale_roas):
                status, reason = "SCALE", "Meets the brand purchase and scale-ROAS thresholds."
            else:
                status, reason = "OBSERVE", "Insufficient evidence for a read-only recommendation."
            results.append({"meta_ad_id": meta_ad_id, "ad_name": ad_name, "campaign_name": campaign_name, "adset_name": adset_name, "currency": currency, "spend": spend, "purchases": purchases, "purchase_value": purchase_value, "roas": roas, "status": status, "reason": reason})
        return results
