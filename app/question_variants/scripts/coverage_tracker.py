#!/usr/bin/env python3
"""Coverage tracker for hard variant generation.

Reports how many questions per test have approved hard variants,
and which ones are still missing.

Usage:
    python -m app.question_variants.coverage_tracker
    python -m app.question_variants.coverage_tracker --output-dir app/data/pruebas/hard_variants
"""

from __future__ import annotations

import argparse
from pathlib import Path

FINALIZED_PATH = Path("app/data/pruebas/finalizadas")
DEFAULT_OUTPUT_DIR = Path("app/data/pruebas/hard_variants")


def get_finalized_questions(test_id: str) -> list[str]:
    """List all finalized question IDs for a test."""
    test_path = FINALIZED_PATH / test_id / "qti"
    if not test_path.exists():
        return []
    return sorted(
        d.name for d in test_path.iterdir()
        if d.is_dir() and d.name.startswith("Q")
    )


def get_approved_variants(output_dir: Path, test_id: str) -> dict[str, list[str]]:
    """Find approved hard variants per question for a given test.

    Returns a dict: {question_id: [variant_ids]}
    """
    approved: dict[str, list[str]] = {}

    # Check the main production directory: {output_dir}/{test_id}/Q*/variants/approved/
    test_path = output_dir / test_id
    if test_path.exists():
        for question_dir in sorted(test_path.glob("Q*")):
            question_id = question_dir.name
            approved_dir = question_dir / "variants" / "approved"
            if not approved_dir.exists():
                approved_dir = question_dir / "approved"
            if approved_dir.exists():
                variant_ids = sorted(
                    d.name for d in approved_dir.iterdir()
                    if d.is_dir() and (d / "question.xml").exists()
                )
                if variant_ids:
                    approved[question_id] = variant_ids

    return approved


def build_coverage_report(output_dir: Path) -> str:
    """Build a coverage report across all finalized tests."""
    tests = sorted(
        d.name for d in FINALIZED_PATH.iterdir()
        if d.is_dir() and (d / "qti").exists()
    )

    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("REPORTE DE COBERTURA — VARIANTES DURAS")
    lines.append("=" * 70)

    total_questions = 0
    total_with_variants = 0
    total_variants = 0

    for test_id in tests:
        finalized = get_finalized_questions(test_id)
        approved = get_approved_variants(output_dir, test_id)

        questions_with = len(approved)
        variant_count = sum(len(v) for v in approved.values())
        missing = [q for q in finalized if q not in approved]

        total_questions += len(finalized)
        total_with_variants += questions_with
        total_variants += variant_count

        lines.append(f"\n📋 {test_id}")
        lines.append(f"   Preguntas finalizadas: {len(finalized)}")
        lines.append(f"   Con variantes duras:   {questions_with}/{len(finalized)}")
        lines.append(f"   Total variantes:       {variant_count}")
        if approved:
            lines.append(f"   Detalle aprobadas:")
            for q_id, v_ids in sorted(approved.items()):
                lines.append(f"     {q_id}: {len(v_ids)} ({', '.join(v_ids)})")
        if missing:
            lines.append(f"   ❌ Faltan ({len(missing)}): {', '.join(missing[:20])}")
            if len(missing) > 20:
                lines.append(f"      ... y {len(missing) - 20} más")

    lines.append(f"\n{'=' * 70}")
    lines.append(f"TOTALES")
    lines.append(f"  Preguntas:        {total_questions}")
    lines.append(f"  Con variantes:    {total_with_variants}/{total_questions}")
    lines.append(f"  Total variantes:  {total_variants}")
    target = total_questions * 10
    lines.append(f"  Objetivo (×10):   {total_variants}/{target} ({total_variants*100//target if target else 0}%)")
    lines.append(f"{'=' * 70}")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Report hard variant coverage across finalized tests.")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Output directory for hard variants (default: app/data/pruebas/hard_variants)",
    )
    args = parser.parse_args()
    print(build_coverage_report(Path(args.output_dir)))


if __name__ == "__main__":
    main()
