from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from typing import Dict, Any, List
from pydantic import BaseModel
import csv
import io
import re
from app.database import get_db
from app.models import AdModule, Brand, Product, User
from app.core.deps import require_permission, get_current_active_user

router = APIRouter()

class KillRuleFlag(BaseModel):
    module_id: str
    module_type: str
    content: str
    score: int
    spend: float
    status: str # "KILL" or "SCALE"
    reason: str

@router.post("/import")
async def import_performance_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("ads:write"))
):
    """
    Ingest a Facebook Ads CSV export.
    We extract the UUID fragments from the bundle code in the Ad Name to link back to modules.
    Scores are mapped 0-5 based on the deepest funnel event using the Retention-Driven Scoring System.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed detected.")

    contents = await file.read()
    try:
        decoded = contents.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Invalid file encoding. Please use UTF-8.")

    reader = csv.DictReader(io.StringIO(decoded))
    
    module_metrics = {}

    for row in reader:
        ad_name = row.get("Ad Name", "")
        spend_str = row.get("Amount spent (USD)", "0")
        
        try:
            spend = float(spend_str.replace(',', '')) if spend_str else 0.0
        except ValueError:
            spend = 0.0

        if spend == 0:
            continue

        # Extract deepest funnel event for the Fit Score
        # 5: AddPaymentInfo, 4: InitiateCheckout, 3: AddToCart, 2: Contact, 1: Lead, 0: CompleteRegistration
        
        def safe_int(val):
            try: return int(val.replace(',', '')) if val else 0
            except ValueError: return 0

        c_pay = safe_int(row.get("AddsPaymentInfo", "0"))
        c_chk = safe_int(row.get("InitiatesCheckout", "0"))
        c_atc = safe_int(row.get("AddsToCart", "0"))
        c_cnt = safe_int(row.get("Contacts", "0"))
        c_led = safe_int(row.get("Leads", "0"))
        c_reg = safe_int(row.get("CompleteRegistration", "0"))

        # Determine highest score for this particular ad row
        row_score = -1
        if c_pay > 0: row_score = 5
        elif c_chk > 0: row_score = 4
        elif c_atc > 0: row_score = 3
        elif c_cnt > 0: row_score = 2
        elif c_led > 0: row_score = 1
        elif c_reg > 0: row_score = 0
        
        # Format I-PAIN-Q-1a2b_B-MEC-3c4d...
        fragments = re.findall(r'-([a-f0-9]{4,8})(?:_|$)', ad_name.lower())
        
        for frag in fragments:
            if frag not in module_metrics:
                module_metrics[frag] = {"spend": 0.0, "max_score": -1}
            
            module_metrics[frag]["spend"] += spend
            if row_score > module_metrics[frag]["max_score"]:
                module_metrics[frag]["max_score"] = row_score

    updated_count = 0
    if not module_metrics:
        return {"message": "No matching bundle codes found in CSV. Updated 0 modules."}

    # Build OR filters to only load modules whose IDs start with a known fragment
    from sqlalchemy import or_, func as sa_func
    fragment_filters = [sa_func.lower(AdModule.id).like(f"{frag}%") for frag in module_metrics.keys()]
    all_modules = db.query(AdModule).filter(or_(*fragment_filters)).all()

    for mod in all_modules:
        mod_id_str = str(mod.id).lower()
        matched_frag = next((f for f in module_metrics.keys() if mod_id_str.startswith(f)), None)
        
        if matched_frag:
            metrics = module_metrics[matched_frag]
            final_score = max(0, metrics["max_score"]) # If -1 it remains 0
            
            mod.performance_score = final_score
            
            # Store raw metrics in metadata as copy to trigger SQLAlchemy change
            new_meta = dict(mod.generation_metadata or {})
            new_meta["total_spend"] = metrics["spend"]
            new_meta["verified_score"] = final_score
            mod.generation_metadata = new_meta
            
            flag_modified(mod, "generation_metadata")
            updated_count += 1

    db.commit()
    return {"message": f"Successfully processed CSV. Updated {updated_count} granular ad modules via Fit Score."}


@router.get("/kill-rule", response_model=List[KillRuleFlag])
def get_kill_rule_flags(
    brand_id: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    US-012: 7-Day Kill Rule using Fit Score mapping.
    Kill if Score <= 1 (Low Quality/Learning) and spend is significant.
    Scale if Score >= 4 (High Retention/Premium LTV).
    Spend threshold is configurable per brand via break_even_roas (defaults to $50).
    """
    # Get brand-specific spend threshold if brand_id provided
    spend_threshold = 50.0
    if brand_id:
        brand = db.query(Brand).filter(Brand.id == brand_id).first()
        if brand and brand.break_even_roas is not None:
            spend_threshold = brand.break_even_roas

    flags = []
    modules = db.query(AdModule).filter(AdModule.performance_score.isnot(None)).all()

    for mod in modules:
        meta = mod.generation_metadata or {}
        spend = meta.get("total_spend", 0)
        score = mod.performance_score or 0

        if spend > spend_threshold:
            if score <= 1:
                flags.append(KillRuleFlag(
                    module_id=str(mod.id),
                    module_type=mod.module_type,
                    content=mod.content,
                    score=score,
                    spend=spend,
                    status="KILL",
                    reason="Low Fit Score (Only Lead or lower). Kill & Replace this chunk."
                ))
            elif score >= 4:
                flags.append(KillRuleFlag(
                    module_id=str(mod.id),
                    module_type=mod.module_type,
                    content=mod.content,
                    score=score,
                    spend=spend,
                    status="SCALE",
                    reason="High Fit Score (Checkout/Purchase intent). Keep as control vector."
                ))

    return flags
