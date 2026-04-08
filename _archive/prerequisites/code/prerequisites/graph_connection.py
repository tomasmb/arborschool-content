"""Phase 3: Connect prerequisite atoms to M1 atoms.

Takes the generated prerequisite atoms and the existing M1 atoms,
then uses GPT-5.1 to determine which prereq atoms should be added
as prerequisites to M1 leaf atoms.

Usage:
    python -m app.prerequisites.graph_connection
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.llm_clients import LLMResponse, OpenAIClient, load_default_openai_client
from app.prerequisites.atoms_generation import load_atoms
from app.prerequisites.constants import grade_order
from app.prerequisites.demand_analysis import (
    compact_atom_for_prompt,
    find_leaf_atoms,
    load_m1_atoms,
)
from app.prerequisites.prompts.graph_connection import (
    build_graph_connection_prompt,
)
from app.standards.helpers import parse_json_response
from app.utils.paths import PREREQUISITES_DIR, PREREQ_CONNECTIONS_FILE

logger = logging.getLogger(__name__)

_REASONING_EFFORT = "medium"
_REQUEST_TIMEOUT = 1800.0
_CONNECTIONS_FILE = PREREQ_CONNECTIONS_FILE


def _get_top_prereq_atoms(
    prereq_atoms: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Get highest-grade-level prereq atoms for connection prompt.

    Returns atoms from the two highest grade levels that have atoms,
    plus any atoms that no other atom depends on (graph leaves from the
    top).
    """
    grades_present: set[str] = set()
    for a in prereq_atoms:
        gl = a.get("grade_level", "")
        if gl:
            grades_present.add(gl)

    sorted_grades = sorted(grades_present, key=grade_order, reverse=True)
    top_grades = set(sorted_grades[:3]) if sorted_grades else set()

    dependents: set[str] = set()
    for a in prereq_atoms:
        for p in a.get("prerrequisitos", []):
            dependents.add(p)

    top_atoms: list[dict[str, Any]] = []
    for a in prereq_atoms:
        is_top_grade = a.get("grade_level", "") in top_grades
        is_leaf = a["id"] not in dependents
        if is_top_grade or is_leaf:
            top_atoms.append({
                "id": a["id"],
                "grade_level": a.get("grade_level", ""),
                "eje": a["eje"],
                "titulo": a["titulo"],
                "descripcion": a["descripcion"],
                "prerrequisitos": a.get("prerrequisitos", []),
            })

    return top_atoms


def run_graph_connection(
    client: OpenAIClient,
    max_retries: int = 2,
) -> dict[str, Any]:
    """Run graph connection between prereq atoms and M1 atoms.

    Args:
        client: GPT-5.1 client.
        max_retries: Retry count on failure.

    Returns:
        Connection result dict with mappings and summary.
    """
    m1_atoms = load_m1_atoms()
    m1_leaves = find_leaf_atoms(m1_atoms)
    prereq_atoms_objs = load_atoms()
    prereq_dicts = [a.model_dump() for a in prereq_atoms_objs]

    top_prereqs = _get_top_prereq_atoms(prereq_dicts)

    logger.info(
        "Connecting %d M1 leaf atoms with %d top prereq atoms",
        len(m1_leaves), len(top_prereqs),
    )

    compact_m1 = [compact_atom_for_prompt(a) for a in m1_leaves]
    prompt = build_graph_connection_prompt(compact_m1, top_prereqs)

    for attempt in range(max_retries + 1):
        try:
            resp: LLMResponse = client.generate_text(
                prompt,
                reasoning_effort=_REASONING_EFFORT,
                response_mime_type="application/json",
                request_timeout_seconds=_REQUEST_TIMEOUT,
                stream=True,
            )
            result = parse_json_response(resp.text)
            if not isinstance(result, dict):
                raise ValueError(f"Expected dict, got {type(result)}")

            connections = result.get("connections", [])
            logger.info("Generated %d connections", len(connections))

            result["_usage"] = {
                "input_tokens": resp.usage.input_tokens,
                "output_tokens": resp.usage.output_tokens,
                "model": resp.usage.model,
            }
            return result

        except Exception as e:
            logger.error(
                "Attempt %d/%d failed: %s",
                attempt + 1, max_retries + 1, e,
            )
            if attempt == max_retries:
                raise

    raise RuntimeError("Unreachable")


def save_connections(result: dict[str, Any]) -> Path:
    """Save connection results to disk."""
    PREREQUISITES_DIR.mkdir(parents=True, exist_ok=True)
    with _CONNECTIONS_FILE.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info("Saved connections to %s", _CONNECTIONS_FILE)
    return _CONNECTIONS_FILE


def load_connections() -> dict[str, Any]:
    """Load previously saved connection results."""
    if not _CONNECTIONS_FILE.exists():
        raise FileNotFoundError(
            f"No connections file at {_CONNECTIONS_FILE}. "
            "Run phase 3 first."
        )
    with _CONNECTIONS_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    """CLI entry point for Phase 3."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    client = load_default_openai_client()
    result = run_graph_connection(client)
    save_connections(result)

    connections = result.get("connections", [])
    summary = result.get("summary", {})
    print(f"\n{'=' * 60}")
    print("GRAPH CONNECTION COMPLETE")
    print(f"{'=' * 60}")
    print(f"Connections created: {len(connections)}")
    print(
        f"M1 atoms connected: "
        f"{summary.get('m1_atoms_connected', '?')}"
    )
    print(f"Output: {_CONNECTIONS_FILE}")


if __name__ == "__main__":
    main()
