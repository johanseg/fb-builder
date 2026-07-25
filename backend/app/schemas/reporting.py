from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel


class ReportingPolicy(BaseModel):
    lookback_days: int | None = None
    min_spend: Decimal | None = None
    break_even_roas: Decimal | None = None
    scale_roas: Decimal | None = None
    min_purchases: int | None = None


class ReportingRecommendation(BaseModel):
    meta_ad_id: str
    ad_name: str | None = None
    campaign_name: str | None = None
    adset_name: str | None = None
    currency: str
    spend: Decimal
    purchases: Decimal
    purchase_value: Decimal
    roas: Decimal | None = None
    status: str
    reason: str


class ReportingSummary(BaseModel):
    currency: str
    spend: Decimal
    impressions: int
    clicks: int
    purchases: Decimal
    purchase_value: Decimal
    ctr: Decimal | None = None
    cpm: Decimal | None = None
    roas: Decimal | None = None


class ReportingResponse(BaseModel):
    brand_id: str
    date_from: date
    date_to: date
    partial: bool
    coverage: dict[str, Any]
    summaries: list[ReportingSummary]
    recommendations: list[ReportingRecommendation]


class SyncRunResponse(BaseModel):
    id: str
    account_id: str
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    lookback_days: int | None = None
    totals: dict[str, Any] | None = None
    error: str | None = None
