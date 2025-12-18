"""
llm_client.py
--------------
Centralised wrapper around AI providers used across the pdf-to-qti service.
Uses Gemini Preview 3 by default, with fallback to OpenAI GPT-5.1 when
Gemini credits are exhausted or unavailable.

All public helpers MUST keep every line shorter than 150 characters to
respect the project's formatting rules.
"""

from __future__ import annotations

import os
import logging
import time
import random
from typing import Any, Dict, List, Literal, Optional

from openai import OpenAI  # type: ignore  # SDK provided in requirements.txt

# Import retry handler
try:
    from ..utils.retry_handler import (
        is_retryable_error,
        extract_retry_after,
        retry_with_backoff,
    )
except ImportError:
    try:
        from modules.utils.retry_handler import (
            is_retryable_error,
            extract_retry_after,
            retry_with_backoff,
        )
    except ImportError:
        # Fallback if retry handler not available
        def is_retryable_error(e: Exception) -> bool:
            return False
        def extract_retry_after(e: Exception) -> Optional[float]:
            return None
        def retry_with_backoff(*args: Any, **kwargs: Any):
            def decorator(func: Any) -> Any:
                return func
            return decorator

# Import usage tracker
try:
    from ..utils.api_usage_tracker import log_api_usage
    USAGE_TRACKING_AVAILABLE = True
except ImportError:
    try:
        from modules.utils.api_usage_tracker import log_api_usage
        USAGE_TRACKING_AVAILABLE = True
    except ImportError:
        USAGE_TRACKING_AVAILABLE = False
        log_api_usage = None

# Try to import Gemini SDK
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    try:
        import google.generativeai as genai
        from google.generativeai.types import GenerationConfig
        GEMINI_AVAILABLE = True
        NEW_SDK = False
    except ImportError:
        genai = None
        GEMINI_AVAILABLE = False
        NEW_SDK = False

__all__ = [
    "chat_completion",
]


# Default provider: Gemini Preview 3 (same as rest of project)
_DEFAULT_PROVIDER = "gemini"
_DEFAULT_GEMINI_MODEL = "gemini-3-pro-preview"
_DEFAULT_OPENAI_MODEL = "gpt-5.1"

# GPT-5.1 reasoning effort levels
ReasoningEffort = Literal["minimal", "low", "medium", "high"]

_logger = logging.getLogger(__name__)


def _build_response_format(json_only: bool) -> Optional[Dict[str, Any]]:
    """Return the response_format parameter expected by the OpenAI SDK."""
    if json_only:
        # The service expects the model to *only* reply with a JSON object
        return {"type": "json_object"}
    return None


def _map_temperature_to_reasoning(temperature: Optional[float]) -> ReasoningEffort:
    """
    Map legacy temperature values to GPT-5.1 reasoning_effort.
    
    Lower temperature (more deterministic) maps to higher reasoning effort.
    For QTI conversion, we generally want high accuracy, so default to "high".
    """
    if temperature is None:
        return "high"
    if temperature <= 0.2:
        return "high"
    if temperature <= 0.5:
        return "medium"
    if temperature <= 0.8:
        return "low"
    return "minimal"


