from .base_agent import BaseAgent
from typing import Dict, Any

class MicroMovieAgent(BaseAgent):
    """
    Generates 30-60 second short stories based on 12 emotional avatars.
    Rule: Product must not be introduced until the emotional shift (40-50% through the story).
    """
    def generate_micro_movies(self, brief: Dict[str, Any], count: int = 2, avatar_type: str = "") -> list[Dict[str, str]]:
        avatar_instructions = f"Must use this specific avatar: '{avatar_type}'" if avatar_type else "Avatars/Personas should be diverse (e.g., Struggling Mom, Skeptical Pro, Relieved Customer)."
        prompt = self.load_prompt("micro_movie", count=count, avatar_instructions=avatar_instructions, **brief)
        result = self.generate_json(prompt)
        return result.get("movies", [])
