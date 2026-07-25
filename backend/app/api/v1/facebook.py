from fastapi import APIRouter, Depends, Header, HTTPException
from typing import Dict, Any, Optional, List, Literal
import base64
import hashlib
import hmac
import json
import logging
import time
from urllib.parse import urlparse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.core.api_errors import log_and_raise_http_error
from app.core.config import settings
from app.services.facebook_service import FacebookService
from app.models import CampaignTemplate, FacebookAd, FacebookAdSet, FacebookCampaign, LaunchJob, LaunchOperation, User
from app.database import get_db
from app.core.deps import get_current_active_user, require_permission
from sqlalchemy.orm import Session

router = APIRouter()
logger = logging.getLogger(__name__)
_facebook_service: Optional[FacebookService] = None


# --- Pydantic request schemas ---

class CampaignCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    objective: str
    status: Optional[str] = "PAUSED"
    budget_type: Optional[str] = Field(default=None, alias="budgetType")
    daily_budget: Optional[float] = Field(default=None, alias="dailyBudget")
    bid_strategy: Optional[str] = Field(default=None, alias="bidStrategy")


class AdSetCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    campaign_id: Optional[str] = Field(default=None, alias="campaignId")
    optimization_goal: Optional[str] = Field(default=None, alias="optimizationGoal")
    status: Optional[str] = "PAUSED"
    targeting: Optional[dict] = None
    daily_budget: Optional[float] = Field(default=None, alias="dailyBudget")
    bid_strategy: Optional[str] = Field(default=None, alias="bidStrategy")
    bid_amount: Optional[float] = Field(default=None, alias="bidAmount")
    budget_type: Optional[str] = Field(default=None, alias="budgetType")
    start_time: Optional[str] = Field(default=None, alias="startTime")
    advantage_audience: Optional[int] = 0
    pixel_id: Optional[str] = Field(default=None, alias="pixelId")
    conversion_event: Optional[str] = Field(default=None, alias="conversionEvent")


class CreativeCreateRequest(BaseModel):
    name: Optional[str] = None
    page_id: Optional[str] = None
    image_hash: Optional[str] = None
    video_id: Optional[str] = None
    primary_text: Optional[str] = None
    headline: Optional[str] = None
    description: Optional[str] = None
    cta: Optional[str] = "LEARN_MORE"
    website_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    instagram_actor_id: Optional[str] = None


class AdCreateRequest(BaseModel):
    name: str
    adset_id: str
    creative_id: str
    status: Optional[str] = "PAUSED"


