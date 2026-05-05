import asyncio
import csv
import io
import logging
import os
import uuid
from math import gcd
from pathlib import Path
from typing import List, Optional, Dict, Any
from urllib.parse import quote_plus, urljoin

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_active_user, require_permission
from app.core.utils import validate_url
from app.database import get_db
from app.models import GeneratedAd, User, WinningAd

logger = logging.getLogger(__name__)

FAL_API_KEY_PLACEHOLDERS = {
    "",
    "...",
    "your-fal-ai-api-key",
    "your-real-key-here",
}



class ImageGenerationRequest(BaseModel):
    model_config = {"populate_by_name": True}

    template: Optional[Dict[str, Any]] = None
    brand: Optional[Dict[str, Any]] = None
    product: Optional[Dict[str, Any]] = None
    ad_copy: Optional[Dict[str, Any]] = Field(None, alias="copy")
    count: int = 1
    imageSizes: List[Dict[str, Any]] = []
    resolution: str = "1K"
    productShots: List[str] = []
    model: str = "nano-banana-2"
    customPrompt: Optional[str] = None
    useProductImage: bool = False  # Use uploaded product image as base

def build_comprehensive_prompt(request: ImageGenerationRequest) -> str:
    """
    Build comprehensive prompt using old system's approach:
    - Product name + description
    - Brand name, voice, and primary color
    - Copy context (headline)
    - Template metadata (mood, lighting, composition, design_style)
    """
    
    # Custom prompt override
    if request.customPrompt:
        return request.customPrompt
    
    # Extract all context
    product_name = request.product.get('name', 'Product') if request.product else 'Product'
    product_desc = request.product.get('description', '') if request.product else ''
    brand_name = request.brand.get('name', '') if request.brand else ''
    brand_voice = request.brand.get('voice', 'Professional') if request.brand else 'Professional'
    brand_color = request.brand.get('colors', {}).get('primary', '') if request.brand else ''
    
    # Get template metadata
    template_type = request.template.get('type') if request.template else None
    
    if template_type == 'style':
        # Style archetype - has metadata fields
        mood = request.template.get('mood', 'Engaging')
        lighting = request.template.get('lighting', 'Professional lighting')
        composition = request.template.get('composition', 'Balanced')
        design_style = request.template.get('design_style', 'Modern')
    else:
        # Regular template - get from template data if available
        mood = request.template.get('mood', 'Engaging') if request.template else 'Engaging'
        lighting = request.template.get('lighting', 'Professional lighting') if request.template else 'Professional lighting'
        composition = request.template.get('composition', 'Balanced') if request.template else 'Balanced'
        design_style = request.template.get('design_style', 'Modern') if request.template else 'Modern'
    
    # Build comprehensive prompt (OLD SYSTEM STYLE)
    parts = [
        f"Product Photography of {product_name}",
        f"- {product_desc}" if product_desc else "",
        f"{brand_name} style: {brand_voice}" if brand_name else f"Style: {brand_voice}",
        f"Primary Color: {brand_color}" if brand_color else "",
    ]
    
    # Add copy context (headline)
    if request.ad_copy and request.ad_copy.get('headline'):
        parts.append(f"Context: Visual representation of \"{request.ad_copy.get('headline')}\"")
    
    # Add template art direction
    parts.append(f"Art Direction: {mood}, {lighting}, {composition}, {design_style}")
    
    # Quality standards
    parts.append("High quality, photorealistic, 4k, advertising standard")
    
    # Join non-empty parts
    prompt = ". ".join([p for p in parts if p])
    
    return prompt


def build_fallback_image_url(width: int, height: int, text: str) -> str:
    """Build a safe placeholder image URL when external generation fails."""
    encoded_text = quote_plus(text[:120])
    return f"https://placehold.co/{width}x{height}/png?text={encoded_text}"


def is_configured_fal_api_key(api_key: Optional[str]) -> bool:
    """Return False for empty or scaffold placeholder Fal keys."""
    normalized = (api_key or "").strip()
    return bool(normalized) and normalized not in FAL_API_KEY_PLACEHOLDERS and not normalized.startswith("your-")


def get_public_backend_base_url() -> Optional[str]:
    """Return a configured public backend origin for serving generated upload assets."""
    for key in ("BACKEND_PUBLIC_URL", "API_PUBLIC_URL", "RAILWAY_SERVICE_FB_BUILDER_URL"):
        value = (os.getenv(key) or "").strip()
        if value:
            return value.rstrip("/")

    railway_domain = (os.getenv("RAILWAY_PUBLIC_DOMAIN") or "").strip()
    if railway_domain:
        if railway_domain.startswith(("http://", "https://")):
            return railway_domain.rstrip("/")
        return f"https://{railway_domain}".rstrip("/")

    return None


