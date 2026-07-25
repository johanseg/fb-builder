"""
Ad Remix Service - Business logic for deconstructing and reconstructing ads
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any

from google import genai
from google.genai import types

from app.core.config import settings
from app.core.utils import (
    IMAGE_CONTENT_TYPES,
    allowed_media_domains,
    download_remote_media,
    extract_json_from_text,
    resolve_managed_upload_path,
    validate_media_bytes,
)
from app.schemas.ad_blueprint import AdBlueprint, AdConcept, BrandData
from app.prompts.ad_remix_prompts import build_deconstruction_prompt, build_reconstruction_prompt

logger = logging.getLogger(__name__)

# Allowed MIME types for image uploads to Gemini
_MIME_MAP = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.webp': 'image/webp',
    '.gif': 'image/gif',
}


async def _download_image(url_or_path: str) -> tuple[bytes, str]:
    """Download image from URL or read from local path. Returns (bytes, mime_type)."""
    upload_dir = Path(__file__).resolve().parents[2] / "uploads"
    path = resolve_managed_upload_path(url_or_path, upload_dir)
    if path:
        mime = _MIME_MAP.get(path.suffix.lower(), 'image/jpeg')
        content = path.read_bytes()
        validate_media_bytes(content, media_kind="image", max_bytes=10 * 1024 * 1024)
        return content, mime

    return await download_remote_media(
        url_or_path,
        media_kind="image",
        allowed_mime_types=IMAGE_CONTENT_TYPES,
        max_bytes=10 * 1024 * 1024,
        allowed_domains=allowed_media_domains(),
    )



async def deconstruct_template(template_image_url: str) -> AdBlueprint:
    """
    Analyze a template image and extract its structural blueprint
    
    Args:
        template_image_url: URL or path to the template image
        
    Returns:
        AdBlueprint with extracted structure
    """
    try:
        # Use Gemini Vision model
        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        # Build the prompt
        prompt = build_deconstruction_prompt(template_image_url)

        # Download the image so we can send actual bytes to Gemini
        image_data, mime_type = await _download_image(template_image_url)

        response = client.models.generate_content(model=settings.GEMINI_VISION_MODEL, contents=[
            prompt,
            types.Part.from_bytes(data=image_data, mime_type=mime_type),
        ])

        # Parse the JSON response (handles markdown code block wrapping)
        blueprint_data = extract_json_from_text(response.text)

        # Validate and return as AdBlueprint
        return AdBlueprint(**blueprint_data)

    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse blueprint JSON: {e}") from e
    except Exception as e:
        raise Exception(f"Failed to deconstruct template: {e}") from e


async def reconstruct_ad(
    blueprint: AdBlueprint,
    brand_data: BrandData
) -> AdConcept:
    """
    Generate a new ad concept by applying brand data to a blueprint
    
    Args:
        blueprint: The structural blueprint to follow
        brand_data: The new brand/product information
        
    Returns:
        AdConcept with generated content
    """
    try:
        # Use Gemini model
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
        # Convert blueprint to dict
        blueprint_dict = blueprint.model_dump()
        
        # Build the reconstruction prompt
        prompt = build_reconstruction_prompt(
            blueprint=blueprint_dict,
            brand_name=brand_data.brand_name,
            brand_voice=brand_data.brand_voice or "",
            product_name=brand_data.product_name,
            product_description=brand_data.product_description,
            audience_demographics=brand_data.audience_demographics,
            audience_pain_points=brand_data.audience_pain_points or "",
            audience_goals=brand_data.audience_goals or "",
            campaign_offer=brand_data.campaign_offer,
            campaign_urgency=brand_data.campaign_urgency or "",
            campaign_messaging=brand_data.campaign_messaging
        )
        
        # Generate the ad concept
        response = client.models.generate_content(model=settings.GEMINI_VISION_MODEL, contents=prompt)
        
        # Parse the JSON response (handles markdown code block wrapping)
        concept_data = extract_json_from_text(response.text)
        
        # Validate and return as AdConcept
        return AdConcept(**concept_data)
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse ad concept JSON: {e}") from e
    except Exception as e:
        raise Exception(f"Failed to reconstruct ad: {e}") from e
