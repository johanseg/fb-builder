"""
Ad Remix API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import List
import json

from app.database import get_db
from app.models import WinningAd, Brand, Product, CustomerProfile, User
from app.core.deps import get_current_active_user
from app.core.rate_limit import limiter
from app.schemas.ad_blueprint import (
    AdBlueprint,
    AdBlueprintResponse,
    AdConcept,
    BrandData,
    DeconstructRequest,
    ReconstructRequest
)
from app.services.ad_remix_service import deconstruct_template, reconstruct_ad

router = APIRouter()


@router.post("/deconstruct", response_model=AdBlueprint)
@limiter.limit("10/minute")
async def deconstruct_ad_template(
    request: Request,
    body: DeconstructRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Deconstruct a template into a structural blueprint
    
    This analyzes the template image and extracts:
    - Layout framework
    - Narrative arc
    - Text hierarchy
    - Psychological triggers
    - Visual style guide
    """
    # Get the template
    template = db.query(WinningAd).filter(WinningAd.id == body.template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Deconstruct the template
    try:
        blueprint = await deconstruct_template(template.image_url)
        
        # Save the blueprint to the template
        template.blueprint_json = blueprint.model_dump()
        template.blueprint_analyzed_at = func.now()
        db.commit()
        
        return blueprint
        
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/reconstruct", response_model=AdConcept)
@limiter.limit("10/minute")
async def reconstruct_ad_from_blueprint(
    request: Request,
    body: ReconstructRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Reconstruct an ad by applying brand data to a blueprint
    
    This takes a template's blueprint and generates a new ad concept
    with your brand/product information while maintaining the proven structure.
    """
    # Get the template with blueprint
    template = db.query(WinningAd).filter(WinningAd.id == body.template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if not template.blueprint_json:
        raise HTTPException(
            status_code=400,
            detail="Template has not been deconstructed yet. Run /deconstruct first."
        )

    # Get brand, product, and profile data
    brand = db.query(Brand).filter(Brand.id == body.brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    product = db.query(Product).filter(Product.id == body.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    profile = db.query(CustomerProfile).filter(CustomerProfile.id == body.profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Customer profile not found")

    # Build brand data
    brand_data = BrandData(
        brand_name=brand.name,
        brand_voice=brand.voice,
        product_name=product.name,
        product_description=product.description or "",
        audience_demographics=profile.demographics or "",
        audience_pain_points=profile.pain_points or "",
        audience_goals=profile.goals or "",
        campaign_offer=body.campaign_offer,
        campaign_urgency=body.campaign_urgency,
        campaign_messaging=body.campaign_messaging
    )
    
    # Reconstruct the blueprint
    blueprint = AdBlueprint(**template.blueprint_json)
    
    try:
        ad_concept = await reconstruct_ad(blueprint, brand_data)
        return ad_concept
        
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/blueprints/{template_id}", response_model=AdBlueprint)
async def get_template_blueprint(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get the blueprint for a specific template
    """
    template = db.query(WinningAd).filter(WinningAd.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    if not template.blueprint_json:
        raise HTTPException(
            status_code=404,
            detail="Template has not been deconstructed yet"
        )
    
    return AdBlueprint(**template.blueprint_json)


@router.get("/blueprints", response_model=List[dict])
async def list_templates_with_blueprints(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all templates that have been deconstructed
    """
    templates = db.query(WinningAd).filter(WinningAd.blueprint_json.isnot(None)).all()
    
    return [
        {
            "template_id": t.id,
            "template_name": t.name,
            "blueprint": t.blueprint_json,
            "analyzed_at": t.blueprint_analyzed_at
        }
        for t in templates
    ]
