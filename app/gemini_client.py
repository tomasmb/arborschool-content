from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from google_gemini3_pro import GeminiClient


ENV_API_KEY = "GEMINI_API_KEY"


@dataclass
class GeminiConfig:
    """Runtime configuration for the Gemini 3 Pro client.

    The default model and behaviour follow our Gemini 3 Pro best practices
    documented in `docs/gemini-3-pro-prompt-engineering-best-practices.md`.
    """

    api_key: str
    model: str = "gemini-3-pro"
    thinking_level: str = "high"  # "low" or "high" per Gemini docs


class GeminiService:
    """Small, reusable wrapper around the Gemini 3 Pro Python client.

    This centralises how we talk to Gemini so that:
    - API keys are always read from the app-level `.env` file.
    - We consistently apply our prompt-engineering best practices.
    - Callers can opt into different thinking levels or response formats.
    """

    def __init__(self, config: GeminiConfig) -> None:
        self._config = config
        self._client = GeminiClient(api_key=config.api_key, model=config.model)

    @property
    def config(self) -> GeminiConfig:
        return self._config

    def generate_text(
        self,
        prompt: str,
        *,
        thinking_level: str | None = None,
        response_mime_type: str | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> str:
        """Generate a single text response from Gemini 3 Pro.

        Callers are responsible for constructing prompts that follow the
        guidelines in `docs/gemini-3-pro-prompt-engineering-best-practices.md`.

        Parameters mirror the Gemini 3 configuration surface, but we keep the
        wrapper intentionally small and opinionated:
        - `thinking_level`: "low" for simple transformations, "high" for
          complex reasoning (Gemini 3 default).
        - `response_mime_type`: e.g. "application/json" for structured output.
        - `temperature`: use `0.0` for deterministic structured output; for most
          other cases rely on the model default as recommended in the Gemini
          3 docs (Nov–Dec 2025 guidance).
        """

        level = thinking_level or self._config.thinking_level

        request_kwargs: dict[str, Any] = {
            "thinking_level": level,
            **kwargs,
        }
        if response_mime_type is not None:
            request_kwargs["response_mime_type"] = response_mime_type
        if temperature is not None:
            request_kwargs["temperature"] = temperature

        response = self._client.generate_text(prompt, **request_kwargs)
        return getattr(response, "text", str(response))


def load_default_gemini_service() -> GeminiService:
    """Construct a `GeminiService` using configuration from the app `.env`.

    Expects `GEMINI_API_KEY` to be defined at the project root level. This
    keeps all Gemini credentials out of the codebase and aligns with our
    project rules around configuration.
    """

    load_dotenv()
    api_key = os.getenv(ENV_API_KEY)
    if not api_key:
        msg = f"Environment variable {ENV_API_KEY} is required for Gemini access."
        raise RuntimeError(msg)

    config = GeminiConfig(api_key=api_key)
    return GeminiService(config)