def to_public_asset_url(asset_url: Optional[str], base_url: Optional[str] = None) -> Optional[str]:
    """Convert backend-local upload paths into URLs the frontend host can load."""
    if not asset_url or not asset_url.startswith("/uploads/"):
        return asset_url

    public_base_url = (base_url or get_public_backend_base_url() or "").strip()
    if not public_base_url:
        return asset_url

    return urljoin(f"{public_base_url.rstrip('/')}/", asset_url.lstrip("/"))


def get_fal_api_key() -> str:
    """Read Fal key at request time so Railway variable changes are picked up after restart."""
    return (os.getenv("FAL_AI_API_KEY") or settings.FAL_AI_API_KEY or "").strip()


def allow_mock_image_generation() -> bool:
    return os.getenv("ALLOW_MOCK_IMAGE_GENERATION", "").strip().lower() in {"1", "true", "yes"}


def get_aspect_ratio(width: int, height: int) -> str:
    if width <= 0 or height <= 0:
        return "auto"

    supported_ratios = {
        (21, 9): "21:9",
        (16, 9): "16:9",
        (3, 2): "3:2",
        (4, 3): "4:3",
        (5, 4): "5:4",
        (1, 1): "1:1",
        (4, 5): "4:5",
        (3, 4): "3:4",
        (2, 3): "2:3",
        (9, 16): "9:16",
        (4, 1): "4:1",
        (1, 4): "1:4",
        (8, 1): "8:1",
        (1, 8): "1:8",
    }
    divisor = gcd(width, height)
    return supported_ratios.get((width // divisor, height // divisor), "auto")


def get_fal_model_attempts(request: ImageGenerationRequest, use_product_image: bool) -> List[str]:
    """Return Fal model attempts, treating the old model value as a compatibility alias."""
    if use_product_image:
        return ["fal-ai/nano-banana-2/edit"]

    if request.model in {"nano-banana-2", "nano-banana-pro"}:
        return ["fal-ai/nano-banana-2", "fal-ai/imagen4/preview"]

    return ["fal-ai/imagen4/preview"]


def build_prompt_variation(base_prompt: str, index: int, total: int, size_name: str) -> str:
    if total <= 1:
        return base_prompt

    directions = [
        "Use the strongest product-first composition with clear hero framing.",
        "Use a distinct camera angle, prop arrangement, and background treatment.",
        "Use a bolder pattern interrupt while preserving the selected template structure.",
        "Use a tighter crop with stronger contrast and a more direct visual metaphor.",
    ]
    direction = directions[index % len(directions)]
    return (
        f"{base_prompt}\n\n"
        f"**Variation {index + 1} of {total}:** {direction} "
        f"Render for {size_name}. Do not reuse the exact same layout, camera angle, "
        "or object placement as the other variations."
    )


def build_fal_arguments(
    model_id: str,
    request: ImageGenerationRequest,
    prompt: str,
    width: int,
    height: int,
) -> Dict[str, Any]:
    """Build request arguments for each Fal model's API contract."""
    if model_id == "fal-ai/nano-banana-2/edit":
        return {
            "prompt": prompt,
            "image_urls": request.productShots,
            "aspect_ratio": get_aspect_ratio(width, height),
            "resolution": request.resolution,
            "output_format": "png",
            "num_images": 1,
        }

    if model_id == "fal-ai/nano-banana-2":
        return {
            "prompt": prompt,
            "aspect_ratio": get_aspect_ratio(width, height),
            "resolution": request.resolution,
            "output_format": "png",
            "num_images": 1,
        }

    return {
        "prompt": prompt,
        "image_size": {
            "width": width,
            "height": height,
        },
    }


def get_persistable_template_id(db: Session, template_id: Optional[str]) -> Optional[str]:
    """Only persist IDs that exist in winning_ads; style archetype IDs are frontend-only."""
    if not template_id:
        return None
    exists = db.query(WinningAd.id).filter(WinningAd.id == template_id).first()
    return template_id if exists else None


class GeneratedAdCreate(BaseModel):
    id: str
    brandId: Optional[str] = None
    productId: Optional[str] = None
    templateId: Optional[str] = None
    imageUrl: Optional[str] = None  # Now optional for video ads
    headline: Optional[str] = None
    body: Optional[str] = None
    cta: Optional[str] = None
    sizeName: Optional[str] = None
    dimensions: Optional[str] = None
    prompt: Optional[str] = None
    adBundleId: Optional[str] = None
    # Video support fields
    mediaType: Optional[str] = 'image'  # 'image' or 'video'
    videoUrl: Optional[str] = None
    videoId: Optional[str] = None  # Facebook video ID
    thumbnailUrl: Optional[str] = None

class BatchSaveRequest(BaseModel):
    ads: List[GeneratedAdCreate]

router = APIRouter()

try:
    import fal_client
except ImportError:
    fal_client = None

# Setup uploads directory
UPLOAD_DIR = Path(__file__).parent.parent.parent.parent / "uploads"
UPLOAD_DIR = UPLOAD_DIR.resolve()
os.makedirs(UPLOAD_DIR, mode=0o755, exist_ok=True)

async def download_and_save_image(image_url: str, prefix: str = "generated") -> str:
    """
    Download image from external URL and save it locally.
    Returns the local URL path.
    """
    # Validate URL to prevent SSRF - only allow known Fal.ai CDN domains
    allowed_domains = ['fal.media', 'v3.fal.media', 'cdn.fal.ai', 'storage.googleapis.com']
    if not validate_url(image_url, allowed_domains=allowed_domains):
        logger.warning("Skipping download from disallowed URL: %s", image_url)
        return image_url

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(image_url, timeout=30.0)
            response.raise_for_status()

            # Generate unique filename
            unique_id = str(uuid.uuid4())
            filename = f"{prefix}_{unique_id}.png"
            file_path = UPLOAD_DIR / filename

            # Save image
            with open(file_path, "wb") as f:
                f.write(response.content)

            # Return local URL
            return f"/uploads/{filename}"
    except Exception as e:
        logger.exception("Error downloading generated image")
        # Return original URL as fallback
        return image_url

@router.post("/generate-image")
async def generate_image(
    request: ImageGenerationRequest,
    http_request: Request,
    current_user: User = Depends(require_permission("ads:write"))
):
    """Generate ad images using Fal.ai."""
    
    images = []
    fal_api_key = get_fal_api_key()
    use_fal = bool(fal_client and is_configured_fal_api_key(fal_api_key))
    use_mock = not use_fal and allow_mock_image_generation()

    if not use_fal and not use_mock:
        raise HTTPException(
            status_code=503,
            detail="Fal.ai image generation is not configured. Set a valid FAL_AI_API_KEY in Railway.",
        )
    
    if use_fal:
        fal_api_client = fal_client.AsyncClient(key=fal_api_key)
        logger.info("Generating images with Fal.ai")
    else:
        fal_api_client = None
        logger.warning("Using mock image generation because ALLOW_MOCK_IMAGE_GENERATION is enabled")
    
    for i in range(request.count):
        for size in request.imageSizes:
            width = size.get('width', 1080)
            height = size.get('height', 1080)
            size_name = size.get('name', 'Square')
            
            # Build comprehensive prompt using old system logic
            base_prompt = build_comprehensive_prompt(request)
            prompt = build_prompt_variation(base_prompt, i, request.count, size_name)
            
            logger.info(
                "Image generation request brand=%s product=%s template_type=%s headline=%s",
                request.brand.get('name') if request.brand else None,
                request.product.get('name') if request.product else None,
                request.template.get('type') if request.template else None,
                request.ad_copy.get('headline') if request.ad_copy else None,
            )
            logger.debug("Generated image prompt: %s", prompt)
            
            if use_fal:
                try:
                    use_product_image = request.useProductImage and bool(request.productShots)
                    if use_product_image:
                        logger.info("Using product image for edit generation")

                    last_error = None
                    for model_id in get_fal_model_attempts(request, use_product_image):
                        try:
                            arguments = build_fal_arguments(model_id, request, prompt, width, height)
                            logger.info("Using image model: %s", model_id)
                            handler = await fal_api_client.submit(model_id, arguments=arguments)
                            result = await handler.get()
                            external_url = result['images'][0]['url']
                            break
                        except Exception as model_error:
                            last_error = model_error
                            logger.warning("Fal.ai model failed model=%s error=%s", model_id, model_error)
                    else:
                        raise last_error or RuntimeError("Fal.ai generation failed")

                    # Download and save image locally
                    logger.info("Downloading image from Fal.ai")
                    image_url = to_public_asset_url(
                        await download_and_save_image(external_url, prefix="generated"),
                        str(http_request.base_url),
                    )
                    logger.info("Saved generated image locally: %s", image_url)

                except Exception as e:
                    logger.exception("Fal.ai generation failed")
                    raise HTTPException(
                        status_code=502,
                        detail="Fal.ai image generation failed. Check FAL_AI_API_KEY and model access.",
                    ) from e
            else:
                # Mock generation
                product_name = request.product.get('name', 'Product') if request.product else 'Product'
                image_url = build_fallback_image_url(width, height, f"{product_name} Mock {i + 1}")
            
            images.append({
                "url": image_url,
                "size": size_name,
                "dimensions": f"{width}x{height}",
                "prompt": prompt
            })
            
    return {"images": images}

@router.get("/")
def get_generated_ads(
    http_request: Request,
    brand_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all generated ads, optionally filtered by brand"""
    query = db.query(GeneratedAd)
    
    if brand_id:
        query = query.filter(GeneratedAd.brand_id == brand_id)
    
    ads = query.order_by(GeneratedAd.created_at.desc()).all()
    
    return [{
        "id": ad.id,
        "brand_id": ad.brand_id,
        "product_id": ad.product_id,
        "template_id": ad.template_id,
        "image_url": to_public_asset_url(ad.image_url, str(http_request.base_url)),
        "headline": ad.headline,
        "body": ad.body,
        "cta": ad.cta,
        "size_name": ad.size_name,
        "dimensions": ad.dimensions,
        "prompt": ad.prompt,
        "ad_bundle_id": ad.ad_bundle_id,
        "created_at": ad.created_at.isoformat() if ad.created_at else None,
        # Video support fields
        "media_type": ad.media_type or 'image',
        "video_url": ad.video_url,
        "video_id": ad.video_id,
        "thumbnail_url": ad.thumbnail_url
    } for ad in ads]

@router.delete("/{ad_id}")
def delete_generated_ad(
    ad_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("ads:delete"))
):
    """Delete a generated ad by ID"""
    ad = db.query(GeneratedAd).filter(GeneratedAd.id == ad_id).first()
    
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")
    
    db.delete(ad)
    db.commit()
    
    return {"message": "Ad deleted successfully"}

@router.post("/export-csv")
def export_ads_csv(
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Export selected ads to CSV"""
    ad_ids = request.get("ids", [])
    
    if not ad_ids:
        raise HTTPException(status_code=400, detail="No ad IDs provided")
    
    ads = db.query(GeneratedAd).filter(GeneratedAd.id.in_(ad_ids)).all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "ID", "Brand ID", "Headline", "Body", "CTA",
        "Size", "Dimensions", "Media Type", "Image URL", "Video URL", "Video ID", "Thumbnail URL", "Created At"
    ])

    # Write data
    for ad in ads:
        writer.writerow([
            ad.id,
            ad.brand_id or "",
            ad.headline or "",
            ad.body or "",
            ad.cta or "",
            ad.size_name or "",
            ad.dimensions or "",
            ad.media_type or "image",
            ad.image_url or "",
            ad.video_url or "",
            ad.video_id or "",
            ad.thumbnail_url or "",
            ad.created_at.isoformat() if ad.created_at else ""
        ])
    
    # Prepare response
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=generated-ads.csv"}
    )

