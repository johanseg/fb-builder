from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from app.services.facebook_service import FacebookService
from app.models import FacebookAd, FacebookAdSet, FacebookCampaign, User
from app.database import get_db
from app.core.deps import get_current_active_user, require_permission
from sqlalchemy.orm import Session

router = APIRouter()


# --- Pydantic request schemas ---

class CampaignCreateRequest(BaseModel):
    name: str
    objective: str
    status: Optional[str] = "PAUSED"
    budget_type: Optional[str] = None
    budgetType: Optional[str] = None
    daily_budget: Optional[float] = None
    dailyBudget: Optional[float] = None
    bid_strategy: Optional[str] = None
    bidStrategy: Optional[str] = None


class AdSetCreateRequest(BaseModel):
    name: str
    campaign_id: Optional[str] = None
    optimization_goal: Optional[str] = None
    optimizationGoal: Optional[str] = None
    status: Optional[str] = "PAUSED"
    targeting: Optional[dict] = None
    daily_budget: Optional[float] = None
    dailyBudget: Optional[float] = None
    bid_strategy: Optional[str] = None
    bidStrategy: Optional[str] = None
    bid_amount: Optional[float] = None
    bidAmount: Optional[float] = None
    budget_type: Optional[str] = None
    budgetType: Optional[str] = None
    start_time: Optional[str] = None
    startTime: Optional[str] = None
    advantage_audience: Optional[int] = 0
    pixelId: Optional[str] = None
    pixel_id: Optional[str] = None
    conversionEvent: Optional[str] = None
    conversion_event: Optional[str] = None


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


class ImageUploadRequest(BaseModel):
    image_url: str


class VideoUploadRequest(BaseModel):
    video_url: str
    wait_for_ready: Optional[bool] = True
    timeout: Optional[int] = 600

def get_facebook_service():
    service = FacebookService()
    try:
        if not service.api:
            service.initialize()
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    return service

@router.get("/accounts")
def get_ad_accounts(
    service: FacebookService = Depends(get_facebook_service),
    current_user: User = Depends(get_current_active_user)
):
    try:
        return service.get_ad_accounts()
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

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
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

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
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

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
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/pages")
def read_pages(
    service: FacebookService = Depends(get_facebook_service),
    current_user: User = Depends(get_current_active_user)
):
    try:
        pages = service.get_pages()
        return pages
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


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
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

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
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

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
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

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
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

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
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

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
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

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
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

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
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

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
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

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
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

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
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

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
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

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
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

