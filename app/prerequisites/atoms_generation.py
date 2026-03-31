"""Phase 2: Generate prerequisite atoms from prerequisite standards.

Processes standards bottom-up (lowest grade first) so that each level
can reference atoms from lower levels as prerequisites.

Usage:
    python -m app.prerequisites.atoms_generation
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.llm_clients import LLMResponse, OpenAIClient, load_default_openai_client
from app.prerequisites.constants import GRADE_LEVELS, PREREQ_OUTPUT_DIR, grade_order
from app.prerequisites.models import (
    PrereqAtom,
    validate_prereq_atom_id_matches_eje,
)
from app.prerequisites.prompts.atom_generation import (
    build_prereq_atom_generation_prompt,
)
from app.prerequisites.standards_generation import load_standards
from app.standards.helpers import parse_json_response

logger = logging.getLogger(__name__)

_REASONING_EFFORT = "high"
_REQUEST_TIMEOUT = 1800.0
_ATOMS_FILE = PREREQ_OUTPUT_DIR / "atoms.json"


@dataclass
class AtomGenResult:
    """Result of generating atoms for a single standard."""

    success: bool
    atoms: list[PrereqAtom] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None


def _validate_atom_granularity(
    atoms: list[PrereqAtom],
) -> list[str]:
    """Basic granularity heuristics (mirrors M1 checks)."""
    warnings: list[str] = []
    for atom in atoms:
        if len(atom.descripcion) > 300:
            warnings.append(
                f"{atom.id}: descripcion may be too long "
                f"({len(atom.descripcion)} chars)"
            )
        if len(atom.criterios_atomicos) > 5:
            warnings.append(
                f"{atom.id}: too many criterios_atomicos "
                f"({len(atom.criterios_atomicos)})"
            )
        if len(atom.habilidades_secundarias) > 2:
            warnings.append(
                f"{atom.id}: many habilidades_secundarias "
                f"({len(atom.habilidades_secundarias)})"
            )
    return warnings


def generate_atoms_for_standard(
    client: OpenAIClient,
    standard: dict[str, Any],
    grade_level: str,
    atoms_below: list[dict[str, Any]],
    max_retries: int = 2,
) -> AtomGenResult:
    """Generate atoms for a single prerequisite standard.

    Args:
        client: GPT-5.1 client.
        standard: Prerequisite standard dict.
        grade_level: Grade prefix.
        atoms_below: Compact atom dicts from lower grades.
        max_retries: Retry count on failure.

    Returns:
        AtomGenResult with validated atoms or error.
    """
    std_id = standard.get("id", "unknown")
    prompt = build_prereq_atom_generation_prompt(
        standard, grade_level, atoms_below,
    )

    for attempt in range(max_retries + 1):
        try:
            resp: LLMResponse = client.generate_text(
                prompt,
                reasoning_effort=_REASONING_EFFORT,
                response_mime_type="application/json",
                request_timeout_seconds=_REQUEST_TIMEOUT,
                stream=True,
            )
            raw = parse_json_response(resp.text)
            if isinstance(raw, dict):
                raw = [raw]
            if not isinstance(raw, list):
                logger.error("Expected list, got %s", type(raw))
                if attempt < max_retries:
                    continue
                return AtomGenResult(
                    success=False,
                    error=f"Expected list, got {type(raw)}",
                )
        except Exception as e:
            logger.error("Attempt %d failed for %s: %s", attempt + 1, std_id, e)
            if attempt < max_retries:
                continue
            return AtomGenResult(success=False, error=str(e))

        validated: list[PrereqAtom] = []
        warnings: list[str] = []

        for idx, atom_dict in enumerate(raw):
            try:
                atom = PrereqAtom.model_validate(atom_dict)
                validate_prereq_atom_id_matches_eje(atom)
                if std_id not in atom.standard_ids:
                    warnings.append(
                        f"{atom.id}: standard_ids missing {std_id}"
                    )
                validated.append(atom)
            except ValueError as e:
                warnings.append(f"Atom {idx} invalid: {e}")

        if not validated:
            if attempt < max_retries:
                logger.warning("No valid atoms, retrying %s...", std_id)
                continue
            return AtomGenResult(
                success=False,
                error="No valid atoms after validation",
                warnings=warnings,
            )

        gran_warnings = _validate_atom_granularity(validated)
        warnings.extend(gran_warnings)

        logger.info(
            "Generated %d atoms for %s", len(validated), std_id,
        )
        return AtomGenResult(
            success=True, atoms=validated, warnings=warnings,
        )

    return AtomGenResult(
        success=False, error=f"Failed after {max_retries + 1} attempts",
    )


def _compact_atom(atom: PrereqAtom) -> dict[str, Any]:
    """Compact representation for passing to next grade's prompt."""
    return {
        "id": atom.id,
        "grade_level": atom.grade_level,
        "titulo": atom.titulo,
        "eje": atom.eje,
    }


