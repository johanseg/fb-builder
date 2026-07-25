from datetime import date, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import require_permission, require_role
from app.database import get_db
from app.models import Brand, BrandAdAccount, MetaSyncRun, User
from app.schemas.reporting import ReportingPolicy, ReportingResponse, SyncRunResponse
from app.services.meta_reporting_service import MetaReportingService, allowed_account_ids, normalized_account_id


router = APIRouter()


@router.get("/meta/report", response_model=ReportingResponse)
def read_meta_report(
    brand_id: str,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reporting:read")),
):
    del current_user
    end = date_to or (date.today() - timedelta(days=1))
    start = date_from or (end - timedelta(days=34))
    if start > end:
        raise HTTPException(status_code=422, detail="date_from must be on or before date_to")
    try:
        return MetaReportingService(db).report(brand_id, start, end)
    except Exception as error:
        if "No row was found" in str(error):
            raise HTTPException(status_code=404, detail="Brand not found") from error
        raise


@router.get("/meta/sync-runs", response_model=list[SyncRunResponse])
def list_meta_sync_runs(
    brand_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reporting:read")),
):
    del current_user
    rows = db.query(MetaSyncRun).join(BrandAdAccount).filter(
        BrandAdAccount.brand_id == brand_id,
    ).order_by(MetaSyncRun.started_at.desc()).limit(limit).all()
    return [
        {
            "id": row.id,
            "account_id": row.brand_ad_account_id,
            "status": row.status,
            "started_at": row.started_at,
            "completed_at": row.completed_at,
            "lookback_days": row.lookback_days,
            "totals": row.totals,
            "error": row.error,
        }
        for row in rows
    ]


@router.get("/meta/brands/{brand_id}/policy", response_model=ReportingPolicy)
def read_reporting_policy(
    brand_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reporting:read")),
):
    del current_user
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return ReportingPolicy(
        lookback_days=brand.lookback_days,
        min_spend=brand.min_spend,
        break_even_roas=brand.break_even_roas,
        scale_roas=brand.scale_roas,
        min_purchases=brand.min_purchases,
    )


@router.put("/meta/brands/{brand_id}/policy", response_model=ReportingPolicy)
def update_reporting_policy(
    brand_id: str,
    policy: ReportingPolicy,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reporting:write")),
):
    del current_user
    if policy.lookback_days is not None and policy.lookback_days < 1:
        raise HTTPException(status_code=422, detail="lookback_days must be at least 1")
    if any(value is not None and value < 0 for value in (policy.min_spend, policy.break_even_roas, policy.scale_roas)):
        raise HTTPException(status_code=422, detail="Metric thresholds cannot be negative")
    if policy.min_purchases is not None and policy.min_purchases < 0:
        raise HTTPException(status_code=422, detail="min_purchases cannot be negative")
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    for key, value in policy.model_dump().items():
        setattr(brand, key, value)
    db.commit()
    return policy


@router.get("/meta/accounts")
def list_brand_ad_accounts(
    brand_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    del current_user
    query = db.query(BrandAdAccount)
    if brand_id:
        query = query.filter(BrandAdAccount.brand_id == brand_id)
    return [
        {"id": row.id, "brand_id": row.brand_id, "meta_account_id": row.meta_account_id, "currency": row.currency, "timezone": row.timezone, "enabled": row.enabled}
        for row in query.order_by(BrandAdAccount.meta_account_id).all()
    ]


@router.post("/meta/accounts", status_code=201)
def create_brand_ad_account(
    brand_id: str,
    meta_account_id: str,
    currency: str,
    timezone: str = "UTC",
    enabled: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    del current_user
    if normalized_account_id(meta_account_id) not in allowed_account_ids():
        raise HTTPException(status_code=422, detail="Account must be in ALLOWED_FB_ACCOUNTS")
    if len(currency) != 3 or not currency.isalpha():
        raise HTTPException(status_code=422, detail="currency must be a three-letter ISO code")
    try:
        ZoneInfo(timezone)
    except ZoneInfoNotFoundError as error:
        raise HTTPException(status_code=422, detail="timezone must be an IANA timezone") from error
    if not db.query(Brand).filter(Brand.id == brand_id).first():
        raise HTTPException(status_code=404, detail="Brand not found")
    account_id = normalized_account_id(meta_account_id)
    if db.query(BrandAdAccount).filter(BrandAdAccount.meta_account_id == account_id).first():
        raise HTTPException(status_code=409, detail="Account is already assigned to a brand")
    try:
        accessible = MetaReportingService(db).accessible_account(account_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    actual_currency = (accessible.get("currency") or "").upper()
    if actual_currency and actual_currency != currency.upper():
        raise HTTPException(status_code=422, detail="currency must match the accessible Meta account")
    account = BrandAdAccount(brand_id=brand_id, meta_account_id=account_id, currency=actual_currency or currency.upper(), timezone=timezone, enabled=enabled)
    db.add(account)
    db.commit()
    db.refresh(account)
    return {"id": account.id, "brand_id": account.brand_id, "meta_account_id": account.meta_account_id}


@router.delete("/meta/accounts/{account_id}", status_code=204)
def delete_brand_ad_account(
    account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    del current_user
    account = db.query(BrandAdAccount).filter(BrandAdAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account mapping not found")
    db.delete(account)
    db.commit()


@router.post("/meta/sync", response_model=list[SyncRunResponse])
def sync_brand_meta_reporting(
    brand_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reporting:sync")),
):
    del current_user
    if not db.query(Brand).filter(Brand.id == brand_id).first():
        raise HTTPException(status_code=404, detail="Brand not found")
    try:
        runs = MetaReportingService(db).sync_brand(brand_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return [
        {
            "id": run.id, "account_id": run.brand_ad_account_id, "status": run.status,
            "started_at": run.started_at, "completed_at": run.completed_at,
            "lookback_days": run.lookback_days, "totals": run.totals, "error": run.error,
        }
        for run in runs
    ]
