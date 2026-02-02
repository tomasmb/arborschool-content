#!/usr/bin/env python3
"""
Generic script to process ANY PAES test.

Usage:
    # Process a test (auto-derives all paths from test name)
    python process_test.py --test-name prueba-invierno-2026

    # With custom paths
    python process_test.py --test-name mi-test \
        --questions-dir /path/to/questions \
        --output-dir /path/to/output

    # Process specific questions only
    python process_test.py --test-name prueba-invierno-2026 --questions 1 5 10

    # Skip existing questions
    python process_test.py --test-name prueba-invierno-2026 --skip-existing

    # Disable PAES optimizations
    python process_test.py --test-name prueba-invierno-2026 --no-paes-mode
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

# Load environment variables from .env file
from dotenv import load_dotenv

# scripts/ -> pdf-to-qti/ -> pruebas/ -> app/ -> repo root
project_root = Path(__file__).resolve().parents[4]
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)

# Add pdf-to-qti directory to path for local imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backup_manager import create_qti_backup
from main import process_single_question_pdf


def get_default_paths(test_name: str) -> dict[str, Path]:
    """
    Derive all paths from test name using standard conventions.

    Directory structure:
        app/data/pruebas/finalizadas/{test-name}/
            ├── questions/     # Input PDFs (Q1.pdf, Q2.pdf, ...)
            ├── qti/           # Output QTI folders
            └── ...
        app/data/pruebas/procesadas/{test-name}/
            └── respuestas_correctas.json   # Answer key (optional)
    """
    data_dir = project_root / "app" / "data" / "pruebas"

    return {
        "questions_dir": data_dir / "finalizadas" / test_name / "questions",
        "output_dir": data_dir / "finalizadas" / test_name / "qti",
        "answer_key": data_dir / "procesadas" / test_name / "respuestas_correctas.json",
        "results_file": data_dir / "finalizadas" / test_name / "processing_results.json",
    }


def find_answer_key(test_name: str, output_dir: Path) -> Path | None:
    """Find answer key file, checking multiple common locations."""
    paths_to_check = [
        # Standard location in procesadas
        project_root / "app" / "data" / "pruebas" / "procesadas" / test_name / "respuestas_correctas.json",
        # Alternative: next to output
        output_dir.parent / "respuestas_correctas.json",
        # Alternative: in finalizadas
        project_root / "app" / "data" / "pruebas" / "finalizadas" / test_name / "respuestas_correctas.json",
    ]

    for path in paths_to_check:
        if path.exists():
            return path
    return None


def process_all_questions(
    test_name: str,
    questions_dir: Path,
    output_dir: Path,
    paes_mode: bool = True,
    skip_existing: bool = True,
    specific_questions: list[int] | None = None,
    backup_interval: int = 10,
) -> dict[str, Any]:
    """
    Process all question PDFs from a directory.

    Args:
        test_name: Name of the test (for metadata and backups)
        questions_dir: Directory containing individual question PDFs
        output_dir: Base directory for outputs
        paes_mode: Use PAES optimizations
        skip_existing: Skip questions that already have valid XML
        specific_questions: If provided, only process these question numbers
        backup_interval: Create backup every N questions

    Returns:
        Dictionary with processing results
    """
    if not questions_dir.exists():
        return {"success": False, "error": f"Questions directory not found: {questions_dir}"}

    # Find all PDF files
    question_pdfs = sorted(questions_dir.glob("Q*.pdf"), key=lambda p: int(p.stem[1:]))

    # Filter to specific questions if requested
    if specific_questions:
        question_pdfs = [p for p in question_pdfs if int(p.stem[1:]) in specific_questions]
        print(f"📋 Filtering to {len(question_pdfs)} specific questions: {specific_questions}")

    if not question_pdfs:
        return {"success": False, "error": f"No matching PDF files found in {questions_dir}"}

    print(f"📋 Found {len(question_pdfs)} question PDFs to process")
    print(f"📁 Output directory: {output_dir}")
    print(f"🏷️  Test name: {test_name}")
    print()

    results = {
        "test_name": test_name,
        "total": len(question_pdfs),
        "successful": [],
        "failed": [],
        "skipped": [],
        "processing_times": [],
        "start_time": time.time(),
    }

    # Load answer key if available
    answer_key_data = None
    answer_key_path = find_answer_key(test_name, output_dir)
    if answer_key_path:
        try:
            with open(answer_key_path, "r", encoding="utf-8") as f:
                answer_key_data = json.load(f)
            print(f"✅ Loaded answer key from {answer_key_path.name}")
            print(f"   Contains {len(answer_key_data.get('answers', {}))} answers")
        except Exception as e:
            print(f"⚠️  Could not load answer key: {e}")
    else:
        print("ℹ️  No answer key found (will process without correct answers)")
    print()

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process each question
    generated_folders = []

    for i, pdf_path in enumerate(question_pdfs, 1):
        question_id = pdf_path.stem  # e.g., "Q1" from "Q1.pdf"
        question_output_dir = output_dir / question_id

        print(f"[{i}/{len(question_pdfs)}] Processing {question_id}...")
        start_time = time.time()

        try:
            result = process_single_question_pdf(
                input_pdf_path=str(pdf_path),
                output_dir=str(question_output_dir),
                openai_api_key=None,  # Use from .env
                paes_mode=paes_mode,
                skip_if_exists=skip_existing,
            )

            elapsed = time.time() - start_time
            results["processing_times"].append(elapsed)

            if result.get("success"):
                was_skipped = result.get("skipped", False)
                was_regenerated = result.get("regenerated", False)

                status_parts = []
                if was_skipped:
                    status_parts.append("Skipped (exists)")
                    results["skipped"].append(question_id)
                else:
                    status_parts.append("Success")
                if was_regenerated:
                    status_parts.append("(regenerated)")

                print(f"   ✅ {' '.join(status_parts)} ({elapsed:.1f}s)")

                results["successful"].append(
                    {
                        "question": question_id,
                        "time": elapsed,
                        "title": result.get("title", "Unknown"),
                        "skipped": was_skipped,
                        "regenerated": was_regenerated,
                    }
                )

                # Track generated XMLs for backup
                xml_file = question_output_dir / "question.xml"
                if xml_file.exists() and not was_skipped:
                    generated_folders.append(question_id)

                    # Create incremental backup
                    if len(generated_folders) % backup_interval == 0:
                        _create_incremental_backup(test_name, output_dir, generated_folders, backup_interval, i)
            else:
                print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
                results["failed"].append(
                    {
                        "question": question_id,
                        "error": result.get("error", "Unknown error"),
                    }
                )

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"   ❌ Exception: {e}")
            results["failed"].append(
                {
                    "question": question_id,
                    "error": str(e),
                }
            )

    # Final backup if there are any unbackuped questions
    remaining = len(generated_folders) % backup_interval
    if remaining > 0 and generated_folders:
        _create_final_backup(test_name, output_dir, generated_folders)

    # Calculate summary
    results["end_time"] = time.time()
    results["total_time"] = results["end_time"] - results["start_time"]
    results["summary"] = {
        "total_questions": len(question_pdfs),
        "successful": len(results["successful"]),
        "failed": len(results["failed"]),
        "skipped": len(results["skipped"]),
        "success_rate": len(results["successful"]) / len(question_pdfs) * 100 if question_pdfs else 0,
        "avg_time": sum(results["processing_times"]) / len(results["processing_times"]) if results["processing_times"] else 0,
    }

    return results


def _create_incremental_backup(
    test_name: str,
    output_dir: Path,
    generated_folders: list[str],
    batch_size: int,
    current_index: int,
) -> None:
    """Create incremental backup of recently generated questions."""
    print("   💾 Creating incremental backup...")
    try:
        last_batch = generated_folders[-batch_size:]
        backup_metadata = {
            "test_name": test_name,
            "batch_number": len(generated_folders) // batch_size,
            "total_processed": current_index,
            "questions_in_batch": last_batch,
        }
        backup_dir = create_qti_backup(
            output_dir=output_dir,
            generated_folders=last_batch,
            backup_metadata=backup_metadata,
        )
        print(f"   ✅ Backup created: {backup_dir.name}")
    except Exception as e:
        print(f"   ⚠️  Backup failed: {e}")


def _create_final_backup(
    test_name: str,
    output_dir: Path,
    generated_folders: list[str],
) -> None:
    """Create final backup of all remaining questions."""
    print("\n💾 Creating final backup...")
    try:
        backup_metadata = {
            "test_name": test_name,
            "final_backup": True,
            "total_questions": len(generated_folders),
        }
        backup_dir = create_qti_backup(
            output_dir=output_dir,
            generated_folders=generated_folders,
            backup_metadata=backup_metadata,
        )
        print(f"✅ Final backup created: {backup_dir.name}")
    except Exception as e:
        print(f"⚠️  Final backup failed: {e}")


def print_summary(results: dict[str, Any]) -> None:
    """Print processing summary."""
    summary = results.get("summary", {})

    print("\n" + "=" * 60)
    print(f"📊 PROCESSING SUMMARY: {results.get('test_name', 'Unknown')}")
    print("=" * 60)
    print(f"Total questions:  {summary.get('total_questions', 0)}")
    print(f"Successful:       {summary.get('successful', 0)}")
    print(f"Failed:           {summary.get('failed', 0)}")
    print(f"Skipped:          {summary.get('skipped', 0)}")
    print(f"Success rate:     {summary.get('success_rate', 0):.1f}%")
    print(f"Average time:     {summary.get('avg_time', 0):.1f}s per question")
    print(f"Total time:       {results.get('total_time', 0):.1f}s")

    if results.get("failed"):
        print("\n❌ Failed questions:")
        for fail in results["failed"]:
            print(f"   - {fail['question']}: {fail['error'][:50]}...")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Process PAES test questions to QTI format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process entire test (auto-derives paths)
  python process_test.py --test-name prueba-invierno-2026

  # Process specific questions
  python process_test.py --test-name prueba-invierno-2026 --questions 1 5 10 15

  # Custom directories
  python process_test.py --test-name my-test \\
      --questions-dir /custom/questions \\
      --output-dir /custom/output

  # Force reprocessing (don't skip existing)
  python process_test.py --test-name prueba-invierno-2026 --no-skip-existing
        """,
    )
    parser.add_argument(
        "--test-name",
        required=True,
        help="Name of the test (e.g., prueba-invierno-2026, seleccion-regular-2025)",
    )
    parser.add_argument(
        "--questions-dir",
        type=Path,
        help="Directory containing question PDFs (default: auto-derived from test name)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for QTI files (default: auto-derived from test name)",
    )
    parser.add_argument(
        "--questions",
        type=int,
        nargs="+",
        help="Process only these specific question numbers (e.g., --questions 1 5 10)",
    )
    parser.add_argument(
        "--no-paes-mode",
        action="store_true",
        help="Disable PAES-specific optimizations",
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Reprocess questions even if they already have valid XML",
    )
    parser.add_argument(
        "--backup-interval",
        type=int,
        default=10,
        help="Create backup every N questions (default: 10)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without actually processing",
    )

    args = parser.parse_args()

    # Get default paths from test name
    default_paths = get_default_paths(args.test_name)

    questions_dir = args.questions_dir or default_paths["questions_dir"]
    output_dir = args.output_dir or default_paths["output_dir"]
    results_file = default_paths["results_file"]

    print(f"🚀 Processing test: {args.test_name}")
    print(f"📁 Questions: {questions_dir}")
    print(f"📁 Output: {output_dir}")
    print()

    if not questions_dir.exists():
        print(f"❌ Questions directory not found: {questions_dir}")
        print()
        print("💡 Make sure you have:")
        print(f"   1. Split the PDF into individual questions in: {questions_dir}")
        print("   2. Or specify a custom path with --questions-dir")
        return 1

    if args.dry_run:
        question_pdfs = sorted(questions_dir.glob("Q*.pdf"))
        if args.questions:
            question_pdfs = [p for p in question_pdfs if int(p.stem[1:]) in args.questions]
        print(f"🔍 DRY RUN - Would process {len(question_pdfs)} questions:")
        for pdf in question_pdfs[:10]:
            print(f"   - {pdf.name}")
        if len(question_pdfs) > 10:
            print(f"   ... and {len(question_pdfs) - 10} more")
        return 0

    # Process questions
    results = process_all_questions(
        test_name=args.test_name,
        questions_dir=questions_dir,
        output_dir=output_dir,
        paes_mode=not args.no_paes_mode,
        skip_existing=not args.no_skip_existing,
        specific_questions=args.questions,
        backup_interval=args.backup_interval,
    )

    # Print summary
    print_summary(results)

    # Save results
    results_file.parent.mkdir(parents=True, exist_ok=True)
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n📄 Results saved to: {results_file}")

    return 0 if results.get("summary", {}).get("failed", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
