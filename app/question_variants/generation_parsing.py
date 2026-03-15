"""Parsing helpers for variant-generation model responses."""

from __future__ import annotations

import json
import re
from typing import Any


def parse_generation_response(response: str) -> list[dict[str, Any]]:
    """Parse a generation response, tolerating common wrapper/format issues."""
    direct = _load_variants(response)
    if direct is not None:
        return direct

    extracted = _extract_json_object(response)
    if extracted is not None:
        variants = extracted.get("variants", [])
        if isinstance(variants, list):
            return variants

    extracted_variants = _extract_variants_array(response)
    if extracted_variants is not None:
        return extracted_variants

    extracted_single = _extract_single_variant(response)
    if extracted_single is not None:
        return [extracted_single]

    cleaned = re.sub(r'\\(?![/"\\\bfnrtu])', r"\\\\", response)
    cleaned_variants = _load_variants(cleaned)
    if cleaned_variants is not None:
        return cleaned_variants

    return []


def _load_variants(text: str) -> list[dict[str, Any]] | None:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    variants = data.get("variants", [])
    return variants if isinstance(variants, list) else None


def _extract_json_object(text: str) -> dict[str, Any] | None:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = text[start : end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def _extract_variants_array(text: str) -> list[dict[str, Any]] | None:
    match = re.search(r'"variants"\s*:\s*(\[[\s\S]*\])', text)
    if not match:
        return None
    candidate = match.group(1)
    depth = 0
    end_index = None
    for idx, char in enumerate(candidate):
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                end_index = idx
                break
    if end_index is None:
        return None
    candidate = candidate[: end_index + 1]
    try:
        data = json.loads(candidate)
        return data if isinstance(data, list) else None
    except json.JSONDecodeError:
        return None


def _extract_single_variant(text: str) -> dict[str, Any] | None:
    qti_match = re.search(r'"qti_xml"\s*:\s*"([\s\S]*?)"\s*,\s*"change_description"\s*:\s*"([\s\S]*?)"', text)
    if not qti_match:
        return None
    qti_xml_raw = qti_match.group(1)
    change_description_raw = qti_match.group(2)
    try:
        qti_xml = json.loads(f'"{qti_xml_raw}"')
        change_description = json.loads(f'"{change_description_raw}"')
    except json.JSONDecodeError:
        return None

    self_check: dict[str, Any] = {}
    self_check_match = re.search(r'"self_check"\s*:\s*(\{[\s\S]*?\})', text)
    if self_check_match:
        try:
            parsed = json.loads(self_check_match.group(1))
            if isinstance(parsed, dict):
                self_check = parsed
        except json.JSONDecodeError:
            self_check = {}

    return {
        "qti_xml": qti_xml,
        "change_description": change_description,
        "self_check": self_check,
    }
