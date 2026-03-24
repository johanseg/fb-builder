from .base_agent import BaseAgent
from typing import Dict, Any

class CtaAgent(BaseAgent):
    """
    Specializes in Call To Actions (10-20 seconds).
    Styles: Reason-Why, Risk-Reversal, Urgency/Scarcity, Free Content, Value-Stack, Premium-Anchor.
    """
    def generate_ctas(self, brief: Dict[str, Any], count: int = 4) -> list[Dict[str, str]]:
        prompt = self.load_prompt("cta", count=count, **brief)
        result = self.generate_json(prompt)
        return result.get("ctas", [])
