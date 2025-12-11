"""Anthropic Claude API client via AWS Bedrock, extending BaseAIClient.

Uses Claude Opus 4.5 via AWS Bedrock for complex segmentation tasks.
Supports multimodal (vision) inputs for image-aware validation.
"""

import os
import json
import base64
import logging
from typing import Any, Dict, List

from .base_ai_client import BaseAIClient

try:
    import boto3
    from botocore.config import Config
except ImportError:
    boto3 = None

logger = logging.getLogger(__name__)


class AnthropicClient(BaseAIClient):
    """
    Anthropic Claude API client via AWS Bedrock for PDF to QTI pipeline.

    Uses Claude Opus 4.5 via Bedrock for complex segmentation tasks.
    """

    def __init__(self, model_name: str = "global.anthropic.claude-opus-4-5-20251101-v1:0"):
        """Initialize Anthropic client with Claude Opus 4.5 via Bedrock."""
        super().__init__(
            max_retries=3,
            base_delay=1.0,
            max_delay=60.0,
            rate_limit_per_minute=50,
        )

        if boto3 is None:
            raise ImportError("Boto3 not installed. Install with: pip install boto3")

        self.model_name = model_name
        self.region = os.environ.get("AWS_REGION", "us-east-1")
        self.client = self._create_bedrock_client()

    def _create_bedrock_client(self):
        """Create Bedrock runtime client."""
        config = Config(
            retries={"max_attempts": 0},
            read_timeout=300,
            connect_timeout=10,
        )
        
        client_kwargs = {
            "service_name": "bedrock-runtime",
            "region_name": self.region,
            "config": config,
        }
        
        endpoint_url = os.environ.get("BEDROCK_ENDPOINT_URL")
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url
            logger.info(f"Using custom Bedrock endpoint: {endpoint_url}")
        
        return boto3.client(**client_kwargs)

    # =========================================================================
    # BaseAIClient Abstract Method Implementations
    # =========================================================================

    def _make_json_request(
        self, prompt: str, temperature: float, max_tokens: int, thinking_level: str
    ) -> Any:
        """Make Bedrock API call for JSON generation."""
        return self._call_converse_api(
            prompt=prompt, temperature=temperature, max_tokens=max_tokens, json_mode=True
        )

    def _make_text_request(
        self, prompt: str, temperature: float, max_tokens: int, thinking_level: str
    ) -> Any:
        """Make Bedrock API call for text generation."""
        return self._call_converse_api(
            prompt=prompt, temperature=temperature, max_tokens=max_tokens, json_mode=False
        )

    def _parse_response(self, response: Any) -> str:
        """Parse Bedrock Converse response to extract content string."""
        if "output" in response and "message" in response["output"]:
            message = response["output"]["message"]
            if "content" in message and message["content"]:
                text_parts = []
                for block in message["content"]:
                    if "text" in block:
                        text_parts.append(block["text"])
                if text_parts:
                    return "".join(text_parts)
        
        stop_reason = response.get("stopReason", "")
        if stop_reason == "max_tokens":
            logger.warning("Response hit max_tokens limit - output may be truncated")
        
        raise Exception(f"Unexpected Bedrock response format: {response}")

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
        return self._generate_with_retry(
            lambda: self._make_multimodal_request(prompt, images, max_tokens),
            parse_json=True,
        )

    def _make_multimodal_request(
        self, prompt: str, images: List[Dict[str, Any]], max_tokens: int
    ) -> Any:
        """Build and execute multimodal request with text + images."""
        content_blocks = []
        
        for img in images:
            url = img.get("url") if isinstance(img, dict) else getattr(img, "url", None)
            if url:
                image_block = self._create_image_block(url)
                if image_block:
                    content_blocks.append(image_block)
        
        content_blocks.append({"text": prompt})
        
        logger.info(f"Sending multimodal request with {len(images)} image(s)")
        
        messages = [{"role": "user", "content": content_blocks}]
        
        inference_config = {
            "maxTokens": max(max_tokens, 32768),
            "temperature": 0.0,
        }
        
        system_prompt = (
            "You are an expert assistant. Always respond with valid JSON only, "
            "no additional text or markdown formatting."
        )
        
        return self.client.converse(
            modelId=self.model_name,
            messages=messages,
            system=[{"text": system_prompt}],
            inferenceConfig=inference_config,
        )

    def _create_image_block(self, url: str) -> Dict[str, Any]:
        """Create an image content block from a URL."""
        try:
            if url.startswith("data:"):
                parts = url.split(",", 1)
                if len(parts) == 2:
                    header, base64_data = parts
                    media_type = "image/png"
                    if "image/jpeg" in header or "image/jpg" in header:
                        media_type = "image/jpeg"
                    elif "image/gif" in header:
                        media_type = "image/gif"
                    elif "image/webp" in header:
                        media_type = "image/webp"
                    
                    return {
                        "image": {
                            "format": media_type.split("/")[1],
                            "source": {"bytes": base64.b64decode(base64_data)},
                        }
                    }
            else:
                import urllib.request
                with urllib.request.urlopen(url, timeout=30) as response:
                    image_data = response.read()
                    content_type = response.headers.get("Content-Type", "image/png")
                    
                    format_map = {
                        "image/jpeg": "jpeg", "image/jpg": "jpeg",
                        "image/png": "png", "image/gif": "gif", "image/webp": "webp",
                    }
                    image_format = format_map.get(content_type, "png")
                    
                    return {
                        "image": {
                            "format": image_format,
                            "source": {"bytes": image_data},
                        }
                    }
        except Exception as e:
            logger.warning(f"Failed to load image from {url}: {e}")
            return None

    # =========================================================================
    # Bedrock Converse API Implementation
    # =========================================================================

    def _call_converse_api(
        self, prompt: str, temperature: float, max_tokens: int, json_mode: bool = True
    ) -> Any:
        """Make the actual API call to Bedrock using Converse API."""
        messages = [{"role": "user", "content": [{"text": prompt}]}]
        
        inference_config = {
            "maxTokens": max(max_tokens, 32768) if max_tokens < 32768 else max_tokens,
            "temperature": temperature,
        }
        
        system_messages = []
        if json_mode:
            system_messages.append({
                "text": (
                    "You are an expert assistant. Always respond with valid JSON only, "
                    "no additional text, markdown formatting, or code blocks."
                )
            })
        
        kwargs = {
            "modelId": self.model_name,
            "messages": messages,
            "inferenceConfig": inference_config,
        }
        
        if system_messages:
            kwargs["system"] = system_messages
        
        return self.client.converse(**kwargs)

