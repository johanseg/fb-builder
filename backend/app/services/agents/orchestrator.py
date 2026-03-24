import uuid
from typing import Dict, Any, List
from .intro_agent import IntroAgent
from .bridge_agent import BridgeAgent
from .core_agent import CoreAgent
from .cta_agent import CtaAgent
from .micro_movie_agent import MicroMovieAgent

class AgentOrchestrator:
    """
    Orchestrates the individual agents to create the full Modular Matrix.
    """
    def __init__(self):
        self.intro_agent = IntroAgent()
        self.bridge_agent = BridgeAgent()
        self.core_agent = CoreAgent()
        self.cta_agent = CtaAgent()
        self.micro_movie_agent = MicroMovieAgent()

    def generate_modular_matrix(self, brief: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Runs the full waterfall generation.
        Returns a list of fully composed script blocks to be saved.
        """
        # 1. Generate Hooks
        intros = self.intro_agent.generate_intros(brief, count=3)
        
        # 2. Iterate to generate bridges for the first intro
        # (For a real factorial matrix we'd generate permutations, but to save context window 
        # we'll build a sequential spine or limit permutations)
        
        base_intro = intros[0]['text'] if intros else ""
        bridges = self.bridge_agent.generate_bridges(brief, base_intro, count=2)
        
        base_bridge = bridges[0]['text'] if bridges else ""
        cores = self.core_agent.generate_cores(brief, base_intro, base_bridge, count=2)
        
        ctas = self.cta_agent.generate_ctas(brief, count=2)

        # Build permutations
        scripts = []
        for i, intro in enumerate(intros):
            for b, bridge in enumerate(bridges):
                for c, core in enumerate(cores):
                    for t, cta in enumerate(ctas):
                        # Construct naming convention code e.g., I-PAIN-1_B-MECH-1_C-LOGIC-1_CTA-RISK-1
                        hook_slug = intro.get('hook_type', 'HOOK').upper()[:4]
                        bridge_slug = bridge.get('bridge_type', 'BRDG').upper()[:4]
                        core_slug = core.get('core_type', 'CORE').upper()[:4]
                        cta_slug = cta.get('cta_type', 'CTA').upper()[:4]
                        
                        code = f"I-{hook_slug}-{i}_B-{bridge_slug}-{b}_C-{core_slug}-{c}_CTA-{cta_slug}-{t}"
                        
                        scripts.append({
                            "intro_hook_type": intro.get('hook_type'),
                            "intro_format": intro.get('format'),
                            "intro_text": intro.get('text'),
                            "bridge_type": bridge.get('bridge_type'),
                            "bridge_text": bridge.get('text'),
                            "core_type": core.get('core_type'),
                            "core_text": core.get('text'),
                            "cta_type": cta.get('cta_type'),
                            "cta_text": cta.get('text'),
                            "naming_convention_code": code.replace(' ', '')
                        })

        return scripts

    def generate_micro_movies(self, brief: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self.micro_movie_agent.generate_micro_movies(brief, count=3)
