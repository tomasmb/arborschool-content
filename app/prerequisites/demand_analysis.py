"""Phase 0: Demand analysis — identify prerequisite knowledge gaps.

Loads M1 atoms, finds "leaf" atoms (the entry points of the knowledge
graph), and uses GPT-5.1 to determine what foundational math topics
students need before tackling those atoms.

Usage:
    python -m app.prerequisites.demand_analysis
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.llm_clients import LLMResponse, OpenAIClient, load_default_openai_client
from app.prerequisites.constants import PREREQ_OUTPUT_DIR
from app.prerequisites.prompts.demand_analysis import (
    build_demand_analysis_prompt,
)
from app.standards.helpers import parse_json_response
from app.utils.paths import get_atoms_file

logger = logging.getLogger(__name__)

_REASONING_EFFORT = "high"
_OUTPUT_FILE = PREREQ_OUTPUT_DIR / "demand_analysis.json"


def load_m1_atoms() -> list[dict[str, Any]]:
    """Load all M1 atoms from the canonical file."""
    atoms_path = get_atoms_file("paes_m1_2026")
    if not atoms_path.exists():
        raise FileNotFoundError(f"Atoms file not found: {atoms_path}")
    with atoms_path.open(encoding="utf-8") as f:
        data = json.load(f)
    return data.get("atoms", [])


def find_leaf_atoms(atoms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Find atoms that are "leaves" — no prerequisites or only basic ones.

    These are the entry points of the M1 knowledge graph and the natural
    starting point for prerequisite analysis.
    """
    atom_ids = {a["id"] for a in atoms}
    leaves: list[dict[str, Any]] = []
    for atom in atoms:
        prereqs = atom.get("prerrequisitos", [])
        internal_prereqs = [p for p in prereqs if p in atom_ids]
        if len(internal_prereqs) == 0:
            leaves.append(atom)
    return leaves


def compact_atom_for_prompt(atom: dict[str, Any]) -> dict[str, Any]:
    """Strip non-essential fields to reduce prompt token count.

    Shared helper used by demand analysis and graph connection phases.
    """
    return {
        "id": atom["id"],
        "eje": atom["eje"],
        "titulo": atom["titulo"],
        "descripcion": atom["descripcion"],
        "criterios_atomicos": atom.get("criterios_atomicos", []),
        "prerrequisitos": atom.get("prerrequisitos", []),
        "notas_alcance": atom.get("notas_alcance", []),
    }


def run_demand_analysis(
    client: OpenAIClient,
    atoms: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run demand analysis using GPT-5.1.

    Args:
        client: Configured OpenAI client (GPT-5.1).
        atoms: Optional pre-loaded atoms list. Loaded from disk if None.

    Returns:
        Demand analysis result dict with prerequisite_topics.
    """
    if atoms is None:
        atoms = load_m1_atoms()

    leaves = find_leaf_atoms(atoms)
    logger.info(
        "Found %d leaf atoms (no M1 prerequisites) out of %d total",
        len(leaves), len(atoms),
    )

    compact_leaves = [compact_atom_for_prompt(a) for a in leaves]
    prompt = build_demand_analysis_prompt(compact_leaves)

    logger.info(
        "Running demand analysis with GPT-5.1 "
        "(reasoning_effort=%s)...", _REASONING_EFFORT,
    )
    resp: LLMResponse = client.generate_text(
        prompt,
        reasoning_effort=_REASONING_EFFORT,
        response_mime_type="application/json",
    )

    result = parse_json_response(resp.text)
    if not isinstance(result, dict):
        raise ValueError(
            f"Expected dict from demand analysis, got {type(result)}"
        )

    topics = result.get("prerequisite_topics", [])
    logger.info("Identified %d prerequisite topics", len(topics))

    result["_usage"] = {
        "input_tokens": resp.usage.input_tokens,
        "output_tokens": resp.usage.output_tokens,
        "model": resp.usage.model,
    }

    return result


def save_demand_analysis(result: dict[str, Any]) -> Path:
    """Save demand analysis results to disk."""
    PREREQ_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with _OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info("Saved demand analysis to %s", _OUTPUT_FILE)
    return _OUTPUT_FILE


def load_demand_analysis() -> dict[str, Any]:
    """Load previously saved demand analysis from disk."""
    if not _OUTPUT_FILE.exists():
        raise FileNotFoundError(
            f"No demand analysis found at {_OUTPUT_FILE}. "
            "Run phase 0 first."
        )
    with _OUTPUT_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    """CLI entry point for Phase 0."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    client = load_default_openai_client()
    result = run_demand_analysis(client)
    save_demand_analysis(result)

    summary = result.get("summary", {})
    topics = result.get("prerequisite_topics", [])
    print(f"\n{'=' * 60}")
    print("DEMAND ANALYSIS COMPLETE")
    print(f"{'=' * 60}")
    print(f"Total prerequisite topics: {len(topics)}")
    if summary.get("by_grade"):
        print("By grade:")
        for grade, count in summary["by_grade"].items():
            if count > 0:
                print(f"  {grade}: {count}")
    print(f"Output: {_OUTPUT_FILE}")


if __name__ == "__main__":
    main()
