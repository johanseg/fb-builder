from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from app.database import get_db
from app.models import AdModule, User
from app.core.deps import require_permission

router = APIRouter()

class AssembleRequest(BaseModel):
    intro_id: str
    bridge_id: str
    core_id: str
    cta_id: str

class AssembleResponse(BaseModel):
    bundle_code: str
    assembled_text: str

def generate_bundle_code(intro: AdModule, bridge: AdModule, core: AdModule, cta: AdModule) -> str:
    """Generate a trackable bundle code like I-PAIN-Q-03_B-MEC-A_C-LOGIC_CTA-RISKREV-01."""
    
    # Safely get metadata, fallback to generic types if missing
    intro_meta = intro.generation_metadata or {}
    bridge_meta = bridge.generation_metadata or {}
    core_meta = core.generation_metadata or {}
    cta_meta = cta.generation_metadata or {}

    # Extract hooks/types
    hook = str(intro_meta.get("hook_type", "HOOK")).split()[0].upper()[:4] # e.g., 'PAIN'
    fmt = str(intro_meta.get("format", "FMT")).split()[0].upper()[:1] # e.g., 'Q'
    
    bridge_type = str(bridge_meta.get("bridge_type", "B")).split()[0].upper()[:3] # 'MEC'
    core_type = str(core_meta.get("core_type", "CORE")).split()[0].upper()[:5] # 'LOGIC'
    cta_type = str(cta_meta.get("cta_type", "CTA")).split()[0].upper()[:7] # 'RISKREV'

    # Short UUIDs or sequence placeholders (last 4 chars of ID)
    i_id = str(intro.id)[-4:]
    
    return f"I-{hook}-{fmt}-{i_id}_B-{bridge_type}_C-{core_type}_CTA-{cta_type}"

@router.post("/assemble", response_model=AssembleResponse)
def assemble_modules(
    request: AssembleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("ads:write"))
):
    """Combine selected modules into a single trackable bundle."""
    
    # Fetch all modules efficiently
    module_ids = [request.intro_id, request.bridge_id, request.core_id, request.cta_id]
    modules = db.query(AdModule).filter(AdModule.id.in_(module_ids)).all()
    
    mod_map = {str(m.id): m for m in modules}
    
    try:
        intro = mod_map[request.intro_id]
        bridge = mod_map[request.bridge_id]
        core = mod_map[request.core_id]
        cta = mod_map[request.cta_id]
    except KeyError:
        raise HTTPException(status_code=404, detail="One or more modules not found.")

    bundle_code = generate_bundle_code(intro, bridge, core, cta)
    
    assembled_text = f"[{bundle_code}]\n\n"
    assembled_text += f"=== INTRO ===\n{intro.content}\n\n"
    assembled_text += f"=== BRIDGE ===\n{bridge.content}\n\n"
    assembled_text += f"=== CORE ===\n{core.content}\n\n"
    assembled_text += f"=== CTA ===\n{cta.content}"

    return AssembleResponse(
        bundle_code=bundle_code,
        assembled_text=assembled_text
    )

@router.get("/export-combinations/{product_id}")
def export_combinations(
    product_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("ads:read"))
):
    """
    US-015: PDCA Campaign export by Bridge type.
    Creates a structural CSV-ready payload matching all current modules for a product 
    using the Cartesian product.
    """
    intros = db.query(AdModule).filter(AdModule.product_id == product_id, AdModule.module_type == "intro").all()
    bridges = db.query(AdModule).filter(AdModule.product_id == product_id, AdModule.module_type == "bridge").all()
    cores = db.query(AdModule).filter(AdModule.product_id == product_id, AdModule.module_type == "core").all()
    ctas = db.query(AdModule).filter(AdModule.product_id == product_id, AdModule.module_type == "cta").all()

    if not all([intros, bridges, cores, ctas]):
        raise HTTPException(status_code=400, detail="Must have at least one of each module type (Intro, Bridge, Core, CTA) to export combinations.")

    rows = []
    ad_group_counter = {}
    # Cartesian product, grouped primarily by Bridge as per PDCA Inceptly spec
    for b in bridges:
        b_meta = b.generation_metadata or {}
        b_type = b_meta.get("bridge_type", "Standard")
        ad_group_counter.setdefault(b_type, 0)
        for i in intros:
            i_meta = i.generation_metadata or {}
            for c in cores:
                c_meta = c.generation_metadata or {}
                for cta_mod in ctas:
                    cta_meta = cta_mod.generation_metadata or {}
                    bundle_code = generate_bundle_code(i, b, c, cta_mod)
                    ad_group_counter[b_type] += 1
                    intro_code = f"{i_meta.get('hook_type', 'STD')}-{i_meta.get('format', 'STD')}"
                    core_pathway = c_meta.get("core_type", "Standard")
                    cta_style = cta_meta.get("cta_type", "Standard")

                    rows.append({
                        "AdGroup": f"AG-{b_type}",
                        "BridgeType": b_type,
                        "BundleCode": bundle_code,
                        "IntroCode": intro_code,
                        "CorePathway": core_pathway,
                        "CTAStyle": cta_style,
                        "AdName": bundle_code,
                        "Intro_Text": i.content,
                        "Bridge_Text": b.content,
                        "Core_Text": c.content,
                        "CTA_Text": cta_mod.content,
                    })
                    
    # Cap combinations to avoid massive memory payloads in browser (e.g. 5000 max)
    if len(rows) > 5000:
        rows = rows[:5000]

    return rows
