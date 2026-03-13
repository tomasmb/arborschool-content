"""Small provider-aware text generation adapter for variant pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.llm_clients import load_default_gemini_service, load_default_openai_client

DEFAULT_GEMINI_MODEL = "gemini-3.1-pro-preview"
DEFAULT_OPENAI_MODEL = "gpt-5.4"


class TextService(Protocol):
    """Minimal interface used by planner/generator/validator."""

    def generate_text(self, prompt: str | list[Any], **kwargs: Any) -> str:
        """Return plain text response."""


@dataclass
class OpenAITextService:
    """Adapter that normalises OpenAIClient to the TextService protocol."""

    model: str = DEFAULT_OPENAI_MODEL

    def __post_init__(self) -> None:
        self._client = load_default_openai_client(model=self.model)

    def generate_text(self, prompt: str | list[Any], **kwargs: Any) -> str:
        response = self._client.generate_text(prompt, **kwargs)
        return response.text


def build_text_service(provider: str, model: str | None = None) -> TextService:
    """Create a provider-specific text service with a common interface."""

    normalized_provider = provider.strip().lower()
    if normalized_provider == "gemini":
        service = load_default_gemini_service()
        return service if model is None else load_default_gemini_service_for_model(model)
    if normalized_provider == "openai":
        return OpenAITextService(model=model or DEFAULT_OPENAI_MODEL)
    raise ValueError(f"Unsupported LLM provider: {provider}")


def load_default_gemini_service_for_model(model: str) -> TextService:
    """Construct a Gemini service pinned to a specific model."""
    service = load_default_gemini_service()
    if service.config.model == model:
        return service

    from app.llm_clients import GeminiConfig, GeminiService

    return GeminiService(GeminiConfig(api_key=service.config.api_key, model=model, thinking_level=service.config.thinking_level))
