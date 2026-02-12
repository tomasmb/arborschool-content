"""Batch atom enrichment service.

Runs Phase 1 enrichment for multiple atoms in parallel using
asyncio.Semaphore for bounded concurrency.

Follows the same async job pattern as enrichment_service.py and
validation_service.py.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from api.services.atom_coverage_service import (
    compute_atom_coverage_status,
    load_atom_coverage_maps,
)
from app.question_generation.helpers import (
    get_last_completed_phase,
    save_checkpoint,
)
from app.question_generation.models import AtomContext, EnrichmentStatus
from app.utils.paths import (
    QUESTION_GENERATION_DIR,
    get_atoms_file,
)

logger = logging.getLogger(__name__)

# Max concurrent LLM calls (safe for Tier 1 TPM limits)
_MAX_CONCURRENT = 5

# GPT-5.1 with reasoning_effort="low"
# ~2000 input tokens @ $1.25/1M = $0.0025
# ~1000 output + ~200 reasoning @ $10.00/1M = $0.012
_COST_PER_ATOM_USD = 0.015


# -------------------------------------------------------------------
# Job state
# -------------------------------------------------------------------


@dataclass
class BatchEnrichJob:
    """State for a batch atom enrichment job."""

    job_id: str
    status: str  # started, in_progress, completed, failed
    total: int
    completed: int
    succeeded: int
    failed: int
    skipped: int
    results: list[dict[str, Any]] = field(default_factory=list)
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    completed_at: datetime | None = None
    current_atom: str | None = None


# In-memory job storage
_jobs: dict[str, BatchEnrichJob] = {}


def get_job_status(job_id: str) -> BatchEnrichJob | None:
    """Get current status of a batch enrichment job."""
    return _jobs.get(job_id)


# -------------------------------------------------------------------
# Cost estimation (no job started)
# -------------------------------------------------------------------


def get_batch_enrich_estimate(
    mode: str = "unenriched_only",
) -> dict[str, int | float]:
    """Preview atom counts and estimated cost without starting a job.

    Reuses the same filtering helpers as start_batch_enrichment.

    Returns:
        Dict with atoms_to_process, skipped, estimated_cost_usd.
    """
    atoms_data = _load_all_atoms()
    if not atoms_data:
        return {
            "atoms_to_process": 0,
            "skipped": 0,
            "estimated_cost_usd": 0.0,
        }

    atom_qs, deps = load_atom_coverage_maps(atoms_data)
    covered = _filter_covered_atoms(atoms_data, atom_qs, deps)
    to_process, mode_skipped = _filter_by_mode(covered, mode)

    total_skipped = len(atoms_data) - len(covered) + mode_skipped
    cost = round(len(to_process) * _COST_PER_ATOM_USD, 3)

    return {
        "atoms_to_process": len(to_process),
        "skipped": total_skipped,
        "estimated_cost_usd": cost,
    }


# -------------------------------------------------------------------
# Entry point
# -------------------------------------------------------------------


async def start_batch_enrichment(
    mode: str = "unenriched_only",
) -> tuple[str, int, int]:
    """Start batch enrichment for atoms.

    Args:
        mode: "unenriched_only" (default) or "all".

    Returns:
        Tuple of (job_id, atoms_to_process, skipped_count).
    """
    atoms_data = _load_all_atoms()
    if not atoms_data:
        raise ValueError("No atoms found. Generate atoms first.")

    # Filter by coverage (only atoms with questions)
    atom_qs, deps = load_atom_coverage_maps(atoms_data)
    covered = _filter_covered_atoms(atoms_data, atom_qs, deps)

    # Filter by enrichment status
    to_process, skipped = _filter_by_mode(covered, mode)

    job_id = f"batch-enrich-{uuid.uuid4().hex[:8]}"
    job = BatchEnrichJob(
        job_id=job_id,
        status="started",
        total=len(to_process),
        completed=0,
        succeeded=0,
        failed=0,
        skipped=len(atoms_data) - len(covered) + skipped,
    )
    _jobs[job_id] = job

    asyncio.create_task(_run_batch(job_id, to_process))
    return job_id, len(to_process), job.skipped


# -------------------------------------------------------------------
# Background execution
# -------------------------------------------------------------------


async def _run_batch(
    job_id: str,
    atoms: list[dict[str, Any]],
) -> None:
    """Run enrichment in background with bounded parallelism."""
    job = _jobs.get(job_id)
    if not job:
        return

    job.status = "in_progress"

    # Initialize enricher once (shared across all tasks)
    try:
        enricher = _create_enricher()
    except Exception as exc:
        job.status = "failed"
        job.completed_at = datetime.now(timezone.utc)
        logger.exception("Failed to initialize enricher: %s", exc)
        return

    semaphore = asyncio.Semaphore(_MAX_CONCURRENT)

    async def enrich_one(atom: dict[str, Any]) -> dict[str, Any]:
        """Enrich a single atom with semaphore control."""
        aid = atom["id"]
        async with semaphore:
            job.current_atom = aid
            try:
                result = await asyncio.to_thread(
                    _enrich_atom, enricher, atom,
                )
                return result
            except Exception as exc:
                logger.exception("Error enriching %s: %s", aid, exc)
                return {
                    "atom_id": aid,
                    "status": "failed",
                    "error": str(exc),
                }

    tasks = [enrich_one(a) for a in atoms]
    results = await asyncio.gather(*tasks)

    # Update job with results
    for result in results:
        job.completed += 1
        job.results.append(result)
        if result.get("status") == "success":
            job.succeeded += 1
        else:
            job.failed += 1

    job.status = "completed"
    job.current_atom = None
    job.completed_at = datetime.now(timezone.utc)
    logger.info(
        "Batch enrichment %s done: %d/%d succeeded",
        job_id, job.succeeded, job.total,
    )


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------


def _load_all_atoms() -> list[dict[str, Any]]:
    """Load all atoms from the canonical file."""
    path = get_atoms_file("paes_m1_2026")
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("atoms", [])


def _filter_covered_atoms(
    atoms: list[dict[str, Any]],
    atom_qs: dict[str, set[str]],
    deps: dict[str, set[str]],
) -> list[dict[str, Any]]:
    """Keep only atoms with direct or transitive coverage."""
    covered: list[dict[str, Any]] = []
    for atom in atoms:
        aid = atom["id"]
        direct = len(atom_qs.get(aid, set()))
        status = compute_atom_coverage_status(
            aid, direct, deps, atom_qs,
        )
        if status != "none":
            covered.append(atom)
    return covered


def _filter_by_mode(
    atoms: list[dict[str, Any]],
    mode: str,
) -> tuple[list[dict[str, Any]], int]:
    """Filter atoms based on enrichment mode.

    Returns:
        Tuple of (atoms_to_process, skipped_count).
    """
    if mode == "all":
        return atoms, 0

    # "unenriched_only": skip atoms that already have enrichment
    to_process: list[dict[str, Any]] = []
    skipped = 0
    for atom in atoms:
        phase = get_last_completed_phase(atom["id"])
        if phase is not None and phase >= 1:
            skipped += 1
        else:
            to_process.append(atom)
    return to_process, skipped


def _create_enricher():  # type: ignore[no-untyped-def]
    """Create an AtomEnricher with default OpenAI client."""
    from app.llm_clients import load_default_openai_client
    from app.question_generation.enricher import AtomEnricher

    client = load_default_openai_client()
    return AtomEnricher(client=client)


def _build_atom_context(
    atom: dict[str, Any],
) -> AtomContext:
    """Build AtomContext from raw atom dict."""
    return AtomContext(
        atom_id=atom["id"],
        atom_title=atom["titulo"],
        atom_description=atom.get("descripcion", ""),
        eje=atom["eje"],
        standard_ids=atom.get("standard_ids", []),
        tipo_atomico=atom["tipo_atomico"],
        criterios_atomicos=atom.get("criterios_atomicos", []),
        ejemplos_conceptuales=atom.get(
            "ejemplos_conceptuales", [],
        ),
        notas_alcance=atom.get("notas_alcance", []),
    )


def _enrich_atom(
    enricher: Any,
    atom: dict[str, Any],
) -> dict[str, Any]:
    """Run enrichment for a single atom (blocking).

    Saves the checkpoint on success and returns a result dict.
    """
    aid = atom["id"]
    ctx = _build_atom_context(atom)
    result = enricher.enrich(ctx)

    enrichment = result.data.get("enrichment") if result.data else None
    status = (
        result.data.get("enrichment_status", EnrichmentStatus.FAILED)
        if result.data else EnrichmentStatus.FAILED
    )

    if enrichment and status == EnrichmentStatus.PRESENT:
        # Save checkpoint (same format as pipeline Phase 1)
        output_dir = QUESTION_GENERATION_DIR / aid
        save_checkpoint(output_dir, 1, "enrichment", {
            "has_enrichment": True,
            "enrichment_data": enrichment.model_dump(),
        })
        return {"atom_id": aid, "status": "success"}

    warning = (
        result.warnings[0] if result.warnings else "Unknown"
    )
    return {
        "atom_id": aid,
        "status": "failed",
        "error": warning,
    }
