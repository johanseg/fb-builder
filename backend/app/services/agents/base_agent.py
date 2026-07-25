from google import genai
import logging
import os
from collections import defaultdict
from typing import Dict, Any

from app.core.config import settings
from app.core.utils import extract_json_from_text

logger = logging.getLogger(__name__)

class BaseAgent:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        self.prompts_dir = os.path.join(os.path.dirname(__file__), 'prompts')

    def load_prompt(self, template_name: str, **kwargs) -> str:
        with open(os.path.join(self.prompts_dir, f"{template_name}.md"), "r") as f:
            template = f.read()
        return template.format_map(defaultdict(str, kwargs))

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            raise ValueError("Gemini API key not configured")
        response = self.client.models.generate_content(model=settings.GEMINI_MODEL, contents=prompt)
        return response.text.strip()

    def generate_json(self, prompt: str) -> Dict[str, Any]:
        text = self.generate(prompt)
        try:
            return extract_json_from_text(text)
        except Exception as exc:
            logger.exception("Agent failed to parse JSON response")
            raise ValueError("Agent failed to return valid JSON.") from exc
