"""Sync utilities for atom enrichment persistence.

persist_enrichment: updates the atoms.enrichment JSONB column
during pipeline Phase 1. This is the only inline DB write the
pipeline performs (atom enrichment is always local).

Generated question sync is handled separately via the sync API
(environment-aware, reads Phase 9 checkpoints from disk).
"""

from __future__ import annotations

import json
import logging

from app.question_generation.models import AtomEnrichment
from app.sync.config import DBConfig, SyncEnvironment
from app.sync.db_client import DBClient

logger = logging.getLogger(__name__)


def persist_enrichment(
    atom_id: str,
    enrichment: AtomEnrichment,
    environment: SyncEnvironment = "local",
) -> bool:
    """Persist enrichment data to the atoms.enrichment JSONB column.

    Updates only the enrichment column for the given atom, leaving
    all other atom fields untouched.

    Args:
        atom_id: Atom ID to update.
        enrichment: AtomEnrichment object to persist.
        environment: Target database environment.

    Returns:
        True if the update succeeded, False otherwise.
    """
    try:
        config = DBConfig.for_environment(environment)
        client = DBClient(config)
        enrichment_json = json.dumps(
            enrichment.model_dump(), ensure_ascii=False,
        )

        with client.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE atoms
                    SET enrichment = %(enrichment)s::jsonb
                    WHERE id = %(atom_id)s
                    """,
                    {"atom_id": atom_id, "enrichment": enrichment_json},
                )
                conn.commit()
                updated = cur.rowcount > 0

        if updated:
            logger.info(
                "Persisted enrichment for atom %s to DB", atom_id,
            )
        else:
            logger.warning(
                "Atom %s not found in DB — enrichment not persisted",
                atom_id,
            )
        return updated

    except Exception as exc:
        logger.error(
            "Failed to persist enrichment for %s: %s", atom_id, exc,
        )
        return False
