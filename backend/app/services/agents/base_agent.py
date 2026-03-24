import google.generativeai as genai
import os
import json
from typing import Dict, Any

class BaseAgent:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-flash-latest')
        self.prompts_dir = os.path.join(os.path.dirname(__file__), 'prompts')

    def load_prompt(self, template_name: str, **kwargs) -> str:
        from collections import defaultdict
        with open(os.path.join(self.prompts_dir, f"{template_name}.md"), "r") as f:
            template = f.read()
        return template.format_map(defaultdict(str, kwargs))

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            raise ValueError("Gemini API key not configured")
        response = self.model.generate_content(prompt)
        return response.text.strip()

    def generate_json(self, prompt: str) -> Dict[str, Any]:
        text = self.generate(prompt)
        if text.startswith('```json'): text = text[7:]
        if text.startswith('```'): text = text[3:]
        if text.endswith('```'): text = text[:-3]
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            print(f"Failed to parse JSON for prompt: {prompt}")
            print(f"Got: {text}")
            raise ValueError("Agent failed to return valid JSON.")
