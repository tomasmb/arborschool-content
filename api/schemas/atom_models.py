"""Pydantic models for atom pipeline API endpoints.

Models for structural checks, LLM validation, and coverage analysis.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# -----------------------------------------------------------------------------
# Atom pipeline summary (used by orchestrator page for tab status)
# -----------------------------------------------------------------------------


class AtomPipelineSummary(BaseModel):
    """Summary counts for tab status derivation in the frontend."""

    has_standards: bool = Field(
        description="Whether standards JSON exists"
    )
    atom_count: int = Field(description="Total atoms in canonical file")
    standards_count: int = Field(description="Total standards in file")
    last_generation_date: str | None = Field(
        None, description="Version date from atoms metadata"
    )
    structural_checks_passed: bool | None = Field(
        None,
        description="None = not run, True = all pass, False = failures",
    )
    standards_validated: int = Field(
        0, description="Standards with saved LLM validation results"
    )
    standards_with_issues: int = Field(
        0, description="Standards where validation found issues"
    )


# -----------------------------------------------------------------------------
# Structural checks
# -----------------------------------------------------------------------------


class StructuralCheckItem(BaseModel):
    """A single issue found during structural validation."""

    atom_id: str | None = Field(
        None, description="Atom that has the issue (None for global)"
    )
    check: str = Field(description="Check category identifier")
    severity: str = Field(description="error | warning")
    message: str


class StructuralChecksResult(BaseModel):
    """Result of running all deterministic structural checks."""

    passed: bool = Field(
        description="True if zero errors (warnings are ok)"
    )
    total_atoms: int
    # Per-check summaries
    schema_errors: int = Field(
        0, description="Pydantic validation failures"
    )
    id_eje_errors: int = Field(
        0, description="ID-eje mismatch errors"
    )
    circular_dependencies: int = Field(
        0, description="Number of cycles found"
    )
    missing_prerequisites: int = Field(
        0, description="References to non-existent atom IDs"
    )
    missing_standard_refs: int = Field(
        0, description="References to non-existent standard IDs"
    )
    granularity_warnings: int = Field(
        0, description="Heuristic granularity warnings"
    )
    # Details
    issues: list[StructuralCheckItem] = Field(default_factory=list)
    cycles: list[list[str]] = Field(
        default_factory=list,
        description="Circular dependency cycles",
    )
    graph_stats: dict = Field(
        default_factory=dict,
        description="Prerequisite graph statistics",
    )


# -----------------------------------------------------------------------------
# LLM validation
# -----------------------------------------------------------------------------


class AtomValidationRequest(BaseModel):
    """Request to start LLM validation of atoms."""

    selection_mode: str = Field(
        "unvalidated",
        description="unvalidated | all | specific",
    )
    standard_ids: list[str] | None = Field(
        None,
        description="Specific standard IDs (only for selection_mode='specific')",
    )


class AtomValidationJobResponse(BaseModel):
    """Response when starting an atom validation job."""

    job_id: str
    status: str = Field(
        description="started | in_progress | completed | failed"
    )
    standards_to_validate: int
    estimated_cost_usd: float


class AtomValidationProgress(BaseModel):
    """Progress tracking for atom validation job."""

    total: int
    completed: int
    passed: int
    with_issues: int


class StandardValidationResult(BaseModel):
    """LLM validation result for one standard's atoms."""

    standard_id: str
    status: str = Field(description="pass | issues | error")
    evaluation_summary: dict | None = None
    atoms_evaluation: list[dict] = Field(default_factory=list)
    coverage_analysis: dict | None = None
    global_recommendations: list[str] = Field(default_factory=list)
    error: str | None = None


class AtomValidationStatusResponse(BaseModel):
    """Response for atom validation job status query."""

    job_id: str
    status: str = Field(
        description="started | in_progress | completed | failed"
    )
    progress: AtomValidationProgress
    results: list[StandardValidationResult] = Field(
        default_factory=list
    )
    started_at: str
    completed_at: str | None = None


# -----------------------------------------------------------------------------
# Coverage analysis
# -----------------------------------------------------------------------------


class StandardCoverageItem(BaseModel):
    """Coverage status for a single standard."""

    standard_id: str
    title: str
    atom_count: int = Field(description="Atoms covering this standard")
    coverage_status: str = Field(
        description="full | partial | none"
    )


class AtomQuestionCoverage(BaseModel):
    """Question coverage status for a single atom."""

    atom_id: str
    titulo: str
    eje: str
    direct_questions: int = Field(
        0, description="Questions directly tagged with this atom"
    )
    transitive_coverage: bool = Field(
        False,
        description="Covered transitively via dependent atoms",
    )
    coverage_status: str = Field(
        description="direct | transitive | none"
    )


class OverlapCandidate(BaseModel):
    """A pair of atoms that may overlap."""

    atom_a: str
    atom_b: str
    shared_standards: list[str]
    reason: str


class CoverageAnalysisResult(BaseModel):
    """Full coverage analysis result."""

    # Standards coverage
    total_standards: int
    standards_fully_covered: int
    standards_partially_covered: int
    standards_not_covered: int
    standards_coverage: list[StandardCoverageItem] = Field(
        default_factory=list
    )
    # Question coverage
    total_atoms: int
    atoms_with_direct_questions: int
    atoms_with_transitive_coverage: int
    atoms_without_coverage: int
    atom_question_coverage: list[AtomQuestionCoverage] = Field(
        default_factory=list
    )
    # Overlap detection
    overlap_candidates: list[OverlapCandidate] = Field(
        default_factory=list
    )
    # Distribution
    eje_distribution: dict[str, int] = Field(default_factory=dict)
    type_distribution: dict[str, int] = Field(default_factory=dict)


# -----------------------------------------------------------------------------
# Saved validation results (from disk)
# -----------------------------------------------------------------------------


class SavedValidationSummary(BaseModel):
    """Summary of saved validation results per standard."""

    standard_id: str
    overall_quality: str | None = None
    coverage_assessment: str | None = None
    granularity_assessment: str | None = None
    total_atoms: int = 0
    atoms_passing: int = 0
    atoms_with_issues: int = 0