def _call_gemini(
    messages: List[Dict[str, Any]],
    gemini_api_key: str,
    *,
    json_only: bool = True,
    thinking_level: str = "high",
    max_tokens: int = 8192,
    **kwargs: Any,
) -> str:
    """Call Gemini API and return content."""
    if not GEMINI_AVAILABLE:
        raise ImportError("Gemini SDK not available. Install with: pip install google-genai")
    
    # Get Gemini API key from env if not provided
    api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not provided and not found in environment")
    
    # Try new SDK first
    try:
        client = genai.Client(api_key=api_key)
        model_name = _DEFAULT_GEMINI_MODEL
        
        # Convert messages to Gemini format
        # Gemini doesn't use system messages, combine all into user content
        parts = []
        full_text = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if isinstance(content, list):
                # Multimodal content (text + images)
                for item in content:
                    if item.get("type") == "text":
                        full_text.append(item["text"])
                    elif item.get("type") == "image_url":
                        # Handle image URLs
                        url = item.get("image_url", {}).get("url", "")
                        if url.startswith("data:"):
                            # Base64 image
                            import base64
                            try:
                                header, encoded = url.split(",", 1)
                                mime_type = header.split(":")[1].split(";")[0]
                                image_data = base64.b64decode(encoded)
                                # Correct API: Part.from_bytes takes data and mime_type as separate args
                                parts.append(types.Part.from_bytes(data=image_data, mime_type=mime_type))
                            except Exception as e:
                                _logger.warning(f"Failed to decode image: {e}")
            else:
                # Simple text content
                full_text.append(str(content))
        
        # Combine all text into one part
        if full_text:
            combined_text = "\n\n".join(full_text)
            # Correct API: Part.from_text takes text as keyword arg
            parts.insert(0, types.Part.from_text(text=combined_text))
        
        if not parts:
            raise ValueError("No content to send to Gemini")
        
        # Build config
        config_dict: Dict[str, Any] = {
            "temperature": 0.0,
            "max_output_tokens": max(max_tokens, 32768),
            "safety_settings": [],
        }
        
        if json_only:
            config_dict["response_mime_type"] = "application/json"
        
        try:
            config = types.GenerateContentConfig(**config_dict, thinking_level=thinking_level)
        except (TypeError, ValueError):
            config = types.GenerateContentConfig(**config_dict)
        
        # Use correct API for new SDK
        response = client.models.generate_content(
            model=model_name,
            contents=parts,
            config=config,
        )
        
        # Parse response
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "content"):
                content_obj = candidate.content
                if hasattr(content_obj, "parts"):
                    text_parts = [p.text for p in content_obj.parts if hasattr(p, "text")]
                    return "".join(text_parts)
        
        raise RuntimeError("Gemini response had no content")
        
    except Exception as e:
        _logger.warning(f"Gemini API call failed: {e}, falling back to OpenAI")
        raise


def _call_openai(
    messages: List[Dict[str, Any]],
    openai_api_key: str,
    *,
    model: str | None = None,
    json_only: bool = True,
    reasoning_effort: ReasoningEffort | None = None,
    **kwargs: Any,
) -> str:
    """Call OpenAI API and return content."""
    client = OpenAI(api_key=openai_api_key)
    
    chosen_model = model or _DEFAULT_OPENAI_MODEL
    response_format = _build_response_format(json_only)
    
    _logger.debug("Calling OpenAI model %s with %d message(s)", chosen_model, len(messages))
    
    params: Dict[str, Any] = {
        "model": chosen_model,
        "messages": messages,
    }
    
    if response_format:
        params["response_format"] = response_format
    
    is_gpt51 = chosen_model.startswith("gpt-5")
    
    if is_gpt51:
        effort = reasoning_effort
        if effort is None and "temperature" in kwargs:
            effort = _map_temperature_to_reasoning(kwargs.pop("temperature"))
        params["reasoning_effort"] = effort or "high"
        params["seed"] = 42
        
        if "max_tokens" in kwargs:
            params["max_completion_tokens"] = kwargs.pop("max_tokens")
    
    # Filtrar parámetros internos de tracking antes de pasar a OpenAI
    internal_params = {"_output_dir", "_question_id", "_operation"}
    filtered_kwargs = {k: v for k, v in kwargs.items() if k not in internal_params}
    
    for key, value in filtered_kwargs.items():
        if is_gpt51 and key == "temperature":
            continue
        params[key] = value
    
    # Retry logic with exponential backoff
    max_retries = 3
    base_delay = 2.0
    max_delay = 60.0
    last_exception: Optional[Exception] = None
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(**params)
            break
        except Exception as e:
            last_exception = e
            
            # Check if error is retryable
            if not is_retryable_error(e):
                _logger.error(f"Non-retryable error in OpenAI call: {e}")
                raise
            
            # Don't retry on last attempt
            if attempt == max_retries - 1:
                _logger.error(
                    f"Max retries ({max_retries}) reached for OpenAI call: {e}"
                )
                raise
            
            # Calculate delay
            delay = extract_retry_after(e)
            if delay is None:
                # Exponential backoff with jitter
                delay = min(base_delay * (2 ** attempt), max_delay)
                jitter = random.uniform(0, delay * 0.1)
                delay += jitter
            
            _logger.warning(
                f"Retryable error in OpenAI call (attempt {attempt + 1}/{max_retries}): "
                f"{e}. Retrying in {delay:.2f}s..."
            )
            time.sleep(delay)
    
    if last_exception and 'response' not in locals():
        raise last_exception
    
    # Track API usage if available
    if USAGE_TRACKING_AVAILABLE and hasattr(response, "usage"):
        usage = response.usage
        # Get output_dir from kwargs if provided (for per-question tracking)
        output_dir = kwargs.get("_output_dir")
        question_id = kwargs.get("_question_id")
        operation = kwargs.get("_operation", "api_call")
        
        # Extract cached tokens safely
        cached_tokens = 0
        if hasattr(usage, "prompt_tokens_details"):
            prompt_details = usage.prompt_tokens_details
            if hasattr(prompt_details, "cached_tokens"):
                cached_tokens = prompt_details.cached_tokens
            elif isinstance(prompt_details, dict):
                cached_tokens = prompt_details.get("cached_tokens", 0)
        
        log_api_usage(
            provider="openai",
            model=chosen_model,
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            cached_input_tokens=cached_tokens,
            question_id=question_id,
            output_dir=output_dir,
            operation=operation,
        )
    
    content = response.choices[0].message.content
    if content is None:
        raise RuntimeError("OpenAI response had no content")
    
    finish_reason = response.choices[0].finish_reason
    if finish_reason == "length":
        _logger.warning("Response hit token limit - may be truncated")
        # Aún así, intentar usar el contenido parcial si existe
        if not content or not content.strip():
            raise RuntimeError("Response hit token limit and content is empty - increase max_tokens")
    
    if json_only:
        first_char = content.strip()[0] if content else ""
        if first_char not in "{[":
            _logger.warning("Expected JSON response but got: %s…", content[:80])
    
    return content


