from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class AIPersonaBase(BaseModel):
    name: str
    description: Optional[str] = None
    visual_characteristics: Optional[Dict[str, Any]] = None
    voice_guidelines: Optional[str] = None
    base_image_url: Optional[str] = None

class AIPersonaCreate(AIPersonaBase):
    brand_id: str

class AIPersonaUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    visual_characteristics: Optional[Dict[str, Any]] = None
    voice_guidelines: Optional[str] = None
    base_image_url: Optional[str] = None

class AIPersona(AIPersonaBase):
    id: str
    brand_id: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
