"""OpenAI API client extending BaseAIClient.

Uses GPT-5.1 with adaptive reasoning for complex segmentation tasks.
Supports multimodal (vision) inputs for image-aware validation.
"""

from __future__ import annotations

import os
import logging
from typing import Any, Literal

from .base_ai_client import BaseAIClient

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

logger = logging.getLogger(__name__)

ReasoningEffort = Literal["minimal", "low", "medium", "high"]


class OpenAIClient(BaseAIClient):
    """
    OpenAI API client for PDF to QTI pipeline.

    Uses GPT-5.1 with adaptive reasoning for complex segmentation tasks.
    """

    def __init__(self, model_name: str = "gpt-5.1"):
        """Initialize OpenAI client with GPT-5.1."""
        super().__init__(
            max_retries=3,
            base_delay=1.0,
            max_delay=60.0,
            rate_limit_per_minute=450,
        )

        if OpenAI is None:
            raise ImportError("OpenAI SDK not installed. Install with: pip install openai")

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.api_key = api_key
        self.model_name = model_name
        self.client = OpenAI(api_key=api_key)

    # =========================================================================
    # BaseAIClient Abstract Method Implementations
    # =========================================================================

    def _make_json_request(
        self, prompt: str, temperature: float, max_tokens: int, thinking_level: str
    ) -> Any:
        """Make OpenAI API call for JSON generation."""
        reasoning_effort = self._map_thinking_to_reasoning(thinking_level)
        return self._call_api(
            prompt, max_tokens, reasoning_effort, json_schema=None, use_json_mode=True
        )

    def _make_text_request(
        self, prompt: str, temperature: float, max_tokens: int, thinking_level: str
    ) -> Any:
        """Make OpenAI API call for text generation."""
        reasoning_effort = self._map_thinking_to_reasoning(thinking_level)
        return self._call_api(
            prompt, max_tokens, reasoning_effort, json_schema=None, use_json_mode=False
        )

    def _parse_response(self, response: Any) -> str:
        """Parse OpenAI response to extract content string."""
        if hasattr(response, "choices") and response.choices:
            content = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason
            if finish_reason == "length":
                logger.warning("Response hit token limit - may be truncated")
            return content
        else:
            raise Exception(f"Unexpected response format: {type(response)}")

    # =========================================================================
    # Multimodal (Vision) Support
    # =========================================================================

    def generate_json_with_images(
        self,
        prompt: str,
        images: list[dict[str, Any]],
        max_tokens: int = 8192,
        thinking_level: str = "high",
    ) -> dict[str, Any]:
        """Generate JSON response with image context for multimodal validation."""
        return self._generate_with_retry(
            lambda: self._make_multimodal_request(prompt, images, max_tokens, thinking_level),
            parse_json=True,
        )

    def _make_multimodal_request(
        self, prompt: str, images: list[dict[str, Any]], max_tokens: int, thinking_level: str
    ) -> Any:
        """Build and execute multimodal request with text + images."""
        content_parts: list[dict[str, Any]] = []
        
        for img in images:
            url = img.get("url") if isinstance(img, dict) else getattr(img, "url", None)
            if url:
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": url, "detail": "high"}
                })
        
        content_parts.append({"type": "text", "text": prompt})
        
        messages = [{"role": "user", "content": content_parts}]
        reasoning_effort = self._map_thinking_to_reasoning(thinking_level)
        
        logger.info(f"Sending multimodal request with {len(images)} image(s)")
        
        params = {
            "model": self.model_name,
            "messages": messages,
            "max_completion_tokens": max_tokens,
            "reasoning_effort": reasoning_effort,
            "verbosity": "medium",
            "seed": 42,
            "response_format": {"type": "json_object"},
        }
        
        return self.client.chat.completions.create(**params)

    # =========================================================================
    # GPT-5.1 Specific Implementation
    # =========================================================================

    def _map_thinking_to_reasoning(self, thinking_level: str) -> ReasoningEffort:
        """Map thinking_level to GPT-5.1 reasoning_effort."""
        mapping = {
            "low": "medium",
            "high": "high",
        }
        return mapping.get(thinking_level, "high")

    def _call_api(
        self,
        prompt: str,
        max_tokens: int,
        reasoning_effort: ReasoningEffort = "high",
        json_schema: Optional[Dict[str, Any]] = None,
        use_json_mode: bool = True,
    ) -> Any:
        """Make the actual API call to GPT-5.1."""
        messages = [{"role": "user", "content": prompt}]

        params = {
            "model": self.model_name,
            "messages": messages,
            "max_completion_tokens": max_tokens,
            "reasoning_effort": reasoning_effort,
            "verbosity": "medium",
            "seed": 42,
        }

        if json_schema:
            params["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "segmentation_result",
                    "schema": json_schema,
                    "strict": True
                }
            }
        elif use_json_mode:
            params["response_format"] = {"type": "json_object"}

        return self.client.chat.completions.create(**params)

