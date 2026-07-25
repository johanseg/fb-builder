import os
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.v1.uploads import valid_media_signature
from app.core.deps import require_permission
from app.database import get_db
from app.models import User, WinningAd as WinningAdModel
from app.schemas.template import WinningAd
from app.services.storage import store_upload

router = APIRouter()
ALLOWED_TEMPLATE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_TEMPLATE_FILE_SIZE = 10 * 1024 * 1024


@router.get("/", response_model=List[WinningAd])
def read_winning_ads(
    search: Optional[str] = None,
    category: Optional[str] = None,
    style: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("templates:read")),
):
    query = db.query(WinningAdModel)
    if category:
        query = query.filter(WinningAdModel.template_category == category)
    if style:
        query = query.filter(WinningAdModel.design_style == style)
    if search:
        term = f"%{search}%"
        query = query.filter(
            (WinningAdModel.name.ilike(term))
            | (WinningAdModel.tags.ilike(term))
            | (WinningAdModel.product_name.ilike(term))
        )
    return query.all()


@router.get("/filters")
def read_template_filters(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("templates:read")),
):
    return {
        "categories": [
            value[0]
            for value in db.query(WinningAdModel.template_category)
            .distinct()
            .filter(WinningAdModel.template_category.isnot(None))
            .all()
        ],
        "styles": [
            value[0]
            for value in db.query(WinningAdModel.design_style)
            .distinct()
            .filter(WinningAdModel.design_style.isnot(None))
            .all()
        ],
    }


@router.get("/{template_id}/preview", response_model=WinningAd)
def read_template_preview(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("templates:read")),
):
    template = db.query(WinningAdModel).filter(WinningAdModel.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.post("/upload", response_model=List[WinningAd])
async def upload_winning_ad(
    images: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("templates:write")),
):
    saved_ads = []
    for image in images:
        extension = os.path.splitext(image.filename or "")[1].lower()
        if extension not in ALLOWED_TEMPLATE_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Invalid template file type")

        stream = image.file
        stream.seek(0, os.SEEK_END)
        if stream.tell() > MAX_TEMPLATE_FILE_SIZE:
            raise HTTPException(status_code=400, detail="Template image exceeds 10MB")
        stream.seek(0)
        if not valid_media_signature(extension, stream.read(32)):
            raise HTTPException(status_code=400, detail="Template content does not match its extension")

        filename = f"template_{uuid.uuid4()}{extension}"
        image_url = store_upload(stream, filename)
        new_ad = WinningAdModel(
            name=image.filename or filename,
            image_url=image_url,
            filename=filename,
            template_category="Uploaded",
            design_style="Unknown",
        )
        db.add(new_ad)
        saved_ads.append(new_ad)
    db.commit()
    for ad in saved_ads:
        db.refresh(ad)
    return saved_ads
