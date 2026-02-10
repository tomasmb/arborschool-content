"""Execute a single FixAction by calling GPT-5.1.

Responsibilities:
  1. Load the standard and its atoms from canonical files.
  2. Build the prompt via ``prompts.py``.
  3. Call ``OpenAIClient.generate_text()`` with the fix-type-specific
     reasoning effort.
  4. Parse + validate the JSON response against the Atom Pydantic model.
  5. Return a ``FixResult``.

For ``FIX_PREREQUISITES`` with deterministic instructions (the validation
explicitly names which atom to add), the fix is applied without an LLM
call.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import ValidationError

from app.atoms.fixing.models import FixAction, FixResult, FixType
from app.atoms.fixing.prompts import build_fix_prompt
from app.atoms.models import Atom
from app.llm_clients import OpenAIClient

logger = logging.getLogger(__name__)

# Regex to extract atom IDs mentioned in free-text issue strings.
_ATOM_ID_RE = re.compile(r"A-M1-[A-Z]+-\d+-\d+")


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------


def execute_fix(
    client: OpenAIClient,
    action: FixAction,
    standard: dict[str, Any],
    all_atoms: list[dict[str, Any]],
    question_refs: dict[str, list[dict[str, Any]]] | None = None,
) -> FixResult:
    """Execute a single fix action and return the result.

    Args:
        client: Configured OpenAI client (GPT-5.1).
        action: The fix to apply.
        standard: Standard definition dict.
        all_atoms: Every atom in ``paes_m1_2026_atoms.json``.
        question_refs: atom_id → question metadata list (for SPLIT/MERGE).

    Returns:
        A FixResult describing the outcome.
    """
    # Attempt deterministic fix first (no LLM needed).
    if action.fix_type == FixType.FIX_PREREQUISITES:
        deterministic = _try_deterministic_prereq_fix(action, all_atoms)
        if deterministic is not None:
            return deterministic

    std_id = action.standard_id
    std_atoms = [a for a in all_atoms if std_id in a.get("standard_ids", [])]
    target_atoms = [a for a in std_atoms if a.get("id") in action.atom_ids]

    next_num = _next_atom_number(std_atoms, std_id)

    prompt = build_fix_prompt(
        action=action,
        standard=standard,
        target_atoms=target_atoms,
        all_standard_atoms=std_atoms,
        next_atom_number=next_num,
        question_refs=question_refs,
    )

    try:
        raw = client.generate_text(
            prompt,
            reasoning_effort=action.reasoning_effort,
            response_mime_type="application/json",
        )
    except Exception as exc:
        logger.error("LLM call failed for %s: %s", action, exc)
        return FixResult(action=action, success=False, error=str(exc))

    return _parse_and_validate(action, raw)


# -----------------------------------------------------------------------------
# Deterministic prerequisite fix
# -----------------------------------------------------------------------------


def _try_deterministic_prereq_fix(
    action: FixAction,
    all_atoms: list[dict[str, Any]],
) -> FixResult | None:
    """Try to fix prerequisites without LLM when the issue is explicit.

    Returns None if the fix is ambiguous and needs LLM intervention.
    """
    if len(action.atom_ids) != 1:
        return None

    atom_id = action.atom_ids[0]
    atom = next((a for a in all_atoms if a.get("id") == atom_id), None)
    if atom is None:
        return None

    # Collect atom IDs suggested as prerequisites in issue text.
    suggested: list[str] = []
    for issue in action.issues:
        suggested.extend(_ATOM_ID_RE.findall(issue))

    # Keep only IDs that actually exist and are not the atom itself.
    existing_ids = {a.get("id") for a in all_atoms}
    suggested = [
        s for s in dict.fromkeys(suggested)
        if s in existing_ids and s != atom_id
    ]

    if not suggested:
        return None  # Ambiguous — fall through to LLM.

    current_prereqs: list[str] = list(atom.get("prerrequisitos", []))
    new_prereqs = list(dict.fromkeys(current_prereqs + suggested))

    if new_prereqs == current_prereqs:
        # Nothing to change.
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


# -----------------------------------------------------------------------------
# Response parsing + validation
# -----------------------------------------------------------------------------


def _parse_and_validate(action: FixAction, raw: str) -> FixResult:
    """Parse LLM JSON response and validate atoms against the Pydantic model."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("JSON parse error: %s — raw[:200]: %s", exc, raw[:200])
        return FixResult(action=action, success=False, error=f"JSON parse: {exc}")

    fixed_atoms: list[dict[str, Any]] = data.get("fixed_atoms", [])
    removed_ids: list[str] = data.get("removed_atom_ids", [])
    id_mapping: dict[str, list[str]] = data.get("id_mapping", {})
    prereq_updates: dict[str, list[str]] = data.get("prerequisite_updates", {})
    qmap_suggestions: dict[str, str] = data.get("question_mapping_suggestions", {})

    # Validate each atom against the Pydantic schema.
    validated_atoms: list[dict[str, Any]] = []
    errors: list[str] = []
    for atom_dict in fixed_atoms:
        try:
            Atom(**atom_dict)
            validated_atoms.append(atom_dict)
        except ValidationError as exc:
            errors.append(f"Atom {atom_dict.get('id','?')}: {exc}")

    if errors:
        error_msg = "; ".join(errors)
        logger.warning("Validation errors: %s", error_msg)
        return FixResult(
            action=action,
            success=False,
            new_atoms=validated_atoms,
            error=f"Atom validation: {error_msg}",
        )

    return FixResult(
        action=action,
        success=True,
        new_atoms=validated_atoms,
        removed_atom_ids=removed_ids,
        id_mapping=id_mapping,
        prerequisite_updates=prereq_updates,
        question_mapping_suggestions=qmap_suggestions,
    )


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _next_atom_number(
    standard_atoms: list[dict[str, Any]],
    standard_id: str,
) -> int:
    """Return the next sequential atom number for a standard.

    Parses existing IDs like ``A-M1-ALG-01-18`` and returns 19.
    """
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
