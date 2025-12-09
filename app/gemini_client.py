from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import google.generativeai as genai
from dotenv import load_dotenv

# Temporary adapter until google_gemini3_pro package is available
class GeminiClient:
    """Temporary adapter for google-generativeai until google_gemini3_pro is available."""

    def __init__(self, api_key: str, model: str) -> None:
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model)

    def generate_text(
        self,
        prompt: str,
        *,
        thinking_level: str | None = None,
        response_mime_type: str | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> Any:
        """Generate text using google-generativeai."""
        generation_config: dict[str, Any] = {}
        if temperature is not None:
            generation_config["temperature"] = temperature
        if response_mime_type:
            generation_config["response_mime_type"] = response_mime_type

        # Note: thinking_level may not be directly supported in google-generativeai
        # This is a temporary adapter
        response = self._model.generate_content(
            prompt,
            generation_config=generation_config if generation_config else None,
        )
        
        # Handle cases where response might be filtered or blocked
        if not response.candidates or not response.candidates[0].content:
            finish_reason = response.candidates[0].finish_reason if response.candidates else "unknown"
            raise ValueError(
                f"Gemini response was filtered or blocked. Finish reason: {finish_reason}. "
                f"This may be due to safety filters or content policy violations."
            )
        
        # Check if text is available
        try:
            text = response.text
        except ValueError as e:
            # If text accessor fails, try to get text from parts
            if response.candidates and response.candidates[0].content.parts:
                text = "".join(part.text for part in response.candidates[0].content.parts if hasattr(part, "text"))
            else:
                finish_reason = response.candidates[0].finish_reason if response.candidates else "unknown"
                raise ValueError(
                    f"Gemini response has no text content. Finish reason: {finish_reason}. "
                    f"Original error: {e}"
                ) from e
        
        return type("Response", (), {"text": text})()


ENV_API_KEY = "GEMINI_API_KEY"


@dataclass
class GeminiConfig:
    """Runtime configuration for the Gemini client.

    Currently using `gemini-3-pro-preview`. The default model and behaviour
    follow our Gemini best practices documented in
    `docs/gemini-3-pro-prompt-engineering-best-practices.md`.
    """

    api_key: str
    model: str = "gemini-3-pro-preview"
    thinking_level: str = "high"


class GeminiService:
    """Small, reusable wrapper around the Gemini client.

    Currently using `gemini-3-pro-preview`.

    This centralises how we talk to Gemini so that:
    - API keys are always read from the app-level `.env` file.
    - We consistently apply our prompt-engineering best practices.
    - Callers can opt into different response formats.
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
        """Generate a single text response from Gemini.

        Currently using `gemini-3-pro-preview`.

        Callers are responsible for constructing prompts that follow the
        guidelines in `docs/gemini-3-pro-prompt-engineering-best-practices.md`.

        Parameters:
        - `thinking_level`: Controls reasoning depth (default: "high").
        - `response_mime_type`: e.g. "application/json" for structured output.
        - `temperature`: use `0.0` for deterministic structured output.
        """

        # Note: thinking_level may not be directly supported in google-generativeai SDK
        # Keeping it in the API for compatibility
        _ = thinking_level or self._config.thinking_level

        request_kwargs: dict[str, Any] = {
            # thinking_level may not be supported by current SDK adapter
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

