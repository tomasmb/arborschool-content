"""Individual LLM call helpers for the notation fix pipeline."""

from __future__ import annotations

import json
import logging

from app.llm_clients import OpenAIClient
from app.prompts.notation_check import (
    build_fix_mini_class_prompt,
    build_fix_xml_file_prompt,
    build_revalidation_prompt,
    build_retry_prompt,
    build_scan_mini_class_prompt,
    build_scan_xml_file_prompt,
    build_validation_prompt,
)

logger = logging.getLogger(__name__)


def _parse_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"parse_error": True, "raw": raw[:200]}


def fix_one(client: OpenAIClient, item: dict) -> dict:
    """Produce corrected content for a flagged item (Pass 2)."""
    src = item["source"]
    label = item["item_key"]
    if src == "mini-class":
        prompt = build_fix_mini_class_prompt(
            label.split(":")[-1], item["original"], item["issues"],
        )
    else:
        prompt = build_fix_xml_file_prompt(
            label, item["original"], item["issues"],
        )
    try:
        resp = client.call(
            prompt,
            response_format={"type": "json_object"},
            reasoning_effort="medium",
        )
        data = _parse_json(resp.text)
        return {
            "status": data.get("status", "ERROR"),
            "issues": data.get("issues", []),
            "corrected": data.get("corrected_content"),
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
        }
    except Exception as exc:
        logger.warning("Fix error for %s: %s", label, exc)
        return {
            "status": "ERROR", "issues": [str(exc)],
            "corrected": None, "input_tokens": 0, "output_tokens": 0,
        }


def validate_one(
    client: OpenAIClient, original: str, corrected: str,
    issues: list[str], content_type: str,
) -> dict:
    """Verify corrected version didn't break anything (Pass 3)."""
    prompt = build_validation_prompt(
        original, corrected, issues, content_type,
    )
    try:
        resp = client.call(
            prompt,
            response_format={"type": "json_object"},
            reasoning_effort="medium",
        )
        data = _parse_json(resp.text)
        return {
            "verdict": data.get("verdict", "UNKNOWN"),
            "reasons": data.get("reasons", []),
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
        }
    except Exception as exc:
        logger.warning("Validation error: %s", exc)
        return {
            "verdict": "ERROR", "reasons": [str(exc)],
            "input_tokens": 0, "output_tokens": 0,
        }


def revalidate_one(
    client: OpenAIClient, original: str, corrected: str,
) -> dict:
    """Independent semantic equivalence check (Pass 4)."""
    prompt = build_revalidation_prompt(original, corrected)
    try:
        resp = client.call(
            prompt,
            response_format={"type": "json_object"},
            reasoning_effort="medium",
        )
        data = _parse_json(resp.text)
        return {
            "pass": data.get("pass", False),
            "issues": data.get("issues", []),
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
        }
    except Exception as exc:
        logger.warning("Revalidation error: %s", exc)
        return {
            "pass": False, "issues": [str(exc)],
            "input_tokens": 0, "output_tokens": 0,
        }


def retry_one(
    client: OpenAIClient, original: str,
    rejection_reasons: list[str],
) -> dict:
    """Re-fix with feedback from failed validation."""
    prompt = build_retry_prompt(original, rejection_reasons)
    try:
        resp = client.call(
            prompt,
            response_format={"type": "json_object"},
            reasoning_effort="medium",
        )
        data = _parse_json(resp.text)
        return {
            "status": data.get("status", "ERROR"),
            "issues": data.get("issues", []),
            "corrected": data.get("corrected_content"),
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
        }
    except Exception as exc:
        logger.warning("Retry error: %s", exc)
        return {
            "status": "ERROR", "issues": [str(exc)],
            "corrected": None, "input_tokens": 0, "output_tokens": 0,
        }


def verify_one(
    client: OpenAIClient, content: str, label: str,
    source: str,
) -> dict:
    """Re-scan applied content to confirm cleanliness."""
    if source == "mini-class":
        prompt = build_scan_mini_class_prompt(
            label.split(":")[-1], content,
        )
    else:
        prompt = build_scan_xml_file_prompt(label, content)
    try:
        resp = client.call(
            prompt,
            response_format={"type": "json_object"},
            reasoning_effort="low",
        )
        data = _parse_json(resp.text)
        return {
            "clean": data.get("status") == "OK",
            "issues": data.get("issues", []),
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
        }
    except Exception as exc:
        logger.warning("Verify error for %s: %s", label, exc)
        return {
            "clean": False, "issues": [str(exc)],
            "input_tokens": 0, "output_tokens": 0,
        }
