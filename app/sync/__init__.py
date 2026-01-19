"""Sync module for migrating content repo data to the student-facing app database.

This module provides tools to extract data from JSON/XML files in the content repo,
transform it to match the database schema, and upsert it to Postgres.

Usage:
    python -m app.sync.scripts.sync_to_db --help

Note:
    DB operations require psycopg[binary]>=3.1.0
    S3 operations require boto3>=1.34.0
"""

from __future__ import annotations

# Core extractors (no external dependencies)
from .extractors import extract_all_tests, extract_atoms, extract_standards
from .models import SyncPayload
from .transformers import build_sync_payload

__all__ = [
    "SyncPayload",
    "build_sync_payload",
    "extract_all_tests",
    "extract_atoms",
    "extract_standards",
]


def get_db_client():
    """Lazily import and return DBClient class (requires psycopg)."""
    from .db_client import DBClient

    return DBClient


def get_db_config():
    """Lazily import and return DBConfig class (requires psycopg)."""
    from .db_client import DBConfig

    return DBConfig
