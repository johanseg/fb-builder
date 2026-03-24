from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    product_shots: Optional[List[str]] = []
    default_url: Optional[str] = None
    pain_points: Optional[List[str]] = None
    desired_outcomes: Optional[List[str]] = None
    root_causes: Optional[List[str]] = None
    proof_points: Optional[List[str]] = None
    differentiators: Optional[List[str]] = None
    risk_reversals: Optional[List[str]] = None

class ProductCreate(ProductBase):
    id: Optional[str] = None
    brand_id: str

class ProductUpdate(ProductBase):
    pass

class Product(ProductBase):
    id: str
    brand_id: str
    created_at: datetime

    class Config:
        from_attributes = True


