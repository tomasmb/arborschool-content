"""Gemini API client extending BaseAIClient.

Implements Gemini-specific API calls while inheriting shared
retry logic, rate limiting, and error handling from BaseAIClient.
"""

import os
import logging
from typing import Any, Dict, List

from .base_ai_client import BaseAIClient

# Try new SDK first, fallback to old SDK for compatibility
try:
    from google import genai
    from google.genai import types
    NEW_SDK_AVAILABLE = True
except ImportError:
    try:
        import google.generativeai as genai
        from google.generativeai.types import GenerationConfig, HarmCategory, HarmBlockThreshold
        NEW_SDK_AVAILABLE = False
    except ImportError:
        genai = None
        NEW_SDK_AVAILABLE = False

logger = logging.getLogger(__name__)


class GeminiClient(BaseAIClient):
    """
    Gemini API client for PDF to QTI pipeline.

    Inherits retry logic, rate limiting, and error handling from BaseAIClient.
    Implements Gemini-specific API calls and response parsing.
    """

    def __init__(self, model_name: str = "gemini-3-pro-preview"):
        """Initialize Gemini client."""
        super().__init__(
            max_retries=3,
            base_delay=1.0,
            max_delay=60.0,
            rate_limit_per_minute=23,
        )

        if genai is None:
            raise ImportError(
                "Gemini SDK not installed. Install with: "
                "pip install google-genai or pip install google-generativeai"
            )

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        self.api_key = api_key
        self.model_name = model_name

        if NEW_SDK_AVAILABLE:
            self.client = genai.Client(api_key=api_key)
            self._use_new_sdk = True
        else:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(
                model_name,
                safety_settings=self._get_safety_settings_old_sdk()
            )
            self._use_new_sdk = False

    # =========================================================================
    # BaseAIClient Abstract Method Implementations
    # =========================================================================

    def _make_json_request(
        self, prompt: str, temperature: float, max_tokens: int, thinking_level: str
    ) -> Any:
        """Make Gemini API call for JSON generation."""
        if self._use_new_sdk:
            return self._call_new_sdk(prompt, temperature, max_tokens, thinking_level, json_mode=True)
        else:
            return self._call_old_sdk(prompt, temperature, max_tokens, json_mode=True)

    def _make_text_request(
        self, prompt: str, temperature: float, max_tokens: int, thinking_level: str
    ) -> Any:
        """Make Gemini API call for text generation."""
        if self._use_new_sdk:
            return self._call_new_sdk(prompt, temperature, max_tokens, thinking_level, json_mode=False)
        else:
            return self._call_old_sdk(prompt, temperature, max_tokens, json_mode=False)

    def _parse_response(self, response: Any) -> str:
        """Parse Gemini response to extract content string."""
        if self._use_new_sdk:
            return self._parse_new_sdk_response(response)
        else:
            return self._parse_old_sdk_response(response)

    # =========================================================================
    # Multimodal (Vision) Support
    # =========================================================================

    def generate_json_with_images(
        self,
        prompt: str,
        images: List[Dict[str, Any]],
        max_tokens: int = 8192,
        thinking_level: str = "high",
    ) -> Dict[str, Any]:
        """Generate JSON response with image context for multimodal validation."""
        if not self._use_new_sdk:
            raise RuntimeError(
                "Multimodal image inputs require the new google-genai SDK. "
                "Install with: pip install google-genai"
            )
        
        return self._generate_with_retry(
            lambda: self._make_multimodal_request(prompt, images, max_tokens, thinking_level),
            parse_json=True,
        )

    def _make_multimodal_request(
        self, prompt: str, images: List[Dict[str, Any]], max_tokens: int, thinking_level: str
    ) -> Any:
        """Build and execute multimodal request with text + images."""
        content_parts = []
        
        for img in images:
            url = img.get("url") if isinstance(img, dict) else getattr(img, "url", None)
            if url:
                content_parts.append(types.Part.from_uri(file_uri=url, mime_type=None))
        
        content_parts.append(types.Part.from_text(prompt))
        
        effective_max_tokens = max(max_tokens, 32768)
        config_dict = {
            "temperature": 0.0,
            "max_output_tokens": effective_max_tokens,
            "safety_settings": self._get_safety_settings_new_sdk(),
            "response_mime_type": "application/json",
        }
        
        try:
            config = types.GenerateContentConfig(**config_dict, thinking_level=thinking_level)
        except (TypeError, ValueError):
            config = types.GenerateContentConfig(**config_dict)
        
        logger.info(f"Sending multimodal request with {len(images)} image(s)")
        
        return self.client.models.generate_content(
            model=self.model_name,
            contents=content_parts,
            config=config,
        )

    # =========================================================================
    # New SDK (google-genai) Implementation
    # =========================================================================

    def _call_new_sdk(
        self, prompt: str, temperature: float, max_tokens: int, thinking_level: str, json_mode: bool
    ) -> Any:
        """Make API call using new SDK."""
        effective_max_tokens = max(max_tokens, 32768) if max_tokens < 32768 else max_tokens

        config_dict = {
            "temperature": temperature,
            "max_output_tokens": effective_max_tokens,
            "safety_settings": self._get_safety_settings_new_sdk(),
        }

        if json_mode:
            config_dict["response_mime_type"] = "application/json"

        try:
            config = types.GenerateContentConfig(**config_dict, thinking_level=thinking_level)
        except (TypeError, ValueError):
            config = types.GenerateContentConfig(**config_dict)

        return self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config,
        )

    def _parse_new_sdk_response(self, response: Any) -> str:
        """Parse new SDK response format."""
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            finish_reason = getattr(candidate, "finish_reason", None)

            if finish_reason and str(finish_reason) in ["MAX_TOKENS", "FinishReason.MAX_TOKENS"]:
                logger.warning("Response hit MAX_TOKENS limit - output may be truncated")

            if hasattr(candidate, "content"):
                content_obj = candidate.content
                if hasattr(content_obj, "parts") and content_obj.parts:
                    text_parts = []
                    for part in content_obj.parts:
                        if hasattr(part, "text") and part.text:
                            text_parts.append(part.text)
                        elif hasattr(part, "inline_data"):
                            raise Exception("Response contains non-text content")
                    if text_parts:
                        return "".join(text_parts)
                    else:
                        raise Exception("Response parts contain no text")
                elif hasattr(content_obj, "text") and content_obj.text:
                    return content_obj.text
                else:
                    raise Exception(f"Response has empty content (finish_reason: {finish_reason})")
            else:
                raise Exception("Response candidate has no content attribute")

        elif hasattr(response, "text") and response.text:
            return response.text
        else:
            raise Exception(f"Unexpected response format: {type(response)}")

    def _get_safety_settings_new_sdk(self):
        """Get safety settings for new SDK to prevent blocking."""
        return [
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=types.HarmBlockThreshold.BLOCK_NONE
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=types.HarmBlockThreshold.BLOCK_NONE
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=types.HarmBlockThreshold.BLOCK_NONE
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.BLOCK_NONE
            ),
        ]

    # =========================================================================
    # Old SDK (google-generativeai) Implementation
    # =========================================================================

    def _call_old_sdk(
        self, prompt: str, temperature: float, max_tokens: int, json_mode: bool
    ) -> Any:
        """Make API call using old SDK."""
        config_dict = {
            "temperature": temperature,
            "top_p": 1.0,
            "top_k": 1,
            "max_output_tokens": max_tokens,
        }

        if json_mode:
            config_dict["response_mime_type"] = "application/json"

        config = GenerationConfig(**config_dict)
        return self.model.generate_content(prompt, generation_config=config)

    def _parse_old_sdk_response(self, response: Any) -> str:
        """Parse old SDK response format."""
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            finish_reason = getattr(candidate, "finish_reason", None)
            if finish_reason == 2:
                raise Exception(
                    f"Response blocked by safety filters (finish_reason=2). "
                    f"Safety ratings: {getattr(candidate, 'safety_ratings', 'N/A')}"
                )

        if hasattr(response, "text") and response.text:
            return response.text
        else:
            return str(response)

    def _get_safety_settings_old_sdk(self):
        """Get safety settings for old SDK to prevent blocking."""
        return [
            {"category": HarmCategory.HARM_CATEGORY_HATE_SPEECH, "threshold": HarmBlockThreshold.BLOCK_NONE},
            {"category": HarmCategory.HARM_CATEGORY_HARASSMENT, "threshold": HarmBlockThreshold.BLOCK_NONE},
            {"category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, "threshold": HarmBlockThreshold.BLOCK_NONE},
            {"category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, "threshold": HarmBlockThreshold.BLOCK_NONE},
        ]

