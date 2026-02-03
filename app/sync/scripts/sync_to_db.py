#!/usr/bin/env python3
"""CLI script for syncing content repo data to the student-facing app database.

Usage:
    # Dry run (see what would change)
    python -m app.sync.scripts.sync_to_db --dry-run

    # Sync everything (including variants)
    python -m app.sync.scripts.sync_to_db --include-variants

    # Sync specific entities
    python -m app.sync.scripts.sync_to_db --only atoms standards

    # Sync questions with variants
    python -m app.sync.scripts.sync_to_db --only questions --include-variants

    # With S3 image upload
    python -m app.sync.scripts.sync_to_db --upload-images

    # Verbose output
    python -m app.sync.scripts.sync_to_db --verbose
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add repo root to path for imports
REPO_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(REPO_ROOT / ".env")

from app.sync.db_client import DBClient, DBConfig
from app.sync.extractors import (
    PRUEBAS_FINALIZADAS_DIR,
    extract_all_tests,
    extract_atoms,
    extract_standards,
)
from app.sync.variant_extractors import extract_variants
from app.sync.s3_client import ImageUploader, S3Config, process_all_questions_images
from app.sync.transformers import (
    build_sync_payload,
)

# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Sync content repo data to the student-facing app database.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Preview what would be synced
    python -m app.sync.scripts.sync_to_db --dry-run

    # Sync all content
    python -m app.sync.scripts.sync_to_db

    # Sync only atoms and standards
    python -m app.sync.scripts.sync_to_db --only atoms standards

    # Sync with S3 image upload
    python -m app.sync.scripts.sync_to_db --upload-images
        """,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be synced without making changes",
    )

    parser.add_argument(
        "--only",
        nargs="+",
        choices=["atoms", "standards", "questions", "tests", "variants"],
        help="Only sync specific entity types",
    )

    parser.add_argument(
        "--include-variants",
        action="store_true",
        help="Include question variants (alternate versions) from alternativas/",
    )

    parser.add_argument(
        "--upload-images",
        action="store_true",
        help="Upload local images in QTI to S3 (requires S3_* env vars)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print detailed progress information",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Determine what to sync
    sync_atoms = args.only is None or "atoms" in args.only
    sync_standards = args.only is None or "standards" in args.only
    sync_questions = args.only is None or "questions" in args.only
    sync_tests = args.only is None or "tests" in args.only
    sync_variants = args.include_variants or (args.only is not None and "variants" in args.only)

    print("=" * 60)
    print("Content Repo → Database Sync")
    print("=" * 60)

    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made\n")

    # -------------------------------------------------------------------------
    # Extract data
    # -------------------------------------------------------------------------
    print("\n📖 Extracting data from content repo...")

    extracted_standards = []
    extracted_atoms = []
    extracted_tests = []
    extracted_questions = []
    extracted_variants = []

    if sync_standards:
        extracted_standards = extract_standards()
        print(f"   ✓ Standards: {len(extracted_standards)}")

    if sync_atoms:
        extracted_atoms = extract_atoms()
        print(f"   ✓ Atoms: {len(extracted_atoms)}")

    if sync_tests or sync_questions:
        extracted_tests, extracted_questions = extract_all_tests()
        print(f"   ✓ Tests: {len(extracted_tests)}")
        print(f"   ✓ Questions: {len(extracted_questions)}")

    if sync_variants:
        extracted_variants = extract_variants()
        print(f"   ✓ Variants: {len(extracted_variants)}")

    # -------------------------------------------------------------------------
    # Process images (if requested)
    # -------------------------------------------------------------------------
    updated_qti: dict[str, str] = {}

    if args.upload_images and extracted_questions:
        print("\n📤 Processing images for S3 upload...")
        try:
            s3_config = S3Config.from_env()
            uploader = ImageUploader(s3_config)
            updated_qti = process_all_questions_images(
                extracted_questions,
                PRUEBAS_FINALIZADAS_DIR,
                uploader,
            )
            print(f"   ✓ Processed {len(updated_qti)} questions for images")
        except ValueError as e:
            print(f"   ⚠ Skipping S3 upload: {e}")
            print("   (Set AWS_S3_KEY, AWS_S3_SECRET environment variables)")

    # Update QTI XML if images were processed
    if updated_qti:
        for q in extracted_questions:
            if q.id in updated_qti:
                q.qti_xml = updated_qti[q.id]

    # -------------------------------------------------------------------------
    # Transform data
    # -------------------------------------------------------------------------
    print("\n🔄 Transforming to database schema...")

    # Filter based on what we're syncing
    if not sync_standards:
        extracted_standards = []
    if not sync_atoms:
        extracted_atoms = []
    if not sync_tests:
        extracted_tests = []
    if not sync_questions:
        extracted_questions = []
    if not sync_variants:
        extracted_variants = []

    payload = build_sync_payload(
        standards=extracted_standards,
        atoms=extracted_atoms,
        tests=extracted_tests,
        questions=extracted_questions,
        variants=extracted_variants if extracted_variants else None,
    )

    summary = payload.summary()
    official_count = len(extracted_questions)
    variant_count = len(extracted_variants)
    print(f"   ✓ Subjects: {summary['subjects']}")
    print(f"   ✓ Standards: {summary['standards']}")
    print(f"   ✓ Atoms: {summary['atoms']}")
    print(f"   ✓ Tests: {summary['tests']}")
    print(f"   ✓ Questions: {summary['questions']} ({official_count} official + {variant_count} variants)")
    print(f"   ✓ Question-Atom links: {summary['question_atoms']}")
    print(f"   ✓ Test-Question links: {summary['test_questions']}")

    # -------------------------------------------------------------------------
    # Sync to database
    # -------------------------------------------------------------------------
    print("\n💾 Syncing to database...")

    try:
        db_config = DBConfig.from_env()
        db_client = DBClient(db_config)

        if args.verbose:
            print(f"   Connecting to {db_config.host}:{db_config.port}/{db_config.database}...")

        results = db_client.sync_all(payload, dry_run=args.dry_run)

        print("\n📊 Results:")
        for table, count in results.items():
            status = "would affect" if args.dry_run else "affected"
            print(f"   {table}: {count} rows {status}")

    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Database error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    print("\n" + "=" * 60)
    if args.dry_run:
        print("✅ Dry run complete - no changes made")
        print("   Run without --dry-run to apply changes")
    else:
        print("✅ Sync complete!")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
