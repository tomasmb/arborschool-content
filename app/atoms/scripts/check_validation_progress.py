"""Script para monitorear el progreso de la validación.

Usage:
    python -m app.atoms.scripts.check_validation_progress --output-dir validation_results
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Expected standards
EXPECTED_STANDARDS = [
    "M1-ALG-01",
    "M1-ALG-02",
    "M1-ALG-03",
    "M1-ALG-04",
    "M1-ALG-05",
    "M1-ALG-06",
    "M1-GEO-01",
    "M1-GEO-02",
    "M1-GEO-03",
    "M1-NUM-01",
    "M1-NUM-02",
    "M1-NUM-03",
    "M1-PROB-01",
    "M1-PROB-02",
    "M1-PROB-03",
    "M1-PROB-04",
]


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Check validation progress.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("validation_results"),
        help="Validation results directory (default: validation_results)",
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed information for each standard",
    )

    args = parser.parse_args()

    results_dir = args.output_dir

    if not results_dir.exists():
        print("❌ Directorio de resultados no existe")
        print(f"   {results_dir}")
        sys.exit(1)

    # Find validation files
    validation_files = sorted(results_dir.glob("validation_M1-*.json"))
    combined_file = results_dir / "validation_all_standards.json"

    print("=" * 70)
    print("PROGRESO DE VALIDACIÓN")
    print("=" * 70)
    print()

    # Check combined file
    if combined_file.exists():
        try:
            with combined_file.open(encoding="utf-8") as f:
                combined_data = json.load(f)
            
            completed = len(combined_data)
            total = len(EXPECTED_STANDARDS)
            progress = (completed / total) * 100 if total > 0 else 0

            print(f"📊 Progreso: {completed}/{total} estándares ({progress:.1f}%)")
            print()

            # Show progress bar
            bar_length = 50
            filled = int(bar_length * progress / 100)
            bar = "█" * filled + "░" * (bar_length - filled)
            print(f"[{bar}] {progress:.1f}%")
            print()

            # Show status by standard
            print("Estado por estándar:")
            print("-" * 70)

            for std_id in EXPECTED_STANDARDS:
                if std_id in combined_data:
                    result = combined_data[std_id]
                    summary = result.get("evaluation_summary", {})
                    total_atoms = summary.get("total_atoms", 0)
                    passing = summary.get("atoms_passing_all_checks", 0)
                    quality = summary.get("overall_quality", "N/A")
                    issues = result.get("detailed_issues", [])
                    high_priority = len([i for i in issues if i.get("priority") == "high"])
                    medium_priority = len([i for i in issues if i.get("priority") == "medium"])

                    if high_priority == 0 and medium_priority == 0:
                        status = "✅"
                    elif high_priority == 0:
                        status = "⚠️"
                    else:
                        status = "❌"

                    print(
                        f"{status} {std_id}: {passing}/{total_atoms} átomos OK | "
                        f"Calidad: {quality} | Issues: {high_priority} alta, {medium_priority} media"
                    )

                    if args.detailed and issues:
                        for issue in issues[:3]:  # Show first 3
                            priority = issue.get("priority", "unknown")
                            desc = issue.get("description", "")[:60]
                            print(f"     [{priority}] {desc}...")
                else:
                    print(f"⏳ {std_id}: Pendiente")

            print()
            print("-" * 70)

            # Summary statistics
            all_high_priority = sum(
                len([i for i in combined_data[s].get("detailed_issues", []) if i.get("priority") == "high"])
                for s in combined_data
            )
            all_medium_priority = sum(
                len([i for i in combined_data[s].get("detailed_issues", []) if i.get("priority") == "medium"])
                for s in combined_data
            )
            total_atoms_validated = sum(
                combined_data[s].get("evaluation_summary", {}).get("total_atoms", 0)
                for s in combined_data
            )
            total_atoms_passing = sum(
                combined_data[s].get("evaluation_summary", {}).get("atoms_passing_all_checks", 0)
                for s in combined_data
            )

            print()
            print("Resumen general:")
            print(f"  Total átomos validados: {total_atoms_validated}")
            print(f"  Átomos sin issues: {total_atoms_passing}")
            print(f"  Issues alta prioridad: {all_high_priority}")
            print(f"  Issues media prioridad: {all_medium_priority}")

        except Exception as e:
            print(f"❌ Error leyendo archivo combinado: {e}")
            sys.exit(1)
    else:
        # Show individual files
        completed = len(validation_files)
        total = len(EXPECTED_STANDARDS)
        progress = (completed / total) * 100 if total > 0 else 0

        print(f"📊 Progreso: {completed}/{total} estándares ({progress:.1f}%)")
        print()

        # Progress bar
        bar_length = 50
        filled = int(bar_length * progress / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"[{bar}] {progress:.1f}%")
        print()

        if validation_files:
            print("Estándares completados:")
            print("-" * 70)
            for vf in validation_files:
                std_id = vf.stem.replace("validation_", "")
                try:
                    with vf.open(encoding="utf-8") as f:
                        data = json.load(f)
                    summary = data.get("evaluation_summary", {})
                    total_atoms = summary.get("total_atoms", 0)
                    passing = summary.get("atoms_passing_all_checks", 0)
                    quality = summary.get("overall_quality", "N/A")
                    print(f"  ✅ {std_id}: {passing}/{total_atoms} átomos OK | Calidad: {quality}")
                except Exception as e:
                    print(f"  ⚠️  {std_id}: Error leyendo - {e}")
        else:
            print("⏳ Aún no hay resultados. La validación puede estar iniciando...")

    print()
    print("=" * 70)
    print(f"Directorio: {results_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()