def run_atoms_generation(
    client: OpenAIClient,
) -> list[PrereqAtom]:
    """Generate atoms for all prerequisite standards, bottom-up.

    Returns:
        Complete list of prerequisite atoms.
    """
    standards = load_standards()
    std_by_grade: dict[str, list[dict[str, Any]]] = {}
    for s in standards:
        grade = s.grade_level
        if grade not in std_by_grade:
            std_by_grade[grade] = []
        std_by_grade[grade].append(s.model_dump())

    all_atoms: list[PrereqAtom] = []
    atoms_below: list[dict[str, Any]] = []
    failed: list[str] = []

    for grade_level in GRADE_LEVELS:
        grade_standards = std_by_grade.get(grade_level, [])
        if not grade_standards:
            continue

        logger.info(
            "=== %s: %d standards ===",
            grade_level, len(grade_standards),
        )

        for std_dict in grade_standards:
            result = generate_atoms_for_standard(
                client, std_dict, grade_level, atoms_below,
            )
            if result.success:
                all_atoms.extend(result.atoms)
                atoms_below.extend(
                    _compact_atom(a) for a in result.atoms
                )
                logger.info(
                    "  ✓ %s: %d atoms",
                    std_dict["id"], len(result.atoms),
                )
            else:
                failed.append(std_dict["id"])
                logger.error(
                    "  ✗ %s: %s", std_dict["id"], result.error,
                )

            for w in result.warnings:
                logger.warning("    ⚠ %s", w)

    if failed:
        logger.error(
            "Failed standards: %s", ", ".join(failed),
        )

    logger.info(
        "Total prerequisite atoms generated: %d", len(all_atoms),
    )
    return all_atoms


def save_atoms(atoms: list[PrereqAtom]) -> Path:
    """Save prerequisite atoms to disk."""
    PREREQ_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "metadata": {
            "type": "prerequisite_atoms",
            "generated_with": "gpt-5.1",
            "total_atoms": len(atoms),
        },
        "atoms": [a.model_dump() for a in atoms],
    }
    with _ATOMS_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info("Saved %d atoms to %s", len(atoms), _ATOMS_FILE)
    return _ATOMS_FILE


def load_atoms() -> list[PrereqAtom]:
    """Load previously saved prerequisite atoms from disk."""
    if not _ATOMS_FILE.exists():
        raise FileNotFoundError(
            f"No atoms file at {_ATOMS_FILE}. Run phase 2 first."
        )
    with _ATOMS_FILE.open(encoding="utf-8") as f:
        data = json.load(f)
    return [
        PrereqAtom.model_validate(a)
        for a in data.get("atoms", [])
    ]


def main() -> None:
    """CLI entry point for Phase 2."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    client = load_default_openai_client()
    atoms = run_atoms_generation(client)
    save_atoms(atoms)

    print(f"\n{'=' * 60}")
    print("ATOM GENERATION COMPLETE")
    print(f"{'=' * 60}")
    print(f"Total atoms: {len(atoms)}")
    by_grade: dict[str, int] = {}
    for a in atoms:
        by_grade[a.grade_level] = by_grade.get(a.grade_level, 0) + 1
    for grade, count in sorted(
        by_grade.items(), key=lambda kv: grade_order(kv[0]),
    ):
        print(f"  {grade}: {count}")
    print(f"Output: {_ATOMS_FILE}")


if __name__ == "__main__":
    main()
