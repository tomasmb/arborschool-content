"""Phase 4: Validate the combined prerequisite + M1 graph.

Performs both deterministic structural checks and LLM-based quality
validation on the prerequisite atoms and the combined graph.

Usage:
    python -m app.prerequisites.validation
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from app.llm_clients import LLMResponse, OpenAIClient, load_default_openai_client
from app.prerequisites.atoms_generation import load_atoms
from app.prerequisites.constants import PREREQ_OUTPUT_DIR
from app.prerequisites.demand_analysis import load_m1_atoms
from app.prerequisites.models import PrereqAtom
from app.prerequisites.prompts.validation import (
    build_prereq_validation_prompt,
)
from app.prerequisites.standards_generation import load_standards
from app.standards.helpers import parse_json_response

logger = logging.getLogger(__name__)

_REASONING_EFFORT = "medium"
_REQUEST_TIMEOUT = 1800.0
_VALIDATION_FILE = PREREQ_OUTPUT_DIR / "validation_result.json"
_MAX_WORKERS = 8


class _AtomLike(Protocol):
    """Minimal protocol for atoms in cycle detection."""

    @property
    def id(self) -> str: ...

    @property
    def prerrequisitos(self) -> list[str]: ...


@dataclass
class StructuralIssue:
    """A single structural check issue."""

    atom_id: str | None
    check: str
    severity: str  # "error" or "warning"
    message: str


@dataclass
class CombinedValidationResult:
    """Result of validating the combined graph."""

    passed: bool
    total_prereq_atoms: int
    total_m1_atoms: int
    structural_issues: list[StructuralIssue] = field(default_factory=list)
    cycles: list[list[str]] = field(default_factory=list)
    llm_results: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-friendly dict."""
        return {
            "passed": self.passed,
            "total_prereq_atoms": self.total_prereq_atoms,
            "total_m1_atoms": self.total_m1_atoms,
            "structural_issues": [
                {
                    "atom_id": i.atom_id, "check": i.check,
                    "severity": i.severity, "message": i.message,
                }
                for i in self.structural_issues
            ],
            "cycles": self.cycles,
            "llm_validation_results": self.llm_results,
        }


def _find_cycles_combined(
    prereq_atoms: Sequence[_AtomLike],
    m1_atoms: list[dict[str, Any]],
) -> list[list[str]]:
    """Find cycles in the combined prerequisite + M1 graph."""
    graph: dict[str, list[str]] = {}
    all_ids: set[str] = set()

    for a in prereq_atoms:
        all_ids.add(a.id)
        graph[a.id] = list(a.prerrequisitos)

    for a in m1_atoms:
        aid = a["id"]
        all_ids.add(aid)
        graph[aid] = list(a.get("prerrequisitos", []))

    cycles: list[list[str]] = []
    visited: set[str] = set()
    rec_stack: set[str] = set()
    path: list[str] = []

    def dfs(node: str) -> None:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        for neighbor in graph.get(node, []):
            if neighbor not in all_ids:
                continue
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in rec_stack:
                idx = path.index(neighbor)
                cycle = path[idx:] + [neighbor]
                min_i = min(
                    range(len(cycle) - 1), key=lambda i: cycle[i],
                )
                norm = cycle[min_i:-1] + [cycle[min_i]]
                if norm not in cycles:
                    cycles.append(norm)
        rec_stack.remove(node)
        path.pop()

    for nid in sorted(all_ids):
        if nid not in visited:
            dfs(nid)

    return cycles


def _check_missing_prereqs(
    prereq_atoms: list[PrereqAtom],
    m1_atoms: list[dict[str, Any]],
) -> list[StructuralIssue]:
    """Check that all referenced prerequisites exist in the combined graph."""
    all_ids: set[str] = set()
    for a in prereq_atoms:
        all_ids.add(a.id)
    for a in m1_atoms:
        all_ids.add(a["id"])

    issues: list[StructuralIssue] = []
    for a in prereq_atoms:
        for pid in a.prerrequisitos:
            if pid not in all_ids:
                issues.append(StructuralIssue(
                    atom_id=a.id,
                    check="missing_prerequisite",
                    severity="error",
                    message=f"Prereq '{pid}' not found",
                ))

    for a in m1_atoms:
        for pid in a.get("prerrequisitos", []):
            if pid not in all_ids:
                issues.append(StructuralIssue(
                    atom_id=a["id"],
                    check="missing_prerequisite",
                    severity="warning",
                    message=f"Prereq '{pid}' not in combined graph",
                ))

    return issues


def _check_duplicate_ids(
    prereq_atoms: list[PrereqAtom],
) -> list[StructuralIssue]:
    """Check for duplicate atom IDs within prerequisite atoms."""
    seen: set[str] = set()
    issues: list[StructuralIssue] = []
    for a in prereq_atoms:
        if a.id in seen:
            issues.append(StructuralIssue(
                atom_id=a.id,
                check="duplicate_id",
                severity="error",
                message=f"Duplicate atom ID: {a.id}",
            ))
        seen.add(a.id)
    return issues


def run_structural_checks(
    prereq_atoms: list[PrereqAtom],
    m1_atoms: list[dict[str, Any]],
) -> tuple[list[StructuralIssue], list[list[str]]]:
    """Run all deterministic structural checks."""
    issues: list[StructuralIssue] = []

    issues.extend(_check_duplicate_ids(prereq_atoms))
    issues.extend(_check_missing_prereqs(prereq_atoms, m1_atoms))
    cycles = _find_cycles_combined(prereq_atoms, m1_atoms)

    for cycle in cycles:
        issues.append(StructuralIssue(
            atom_id=cycle[0],
            check="circular_dependency",
            severity="error",
            message=f"Cycle: {' → '.join(cycle)}",
        ))

    return issues, cycles


