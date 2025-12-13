"""
llm_client.py
--------------
Centralised wrapper around the OpenAI Python SDK used across the
pdf-to-qti service.  Having all LLM calls go through a single helper
ensures a consistent configuration, makes it easy to swap models or add
retry / logging logic and avoids code duplication.

Uses GPT-5.1 with adaptive reasoning for complex PDF-to-QTI conversion tasks.

GPT-5.1 Best Practices (per gpt5_ultimate_prompting_guide.md):
- Use reasoning_effort instead of temperature (deprecated)
- Use max_completion_tokens instead of max_tokens

All public helpers MUST keep every line shorter than 150 characters to
respect the project's formatting rules.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Literal, Optional

from openai import OpenAI  # type: ignore  # SDK provided in requirements.txt

__all__ = [
    "chat_completion",
]


# Default model: GPT-5.1 for improved instruction following and reduced hallucinations
_DEFAULT_MODEL = "gpt-5.1"

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


def chat_completion(
    messages: List[Dict[str, Any]],
    api_key: str,
    *,
    model: str | None = None,
    json_only: bool = True,
    reasoning_effort: ReasoningEffort | None = None,
    **kwargs: Any,
) -> str:
    """Call the LLM and return the content of the first choice.

    Parameters
    ----------
    messages:
        List of chat messages as expected by the OpenAI Chat Completions API.
    api_key:
        Secret key to authenticate against the OpenAI service.
    model:
        Name of the model to use.  Defaults to GPT-5.1.
    json_only:
        If ``True`` (default) instruct the model to respond with a JSON
        object via the `response_format` parameter.
    reasoning_effort:
        GPT-5.1 reasoning effort level: "minimal", "low", "medium", "high".
        Defaults to "high" for accurate QTI conversion.
    **kwargs:
        Any additional keyword arguments are forwarded verbatim to
        ``client.chat.completions.create``. Note: temperature is deprecated
        in GPT-5.1 and will be mapped to reasoning_effort.

    Returns
    -------
    str
        The text content of the first LLM choice.
    """
    client = OpenAI(api_key=api_key)

    chosen_model = model or _DEFAULT_MODEL
    response_format = _build_response_format(json_only)

    _logger.debug("Calling model %s with %d message(s)", chosen_model, len(messages))

    # Build GPT-5.1 compatible parameters
    params: Dict[str, Any] = {
        "model": chosen_model,
        "messages": messages,
    }

    if response_format:
        params["response_format"] = response_format

    # Handle GPT-5.1 specific parameters
    is_gpt51 = chosen_model.startswith("gpt-5")

    if is_gpt51:
        # GPT-5.1 uses reasoning_effort instead of temperature
        effort = reasoning_effort
        if effort is None and "temperature" in kwargs:
            effort = _map_temperature_to_reasoning(kwargs.pop("temperature"))
        params["reasoning_effort"] = effort or "high"
        params["seed"] = 42

        # Convert max_tokens to max_completion_tokens for GPT-5.1
        if "max_tokens" in kwargs:
            params["max_completion_tokens"] = kwargs.pop("max_tokens")
    else:
        # For non-GPT-5.1 models, pass through kwargs as-is
        pass

    # Add remaining kwargs (excluding deprecated params for GPT-5.1)
    for key, value in kwargs.items():
        if is_gpt51 and key == "temperature":
            continue  # Already handled above
        params[key] = value

    response = client.chat.completions.create(**params)

    content = response.choices[0].message.content
    if content is None:
        raise RuntimeError("LLM response had no content")

    # Check for finish reason issues
    finish_reason = response.choices[0].finish_reason
    if finish_reason == "length":
        _logger.warning("Response hit token limit - may be truncated")

    # Basic sanity check if json_only was requested – helps detect model drift.
    if json_only:
        first_char = content.strip()[0] if content else ""
        if first_char not in "{[":
            _logger.warning("Expected JSON response but got: %s…", content[:80])

    return content 