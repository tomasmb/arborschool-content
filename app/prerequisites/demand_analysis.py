"""Phase 0: Demand analysis — identify prerequisite knowledge gaps.

Loads M1 atoms, finds "leaf" atoms (the entry points of the knowledge
graph), and uses GPT-5.1 to determine what foundational math topics
students need before tackling those atoms.

Analysis is split per eje (mathematical domain) for focused quality,
then merged into a unified deduplicated result.

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
    build_demand_merge_prompt,
    build_eje_demand_prompt,
)
from app.standards.helpers import parse_json_response
from app.utils.paths import get_atoms_file

logger = logging.getLogger(__name__)

_REASONING_EFFORT = "high"
_MERGE_REASONING_EFFORT = "high"
_REQUEST_TIMEOUT = 1800.0
_MAX_ATOMS_PER_CALL = 12
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
    """Find atoms that have no M1-internal prerequisites.

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


def _split_into_batches(
    items: list[dict[str, Any]],
    max_size: int,
) -> list[list[dict[str, Any]]]:
    """Split a list into batches of at most max_size."""
    if len(items) <= max_size:
        return [items]
    return [
        items[i:i + max_size]
        for i in range(0, len(items), max_size)
    ]


def _group_leaves_by_eje(
    leaves: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Split leaf atoms by eje, returning compact versions."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for atom in leaves:
        eje = atom["eje"]
        if eje not in grouped:
            grouped[eje] = []
        grouped[eje].append(compact_atom_for_prompt(atom))
    return grouped


def _run_eje_analysis(
    client: OpenAIClient,
    eje: str,
    atoms: list[dict[str, Any]],
    max_retries: int = 2,
) -> list[dict[str, Any]]:
    """Run prerequisite analysis for a single eje.

    Args:
        client: GPT-5.1 client.
        eje: Eje key (e.g. "numeros").
        atoms: Compact leaf atoms for this eje.
        max_retries: Retry count on parse/validation failure.

    Returns:
        List of prerequisite topic dicts for this eje.
    """
    prompt = build_eje_demand_prompt(atoms, eje)

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
                raise ValueError(
                    f"Expected dict, got {type(result)}"
                )

            topics = result.get("prerequisite_topics", [])
            logger.info(
                "  %s: %d topics identified "
                "(in=%d, out=%d tokens)",
                eje, len(topics),
                resp.usage.input_tokens,
                resp.usage.output_tokens,
            )
            return topics

        except Exception as e:
            logger.error(
                "  %s attempt %d/%d failed: %s",
                eje, attempt + 1, max_retries + 1, e,
            )
            if attempt == max_retries:
                raise

    return []  # unreachable, satisfies type checker


def _run_merge(
    client: OpenAIClient,
    per_eje_results: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Merge and deduplicate per-eje demand results.

    Args:
        client: GPT-5.1 client.
        per_eje_results: Dict mapping eje → list of topic dicts.

    Returns:
        Unified demand analysis result dict.
    """
    prompt = build_demand_merge_prompt(per_eje_results)

    logger.info(
        "Merging %d per-eje results (reasoning_effort=%s)...",
        len(per_eje_results), _MERGE_REASONING_EFFORT,
    )
    resp: LLMResponse = client.generate_text(
        prompt,
        reasoning_effort=_MERGE_REASONING_EFFORT,
        response_mime_type="application/json",
        request_timeout_seconds=_REQUEST_TIMEOUT,
        stream=True,
    )

    result = parse_json_response(resp.text)
    if not isinstance(result, dict):
        raise ValueError(f"Expected dict from merge, got {type(result)}")

    topics = result.get("prerequisite_topics", [])
    summary = result.get("summary", {})
    logger.info(
        "Merge complete: %d unified topics "
        "(before=%s, removed=%s)",
        len(topics),
        summary.get("topics_before_dedup", "?"),
        summary.get("topics_removed", "?"),
    )

    result["_usage"] = {
        "merge_input_tokens": resp.usage.input_tokens,
        "merge_output_tokens": resp.usage.output_tokens,
        "model": resp.usage.model,
    }

    return result


def run_demand_analysis(
    client: OpenAIClient,
    atoms: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run per-eje demand analysis + merge using GPT-5.1.

    Splits leaf atoms by eje, runs focused analysis per domain, then
    merges and deduplicates into a unified result.

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

    grouped = _group_leaves_by_eje(leaves)
    logger.info(
        "Split into %d ejes: %s",
        len(grouped),
        {k: len(v) for k, v in grouped.items()},
    )

    per_eje_results: dict[str, list[dict[str, Any]]] = {}

    for eje, eje_atoms in sorted(grouped.items()):
        batches = _split_into_batches(eje_atoms, _MAX_ATOMS_PER_CALL)
        n_batches = len(batches)
        logger.info(
            "--- Analyzing %s (%d leaves, %d batch%s) ---",
            eje, len(eje_atoms), n_batches,
            "es" if n_batches > 1 else "",
        )

        eje_topics: list[dict[str, Any]] = []
        for i, batch in enumerate(batches):
            if n_batches > 1:
                logger.info(
                    "  Batch %d/%d (%d atoms)",
                    i + 1, n_batches, len(batch),
                )
            topics = _run_eje_analysis(client, eje, batch)
            eje_topics.extend(topics)
        per_eje_results[eje] = eje_topics

    total_raw = sum(len(t) for t in per_eje_results.values())
    logger.info(
        "Per-eje analysis complete: %d total raw topics across %d ejes",
        total_raw, len(per_eje_results),
    )

    result = _run_merge(client, per_eje_results)
    result["_per_eje_raw_counts"] = {
        k: len(v) for k, v in per_eje_results.items()
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
    raw_counts = result.get("_per_eje_raw_counts", {})
    print(f"\n{'=' * 60}")
    print("DEMAND ANALYSIS COMPLETE")
    print(f"{'=' * 60}")
    print(f"Total prerequisite topics: {len(topics)}")
    if raw_counts:
        print(f"Raw topics before merge: {sum(raw_counts.values())}")
        for eje, count in raw_counts.items():
            print(f"  {eje}: {count}")
    if summary.get("by_grade"):
        print("By grade:")
        for grade, count in summary["by_grade"].items():
            if count > 0:
                print(f"  {grade}: {count}")
    print(f"Output: {_OUTPUT_FILE}")


if __name__ == "__main__":
    main()
