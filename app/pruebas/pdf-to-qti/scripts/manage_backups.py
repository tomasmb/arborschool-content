#!/usr/bin/env python3
"""
Script CLI para gestionar backups de QTI.

Usage:
    python manage_backups.py list --test-name prueba-invierno-2026
    python manage_backups.py delete --test-name prueba-invierno-2026 --backup-name backup_20241216_143022
    python manage_backups.py restore --test-name prueba-invierno-2026 --backup-name backup_20241216_143022
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# scripts/ -> pdf-to-qti/ -> pruebas/ -> app/ -> repo root
project_root = Path(__file__).resolve().parents[4]

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backup_manager import delete_backup, list_backups, restore_from_backup


def get_output_dir(test_name: str) -> Path:
    """Get the QTI output directory for a test."""
    return project_root / "app" / "data" / "pruebas" / "finalizadas" / test_name / "qti"


def main():
    """CLI para gestionar backups."""
    parser = argparse.ArgumentParser(
        description="Manage QTI backups",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python manage_backups.py list --test-name prueba-invierno-2026
  python manage_backups.py delete --test-name prueba-invierno-2026 --backup-name backup_20241216
  python manage_backups.py restore --test-name prueba-invierno-2026 --backup-name backup_20241216
        """,
    )
    parser.add_argument(
        "action",
        choices=["list", "delete", "restore"],
        help="Action to perform",
    )
    parser.add_argument(
        "--test-name",
        required=True,
        help="Name of the test (e.g., prueba-invierno-2026)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Override: Base QTI output directory (default: auto-derived from test name)",
    )
    parser.add_argument(
        "--backup-name",
        help="Backup name (e.g., 'backup_20241216_143022') for delete/restore",
    )
    parser.add_argument(
        "--folders",
        nargs="+",
        help="Specific folders to restore (only for restore action)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing folders when restoring",
    )
    parser.add_argument(
        "--no-confirm",
        action="store_true",
        help="Skip confirmation prompt (use with caution)",
    )

    args = parser.parse_args()

    output_dir = args.output_dir or get_output_dir(args.test_name)
    output_dir = output_dir.resolve()

    if args.action == "list":
        backups = list_backups(output_dir)

        if not backups:
            print("📦 No backups found")
            return

        print(f"📦 Found {len(backups)} backup(s):")
        print()

        for backup in backups:
            timestamp = backup.get("timestamp", "unknown")
            total = backup.get("total_backed_up", 0)
            backup_dir = backup.get("backup_dir", "")

            print(f"  {timestamp}")
            print(f"    Folders: {total}")
            print(f"    Location: {backup_dir}")
            print()

    elif args.action == "delete":
        if not args.backup_name:
            print("❌ --backup-name is required for delete action")
            sys.exit(1)

        backups_dir = output_dir / ".backups"
        backup_dir = backups_dir / args.backup_name

        if not backup_dir.exists():
            print(f"❌ Backup not found: {backup_dir}")
            sys.exit(1)

        delete_backup(backup_dir, require_confirmation=not args.no_confirm)

    elif args.action == "restore":
        if not args.backup_name:
            print("❌ --backup-name is required for restore action")
            sys.exit(1)

        backups_dir = output_dir / ".backups"
        backup_dir = backups_dir / args.backup_name

        if not backup_dir.exists():
            print(f"❌ Backup not found: {backup_dir}")
            sys.exit(1)

        print(f"🔄 Restoring from backup: {backup_dir}")
        print()

        result = restore_from_backup(
            backup_dir=backup_dir,
            output_dir=output_dir,
            folders_to_restore=args.folders,
            overwrite=args.overwrite,
        )

        print()
        if result["success"]:
            print(f"✅ Restored {result['total_restored']} folder(s)")
            if result["skipped"]:
                print(f"⏭️  Skipped {len(result['skipped'])} folder(s) (use --overwrite to overwrite)")
            if result["errors"]:
                print(f"❌ Errors: {len(result['errors'])}")
        else:
            print(f"❌ Restore failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)


if __name__ == "__main__":
    main()
