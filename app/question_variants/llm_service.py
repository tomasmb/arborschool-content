"""Small provider-aware text generation adapter for variant pipelines."""

from __future__ import annotations

import queue
import threading
import time
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


@dataclass
class RetryingTextService:
    """Variant-scoped timeout and retry wrapper around a base text service."""

    wrapped: TextService
    timeout_seconds: int = 180
    max_attempts: int = 2
    retry_delay_seconds: float = 2.0

    def generate_text(self, prompt: str | list[Any], **kwargs: Any) -> str:
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return self._generate_once(prompt, **kwargs)
            except Exception as exc:
                last_error = exc
                if attempt == self.max_attempts:
                    break
                time.sleep(self.retry_delay_seconds * attempt)
        assert last_error is not None
        raise last_error

    def _generate_once(self, prompt: str | list[Any], **kwargs: Any) -> str:
        result_queue: queue.Queue[tuple[bool, Any]] = queue.Queue(maxsize=1)

        def _run() -> None:
            try:
                result_queue.put((True, self.wrapped.generate_text(prompt, **kwargs)))
            except Exception as exc:  # pragma: no cover - thin transport wrapper
                result_queue.put((False, exc))

        worker = threading.Thread(target=_run, daemon=True)
        worker.start()

        try:
            ok, payload = result_queue.get(timeout=self.timeout_seconds)
        except queue.Empty as exc:
            raise TimeoutError(
                f"Variant LLM call exceeded {self.timeout_seconds}s timeout."
            ) from exc

        if ok:
            return str(payload)
        raise payload


def build_text_service(
    provider: str,
    model: str | None = None,
    *,
    timeout_seconds: int = 180,
    max_attempts: int = 2,
) -> TextService:
    """Create a provider-specific text service with a common interface."""

    normalized_provider = provider.strip().lower()
    if normalized_provider == "gemini":
        service = load_default_gemini_service() if model is None else load_default_gemini_service_for_model(model)
        return RetryingTextService(service, timeout_seconds=timeout_seconds, max_attempts=max_attempts)
    if normalized_provider == "openai":
        return RetryingTextService(
            OpenAITextService(model=model or DEFAULT_OPENAI_MODEL),
            timeout_seconds=timeout_seconds,
            max_attempts=max_attempts,
        )
    raise ValueError(f"Unsupported LLM provider: {provider}")


def load_default_gemini_service_for_model(model: str) -> TextService:
    """Construct a Gemini service pinned to a specific model."""
    service = load_default_gemini_service()
    if service.config.model == model:
        return service

    from app.llm_clients import GeminiConfig, GeminiService

    return GeminiService(GeminiConfig(api_key=service.config.api_key, model=model, thinking_level=service.config.thinking_level))