@router.post("/batch")
def batch_save_ads(
    request: BatchSaveRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("ads:write"))
):
    """Batch save generated ads"""
    
    saved_ads = []
    for ad_data in request.ads:
        # Check if ad already exists
        existing = db.query(GeneratedAd).filter(GeneratedAd.id == ad_data.id).first()
        if existing:
            continue

        template_id = get_persistable_template_id(db, ad_data.templateId)
            
        new_ad = GeneratedAd(
            id=ad_data.id,
            brand_id=ad_data.brandId,
            product_id=ad_data.productId,
            template_id=template_id,
            image_url=to_public_asset_url(ad_data.imageUrl, str(http_request.base_url)),
            headline=ad_data.headline,
            body=ad_data.body,
            cta=ad_data.cta,
            size_name=ad_data.sizeName,
            dimensions=ad_data.dimensions,
            prompt=ad_data.prompt,
            ad_bundle_id=ad_data.adBundleId,
            # Video support fields
            media_type=ad_data.mediaType or 'image',
            video_url=ad_data.videoUrl,
            video_id=ad_data.videoId,
            thumbnail_url=ad_data.thumbnailUrl
        )
        db.add(new_ad)
        saved_ads.append(new_ad)
    
    try:
        db.commit()
        return {"message": f"Saved {len(saved_ads)} ads", "count": len(saved_ads)}
    except Exception as e:
        db.rollback()
        logger.exception("Failed to save generated ads")
        raise HTTPException(status_code=500, detail="Internal server error") from e
