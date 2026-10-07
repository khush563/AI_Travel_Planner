import json
from typing import Any, Protocol

from openai import OpenAI

from app.config import Settings


class JsonLLM(Protocol):
    def generate(self, instructions: str, input_data: dict[str, Any]) -> dict[str, Any]: ...


class OpenAIJsonLLM:
    def __init__(self, settings: Settings):
        if settings.llm_provider not in {"openai", "openai_compatible"}:
            raise ValueError("LLM_PROVIDER must be openai or openai_compatible")
        if settings.llm_provider == "openai_compatible" and not settings.llm_base_url:
            raise ValueError("LLM_BASE_URL is required for openai_compatible")
        self.settings = settings

    def generate(self, instructions: str, input_data: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required")
        client = OpenAI(
            api_key=self.settings.openai_api_key,
            base_url=self.settings.llm_base_url,
            timeout=self.settings.llm_timeout_seconds,
        )
        response = client.responses.create(
            model=self.settings.llm_model,
            instructions=instructions + " Return exactly one valid JSON object and no Markdown.",
            input=json.dumps(input_data, default=str),
            text={"format": {"type": "json_object"}},
        )
        return json.loads(response.output_text)

