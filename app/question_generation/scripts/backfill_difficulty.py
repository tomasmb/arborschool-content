"""Backfill missing difficulty tags in Phase 9 validated questions.

Reads each atom's enrichment difficulty rubric and uses GPT-5.1
(reasoning_effort=low) to classify questions as easy/medium/hard.
Also recovers other deterministic pipeline_meta fields (atom_id,
fingerprint, validators).

Usage:
    python -m app.question_generation.scripts.backfill_difficulty
    python -m app.question_generation.scripts.backfill_difficulty --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from app.llm_clients import load_default_openai_client
from app.question_generation.validation_checks import compute_fingerprint
from app.utils.paths import QUESTION_GENERATION_DIR
from app.utils.qti_extractor import parse_qti_xml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

_VALID_DIFFICULTIES = {"easy", "medium", "hard"}

DIFFICULTY_CLASSIFICATION_PROMPT = """\
<role>
Clasificador de dificultad para preguntas PAES M1 (Chile).
</role>

<rubric>
{rubric_text}
</rubric>

<question>
{question_text}
</question>

<choices>
{choices_text}
</choices>

<task>
Clasifica la pregunta según la rúbrica. Responde JSON puro:
{{"difficulty": "easy" | "medium" | "hard"}}
</task>"""


def _format_rubric(rubric: dict[str, list[str]]) -> str:
    """Format the enrichment difficulty rubric for the prompt."""
    lines: list[str] = []
    for level in ("easy", "medium", "hard"):
        criteria = rubric.get(level, [])
        if criteria:
            lines.append(f"{level}:")
            for c in criteria:
                lines.append(f"  - {c}")
    return "\n".join(lines)


def _build_prompt(
    rubric: dict[str, list[str]],
    question_text: str,
    choices: list[str],
) -> str:
    """Build the classification prompt from rubric + question."""
    return DIFFICULTY_CLASSIFICATION_PROMPT.format(
        rubric_text=_format_rubric(rubric),
        question_text=question_text,
        choices_text="\n".join(f"  {chr(65 + i)}) {c}" for i, c in enumerate(choices)),
    )


def _load_enrichment_rubric(atom_id: str) -> dict[str, list[str]]:
    """Load the difficulty rubric from an atom's enrichment checkpoint."""
    path = (
        QUESTION_GENERATION_DIR / atom_id
        / "checkpoints" / "phase_1_enrichment.json"
    )
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    enrichment = data.get("enrichment_data", {})
    return enrichment.get("difficulty_rubric", {})


def _build_backfilled_meta(
    atom_id: str,
    difficulty: str,
    qti_xml: str,
) -> dict:
    """Build a minimal pipeline_meta with recoverable fields."""
    return {
        "atom_id": atom_id,
        "component_tag": "",
        "difficulty_level": difficulty,
        "operation_skeleton_ast": "",
        "surface_context": "",
        "numbers_profile": "",
        "fingerprint": f"sha256:{compute_fingerprint(qti_xml)}",
        "target_exemplar_id": None,
        "distance_level": None,
        "validators": {
            "xsd": "pass",
            "paes": "pass",
            "solve_check": "pass",
            "scope": "pass",
            "exemplar_copy_check": "pass",
            "feedback": "pass",
            "dedupe": "pass",
            "final_llm_check": "pass",
        },
    }


def scan_missing_items() -> dict[str, list[int]]:
    """Scan all phase 9 checkpoints for items with missing pipeline_meta.

    Returns:
        Mapping of atom_id to list of item indices that need backfill.
    """
    missing: dict[str, list[int]] = {}

    for atom_dir in sorted(QUESTION_GENERATION_DIR.iterdir()):
        if not atom_dir.name.startswith("A-"):
            continue
        phase9 = atom_dir / "checkpoints" / "phase_9_final_validation.json"
        if not phase9.exists():
            continue

        data = json.loads(phase9.read_text(encoding="utf-8"))
        indices: list[int] = []
        for i, item in enumerate(data.get("items", [])):
            meta = item.get("pipeline_meta")
            if not meta or not meta.get("difficulty_level"):
                indices.append(i)
        if indices:
            missing[atom_dir.name] = indices

    return missing


def backfill(*, dry_run: bool = False) -> None:
    """Run the backfill process for all missing difficulty tags."""
    missing = scan_missing_items()
    total = sum(len(v) for v in missing.values())

    if total == 0:
        logger.info("All questions already have difficulty tags.")
        return

    logger.info(
        "Found %d questions missing difficulty across %d atoms.",
        total, len(missing),
    )
    if dry_run:
        for atom_id, indices in missing.items():
            logger.info("  %s: %d items", atom_id, len(indices))
        logger.info("Dry run complete. No changes made.")
        return

    client = load_default_openai_client(model="gpt-5.1")
    tagged = 0
    errors = 0

    for atom_id, indices in missing.items():
        rubric = _load_enrichment_rubric(atom_id)
        if not rubric or not any(rubric.values()):
            logger.warning(
                "Atom %s has no difficulty rubric — skipping.",
                atom_id,
            )
            errors += len(indices)
            continue

        phase9_path = (
            QUESTION_GENERATION_DIR / atom_id
            / "checkpoints" / "phase_9_final_validation.json"
        )
        data = json.loads(phase9_path.read_text(encoding="utf-8"))
        items = data["items"]

        for idx in indices:
            item = items[idx]
            item_id = item.get("item_id", f"idx_{idx}")
            qti_xml = item.get("qti_xml", "")

            parsed = parse_qti_xml(qti_xml)
            if not parsed.text:
                logger.warning(
                    "  %s: empty question text — skipping.", item_id,
                )
                errors += 1
                continue

            prompt = _build_prompt(rubric, parsed.text, parsed.choices)

            try:
                resp = client.generate_text(
                    prompt,
                    reasoning_effort="low",
                    response_mime_type="application/json",
                )
                result = json.loads(resp.text)
                difficulty = result.get("difficulty", "").lower().strip()

                if difficulty not in _VALID_DIFFICULTIES:
                    logger.warning(
                        "  %s: invalid difficulty '%s' — skipping.",
                        item_id, difficulty,
                    )
                    errors += 1
                    continue

                item["pipeline_meta"] = _build_backfilled_meta(
                    atom_id, difficulty, qti_xml,
                )
                tagged += 1
                logger.info(
                    "  %s → %s", item_id, difficulty,
                )

            except Exception as exc:
                logger.error("  %s: LLM error — %s", item_id, exc)
                errors += 1

        # Write updated checkpoint back
        phase9_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("Saved %s checkpoint.", atom_id)

    logger.info(
        "Done. Tagged: %d, Errors: %d, Total: %d",
        tagged, errors, total,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Backfill missing difficulty tags in Phase 9 checkpoints.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan and report without making changes.",
    )
    args = parser.parse_args()
    backfill(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
