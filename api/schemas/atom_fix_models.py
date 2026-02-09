"""Pydantic models for atom fix pipeline API endpoints.

Request/response schemas for starting and monitoring fix jobs.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Request
# -----------------------------------------------------------------------------


class AtomFixRequest(BaseModel):
    """Request to start an LLM atom fix job."""

    dry_run: bool = Field(
        True,
        description="If true, report changes without writing files.",
    )
    fix_types: list[str] | None = Field(
        None,
        description=(
            "Optional filter. Values: split, merge, fix_content, "
            "fix_fidelity, fix_completeness, fix_prerequisites, "
            "add_missing."
        ),
    )
    standard_ids: list[str] | None = Field(
        None,
        description="Optional filter for specific standard IDs.",
    )


# -----------------------------------------------------------------------------
# Response — job start
# -----------------------------------------------------------------------------


class AtomFixJobResponse(BaseModel):
    """Response when starting an atom fix job."""

    job_id: str
    status: str = Field(description="started | in_progress | completed | failed")
    actions_to_fix: int
    estimated_cost_usd: float
    dry_run: bool


# -----------------------------------------------------------------------------
# Response — job status
# -----------------------------------------------------------------------------


class AtomFixProgress(BaseModel):
    """Progress counters for an atom fix job."""

    total: int
    completed: int
    succeeded: int
    failed: int


class AtomFixActionResult(BaseModel):
    """Result of a single fix action."""

    fix_type: str
    atom_ids: list[str]
    standard_id: str
    success: bool
    error: str | None = None


class AtomFixChangeReport(BaseModel):
    """Summary of changes produced by the fix pipeline."""

    atoms_added: list[str] = Field(default_factory=list)
    atoms_removed: list[str] = Field(default_factory=list)
    atoms_modified: list[str] = Field(default_factory=list)
    prerequisite_cascades: int = 0
    question_mapping_updates: int = 0
    manual_review_needed: list[str] = Field(default_factory=list)


class AtomFixStatusResponse(BaseModel):
    """Full status response for an atom fix job."""

    job_id: str
    status: str = Field(description="started | in_progress | completed | failed")
    dry_run: bool
    progress: AtomFixProgress
    results: list[AtomFixActionResult] = Field(default_factory=list)
    change_report: AtomFixChangeReport | None = None
    started_at: str
    completed_at: str | None = None
