from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class AdModuleBase(BaseModel):
    product_id: str
    module_type: str # 'intro', 'bridge', 'core', 'cta', 'micro_movie'
    content: str
    generation_metadata: Optional[Dict[str, Any]] = None
    performance_score: Optional[int] = 0
    tags: Optional[List[str]] = []

class AdModuleCreate(AdModuleBase):
    pass

class AdModuleUpdate(BaseModel):
    content: Optional[str] = None
    performance_score: Optional[int] = None
    tags: Optional[List[str]] = None

class AdModule(AdModuleBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
