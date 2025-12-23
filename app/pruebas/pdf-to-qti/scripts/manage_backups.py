#!/usr/bin/env python3
"""
Script CLI para gestionar backups de QTI.
"""

from __future__ import annotations

import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backup_manager import list_backups, delete_backup, restore_from_backup


def main():
    """CLI para gestionar backups."""
    parser = argparse.ArgumentParser(description="Manage QTI backups")
    parser.add_argument(
        "action",
        choices=["list", "delete", "restore"],
        help="Action to perform",
    )
    parser.add_argument(
        "--output-dir",
        default="../../data/pruebas/procesadas/seleccion-regular-2026/qti",
        help="Base QTI output directory",
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
    
    output_dir = Path(args.output_dir).resolve()
    
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
