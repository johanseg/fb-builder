from .base_agent import BaseAgent
from typing import Dict, Any

class BridgeAgent(BaseAgent):
    """
    Specializes in Belief-Transition Layer (10-30 seconds).
    Types: Reframe, Mechanism, Permission, Contrast, Proof, Gradualization.
    """
    def generate_bridges(self, brief: Dict[str, Any], intro_context: str, count: int = 3) -> list[Dict[str, str]]:
        prompt = self.load_prompt("bridge", count=count, base_intro=intro_context, **brief)
        result = self.generate_json(prompt)
        return result.get("bridges", [])
