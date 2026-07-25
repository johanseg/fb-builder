from datetime import date, datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from app.models import Brand, BrandAdAccount, MetaInsightDaily
from app.services.meta_reporting_service import MetaReportingService


class FakeAccount:
    def __init__(self, mismatch=False):
        self.mismatch = mismatch

    def get_insights(self, fields, params):
        del fields
        day = params["time_range"]["until"]
        if params["level"] == "account":
            return [{"date_start": day, "spend": "13.50" if self.mismatch else "12.50", "impressions": "100", "clicks": "5", "actions": [{"action_type": "purchase", "value": "1"}], "action_values": [{"action_type": "purchase", "value": "25"}]}]
        return [{"ad_id": "meta-ad-1", "ad_name": "Control", "campaign_name": "Campaign", "adset_name": "Ad set", "date_start": day, "spend": "12.50", "impressions": "100", "clicks": "5", "actions": [{"action_type": "purchase", "value": "1"}], "action_values": [{"action_type": "purchase", "value": "25"}]}]


class FakeFacebook:
    def __init__(self, mismatch=False):
        self.mismatch = mismatch

    def _get_account(self, account_id):
        assert account_id in {"act_123", "act_456"}
        return FakeAccount(self.mismatch)

    def get_ad_accounts(self):
        return [{"id": "act_123", "currency": "USD"}]


def test_meta_sync_is_ad_day_idempotent_and_reconciled(db_session, monkeypatch):
    monkeypatch.setenv("ALLOWED_FB_ACCOUNTS", "123")
    brand = Brand(name="Reporting test", lookback_days=35, min_spend=10, break_even_roas=1, scale_roas=1.5, min_purchases=1)
    db_session.add(brand)
    db_session.commit()
    account = BrandAdAccount(brand_id=brand.id, meta_account_id="act_123", currency="USD", timezone="UTC", enabled=True)
    db_session.add(account)
    db_session.commit()

    service = MetaReportingService(db_session, FakeFacebook())
    first = service.sync_account(account)
    second = service.sync_account(account)

    assert first.status == "completed"
    assert second.status == "completed"
    assert db_session.query(MetaInsightDaily).count() == 1
    report = service.report(brand.id, date.today() - timedelta(days=91), date.today())
    assert report["partial"] is False
    assert report["summaries"][0]["spend"] == 12.5
    assert report["recommendations"][0]["status"] == "SCALE"


def test_recommendations_are_observe_when_any_mapped_account_lacks_a_completed_sync(db_session, monkeypatch):
    monkeypatch.setenv("ALLOWED_FB_ACCOUNTS", "act_123,act_456")
    brand = Brand(name="Partial reporting", min_spend=1, break_even_roas=1, scale_roas=2, min_purchases=1)
    db_session.add(brand)
    db_session.commit()
    first = BrandAdAccount(brand_id=brand.id, meta_account_id="act_123", currency="USD", timezone="UTC", enabled=True)
    second = BrandAdAccount(brand_id=brand.id, meta_account_id="act_456", currency="USD", timezone="UTC", enabled=True)
    db_session.add_all([first, second])
    db_session.commit()
    MetaReportingService(db_session, FakeFacebook()).sync_account(first)

    report = MetaReportingService(db_session, FakeFacebook()).report(brand.id, date.today() - timedelta(days=91), date.today())
    assert report["partial"] is True
    assert report["recommendations"][0]["status"] == "OBSERVE"


def test_window_uses_account_timezone_and_initial_lookback(db_session):
    brand = Brand(name="Timezone reporting")
    db_session.add(brand)
    db_session.commit()
    account = BrandAdAccount(brand_id=brand.id, meta_account_id="act_123", currency="USD", timezone="America/Los_Angeles", enabled=True)
    db_session.add(account)
    db_session.commit()

    start, end, lookback = MetaReportingService(db_session, FakeFacebook())._window(account, brand)

    assert lookback == 90
    assert end == datetime.now(ZoneInfo("America/Los_Angeles")).date() - timedelta(days=1)
    assert start == end - timedelta(days=89)


def test_reconciliation_mismatch_marks_sync_partial_and_suppresses_recommendations(db_session, monkeypatch):
    monkeypatch.setenv("ALLOWED_FB_ACCOUNTS", "act_123")
    brand = Brand(name="Mismatch reporting", min_spend=1, break_even_roas=1, scale_roas=2, min_purchases=1)
    db_session.add(brand)
    db_session.commit()
    account = BrandAdAccount(brand_id=brand.id, meta_account_id="act_123", currency="USD", timezone="UTC", enabled=True)
    db_session.add(account)
    db_session.commit()

    run = MetaReportingService(db_session, FakeFacebook(mismatch=True)).sync_account(account)

    assert run.status == "partial"
    report = MetaReportingService(db_session, FakeFacebook()).report(brand.id, date.today() - timedelta(days=91), date.today())
    assert report["partial"] is True
    assert report["recommendations"][0]["status"] == "OBSERVE"


def test_mapping_accessibility_requires_both_allowlist_and_meta_access(db_session, monkeypatch):
    monkeypatch.setenv("ALLOWED_FB_ACCOUNTS", "act_123")
    service = MetaReportingService(db_session, FakeFacebook())

    assert service.accessible_account("123")["currency"] == "USD"


def test_summaries_do_not_mix_currencies(db_session):
    rows = [
        SimpleNamespace(currency="USD", spend=10, impressions=100, clicks=10, actions=[], purchase_value=20),
        SimpleNamespace(currency="EUR", spend=12, impressions=120, clicks=12, actions=[], purchase_value=24),
    ]

    summaries = MetaReportingService(db_session, FakeFacebook())._summaries(rows)

    assert {summary["currency"] for summary in summaries} == {"USD", "EUR"}
    assert {summary["spend"] for summary in summaries} == {10, 12}
