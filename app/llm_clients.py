import base64
import io
import logging
import os
from dataclasses import dataclass, field
from typing import Any, List, Optional, Union

import requests
from dotenv import load_dotenv
from PIL import Image

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Token / cost tracking dataclasses
# ---------------------------------------------------------------------------


@dataclass
class LLMUsage:
    """Token usage from a single LLM call."""

    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""


@dataclass
class LLMResponse:
    """LLM response bundled with token usage.

    Callers that only need the text can use ``resp.text``.
    Cost-aware callers can inspect ``resp.usage``.
    """

    text: str
    usage: LLMUsage = field(default_factory=LLMUsage)


# ---------------------------------------------------------------------------
# Global cost accumulator hook (set by pipeline orchestrators)
# ---------------------------------------------------------------------------

# When set, every OpenAIClient.generate_text call automatically feeds
# usage into this accumulator.  Pipeline code sets it before a run
# and calls .report() at the end.
_global_cost_accumulator: Any = None


def set_cost_accumulator(acc: Any) -> None:
    """Install a CostAccumulator for automatic usage tracking."""
    global _global_cost_accumulator
    _global_cost_accumulator = acc


def clear_cost_accumulator() -> None:
    """Remove the global cost accumulator."""
    global _global_cost_accumulator
    _global_cost_accumulator = None


# Lazy import for google-generativeai - only loaded when GeminiClient is used
# This allows OpenAIClient to be imported without requiring google-generativeai
genai = None
google_exceptions = None


def _ensure_google_imports() -> None:
    """Lazy import of google-generativeai to avoid import errors when not using Gemini."""
    global genai, google_exceptions
    if genai is None:
        import google.generativeai as _genai
        from google.api_core import exceptions as _google_exceptions
        genai = _genai
        google_exceptions = _google_exceptions


class GeminiClient:
    """Wrapper for google-generativeai client."""

    def __init__(self, api_key: str, model: str) -> None:
        _ensure_google_imports()
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model)

    def generate_text(
        self,
        prompt: str | list[Any],
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

        # Relax safety filters to avoid false positives in math questions
        safety_settings = {
            genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
            genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai.types.HarmBlockThreshold.BLOCK_NONE,
            genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: genai.types.HarmBlockThreshold.BLOCK_NONE,
            genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
        }

        # Use longer timeout for large prompts
        request_options = {"timeout": 1200}  # 20 minutes (1200 seconds)
        response = self._model.generate_content(
            prompt,
            generation_config=generation_config if generation_config else None,
            request_options=request_options,
            safety_settings=safety_settings,
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
                text = "".join(
                    part.text
                    for part in response.candidates[0].content.parts
                    if hasattr(part, "text")
                )
            else:
                finish_reason = (
                    response.candidates[0].finish_reason
                    if response.candidates else "unknown"
                )
                raise ValueError(
                    f"Gemini response has no text content. "
                    f"Finish reason: {finish_reason}. "
                    f"Original error: {e}"
                ) from e

        # Extract token usage from response metadata
        usage = LLMUsage(model=self._model._model_name)
        try:
            meta = response.usage_metadata
            if meta:
                usage.input_tokens = getattr(
                    meta, "prompt_token_count", 0,
                ) or 0
                usage.output_tokens = getattr(
                    meta, "candidates_token_count", 0,
                ) or 0
        except Exception:
            pass  # Usage tracking is best-effort

        return LLMResponse(text=text, usage=usage)


class OpenAIClient:
    """Client for OpenAI Chat Completions with reasoning-effort support."""

    _VALID_EFFORTS = {"none", "low", "medium", "high"}

    def __init__(self, api_key: str, model: str = "gpt-5.1") -> None:
        self._api_key = api_key
        self._model = model
        self._url = "https://api.openai.com/v1/chat/completions"

    def _pil_to_base64(self, pil_img: Image.Image) -> str:
        """Convert a PIL image to a base64-encoded JPEG string."""
        buffered = io.BytesIO()
        if pil_img.mode in ("RGBA", "P"):
            pil_img = pil_img.convert("RGB")
        pil_img.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

    # ------------------------------------------------------------------
    # Core generation
    # ------------------------------------------------------------------

    def generate_text(
        self,
        prompt: Union[str, List[Any]],
        *,
        reasoning_effort: Optional[str] = None,
        response_mime_type: Optional[str] = None,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> LLMResponse:
        """Call Chat Completions API, return ``LLMResponse(text, usage)``."""
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        messages = [
            {"role": "user", "content": self._build_content(prompt)},
        ]

        data: dict[str, Any] = {
            "model": self._model, "messages": messages,
        }

        # --- reasoning vs temperature (mutually exclusive) ---
        is_reasoning_model = (
            "gpt-5" in self._model or "o1" in self._model
        )
        uses_reasoning = (
            reasoning_effort is not None
            and reasoning_effort != "none"
        )

        if is_reasoning_model and uses_reasoning:
            data["reasoning_effort"] = reasoning_effort
        else:
            data["temperature"] = temperature

        # --- JSON mode ---
        if response_mime_type == "application/json":
            data["response_format"] = {"type": "json_object"}

        resp = requests.post(
            self._url, headers=headers, json=data, timeout=300,
        )
        resp.raise_for_status()
        body = resp.json()

        text = body["choices"][0]["message"]["content"]

        # Extract token usage
        usage = LLMUsage(model=self._model)
        raw_usage = body.get("usage")
        if raw_usage:
            usage.input_tokens = raw_usage.get(
                "prompt_tokens", 0,
            )
            usage.output_tokens = raw_usage.get(
                "completion_tokens", 0,
            )

        # Auto-feed global cost accumulator when installed
        if _global_cost_accumulator is not None:
            _global_cost_accumulator.add(usage)

        return LLMResponse(text=text, usage=usage)

    # ------------------------------------------------------------------
    # Multimodal helper  (DRY -- used by enhancer / validator)
    # ------------------------------------------------------------------

    def call_with_images(
        self,
        prompt: str,
        images: list[Any],
        *,
        reasoning_effort: Optional[str] = None,
        response_mime_type: Optional[str] = None,
    ) -> LLMResponse:
        """Send *prompt* to the LLM, attaching *images* when present.

        Eliminates the duplicated ``if images … else …`` dispatch
        pattern that was repeated across enhancer / validator callers.
        """
        kwargs: dict[str, Any] = {
            "reasoning_effort": reasoning_effort,
            "response_mime_type": response_mime_type,
        }

        if images:
            multimodal_prompt: list[Any] = [prompt, *images]
            return self.generate_text(multimodal_prompt, **kwargs)
        return self.generate_text(prompt, **kwargs)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_content(
        self, prompt: Union[str, List[Any]],
    ) -> list[dict[str, Any]]:
        """Convert a prompt (str or list of parts) to API content array."""
        content: list[dict[str, Any]] = []
        if isinstance(prompt, list):
            for part in prompt:
                if isinstance(part, str):
                    content.append({"type": "text", "text": part})
                elif hasattr(part, "save"):  # PIL Image
                    b64 = self._pil_to_base64(part)
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64}",
                        },
                    })
        else:
            content.append({"type": "text", "text": str(prompt)})
        return content


