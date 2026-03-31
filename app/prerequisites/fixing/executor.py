"""Execute a single prereq FixAction by calling GPT-5.1.

Mirrors the M1 executor but validates against PrereqAtom
and uses prereq ID patterns for deterministic fixes.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import ValidationError

from app.atoms.fixing.models import FixAction, FixResult, FixType
from app.llm_clients import OpenAIClient
from app.prerequisites.constants import PREREQ_ATOM_ID_PATTERN
from app.prerequisites.fixing.prompts import build_prereq_fix_prompt
from app.prerequisites.models import PrereqAtom

logger = logging.getLogger(__name__)

_ATOM_ID_RE = re.compile(PREREQ_ATOM_ID_PATTERN)


def execute_prereq_fix(
    client: OpenAIClient,
    action: FixAction,
    standard: dict[str, Any],
    all_atoms: list[dict[str, Any]],
) -> FixResult:
    """Execute a single fix action for a prerequisite atom.

    Args:
        client: Configured OpenAI client (GPT-5.1).
        action: The fix to apply.
        standard: Standard definition dict.
        all_atoms: Every prerequisite atom (all grades).

    Returns:
        A FixResult describing the outcome.
    """
    if action.fix_type == FixType.FIX_PREREQUISITES:
        deterministic = _try_deterministic_prereq_fix(action, all_atoms)
        if deterministic is not None:
            return deterministic

    std_id = action.standard_id
    std_atoms = [
        a for a in all_atoms if std_id in a.get("standard_ids", [])
    ]
    target_atoms = [
        a for a in std_atoms if a.get("id") in action.atom_ids
    ]
    next_num = _next_atom_number(std_atoms)

    prompt = build_prereq_fix_prompt(
        action=action,
        standard=standard,
        target_atoms=target_atoms,
        all_standard_atoms=std_atoms,
        next_atom_number=next_num,
    )

    try:
        llm_resp = client.generate_text(
            prompt,
            reasoning_effort=action.reasoning_effort,
            response_mime_type="application/json",
            stream=True,
        )
    except Exception as exc:
        logger.error("LLM call failed for %s: %s", action, exc)
        return FixResult(action=action, success=False, error=str(exc))

    return _parse_and_validate(action, llm_resp.text)


def _try_deterministic_prereq_fix(
    action: FixAction,
    all_atoms: list[dict[str, Any]],
) -> FixResult | None:
    """Try to fix prerequisites without LLM when explicit."""
    if len(action.atom_ids) != 1:
        return None

    atom_id = action.atom_ids[0]
    atom = next((a for a in all_atoms if a.get("id") == atom_id), None)
    if atom is None:
        return None

    suggested: list[str] = []
    for issue in action.issues:
        suggested.extend(_ATOM_ID_RE.findall(issue))

    existing_ids = {a.get("id") for a in all_atoms}
    suggested = [
        s for s in dict.fromkeys(suggested)
        if s in existing_ids and s != atom_id
    ]

    if not suggested:
        return None

    current_prereqs: list[str] = list(atom.get("prerrequisitos", []))
    new_prereqs = list(dict.fromkeys(current_prereqs + suggested))

    if new_prereqs == current_prereqs:
        return FixResult(action=action, success=True)

    updated_atom = {**atom, "prerrequisitos": new_prereqs}
    logger.info(
        "Deterministic prereq fix for %s: added %s",
        atom_id,
        [s for s in suggested if s not in current_prereqs],
    )
    return FixResult(
        action=action,
        success=True,
        new_atoms=[updated_atom],
        prerequisite_updates={atom_id: new_prereqs},
    )


def _parse_and_validate(action: FixAction, raw: str) -> FixResult:
    """Parse LLM JSON and validate atoms against PrereqAtom."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("JSON parse error: %s", exc)
        return FixResult(
            action=action, success=False,
            error=f"JSON parse: {exc}",
        )

    fixed_atoms: list[dict[str, Any]] = data.get("fixed_atoms", [])
    removed_ids: list[str] = data.get("removed_atom_ids", [])
    id_mapping: dict[str, list[str]] = data.get("id_mapping", {})
    prereq_updates: dict[str, list[str]] = data.get(
        "prerequisite_updates", {},
    )

    validated: list[dict[str, Any]] = []
    errors: list[str] = []
    for atom_dict in fixed_atoms:
        try:
            PrereqAtom(**atom_dict)
            validated.append(atom_dict)
        except ValidationError as exc:
            errors.append(f"Atom {atom_dict.get('id', '?')}: {exc}")

    if errors:
        error_msg = "; ".join(errors)
        logger.warning("Validation errors: %s", error_msg)
        return FixResult(
            action=action, success=False,
            new_atoms=validated, error=f"Atom validation: {error_msg}",
        )

    return FixResult(
        action=action,
        success=True,
        new_atoms=validated,
        removed_atom_ids=removed_ids,
        id_mapping=id_mapping,
        prerequisite_updates=prereq_updates,
    )


def _next_atom_number(standard_atoms: list[dict[str, Any]]) -> int:
    """Return next sequential atom number (parses A-GRADE-EJE-NN-MM)."""
    max_num = 0
    for atom in standard_atoms:
        aid: str = atom.get("id", "")
        parts = aid.split("-")
        if len(parts) == 5:
            try:
                max_num = max(max_num, int(parts[4]))
            except ValueError:
                continue
    return max_num + 1
