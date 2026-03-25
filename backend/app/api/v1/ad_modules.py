from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import AdModule
from app.schemas.ad_module import AdModuleCreate, AdModuleUpdate, AdModule as AdModuleSchema
from app.core.deps import get_current_active_user

router = APIRouter()

@router.post("/", response_model=AdModuleSchema)
def create_ad_module(
    ad_module: AdModuleCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    db_module = AdModule(
        product_id=ad_module.product_id,
        module_type=ad_module.module_type,
        content=ad_module.content,
        generation_metadata=ad_module.generation_metadata,
        performance_score=ad_module.performance_score,
        tags=ad_module.tags
    )
    db.add(db_module)
    db.commit()
    db.refresh(db_module)
    return db_module

@router.get("/", response_model=List[AdModuleSchema])
def get_ad_modules(
    product_id: str = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    query = db.query(AdModule)
    if product_id:
        query = query.filter(AdModule.product_id == product_id)
    return query.all()

@router.get("/{module_id}", response_model=AdModuleSchema)
def get_ad_module(
    module_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    db_module = db.query(AdModule).filter(AdModule.id == module_id).first()
    if not db_module:
        raise HTTPException(status_code=404, detail="Ad module not found")
    return db_module

@router.put("/{module_id}", response_model=AdModuleSchema)
def update_ad_module(
    module_id: str,
    update_data: AdModuleUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    db_module = db.query(AdModule).filter(AdModule.id == module_id).first()
    if not db_module:
        raise HTTPException(status_code=404, detail="Ad module not found")
    
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(db_module, key, value)
        
    db.commit()
    db.refresh(db_module)
    return db_module

@router.delete("/{module_id}")
def delete_ad_module(
    module_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    db_module = db.query(AdModule).filter(AdModule.id == module_id).first()
    if not db_module:
        raise HTTPException(status_code=404, detail="Ad module not found")
        
    db.delete(db_module)
    db.commit()
    return {"message": "Ad module deleted successfully"}
