from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from app.database import get_db
from app.models import Product, User, AdModule
from app.core.deps import get_current_active_user, require_permission
from app.services.agents.orchestrator import AgentOrchestrator
from app.schemas.ad_module import AdModule as AdModuleSchema

router = APIRouter()
orchestrator = AgentOrchestrator()

class ModularGenerationRequest(BaseModel):
    product_id: str
    module_type: str  # "intro", "bridge", "core", "cta", "micro_movie"
    count: int = 5
    base_intro: Optional[str] = ""
    base_bridge: Optional[str] = ""
    avatar_type: Optional[str] = ""

class IterationRequest(BaseModel):
    module_id: str
    count: int = 3

@router.post("/generate", response_model=List[AdModuleSchema])
def generate_modular_scripts(
    request: ModularGenerationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("ads:write"))
):
    """Generate isolated modular script blocks and save to AdModule table."""
    
    product = db.query(Product).filter(Product.id == request.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
        
    if not product.pain_points:
        raise HTTPException(status_code=400, detail="Product Brief must be completed before generating modular scripts.")

    brief_dict = {
        "target_audience": "your target demographic",
        "primary_pain_points": ", ".join(product.pain_points) if product.pain_points else "",
        "desired_outcomes": ", ".join(product.desired_outcomes) if product.desired_outcomes else "",
        "root_causes_mechanisms": ", ".join(product.root_causes) if product.root_causes else "",
        "proof_points": ", ".join(product.proof_points) if product.proof_points else "",
        "differentiators": ", ".join(product.differentiators) if product.differentiators else "",
        "risk_reversals": ", ".join(product.risk_reversals) if product.risk_reversals else ""
    }

    try:
        db_modules = []

        if request.module_type == "intro":
            items = orchestrator.intro_agent.generate_intros(brief_dict, count=request.count)
            for item in items:
                db_modules.append(AdModule(
                    product_id=product.id,
                    module_type="intro",
                    content=item.get("text", ""),
                    generation_metadata={"hook_type": item.get("hook_type"), "format": item.get("format")}
                ))
        
        elif request.module_type == "bridge":
            if not request.base_intro:
                raise ValueError("base_intro is required to generate bridges.")
            items = orchestrator.bridge_agent.generate_bridges(brief_dict, request.base_intro, count=request.count)
            for item in items:
                db_modules.append(AdModule(
                    product_id=product.id,
                    module_type="bridge",
                    content=item.get("text", ""),
                    generation_metadata={"bridge_type": item.get("bridge_type")}
                ))

        elif request.module_type == "core":
            if not request.base_intro or not request.base_bridge:
                raise ValueError("base_intro and base_bridge are required to generate cores.")
            items = orchestrator.core_agent.generate_cores(brief_dict, request.base_intro, request.base_bridge, count=request.count)
            for item in items:
                db_modules.append(AdModule(
                    product_id=product.id,
                    module_type="core",
                    content=item.get("text", ""),
                    generation_metadata={"core_type": item.get("core_type")}
                ))

        elif request.module_type == "cta":
            items = orchestrator.cta_agent.generate_ctas(brief_dict, count=request.count)
            for item in items:
                db_modules.append(AdModule(
                    product_id=product.id,
                    module_type="cta",
                    content=item.get("text", ""),
                    generation_metadata={"cta_type": item.get("cta_type")}
                ))

        elif request.module_type == "micro_movie":
            items = orchestrator.micro_movie_agent.generate_micro_movies(brief_dict, count=request.count, avatar_type=request.avatar_type)
            for item in items:
                db_modules.append(AdModule(
                    product_id=product.id,
                    module_type="micro_movie",
                    content=item.get("text", ""),
                    generation_metadata={
                        "avatar_type": item.get("avatar_type"),
                        "hook_method": item.get("hook_method", "Product Drop")
                    }
                ))
        else:
            raise ValueError(f"Unknown module_type: {request.module_type}")

        if db_modules:
            db.add_all(db_modules)
            db.commit()
            for m in db_modules:
                db.refresh(m)

        return db_modules

    except Exception as e:
        print(f"Modular Generation Error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Script generation failed: {str(e)}")

@router.post("/iterate", response_model=List[AdModuleSchema])
def iterate_winning_module(
    request: IterationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("ads:write"))
):
    """
    US-013: Winner iteration engine.
    Takes an existing top-performing block and spawns slight variations.
    """
    source_mod = db.query(AdModule).filter(AdModule.id == request.module_id).first()
    if not source_mod:
        raise HTTPException(status_code=404, detail="Source module not found")
        
    product = db.query(Product).filter(Product.id == source_mod.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    brief_dict = {
        "target_audience": "your target demographic",
        "primary_pain_points": ", ".join(product.pain_points) if product.pain_points else "",
        "desired_outcomes": ", ".join(product.desired_outcomes) if product.desired_outcomes else "",
        "root_causes_mechanisms": ", ".join(product.root_causes) if product.root_causes else "",
        "proof_points": ", ".join(product.proof_points) if product.proof_points else "",
        "differentiators": ", ".join(product.differentiators) if product.differentiators else "",
        "risk_reversals": ", ".join(product.risk_reversals) if product.risk_reversals else ""
    }

    # Custom iteration instruction bypassing specific agents, using base orchestrator LLM directly
    iteration_prompt = f"You are iterating on a highly successful Facebook ad chunk. Analyze this winning {source_mod.module_type}:\n\n'{source_mod.content}'\n\nGenerate {request.count} new variations of this exact block. Keep the core psychology, hook mechanism, and value proposition the same, but rewrite the delivery, vocabulary, and pacing to create slight visual/auditory disruption. Output purely the script text variants as a markdown bulleted list. Do not include introductory text."
    
    agent = getattr(orchestrator, f"{source_mod.module_type}_agent", orchestrator.intro_agent)
    
    try:
        # Generate generic response leveraging Gemini directly via the agent's generative function
        # We will reuse the core logic but this invokes the LLM generically
        response = agent.model.generate_content(iteration_prompt)
        raw_response = response.text
        
        # Parse the bullet points
        lines = [line.strip().lstrip('-').lstrip('*').strip() for line in raw_response.split('\\n') if line.strip() and (line.strip().startswith('-') or line.strip().startswith('*') or line[0].isdigit())]
        
        if not lines:
            lines = [raw_response] # Fallback
            
        lines = lines[:request.count]
        
        db_modules = []
        for line in lines:
            new_mod = AdModule(
                product_id=source_mod.product_id,
                module_type=source_mod.module_type,
                content=line,
                generation_metadata={"parent_id": str(source_mod.id), "iteration": True, **(source_mod.generation_metadata or {})},
                performance_score=0
            )
            db.add(new_mod)
            db_modules.append(new_mod)
            
        db.commit()
        for m in db_modules:
            db.refresh(m)
            
        return db_modules
    except Exception as e:
        print(f"Iteration Error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Iteration failed: {str(e)}")