# ---------------------------------------------------------------------------
# Gemini Image Generation (uses google-genai SDK)
# ---------------------------------------------------------------------------

# Default model for image generation.
# Nano Banana Pro (gemini-3-pro-image-preview) delivers significantly
# higher mathematical accuracy than Gemini 2.5 Flash Image — critical
# for function graphs, statistical charts, and number lines.
_IMAGE_MODEL = "gemini-3-pro-image-preview"


class GeminiImageClient:
    """Client for Gemini image generation using the google-genai SDK.

    Uses the newer google.genai SDK which supports native image
    generation via response_modalities=['TEXT', 'IMAGE'].
    """

    def __init__(
        self, api_key: str, model: str = _IMAGE_MODEL,
    ) -> None:
        from google import genai as google_genai

        self._client = google_genai.Client(api_key=api_key)
        self._model = model

    def generate_image(self, prompt: str) -> bytes | None:
        """Generate an image from a text prompt.

        Args:
            prompt: Detailed description of the image to generate.

        Returns:
            Raw PNG bytes if generation succeeded, None otherwise.
        """
        from google.genai import types as genai_types

        response = self._client.models.generate_content(
            model=self._model,
            contents=[prompt],
            config=genai_types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
            ),
        )

        # Extract image data from response parts
        if not response.candidates:
            return None

        for part in response.parts:
            if part.inline_data is not None:
                return part.inline_data.data

        return None


ENV_API_KEY = "GEMINI_API_KEY"


@dataclass
class GeminiConfig:
    """Runtime config for Gemini (see gemini best-practices doc)."""

    api_key: str
    model: str = "gemini-3-pro-preview"
    thinking_level: str = "high"


class GeminiService:
    """Reusable Gemini wrapper with OpenAI quota-fallback."""

    def __init__(self, config: GeminiConfig) -> None:
        self._config = config
        self._client = GeminiClient(
            api_key=config.api_key, model=config.model,
        )
        openai_key = os.getenv("OPENAI_API_KEY")
        self._openai = (
            OpenAIClient(api_key=openai_key) if openai_key else None
        )

    @property
    def config(self) -> GeminiConfig:
        return self._config

    def generate_text(
        self,
        prompt: str | list[Any],
        *,
        thinking_level: str | None = None,
        response_mime_type: str | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> str:
        """Generate text via Gemini, falling back to OpenAI on 429."""
        _ = thinking_level or self._config.thinking_level
        request_kwargs: dict[str, Any] = {**kwargs}
        if response_mime_type is not None:
            request_kwargs["response_mime_type"] = response_mime_type
        if temperature is not None:
            request_kwargs["temperature"] = temperature

        try:
            resp = self._client.generate_text(
                prompt, **request_kwargs,
            )
            return resp.text if isinstance(resp, LLMResponse) else str(resp)
        except google_exceptions.ResourceExhausted as e:
            if self._openai:
                _logger.warning("Gemini 429 — falling back to OpenAI")
                fb = self._openai.generate_text(
                    prompt,
                    reasoning_effort="low",
                    response_mime_type=response_mime_type,
                )
                return fb.text
            raise e


def load_default_gemini_service() -> GeminiService:
    """Construct a ``GeminiService`` from ``GEMINI_API_KEY`` env var."""
    load_dotenv()
    api_key = os.getenv(ENV_API_KEY)
    if not api_key:
        raise RuntimeError(f"{ENV_API_KEY} is required.")
    return GeminiService(GeminiConfig(api_key=api_key))


def load_default_openai_client(
    model: str = "gpt-5.1",
) -> OpenAIClient:
    """Construct an ``OpenAIClient`` from ``OPENAI_API_KEY`` env var."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required.")
    return OpenAIClient(api_key=api_key, model=model)


def load_default_gemini_image_client(
    model: str = _IMAGE_MODEL,
) -> GeminiImageClient:
    """Construct a ``GeminiImageClient`` from ``GEMINI_API_KEY`` env var."""
    load_dotenv()
    api_key = os.getenv(ENV_API_KEY)
    if not api_key:
        raise RuntimeError(f"{ENV_API_KEY} is required.")
    return GeminiImageClient(api_key=api_key, model=model)