class CampaignSaveRequest(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    objective: Optional[str] = None
    budgetType: Optional[str] = "ABO"
    dailyBudget: Optional[float] = None
    bidStrategy: Optional[str] = None
    status: Optional[str] = None
    fbCampaignId: Optional[str] = None


class AdSetSaveRequest(BaseModel):
    id: Optional[str] = None
    campaignId: str
    name: Optional[str] = None
    optimizationGoal: Optional[str] = None
    dailyBudget: Optional[float] = None
    bidStrategy: Optional[str] = None
    bidAmount: Optional[float] = None
    targeting: Optional[dict] = None
    pixelId: Optional[str] = None
    conversionEvent: Optional[str] = None
    status: Optional[str] = None
    fbAdsetId: Optional[str] = None


class AdSaveRequest(BaseModel):
    id: Optional[str] = None
    adsetId: Optional[str] = None
    name: Optional[str] = None
    creativeName: Optional[str] = None
    imageUrl: Optional[str] = None
    mediaType: Optional[str] = "image"
    videoUrl: Optional[str] = None
    videoId: Optional[str] = None
    thumbnailUrl: Optional[str] = None
    bodies: Optional[List[str]] = None
    headlines: Optional[List[str]] = None
    description: Optional[str] = None
    cta: Optional[str] = None
    websiteUrl: Optional[str] = None
    status: Optional[str] = None
    fbAdId: Optional[str] = None
    fbCreativeId: Optional[str] = None


class LaunchCampaign(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = Field(min_length=1, max_length=255)
    objective: str = Field(min_length=1, max_length=100)
    budgetType: Literal["ABO", "CBO"] = "ABO"
    dailyBudget: Optional[float] = Field(default=None, gt=0)
    bidStrategy: Optional[str] = None
    bidAmount: Optional[float] = Field(default=None, gt=0)
    isExisting: bool = False
    fbCampaignId: Optional[str] = None


class LaunchAdSet(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = Field(min_length=1, max_length=255)
    optimizationGoal: str = Field(min_length=1, max_length=100)
    dailyBudget: Optional[float] = Field(default=None, gt=0)
    bidStrategy: Optional[str] = None
    bidAmount: Optional[float] = Field(default=None, gt=0)
    targeting: dict
    fbAdsetId: Optional[str] = None


class LaunchCreative(BaseModel):
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    media_type: Literal["image", "video"] = "image"
    name: Optional[str] = None
    module_ids: List[str] = Field(default_factory=list, max_length=4)

    @model_validator(mode="after")
    def validate_media(self):
        expected = self.video_url if self.media_type == "video" else self.image_url
        other = self.image_url if self.media_type == "video" else self.video_url
        if not expected or other:
            raise ValueError("Creative must provide exactly one URL matching media_type")
        for value in (expected, self.thumbnail_url):
            if value and urlparse(value).scheme not in ("http", "https"):
                raise ValueError("Launch media URLs must be public http(s) URLs")
        return self


class LaunchCreateRequest(BaseModel):
    ad_account_ids: List[str] = Field(min_length=1, max_length=10)
    launch_status: Literal["PAUSED"] = "PAUSED"
    campaign: LaunchCampaign
    adset: LaunchAdSet
    source_account_id: Optional[str] = None
    page_id: str = Field(pattern=r"^\d+$")
    instagram_id: Optional[str] = None
    creative_name: Optional[str] = None
    creatives: List[LaunchCreative] = Field(min_length=1, max_length=20)
    headlines: List[str] = Field(min_length=1, max_length=5)
    bodies: List[str] = Field(min_length=1, max_length=5)
    description: Optional[str] = None
    cta: Optional[str] = "LEARN_MORE"
    website_url: Optional[str] = None

    @field_validator("headlines", "bodies")
    @classmethod
    def validate_copy(cls, values):
        if any(not isinstance(value, str) or not value.strip() for value in values):
            raise ValueError("Copy variants cannot be blank")
        return values

    @model_validator(mode="after")
    def validate_budget_and_destination(self):
        if self.website_url and urlparse(self.website_url).scheme not in ("http", "https"):
            raise ValueError("website_url must be an http(s) URL")
        if self.campaign.budgetType == "CBO" and self.campaign.dailyBudget is None:
            raise ValueError("CBO launches require a positive campaign daily budget")
        if self.campaign.budgetType == "ABO" and self.adset.dailyBudget is None:
            raise ValueError("ABO launches require a positive ad set daily budget")
        return self


class ActivationRequest(BaseModel):
    confirmation_token: str


class CampaignTemplateCreateRequest(BaseModel):
    name: str
    config: dict


class ImageUploadRequest(BaseModel):
    image_url: str


class VideoUploadRequest(BaseModel):
    video_url: str
    wait_for_ready: Optional[bool] = True
    timeout: Optional[int] = 600

def get_facebook_service():
    global _facebook_service
    if _facebook_service is None:
        _facebook_service = FacebookService()
    try:
        if not _facebook_service.api:
            _facebook_service.initialize()
    except Exception as e:
        _facebook_service = None
        log_and_raise_http_error(
            logger,
            "Failed to initialize Facebook service",
            e,
            expose_detail=True,
        )
    return _facebook_service

@router.get("/accounts")
def get_ad_accounts(
    service: FacebookService = Depends(get_facebook_service),
    current_user: User = Depends(get_current_active_user)
):
    try:
        return service.get_ad_accounts()
    except Exception as e:
        log_and_raise_http_error(logger, "Failed to fetch ad accounts", e, expose_detail=True)

@router.get("/campaigns")
def read_campaigns(
    ad_account_id: Optional[str] = None,
    service: FacebookService = Depends(get_facebook_service),
    current_user: User = Depends(get_current_active_user)
):
    try:
        campaigns = service.get_campaigns(ad_account_id)
        # Convert FB objects to dicts
        return [dict(c) for c in campaigns]
    except Exception as e:
        log_and_raise_http_error(logger, "Failed to fetch campaigns", e, expose_detail=True)

@router.post("/campaigns")
def create_campaign(
    campaign: CampaignCreateRequest,
    ad_account_id: Optional[str] = None,
    service: FacebookService = Depends(get_facebook_service),
    current_user: User = Depends(require_permission("campaigns:write"))
):
    try:
        result = service.create_campaign(campaign.model_dump(exclude_none=True), ad_account_id)
        return dict(result)
    except Exception as e:
        log_and_raise_http_error(logger, "Failed to create campaign", e, expose_detail=True)

@router.get("/pixels")
def read_pixels(
    ad_account_id: Optional[str] = None,
    service: FacebookService = Depends(get_facebook_service),
    current_user: User = Depends(get_current_active_user)
):
    try:
        pixels = service.get_pixels(ad_account_id)
        # Convert FB objects to dicts
        return [dict(p) for p in pixels]
    except Exception as e:
        log_and_raise_http_error(logger, "Failed to fetch pixels", e, expose_detail=True)

@router.get("/pages")
def read_pages(
    service: FacebookService = Depends(get_facebook_service),
    current_user: User = Depends(get_current_active_user)
):
    try:
        pages = service.get_pages()
        return pages
    except Exception as e:
        log_and_raise_http_error(logger, "Failed to fetch pages", e, expose_detail=True)


@router.get("/adsets")
def read_adsets(
    ad_account_id: Optional[str] = None,
    campaign_id: Optional[str] = None,
    service: FacebookService = Depends(get_facebook_service),
    current_user: User = Depends(get_current_active_user)
):
    try:
        adsets = service.get_adsets(ad_account_id, campaign_id)
        return [dict(a) for a in adsets]
    except Exception as e:
        log_and_raise_http_error(logger, "Failed to fetch ad sets", e, expose_detail=True)

@router.post("/adsets")
def create_adset(
    adset: AdSetCreateRequest,
    ad_account_id: Optional[str] = None,
    service: FacebookService = Depends(get_facebook_service),
    current_user: User = Depends(require_permission("campaigns:write"))
):
    try:
        result = service.create_adset(adset.model_dump(exclude_none=True), ad_account_id)
        return dict(result)
    except Exception as e:
        log_and_raise_http_error(logger, "Failed to create ad set", e, expose_detail=True)

@router.post("/creatives")
def create_creative(
    creative: CreativeCreateRequest,
    ad_account_id: Optional[str] = None,
    service: FacebookService = Depends(get_facebook_service),
    current_user: User = Depends(require_permission("campaigns:write"))
):
    try:
        result = service.create_creative(creative.model_dump(exclude_none=True), ad_account_id)
        return dict(result)
    except Exception as e:
        log_and_raise_http_error(logger, "Failed to create creative", e, expose_detail=True)

@router.post("/ads")
def create_ad(
    ad: AdCreateRequest,
    ad_account_id: Optional[str] = None,
    service: FacebookService = Depends(get_facebook_service),
    current_user: User = Depends(require_permission("campaigns:write"))
):
    try:
        result = service.create_ad(ad.model_dump(exclude_none=True), ad_account_id)
        return dict(result)
    except Exception as e:
        log_and_raise_http_error(logger, "Failed to create ad", e, expose_detail=True)

@router.get("/ads")
def read_ads(
    adset_id: str,
    service: FacebookService = Depends(get_facebook_service),
    current_user: User = Depends(get_current_active_user)
):
    try:
        ads = service.get_ads(adset_id)
        return [dict(a) for a in ads]
    except Exception as e:
        log_and_raise_http_error(logger, "Failed to fetch ads", e, expose_detail=True)

@router.post("/campaigns/save")
def save_campaign_locally(
    campaign_data: CampaignSaveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("campaigns:write"))
):
    try:
        # Check if exists
        existing = db.query(FacebookCampaign).filter(FacebookCampaign.id == campaign_data.id).first()
        if existing:
            return {"message": "Campaign already exists", "id": existing.id}

        # Handle daily_budget casting
        daily_budget = campaign_data.dailyBudget
        if daily_budget is not None:
            daily_budget = int(float(daily_budget))

        new_campaign = FacebookCampaign(
            id=campaign_data.id,
            name=campaign_data.name,
            objective=campaign_data.objective,
            budget_type=campaign_data.budgetType or 'ABO',
            daily_budget=daily_budget,
            bid_strategy=campaign_data.bidStrategy,
            status=campaign_data.status,
            fb_campaign_id=campaign_data.fbCampaignId
        )
        db.add(new_campaign)
        db.commit()
        db.refresh(new_campaign)
        return {"message": "Campaign saved locally", "id": new_campaign.id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        log_and_raise_http_error(logger, "Failed to save campaign locally", e, expose_detail=True)

@router.post("/adsets/save")
def save_adset_locally(
    adset_data: AdSetSaveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("campaigns:write"))
):
    try:
        # Check if exists
        existing = db.query(FacebookAdSet).filter(FacebookAdSet.id == adset_data.id).first()
        if existing:
            return {"message": "AdSet already exists", "id": existing.id}

        # We assume campaign is already saved by the frontend calling /campaigns/save first

        # Handle numeric fields casting
        daily_budget = adset_data.dailyBudget
        if daily_budget is not None:
            daily_budget = int(float(daily_budget))

        bid_amount = adset_data.bidAmount
        if bid_amount is not None:
            bid_amount = int(float(bid_amount))

        new_adset = FacebookAdSet(
            id=adset_data.id,
            campaign_id=adset_data.campaignId,
            name=adset_data.name,
            optimization_goal=adset_data.optimizationGoal,
            daily_budget=daily_budget,
            bid_strategy=adset_data.bidStrategy,
            bid_amount=bid_amount,
            targeting=adset_data.targeting,
            pixel_id=adset_data.pixelId,
            conversion_event=adset_data.conversionEvent,
            status=adset_data.status,
            fb_adset_id=adset_data.fbAdsetId
        )
        db.add(new_adset)
        db.commit()
        db.refresh(new_adset)
        return {"message": "AdSet saved locally", "id": new_adset.id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        log_and_raise_http_error(logger, "Failed to save ad set locally", e, expose_detail=True)

@router.post("/ads/save")
def save_ad_locally(
    ad_data: AdSaveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("campaigns:write"))
):
    try:
        new_ad = FacebookAd(
            id=ad_data.id,
            adset_id=ad_data.adsetId,
            name=ad_data.name,
            creative_name=ad_data.creativeName,
            image_url=ad_data.imageUrl,
            media_type=ad_data.mediaType or 'image',
            video_url=ad_data.videoUrl,
            video_id=ad_data.videoId,
            thumbnail_url=ad_data.thumbnailUrl,
            bodies=ad_data.bodies,
            headlines=ad_data.headlines,
            description=ad_data.description,
            cta=ad_data.cta,
            website_url=ad_data.websiteUrl,
            status=ad_data.status,
            fb_ad_id=ad_data.fbAdId,
            fb_creative_id=ad_data.fbCreativeId
        )
        db.add(new_ad)
        db.commit()
        db.refresh(new_ad)
        return {"message": "Ad saved locally", "id": new_ad.id}
    except Exception as e:
        db.rollback()
        log_and_raise_http_error(logger, "Failed to save ad locally", e, expose_detail=True)

@router.post("/upload-image")
def upload_image(
    data: ImageUploadRequest,
    ad_account_id: Optional[str] = None,
    service: FacebookService = Depends(get_facebook_service),
    current_user: User = Depends(require_permission("campaigns:write"))
):
    try:
        image_hash = service.upload_image(data.image_url, ad_account_id)
        return {"image_hash": image_hash}
    except HTTPException:
        raise
    except Exception as e:
        log_and_raise_http_error(logger, "Failed to upload image", e, expose_detail=True)

@router.post("/upload-video")
def upload_video(
    data: VideoUploadRequest,
    ad_account_id: Optional[str] = None,
    service: FacebookService = Depends(get_facebook_service),
    current_user: User = Depends(require_permission("campaigns:write"))
):
    """Upload a video to Facebook Ad Library.

    Request body:
        video_url: URL of the video to upload
        wait_for_ready: Whether to wait for processing (default True)
        timeout: Max seconds to wait (default 600)

    Returns:
        video_id: Facebook video ID
        status: 'processing', 'ready', or 'error'
        thumbnails: List of auto-generated thumbnail URLs (if ready)
    """
    try:
        result = service.upload_video(
            data.video_url,
            ad_account_id,
            wait_for_ready=data.wait_for_ready,
            timeout=data.timeout
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        log_and_raise_http_error(logger, "Failed to upload video", e, expose_detail=True)

@router.get("/video-status/{video_id}")
def get_video_status(
    video_id: str,
    service: FacebookService = Depends(get_facebook_service),
    current_user: User = Depends(get_current_active_user)
):
    """Check the processing status of a video.

    Returns:
        status: 'processing', 'ready', or 'error'
        video_id: The video ID
        length: Video duration in seconds (if ready)
    """
    try:
        return service.get_video_status(video_id)
    except Exception as e:
        log_and_raise_http_error(logger, "Failed to fetch video status", e, expose_detail=True)

@router.get("/video-thumbnails/{video_id}")
def get_video_thumbnails(
    video_id: str,
    service: FacebookService = Depends(get_facebook_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get auto-generated thumbnails for a video.

    Returns:
        thumbnails: List of thumbnail URLs
    """
    try:
        thumbnails = service.get_video_thumbnails(video_id)
        return {"thumbnails": thumbnails}
    except Exception as e:
        log_and_raise_http_error(logger, "Failed to fetch video thumbnails", e, expose_detail=True)

# --- Cross-account insights overview ---

# ponytail: in-process TTL cache; move to DB/Redis if this ever runs multi-instance
_insights_cache: Dict[str, Any] = {}
INSIGHTS_CACHE_TTL_SECONDS = 300
VALID_DATE_PRESETS = {"today", "yesterday", "last_7d", "last_14d", "last_30d", "this_month", "last_month"}


@router.get("/insights/overview")
def get_insights_overview(
    date_preset: str = "last_7d",
    service: FacebookService = Depends(get_facebook_service),
    current_user: User = Depends(get_current_active_user),
):
    """Spend/KPIs for every accessible ad account — one row per account."""
    import time as _time

    if date_preset not in VALID_DATE_PRESETS:
        raise HTTPException(status_code=422, detail=f"date_preset must be one of {sorted(VALID_DATE_PRESETS)}")

    cached = _insights_cache.get(date_preset)
    if cached and _time.time() - cached[0] < INSIGHTS_CACHE_TTL_SECONDS:
        return cached[1]

    try:
        accounts = service.get_ad_accounts()
    except Exception as e:
        log_and_raise_http_error(logger, "Failed to fetch ad accounts for insights", e, expose_detail=True)

    rows = []
    for account in accounts:
        row = {
            "account_id": account.get("id"),
            "account_name": account.get("name"),
            "currency": account.get("currency"),
        }
        try:
            row.update(service.get_account_insights(account.get("id"), date_preset))
        except Exception as e:
            logger.warning("Insights failed for %s: %s", account.get("id"), e)
            row["error"] = str(e)
        rows.append(row)

    _insights_cache[date_preset] = (_time.time(), rows)
    return rows


# --- Multi-account launch jobs ---

def _sign_confirmation(payload: dict) -> str:
    body = base64.urlsafe_b64encode(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).decode().rstrip("=")
    signature = hmac.new(settings.SECRET_KEY.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def _verify_confirmation(token: str, *, kind: str, user_id: str, digest: str) -> None:
    try:
        body, signature = token.rsplit(".", 1)
        expected = hmac.new(settings.SECRET_KEY.encode(), body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError
        decoded = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if (
            decoded.get("kind") != kind
            or decoded.get("user_id") != user_id
            or decoded.get("digest") != digest
            or int(decoded.get("expires_at", 0)) < int(time.time())
        ):
            raise ValueError
    except (TypeError, ValueError, KeyError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=409, detail="Confirmation token is invalid or expired") from error


def _launch_preflight(payload: dict) -> int:
    from app.services.launch_service import validate_launch_payload

    total = validate_launch_payload(payload)
    accessible = {account.get("id") for account in get_facebook_service().get_ad_accounts()}
    unavailable = set(payload["ad_account_ids"]) - accessible
    if unavailable:
        raise ValueError("Selected ad account is unavailable")
    return total


def _job_to_dict(job: LaunchJob) -> dict:
    operation_results = [
        {
            "ad_account_id": operation.target.ad_account_id,
            "entity": operation.kind,
            "name": (operation.request_payload or {}).get("name"),
            "fb_id": operation.fb_object_id,
            "error": operation.last_error,
            "status": operation.status,
        }
        for target in job.targets
        for operation in target.operations
        if operation.kind == "ad" or operation.last_error
    ]
    return {
        "id": job.id,
        "status": job.status,
        "total_steps": job.total_steps,
        "completed_steps": job.completed_steps,
        "failed_steps": job.failed_steps,
        "results": operation_results,
        "error": job.error,
        "ad_account_ids": (job.payload or {}).get("ad_account_ids", []),
        "launch_status": (job.payload or {}).get("launch_status"),
        "campaign_name": ((job.payload or {}).get("campaign") or {}).get("name"),
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        "activation_eligible": job.status == "ready",
        "targets": [{
            "ad_account_id": target.ad_account_id,
            "status": target.status,
            "error": target.last_error,
        } for target in job.targets],
    }


@router.post("/launches/preflight")
def preflight_launch(
    launch: LaunchCreateRequest,
    current_user: User = Depends(require_permission("campaigns:write")),
):
    """Validate a PAUSED launch without creating local or Meta entities."""
    from app.services.launch_service import payload_digest

    payload = launch.model_dump()
    try:
        total = _launch_preflight(payload)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    digest = payload_digest(payload)
    token = _sign_confirmation(
        {
            "kind": "launch",
            "user_id": current_user.id,
            "digest": digest,
            "expires_at": int(time.time()) + 600,
        }
    )
    return {
        "confirmation_token": token,
        "summary": {
            "status": "PAUSED",
            "accounts": payload["ad_account_ids"],
            "account_count": len(payload["ad_account_ids"]),
            "ad_count": total,
            "campaign_budget": payload["campaign"].get("dailyBudget"),
            "adset_budget": payload["adset"].get("dailyBudget"),
        },
    }


@router.post("/launches")
def create_launch(
    launch: LaunchCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("campaigns:write")),
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=255),
    preflight_token: str = Header(..., alias="X-Preflight-Token"),
):
    """Persist PAUSED work for the dedicated Railway worker."""
    from app.services.launch_service import create_job, payload_digest
    payload = launch.model_dump()
    try:
        _launch_preflight(payload)
        _verify_confirmation(
            preflight_token,
            kind="launch",
            user_id=current_user.id,
            digest=payload_digest(payload),
        )
        job, replayed = create_job(db, payload, current_user.id, idempotency_key)
        return {"job_id": job.id, "status": job.status, "idempotent_replay": replayed}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        db.rollback()
        log_and_raise_http_error(logger, "Failed to queue launch", e, expose_detail=True)


@router.get("/launches")
def list_launches(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    jobs = db.query(LaunchJob).order_by(LaunchJob.created_at.desc()).limit(min(limit, 100)).all()
    return [_job_to_dict(j) for j in jobs]


@router.get("/launches/{job_id}")
def get_launch(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    job = db.query(LaunchJob).filter(LaunchJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Launch job not found")
    return _job_to_dict(job)


@router.post("/launches/{job_id}/activation-preflight")
def preflight_activation(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("campaigns:activate")),
):
    """Return the actual ready launch summary used by the manager confirmation modal."""
    from app.services.launch_service import payload_digest, verify_activation_ready

    job = db.query(LaunchJob).filter(LaunchJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Launch job not found")
    try:
        verify_activation_ready(db, job, get_facebook_service())
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    digest = payload_digest(job.payload)
    token = _sign_confirmation(
        {
            "kind": "activate",
            "user_id": current_user.id,
            "digest": digest,
            "expires_at": int(time.time()) + 600,
        }
    )
    return {"confirmation_token": token, "summary": _job_to_dict(job)}


@router.post("/launches/{job_id}/reconcile")
def reconcile_launch(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("campaigns:write")),
):
    """Reconcile known provider IDs without retrying an uncertain create."""
    del current_user
    from app.services.launch_service import reconcile_job

    job = db.query(LaunchJob).filter(LaunchJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Launch job not found")
    blocked = reconcile_job(db, job, get_facebook_service())
    db.refresh(job)
    return {"job_id": job.id, "status": job.status, "blocked_operations": blocked}


@router.post("/launches/{job_id}/activate")
def activate_launch(
    job_id: str,
    confirmation: ActivationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("campaigns:activate")),
):
    """Explicitly activate only a fully reconciled, PAUSED launch."""
    from app.services.launch_service import request_activation
    job = db.query(LaunchJob).filter(LaunchJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Launch job not found")
    if job.status in ("activation_queued", "activating", "active"):
        return {"job_id": job.id, "status": job.status, "idempotent_replay": True}
    try:
        from app.services.launch_service import payload_digest
        _verify_confirmation(
            confirmation.confirmation_token,
            kind="activate",
            user_id=current_user.id,
            digest=payload_digest(job.payload),
        )
        request_activation(db, job, get_facebook_service())
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"job_id": job.id, "status": job.status}


# --- Campaign templates ---

@router.get("/campaign-templates")
def list_campaign_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    templates = db.query(CampaignTemplate).order_by(CampaignTemplate.created_at.desc()).all()
    return [{
        "id": t.id,
        "name": t.name,
        "config": t.config,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    } for t in templates]


@router.post("/campaign-templates")
def create_campaign_template(
    template: CampaignTemplateCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("campaigns:write")),
):
    try:
        existing = db.query(CampaignTemplate).filter(CampaignTemplate.name == template.name).first()
        if existing:
            existing.config = template.config
            db.commit()
            return {"id": existing.id, "message": "Template updated"}
        new_template = CampaignTemplate(
            name=template.name, config=template.config, created_by=current_user.id
        )
        db.add(new_template)
        db.commit()
        db.refresh(new_template)
        return {"id": new_template.id, "message": "Template saved"}
    except Exception as e:
        db.rollback()
        log_and_raise_http_error(logger, "Failed to save campaign template", e, expose_detail=True)


@router.delete("/campaign-templates/{template_id}")
def delete_campaign_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("campaigns:write")),
):
    template = db.query(CampaignTemplate).filter(CampaignTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(template)
    db.commit()
    return {"message": "Template deleted"}


@router.get("/locations/search")
def search_locations(
    q: str,
    type: str = "city",
    limit: int = 10,
    ad_account_id: Optional[str] = None,
    service: FacebookService = Depends(get_facebook_service),
    current_user: User = Depends(get_current_active_user)
):
    try:
        locations = service.search_locations(q, type, limit, ad_account_id)
        return [dict(loc) for loc in locations]
    except Exception as e:
        log_and_raise_http_error(logger, "Failed to search locations", e, expose_detail=True)
