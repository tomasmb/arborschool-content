#!/usr/bin/env python3
"""
Módulo para gestionar backups automáticos de archivos QTI generados.

Crea backups timestamped de las carpetas QTI cuando se generan XMLs,
y solo permite eliminarlos con confirmación explícita del usuario.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def create_qti_backup(
    output_dir: Path,
    generated_folders: List[str],
    backup_metadata: Dict[str, Any] | None = None,
) -> Path:
    """
    Crea un backup de las carpetas QTI generadas.

    Args:
        output_dir: Directorio base donde están las carpetas QTI
        generated_folders: Lista de nombres de carpetas que se generaron (e.g., ['Q1', 'Q19', 'Q22'])
        backup_metadata: Información adicional sobre el backup (opcional)

    Returns:
        Path al directorio de backup creado
    """
    # Crear directorio de backups si no existe
    backups_dir = output_dir / ".backups"
    backups_dir.mkdir(exist_ok=True)

    # Crear directorio de backup con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = backups_dir / f"backup_{timestamp}"
    backup_dir.mkdir(exist_ok=True)

    print(f"📦 Creando backup en: {backup_dir}")
    print()

    backed_up = []
    skipped = []
    errors = []

    # Copiar cada carpeta generada
    for folder_name in generated_folders:
        source_folder = output_dir / folder_name

        if not source_folder.exists():
            skipped.append(folder_name)
            continue

        # Verificar que tenga XML (solo hacer backup de carpetas con XML generado)
        xml_file = source_folder / "question.xml"
        if not xml_file.exists():
            skipped.append(folder_name)
            continue

        try:
            dest_folder = backup_dir / folder_name
            shutil.copytree(source_folder, dest_folder)
            backed_up.append(folder_name)
            print(f"   ✅ {folder_name}")
        except Exception as e:
            errors.append({"folder": folder_name, "error": str(e)})
            print(f"   ❌ {folder_name}: {e}")

    # Guardar metadata del backup
    metadata = {
        "timestamp": timestamp,
        "backup_dir": str(backup_dir),
        "backed_up_folders": backed_up,
        "skipped_folders": skipped,
        "errors": errors,
        "total_backed_up": len(backed_up),
    }

    if backup_metadata:
        metadata.update(backup_metadata)

    metadata_file = backup_dir / "backup_metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print()
    print(f"✅ Backup completado: {len(backed_up)} carpetas respaldadas")
    if skipped:
        print(f"⏭️  Saltadas (sin XML): {len(skipped)}")
    if errors:
        print(f"❌ Errores: {len(errors)}")
    print(f"📁 Ubicación: {backup_dir}")
    print()

    return backup_dir


def list_backups(output_dir: Path) -> List[Dict[str, Any]]:
    """
    Lista todos los backups disponibles.

    Args:
        output_dir: Directorio base donde están los backups

    Returns:
        Lista de diccionarios con información de cada backup
    """
    backups_dir = output_dir / ".backups"

    if not backups_dir.exists():
        return []

    backups = []
    for backup_folder in sorted(backups_dir.glob("backup_*"), reverse=True):
        if not backup_folder.is_dir():
            continue

        metadata_file = backup_folder / "backup_metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                backups.append(metadata)
            except Exception:
                # Si no se puede leer, crear metadata básica
                backups.append(
                    {
                        "backup_dir": str(backup_folder),
                        "timestamp": backup_folder.name.replace("backup_", ""),
                        "total_backed_up": len(list((backup_folder).glob("Q*"))),
                    }
                )

    return backups


def delete_backup(backup_dir: Path, require_confirmation: bool = True) -> bool:
    """
    Elimina un backup específico.

    Args:
        backup_dir: Directorio del backup a eliminar
        require_confirmation: Si True, no elimina sin confirmación explícita

    Returns:
        True si se eliminó, False si se canceló
    """
    if require_confirmation:
        print(f"⚠️  ADVERTENCIA: Esto eliminará el backup en {backup_dir}")
        print("   Esta operación no se puede deshacer.")
        response = input("   ¿Estás seguro? Escribe 'SI' para confirmar: ")
        if response.strip().upper() != "SI":
            print("   ❌ Operación cancelada")
            return False

    try:
        shutil.rmtree(backup_dir)
        print(f"✅ Backup eliminado: {backup_dir}")
        return True
    except Exception as e:
        print(f"❌ Error eliminando backup: {e}")
        return False


def restore_from_backup(
    backup_dir: Path,
    output_dir: Path,
    folders_to_restore: List[str] | None = None,
    overwrite: bool = False,
) -> Dict[str, Any]:
    """
    Restaura carpetas desde un backup.

    Args:
        backup_dir: Directorio del backup
        output_dir: Directorio donde restaurar
        folders_to_restore: Lista de carpetas a restaurar (None = todas)
        overwrite: Si True, sobrescribe carpetas existentes

    Returns:
        Diccionario con resultados de la restauración
    """
    if not backup_dir.exists():
        return {
            "success": False,
            "error": f"Backup directory does not exist: {backup_dir}",
        }

    output_dir.mkdir(parents=True, exist_ok=True)

    restored = []
    skipped = []
    errors = []

    # Obtener lista de carpetas en el backup
    backup_folders = [f.name for f in backup_dir.iterdir() if f.is_dir() and f.name.startswith("Q")]

    if folders_to_restore:
        backup_folders = [f for f in backup_folders if f in folders_to_restore]

    for folder_name in backup_folders:
        source_folder = backup_dir / folder_name
        dest_folder = output_dir / folder_name

        if dest_folder.exists() and not overwrite:
            skipped.append(folder_name)
            continue

        try:
            if dest_folder.exists():
                shutil.rmtree(dest_folder)
            shutil.copytree(source_folder, dest_folder)
            restored.append(folder_name)
            print(f"   ✅ {folder_name}")
        except Exception as e:
            errors.append({"folder": folder_name, "error": str(e)})
            print(f"   ❌ {folder_name}: {e}")

    return {
        "success": True,
        "restored": restored,
        "skipped": skipped,
        "errors": errors,
        "total_restored": len(restored),
    }
