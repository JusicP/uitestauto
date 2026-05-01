import json
import google.genai as genai
from google.genai import types

from uitestauto.ai.base_agent import AbstractReActAgent, AgentResponse
from uitestauto.core.settings import SettingsManager


class GeminiAIAgent(AbstractReActAgent):
    @classmethod
    def supported_models(cls) -> list[str]:
        # FIXME: add more models or get from API?
        return [
            "gemini-2.0-flash",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-3-flash-preview",
            "gemini-3-pro",
        ]

    def __init__(self):
        super().__init__()
        self.settings = SettingsManager()
        self.api_key = self.settings.get_api_key()
        self.model_name = self.settings.get_ai_model()
        self.client: genai.Client | None = None

        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)

    def _ask_llm(self, prompt: str) -> AgentResponse:
        if not self.client:
            raise ValueError("Gemini API Key is missing. Please set it in Settings.")
            
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        raw_text = response.text
        if not raw_text:
            raise ValueError("Empty response from Gemini API.")
        
        # cleanup raw_text from markdown JSON blocks
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:]
            
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
            
        raw_text = raw_text.strip()
        result_dict = json.loads(raw_text)
        return AgentResponse(**result_dict)
