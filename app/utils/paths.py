"""Centralized path constants for the application.

This module provides a single source of truth for all commonly-used paths
in the codebase, eliminating duplicate Path(__file__) calculations and
ensuring consistent path resolution across all modules.

Usage:
    from app.utils.paths import DATA_DIR, ATOMS_DIR, STANDARDS_DIR

    # Use paths directly
    atoms_file = ATOMS_DIR / "paes_m1_2026_atoms.json"

    # Or use helper functions for common files
    atoms_file = get_atoms_file("paes_m1_2026")
"""

from __future__ import annotations

from pathlib import Path

# -----------------------------------------------------------------------------
# Root directories
# -----------------------------------------------------------------------------

# Repository root - calculated once, used everywhere
# This file is at: app/utils/paths.py
# So parents[2] gets us to repo root
REPO_ROOT = Path(__file__).resolve().parents[2]

# App directory
APP_DIR = REPO_ROOT / "app"

# Main data directory
DATA_DIR = APP_DIR / "data"

# -----------------------------------------------------------------------------
# Data subdirectories
# -----------------------------------------------------------------------------

# Atoms data
ATOMS_DIR = DATA_DIR / "atoms"

# Standards data
STANDARDS_DIR = DATA_DIR / "standards"

# Temarios data
TEMARIOS_DIR = DATA_DIR / "temarios"
TEMARIOS_PDF_DIR = TEMARIOS_DIR / "pdf"
TEMARIOS_JSON_DIR = TEMARIOS_DIR / "json"

# Pruebas (tests) data
PRUEBAS_DIR = DATA_DIR / "pruebas"
PRUEBAS_FINALIZADAS_DIR = PRUEBAS_DIR / "finalizadas"
PRUEBAS_PROCESADAS_DIR = PRUEBAS_DIR / "procesadas"
PRUEBAS_RAW_DIR = PRUEBAS_DIR / "raw"
PRUEBAS_ALTERNATIVAS_DIR = PRUEBAS_DIR / "alternativas"

# Diagnostic test variants (flat structure)
DIAGNOSTICO_DIR = DATA_DIR / "diagnostico"
DIAGNOSTICO_VARIANTES_DIR = DIAGNOSTICO_DIR / "variantes"

# Backups
BACKUPS_DIR = DATA_DIR / "backups"

# Jobs state (for pipeline resume functionality)
JOBS_DIR = DATA_DIR / ".jobs"


# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------


def get_atoms_file(name: str = "paes_m1_2026") -> Path:
    """Get the path to an atoms JSON file.

    Args:
        name: Base name of the atoms file (without '_atoms.json' suffix).
              Defaults to "paes_m1_2026".

    Returns:
        Path to the atoms JSON file.

    Example:
        >>> get_atoms_file("paes_m1_2026")
        PosixPath('.../app/data/atoms/paes_m1_2026_atoms.json')
    """
    return ATOMS_DIR / f"{name}_atoms.json"


def get_standards_file(name: str = "paes_m1_2026") -> Path:
    """Get the path to a standards JSON file.

    Args:
        name: Base name of the standards file (without '.json' suffix).
              Defaults to "paes_m1_2026".

    Returns:
        Path to the standards JSON file.

    Example:
        >>> get_standards_file("paes_m1_2026")
        PosixPath('.../app/data/standards/paes_m1_2026.json')
    """
    return STANDARDS_DIR / f"{name}.json"


def get_temario_pdf(stem: str) -> Path:
    """Get the path to a temario PDF file.

    Args:
        stem: PDF filename without extension.

    Returns:
        Path to the temario PDF file.
    """
    return TEMARIOS_PDF_DIR / f"{stem}.pdf"


def get_temario_json(name: str) -> Path:
    """Get the path to a temario JSON file.

    Args:
        name: JSON filename (with or without .json extension).

    Returns:
        Path to the temario JSON file.
    """
    if not name.endswith(".json"):
        name = f"{name}.json"
    return TEMARIOS_JSON_DIR / name


def get_test_dir(test_name: str) -> Path:
    """Get the path to a finalized test directory.

    Args:
        test_name: Name of the test (e.g., "prueba-invierno-2026").

    Returns:
        Path to the test directory in pruebas/finalizadas.
    """
    return PRUEBAS_FINALIZADAS_DIR / test_name


def get_test_qti_dir(test_name: str) -> Path:
    """Get the path to a test's QTI directory.

    Args:
        test_name: Name of the test.

    Returns:
        Path to the test's qti/ subdirectory.
    """
    return PRUEBAS_FINALIZADAS_DIR / test_name / "qti"


def get_question_dir(test_name: str, question_id: str) -> Path:
    """Get the path to a specific question's directory.

    Args:
        test_name: Name of the test.
        question_id: Question identifier (e.g., "Q1", "Q15").

    Returns:
        Path to the question directory.
    """
    return PRUEBAS_FINALIZADAS_DIR / test_name / "qti" / question_id


def get_question_metadata_path(test_name: str, question_id: str) -> Path:
    """Get the path to a question's metadata_tags.json file.

    Args:
        test_name: Name of the test (e.g., "prueba-invierno-2026").
        question_id: Question identifier (e.g., "Q1").

    Returns:
        Path to the metadata_tags.json file.
    """
    return PRUEBAS_FINALIZADAS_DIR / test_name / "qti" / question_id / "metadata_tags.json"


# -----------------------------------------------------------------------------
# Validation (optional - runs on import in debug mode)
# -----------------------------------------------------------------------------


def validate_paths() -> dict[str, bool]:
    """Validate that expected directories exist.

    Returns:
        Dict mapping path names to existence status.
    """
    paths_to_check = {
        "REPO_ROOT": REPO_ROOT,
        "APP_DIR": APP_DIR,
        "DATA_DIR": DATA_DIR,
        "ATOMS_DIR": ATOMS_DIR,
        "STANDARDS_DIR": STANDARDS_DIR,
        "TEMARIOS_DIR": TEMARIOS_DIR,
        "PRUEBAS_FINALIZADAS_DIR": PRUEBAS_FINALIZADAS_DIR,
        "PRUEBAS_ALTERNATIVAS_DIR": PRUEBAS_ALTERNATIVAS_DIR,
    }
    return {name: path.exists() for name, path in paths_to_check.items()}
