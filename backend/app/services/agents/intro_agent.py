from .base_agent import BaseAgent
from typing import Dict, Any

class IntroAgent(BaseAgent):
    """
    Specializes in Pattern-Interrupt Layer (3-7 seconds)
    Focuses on: Desire Creation, Curiosity, Pain Activation, Alternative Disruption, Direct Intent Capture
    Formats: Bold Assertion, Question, Direct Qualification, Open Loop, Problem Framing, Contrast/Reframe
    """
    def generate_intros(self, brief: Dict[str, Any], count: int = 5) -> list[Dict[str, str]]:
        prompt = self.load_prompt("intro", count=count, **brief)
        result = self.generate_json(prompt)
        return result.get("intros", [])
