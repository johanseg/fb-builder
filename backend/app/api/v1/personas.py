from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import AIPersona, Brand, User
from app.schemas.ai_persona import AIPersona as AIPersonaSchema, AIPersonaCreate, AIPersonaUpdate
from app.core.deps import get_current_active_user, require_permission

router = APIRouter()

@router.get("/", response_model=List[AIPersonaSchema])
def list_personas(
    brand_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """US-010: List all custom AI Personas for a brand"""
    return db.query(AIPersona).filter(AIPersona.brand_id == brand_id).all()

@router.post("/", response_model=AIPersonaSchema)
def create_persona(
    persona_in: AIPersonaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("brands:write"))
):
    """Create a new custom AI Persona"""
    # Verify brand
    brand = db.query(Brand).filter(Brand.id == persona_in.brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    new_persona = AIPersona(**persona_in.model_dump())
    db.add(new_persona)
    db.commit()
    db.refresh(new_persona)
    return new_persona

@router.put("/{persona_id}", response_model=AIPersonaSchema)
def update_persona(
    persona_id: str,
    persona_in: AIPersonaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("brands:write"))
):
    """Update custom AI Persona"""
    db_persona = db.query(AIPersona).filter(AIPersona.id == persona_id).first()
    if not db_persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    update_data = persona_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_persona, field, value)

    db.commit()
    db.refresh(db_persona)
    return db_persona

@router.delete("/{persona_id}")
def delete_persona(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("brands:delete"))
):
    """Delete a custom AI Persona"""
    db_persona = db.query(AIPersona).filter(AIPersona.id == persona_id).first()
    if not db_persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    db.delete(db_persona)
    db.commit()
    return {"message": "Persona successfully deleted"}
