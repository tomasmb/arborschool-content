import base64
import io
import os
from dataclasses import dataclass
from typing import Any, List, Optional, Union

import google.generativeai as genai
import requests
from dotenv import load_dotenv
from google.api_core import exceptions as google_exceptions
from PIL import Image


class GeminiClient:
    """Wrapper for google-generativeai client."""

    def __init__(self, api_key: str, model: str) -> None:
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
                text = "".join(part.text for part in response.candidates[0].content.parts if hasattr(part, "text"))
            else:
                finish_reason = response.candidates[0].finish_reason if response.candidates else "unknown"
                raise ValueError(f"Gemini response has no text content. Finish reason: {finish_reason}. Original error: {e}") from e

        return type("Response", (), {"text": text})()


class OpenAIClient:
    """Lightweight client for OpenAI API with thinking support."""

    def __init__(self, api_key: str, model: str = "gpt-5.1") -> None:
        self._api_key = api_key
        self._model = model
        self._url = "https://api.openai.com/v1/chat/completions"

    def _pil_to_base64(self, pil_img: Image.Image) -> str:
        buffered = io.BytesIO()
        # Ensure image is in a web-compatible format
        if pil_img.mode in ("RGBA", "P"):
            pil_img = pil_img.convert("RGB")
        pil_img.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

    def generate_text(
        self,
        prompt: Union[str, List[Any]],
        *,
        response_mime_type: Optional[str] = None,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> str:
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

        messages: list[dict[str, Any]] = []
        content: list[dict[str, Any]] = []

        # Handle multimodal prompt
        if isinstance(prompt, list):
            for part in prompt:
                if isinstance(part, str):
                    content.append({"type": "text", "text": part})
                elif hasattr(part, "save"):  # Assume PIL Image
                    base64_img = self._pil_to_base64(part)
                    content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}})
        else:
            content.append({"type": "text", "text": str(prompt)})

        messages.append({"role": "user", "content": content})

        data = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
        }

        # Reasoning-capable models use max_completion_tokens
        if "gpt-5" in self._model or "o1" in self._model:
            data["max_completion_tokens"] = kwargs.get("max_tokens", 4000)
        else:
            data["max_tokens"] = kwargs.get("max_tokens", 4000)

        if response_mime_type == "application/json":
            data["response_format"] = {"type": "json_object"}

        response = requests.post(self._url, headers=headers, json=data, timeout=300)
        response.raise_for_status()

        return response.json()["choices"][0]["message"]["content"]


ENV_API_KEY = "GEMINI_API_KEY"


@dataclass
class GeminiConfig:
    """Runtime configuration for the Gemini client.

    The default model and behaviour follow our Gemini best practices documented in
    `docs/specifications/gemini-prompt-engineering-best-practices.md`.
    """

    api_key: str
    model: str = "gemini-3-pro-preview"
    thinking_level: str = "high"


class GeminiService:
    """Small, reusable wrapper around the Gemini client.

    This centralises how we talk to Gemini so that:
    - API keys are always read from the app-level `.env` file.
    - We consistently apply our prompt-engineering best practices.
    - Callers can opt into different response formats.
    """

    def __init__(self, config: GeminiConfig) -> None:
        self._config = config
        self._client = GeminiClient(api_key=config.api_key, model=config.model)

        # Initialize OpenAI fallback client
        openai_key = os.getenv("OPENAI_API_KEY")
        self._openai = OpenAIClient(api_key=openai_key) if openai_key else None

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
        """Generate a single text response from Gemini.

        Currently using `gemini-3-pro-preview`.

        Callers are responsible for constructing prompts that follow the
        guidelines in `docs/gemini-3-pro-prompt-engineering-best-practices.md`.

        Parameters:
        - `thinking_level`: Controls reasoning depth (default: "high").
        - `response_mime_type`: e.g. "application/json" for structured output.
        - `temperature`: use `0.0` for deterministic structured output.
        - `prompt`: Can be a string or a list of parts (including images).
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

        try:
            response = self._client.generate_text(prompt, **request_kwargs)
            return getattr(response, "text", str(response))
        except google_exceptions.ResourceExhausted as e:
            if self._openai:
                print(f"\n⚠️ Gemini Quota Exhausted (429). Falling back to OpenAI ({self._openai._model})...")
                try:
                    return self._openai.generate_text(prompt, response_mime_type=response_mime_type, temperature=temperature or 0.0, **kwargs)
                except Exception as oa_err:
                    print(f"❌ OpenAI Fallback also failed: {oa_err}")
                    raise oa_err
            else:
                print("❌ Gemini Quota Exhausted and no OpenAI key found.")
                raise e
        except Exception as e:
            # Re-raise other exceptions
            raise e


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