def chat_completion(
    messages: List[Dict[str, Any]],
    api_key: str | None = None,
    *,
    model: str | None = None,
    json_only: bool = True,
    reasoning_effort: ReasoningEffort | None = None,
    thinking_level: str = "high",
    provider: str | None = None,
    max_tokens: int = 8192,
    output_dir: str | None = None,
    question_id: str | None = None,
    operation: str = "api_call",
    **kwargs: Any,
) -> str:
    """Call the LLM and return the content of the first choice.
    
    Uses Gemini Preview 3 by default, with automatic fallback to OpenAI GPT-5.1
    if Gemini fails (e.g., credits exhausted).

    Parameters
    ----------
    messages:
        List of chat messages as expected by the OpenAI Chat Completions API.
    api_key:
        API key (Gemini or OpenAI). If None, uses GEMINI_API_KEY from env.
    model:
        Model name (for OpenAI). Ignored for Gemini.
    json_only:
        If ``True`` (default) instruct the model to respond with JSON.
    reasoning_effort:
        OpenAI GPT-5.1 reasoning effort level (ignored for Gemini).
    thinking_level:
        Gemini thinking level: "low" or "high" (default: "high").
    provider:
        Force provider: "gemini" or "openai". If None, uses default (Gemini).
    max_tokens:
        Maximum output tokens.
    **kwargs:
        Additional arguments forwarded to the provider.

    Returns
    -------
    str
        The text content of the first LLM choice.
    """
    # Determine provider
    if provider is None:
        provider = _DEFAULT_PROVIDER
    
    # Get API keys from environment if not provided
    gemini_key = os.environ.get("GEMINI_API_KEY") if api_key is None else None
    openai_key = os.environ.get("OPENAI_API_KEY") if api_key is None else None
    
    # If api_key provided, try to determine which provider it's for
    if api_key:
        if provider == "gemini" or (provider is None and gemini_key):
            gemini_key = api_key
        else:
            openai_key = api_key
    
    # Pass tracking parameters to kwargs
    if output_dir:
        kwargs["_output_dir"] = output_dir
    if question_id:
        kwargs["_question_id"] = question_id
    kwargs["_operation"] = operation
    
    # Try Gemini first (if provider is gemini or default)
    if provider == "gemini" or (provider is None and gemini_key):
        try:
            _logger.info("Using Gemini Preview 3")
            result = _call_gemini(
                messages,
                gemini_key or "",
                json_only=json_only,
                thinking_level=thinking_level,
                max_tokens=max_tokens,
                **kwargs,
            )
            # TODO: Track Gemini usage when response object is available
            return result
        except Exception as e:
            _logger.warning(f"Gemini failed: {e}, falling back to OpenAI")
            # Fall through to OpenAI
    
    # Fallback to OpenAI
    if not openai_key:
        openai_key = os.environ.get("OPENAI_API_KEY")
    
    if not openai_key:
        raise ValueError(
            "No API key available. Provide api_key or set "
            "GEMINI_API_KEY/OPENAI_API_KEY in environment"
        )
    
    _logger.info("Using OpenAI GPT-5.1 (fallback)")
    return _call_openai(
        messages,
        openai_key,
        model=model,
        json_only=json_only,
        reasoning_effort=reasoning_effort,
        max_tokens=max_tokens,
        **kwargs,
    ) 