def _validate_one_standard(
    client: OpenAIClient,
    std_id: str,
    std_dict: dict[str, Any],
    atom_dicts: list[dict[str, Any]],
    max_per_batch: int,
) -> dict[str, Any] | None:
    """Validate atoms for a single standard (thread-safe)."""
    batch = atom_dicts[:max_per_batch]
    prompt = build_prereq_validation_prompt(std_dict, batch)
    try:
        resp: LLMResponse = client.generate_text(
            prompt,
            reasoning_effort=_REASONING_EFFORT,
            response_mime_type="application/json",
            request_timeout_seconds=_REQUEST_TIMEOUT,
            stream=True,
        )
        result = parse_json_response(resp.text)
        if isinstance(result, dict):
            result["_standard_id"] = std_id
            quality = result.get(
                "evaluation_summary", {},
            ).get("overall_quality", "?")
            logger.info(
                "Validated %s: %s (%d atoms)",
                std_id, quality, len(batch),
            )
            return result
    except Exception as e:
        logger.error("Validation failed for %s: %s", std_id, e)
    return None


def run_llm_validation(
    client: OpenAIClient,
    prereq_atoms: list[PrereqAtom],
    max_per_batch: int = 15,
) -> list[dict[str, Any]]:
    """Run LLM validation on prerequisite atoms grouped by standard.

    Uses ThreadPoolExecutor to validate all standards in parallel.

    Args:
        client: GPT-5.1 client.
        prereq_atoms: All prerequisite atoms.
        max_per_batch: Max atoms per LLM call.

    Returns:
        List of validation result dicts (one per standard).
    """
    standards = load_standards()
    std_map = {s.id: s.model_dump() for s in standards}

    by_standard: dict[str, list[dict[str, Any]]] = {}
    for a in prereq_atoms:
        for sid in a.standard_ids:
            if sid not in by_standard:
                by_standard[sid] = []
            by_standard[sid].append(a.model_dump())

    tasks: list[tuple[str, dict[str, Any], list[dict[str, Any]]]] = []
    for std_id, atom_dicts in by_standard.items():
        std_dict = std_map.get(std_id)
        if std_dict is None:
            logger.warning("Standard %s not found, skipping", std_id)
            continue
        tasks.append((std_id, std_dict, atom_dicts))

    workers = min(_MAX_WORKERS, len(tasks))
    logger.info(
        "LLM validation: %d standards (%d workers)",
        len(tasks), workers,
    )

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(
                _validate_one_standard,
                client, std_id, std_dict, atom_dicts, max_per_batch,
            ): std_id
            for std_id, std_dict, atom_dicts in tasks
        }
        for future in as_completed(futures):
            result = future.result()
            if result is not None:
                results.append(result)

    return results


def run_full_validation(
    client: OpenAIClient,
) -> CombinedValidationResult:
    """Run complete validation pipeline (structural + LLM)."""
    prereq_atoms = load_atoms()
    m1_atoms = load_m1_atoms()

    logger.info(
        "Validating combined graph: %d prereq + %d M1 atoms",
        len(prereq_atoms), len(m1_atoms),
    )

    issues, cycles = run_structural_checks(prereq_atoms, m1_atoms)
    error_count = sum(1 for i in issues if i.severity == "error")

    logger.info(
        "Structural: %d issues (%d errors), %d cycles",
        len(issues), error_count, len(cycles),
    )

    llm_results = run_llm_validation(client, prereq_atoms)

    passed = error_count == 0

    return CombinedValidationResult(
        passed=passed,
        total_prereq_atoms=len(prereq_atoms),
        total_m1_atoms=len(m1_atoms),
        structural_issues=issues,
        cycles=cycles,
        llm_results=llm_results,
    )


def save_validation(result: CombinedValidationResult) -> Path:
    """Save validation results to disk."""
    PREREQ_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with _VALIDATION_FILE.open("w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
    logger.info("Saved validation to %s", _VALIDATION_FILE)
    return _VALIDATION_FILE


def main() -> None:
    """CLI entry point for Phase 4."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    client = load_default_openai_client()
    result = run_full_validation(client)
    save_validation(result)

    errors = [i for i in result.structural_issues if i.severity == "error"]
    warnings = [
        i for i in result.structural_issues if i.severity == "warning"
    ]

    print(f"\n{'=' * 60}")
    print("VALIDATION COMPLETE")
    print(f"{'=' * 60}")
    print(f"Passed: {'✓' if result.passed else '✗'}")
    print(f"Prereq atoms: {result.total_prereq_atoms}")
    print(f"M1 atoms: {result.total_m1_atoms}")
    print(f"Errors: {len(errors)}")
    print(f"Warnings: {len(warnings)}")
    print(f"Cycles: {len(result.cycles)}")
    print(f"LLM validations: {len(result.llm_results)}")
    print(f"Output: {_VALIDATION_FILE}")

    if errors:
        print(f"\n{'─' * 40}")
        print("ERRORS:")
        for e in errors[:20]:
            print(f"  [{e.check}] {e.atom_id}: {e.message}")


if __name__ == "__main__":
    main()
