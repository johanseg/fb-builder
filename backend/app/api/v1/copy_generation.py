from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
from app.models import User
from app.core.api_errors import log_and_raise_http_error
from app.core.config import settings
from app.core.deps import get_current_active_user
from app.core.rate_limit import limiter
from app.core.utils import extract_json_from_text
import google.generativeai as genai
import json

router = APIRouter()
logger = logging.getLogger(__name__)

class CopyGenerationRequest(BaseModel):
    brand: Dict[str, Any]
    product: Dict[str, Any]
    profile: Dict[str, Any]
    template: Optional[Dict[str, Any]] = None
    variationCount: int = 3
    campaignDetails: Dict[str, str]
    customPrompt: Optional[str] = None

class FieldRegenerationRequest(BaseModel):
    field: str
    currentValue: str
    brand: Dict[str, Any]
    product: Dict[str, Any]
    profile: Dict[str, Any]
    template: Optional[Dict[str, Any]] = None
    campaignDetails: Dict[str, str]

@router.post("/generate")
@limiter.limit("20/minute")
async def generate_copy(request: Request, body: CopyGenerationRequest, current_user: User = Depends(get_current_active_user)):
    """Generate ad copy variations using Gemini AI"""
    
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API key not configured")
    
    try:
        # Build the prompt
        count = body.variationCount
        prompt = f"""You are an expert ad copywriter. Generate {count} variations of ad copy for a Facebook/Instagram ad campaign.

BRAND VOICE: {body.brand.get('voice', 'Professional and friendly')}

PRODUCT: {body.product.get('name')}
{f"Description: {body.product.get('description')}" if body.product.get('description') else ''}

TARGET AUDIENCE:
- Demographics: {body.profile.get('demographics', 'General audience')}
- Pain Points: {body.profile.get('pain_points', 'Not specified')}
- Goals: {body.profile.get('goals', 'Not specified')}

CAMPAIGN DETAILS:
- Offer: {body.campaignDetails.get('offer')}
- Key Messaging: {body.campaignDetails.get('messaging')}

TEMPLATE STYLE: {body.template.get('design_style', 'Modern and clean') if body.template else 'Modern and clean'}

BODY COPY STYLES (vary across variations):
1. BULLET POINTS WITH EMOJIS: Use 2-4 bullet points with emojis at the start
   - Sometimes use the same emoji (e.g., ✓ ✓ ✓ or ⭐ ⭐ ⭐)
   - Sometimes use mixed emojis (e.g., 🎯 💪 ✨ 🚀)
   - Keep each bullet concise and benefit-focused
   Example: "✓ Save 50% today
✓ Free shipping
✓ 30-day guarantee"

2. EMOTIONAL STORYTELLING: Longer narrative that connects emotionally
   - Tell a relatable story or paint a vivid picture
   - Use emotional triggers and sensory details
   - Build desire and urgency through narrative
   - Can be 150-200 characters for story-driven ads
   Example: "Remember that feeling when everything just clicks? When you finally found the solution you've been searching for? That's what our customers experience every day..."

INSTRUCTIONS:
Generate {count} distinct variations. Mix both body copy styles across variations. Each variation should:
1. Match the brand voice consistently
2. Address the audience's pain points and goals
3. Incorporate the campaign offer and key messaging
4. Be compelling, conversion-focused, and ad-appropriate
5. Keep headlines under 40 characters
6. For bullet-point style: Keep body under 125 characters
7. For storytelling style: Can extend to 200 characters
8. Keep CTAs under 20 characters

Return ONLY valid JSON in this exact format:
{{
  "variations": [
    {{
      "headline": "Short, punchy headline",
      "body": "Compelling body copy (bullets with emojis OR emotional story)",
      "cta": "Action CTA"
    }}
  ]
}}"""

        # Use custom prompt if provided
        if body.customPrompt:
            prompt = body.customPrompt
        
        # Generate with Gemini
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        response = model.generate_content(prompt)
        return extract_json_from_text(response.text)
        
    except json.JSONDecodeError as e:
        log_and_raise_http_error(
            logger,
            "Copy generation returned invalid JSON",
            e,
            status_code=502,
            detail="Gemini returned invalid JSON",
        )
    except Exception as e:
        log_and_raise_http_error(
            logger,
            "Copy generation request failed",
            e,
            expose_detail=True,
        )

@router.post("/regenerate-field")
@limiter.limit("20/minute")
async def regenerate_field(request: Request, body: FieldRegenerationRequest, current_user: User = Depends(get_current_active_user)):
    """Regenerate a specific field (headline, body, or cta)"""
    
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API key not configured")
    
    try:
        field_prompts = {
            "headline": "Generate a new headline (under 40 characters)",
            "body": "Generate new body copy (under 125 characters for bullets, or up to 200 for storytelling)",
            "cta": "Generate a new call-to-action (under 20 characters)"
        }

        prompt = f"""You are an expert ad copywriter. {field_prompts.get(body.field, 'Generate new copy')}.

BRAND VOICE: {body.brand.get('voice', 'Professional and friendly')}
PRODUCT: {body.product.get('name')}
TARGET AUDIENCE: {body.profile.get('demographics', 'General audience')}
CAMPAIGN: {body.campaignDetails.get('offer')}

Current {body.field}: {body.currentValue}

Generate a DIFFERENT, fresh variation that:
1. Matches the brand voice
2. Is compelling and conversion-focused
3. Follows the character limits

Return ONLY the new {body.field} text, nothing else."""

        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        response = model.generate_content(prompt)
        
        new_value = response.text.strip().strip('"').strip("'")
        
        return {"newValue": new_value}
        
    except Exception as e:
        log_and_raise_http_error(
            logger,
            "Field regeneration request failed",
            e,
            expose_detail=True,
        )
