from .base_agent import BaseAgent
from typing import Dict, Any

class CoreAgent(BaseAgent):
    """
    Specializes in Decision & Commitment Stage.
    A 5-block sequence: Solution Clarity -> Value Translation -> Differentiation Snapshot -> Risk/Friction Removal -> Action Clarity.
    Pathways: Core A 'Logic Lock', Core B 'Identity Close'.
    """
    def generate_cores(self, brief: Dict[str, Any], intro_context: str, bridge_context: str, count: int = 2) -> list[Dict[str, str]]:
        prompt = self.load_prompt("core", count=count, base_intro=intro_context, base_bridge=bridge_context, **brief)
        result = self.generate_json(prompt)
        return result.get("cores", [])
