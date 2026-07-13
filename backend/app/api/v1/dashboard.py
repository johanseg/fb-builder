from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Brand, Product, GeneratedAd, WinningAd, FacebookCampaign, User
from app.core.deps import get_current_active_user

router = APIRouter()

@router.get("/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get aggregated statistics for the dashboard.
    """
    counts = db.execute(
        select(
            select(func.count(Brand.id)).scalar_subquery().label("brands_count"),
            select(func.count(Product.id)).scalar_subquery().label("products_count"),
            select(func.count(GeneratedAd.id)).scalar_subquery().label("generated_ads_count"),
            select(func.count(WinningAd.id)).scalar_subquery().label("templates_count"),
            select(func.count(FacebookCampaign.id)).scalar_subquery().label("campaigns_count"),
        )
    ).one()

    return {
        "brands_count": counts.brands_count,
        "products_count": counts.products_count,
        "generated_ads_count": counts.generated_ads_count,
        "templates_count": counts.templates_count,
        "campaigns_count": counts.campaigns_count,
    }
