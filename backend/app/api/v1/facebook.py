from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from typing import Dict, Any, Optional, List
import logging
from pydantic import BaseModel, ConfigDict, Field
from app.core.api_errors import log_and_raise_http_error
from app.services.facebook_service import FacebookService
from app.models import CampaignTemplate, FacebookAd, FacebookAdSet, FacebookCampaign, LaunchJob, User
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
    status: Optional[str] = "ACTIVE"


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


class LaunchCreative(BaseModel):
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    media_type: Optional[str] = "image"
    name: Optional[str] = None


class LaunchCreateRequest(BaseModel):
    ad_account_ids: List[str]
    launch_status: Optional[str] = "PAUSED"
    campaign: dict
    adset: dict
    source_account_id: Optional[str] = None
    page_id: str
    instagram_id: Optional[str] = None
    creative_name: Optional[str] = None
    creatives: List[LaunchCreative]
    headlines: List[str]
    bodies: List[str]
    description: Optional[str] = None
    cta: Optional[str] = "LEARN_MORE"
    website_url: Optional[str] = None


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

def _job_to_dict(job: LaunchJob) -> dict:
    return {
        "id": job.id,
        "status": job.status,
        "total_steps": job.total_steps,
        "completed_steps": job.completed_steps,
        "failed_steps": job.failed_steps,
        "results": job.results or [],
        "error": job.error,
        "ad_account_ids": (job.payload or {}).get("ad_account_ids", []),
        "launch_status": (job.payload or {}).get("launch_status"),
        "campaign_name": ((job.payload or {}).get("campaign") or {}).get("name"),
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


@router.post("/launches")
def create_launch(
    launch: LaunchCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("campaigns:write")),
):
    """Queue a background launch of creatives into one or more ad accounts."""
    from app.services.launch_service import count_total_steps, run_launch_job

    if not launch.ad_account_ids:
        raise HTTPException(status_code=422, detail="Select at least one ad account")
    if not launch.creatives:
        raise HTTPException(status_code=422, detail="Add at least one creative")
    if launch.launch_status not in ("ACTIVE", "PAUSED"):
        raise HTTPException(status_code=422, detail="launch_status must be ACTIVE or PAUSED")
    payload = launch.model_dump()
    if count_total_steps(payload) == 0:
        raise HTTPException(status_code=422, detail="Nothing to launch: need creatives, headlines and bodies")

    try:
        job = LaunchJob(payload=payload, created_by=current_user.id)
        db.add(job)
        db.commit()
        db.refresh(job)
        background_tasks.add_task(run_launch_job, job.id)
        return {"job_id": job.id}
    except HTTPException:
        raise
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
