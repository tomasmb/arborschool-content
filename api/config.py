"""Configuration and settings for the API.

Loads settings from environment variables and provides path constants.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings

# Re-export paths from app.utils.paths for convenience
# These are imported and re-exported for use by API modules
from app.utils.paths import (  # noqa: F401
    ATOM_VALIDATION_RESULTS_DIR,
    ATOMS_DIR,
    DATA_DIR,
    PRUEBAS_ALTERNATIVAS_DIR,
    PRUEBAS_DIR,
    PRUEBAS_FINALIZADAS_DIR,
    PRUEBAS_PROCESADAS_DIR,
    PRUEBAS_RAW_DIR,
    STANDARDS_DIR,
    TEMARIOS_JSON_DIR,
    TEMARIOS_PDF_DIR,
)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API settings
    api_title: str = "Arbor Content Dashboard API"
    api_version: str = "0.1.0"
    debug: bool = False

    # CORS settings (for frontend dev server)
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Default subject ID (currently only PAES M1)
    default_subject_id: str = "paes-m1-2026"

    class Config:
        """Pydantic settings configuration."""

        env_prefix = "DASHBOARD_"
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Subject configuration (hardcoded for now, could be DB-driven later)
SUBJECTS_CONFIG = {
    "paes-m1-2026": {
        "id": "paes-m1-2026",
        "name": "PAES M1",
        "full_name": "Prueba de Competencia Matemática 1",
        "year": 2026,
        "temario_file": "temario-paes-m1-invierno-y-regular-2026.json",
        "standards_file": "paes_m1_2026.json",
        "atoms_file": "paes_m1_2026_atoms.json",
    }
}
