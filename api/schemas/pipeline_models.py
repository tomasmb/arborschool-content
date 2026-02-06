"""Pydantic models for pipeline API endpoints.

Models for enrichment, validation, and test-level sync operations.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# -----------------------------------------------------------------------------
# Enrichment models (test-level feedback pipeline)
# -----------------------------------------------------------------------------


class EnrichmentRequest(BaseModel):
    """Request to start enrichment job for a test."""

    question_ids: list[str] | None = Field(
        None, description="Specific question IDs (e.g., ['Q1', 'Q2'])"
    )
    all_tagged: bool = Field(False, description="Process all tagged questions")
    skip_already_enriched: bool = Field(
        True, description="Skip questions with existing feedback"
    )
    only_failed_validation: bool = Field(
        False,
        description="Only re-enrich questions that are enriched but failed validation"
    )


class EnrichmentJobResponse(BaseModel):
    """Response when starting an enrichment job."""

    job_id: str
    status: str = Field(description="started | in_progress | completed | failed")
    questions_to_process: int
    estimated_cost_usd: float


class EnrichmentProgress(BaseModel):
    """Progress tracking for enrichment job."""

    total: int
    completed: int
    successful: int
    failed: int


class EnrichmentFailureDetails(BaseModel):
    """Detailed failure information for enrichment."""

    stage_failed: str | None = Field(None, description="Stage where failure occurred")
    issues: list[str] = Field(default_factory=list, description="Specific issues found")
    reasoning: str | None = Field(None, description="Explanation of why it failed")


class EnrichmentQuestionResult(BaseModel):
    """Result for a single question in enrichment job."""

    question_id: str
    status: str = Field(description="success | failed")
    error: str | None = None
    details: EnrichmentFailureDetails | None = Field(
        None, description="Detailed failure info when status=failed"
    )


class EnrichmentStatusResponse(BaseModel):
    """Response for enrichment job status query."""

    job_id: str
    status: str = Field(description="started | in_progress | completed | failed")
    progress: EnrichmentProgress
    current_question: str | None = None
    results: list[EnrichmentQuestionResult] = Field(default_factory=list)
    started_at: str
    completed_at: str | None = None


# -----------------------------------------------------------------------------
# Validation models (test-level LLM validation)
# -----------------------------------------------------------------------------


class ValidationRequest(BaseModel):
    """Request to start validation job for a test."""

    question_ids: list[str] | None = Field(
        None, description="Specific question IDs (e.g., ['Q1', 'Q2'])"
    )
    all_enriched: bool = Field(False, description="Process all enriched questions")
    revalidate_passed: bool = Field(
        False, description="Include already-passed questions"
    )


class ValidationJobResponse(BaseModel):
    """Response when starting a validation job."""

    job_id: str
    status: str = Field(description="started | in_progress | completed | failed")
    questions_to_process: int
    estimated_cost_usd: float


class ValidationProgress(BaseModel):
    """Progress tracking for validation job."""

    total: int
    completed: int
    passed: int
    failed: int


class ValidationQuestionResult(BaseModel):
    """Result for a single question in validation job."""

    question_id: str
    status: str = Field(description="pass | fail")
    failed_checks: list[str] | None = None
    issues: list[str] | None = None


class ValidationStatusResponse(BaseModel):
    """Response for validation job status query."""

    job_id: str
    status: str = Field(description="started | in_progress | completed | failed")
    progress: ValidationProgress
    results: list[ValidationQuestionResult] = Field(default_factory=list)
    started_at: str
    completed_at: str | None = None


# -----------------------------------------------------------------------------
# Test-level sync models
# -----------------------------------------------------------------------------


class TestSyncPreviewRequest(BaseModel):
    """Request for test-level sync preview."""

    environment: str = Field("local", description="Target DB: local|staging|prod")
    include_variants: bool = Field(True, description="Include variant questions")
    upload_images: bool = Field(True, description="Upload images to S3")


class QuestionSyncChange(BaseModel):
    """Change details for a question in sync preview."""

    qti_xml_changed: bool = False
    feedback_added: bool = False
    feedback_changed: bool = False


class QuestionSyncItem(BaseModel):
    """A single question in sync preview."""

    question_id: str
    question_number: int
    status: str = Field(description="create | update | unchanged | skipped")
    reason: str | None = Field(None, description="Reason if skipped")
    changes: QuestionSyncChange | None = None


class TestSyncSummary(BaseModel):
    """Summary counts for test sync preview."""

    create: int
    update: int
    unchanged: int
    skipped: int


class TestSyncPreviewResponse(BaseModel):
    """Response for test-level sync preview."""

    questions: dict = Field(
        description="Categories: to_create, to_update, unchanged, skipped"
    )
    variants: dict = Field(
        default_factory=dict,
        description="Variant categories: to_create, to_update, unchanged, skipped",
    )
    summary: TestSyncSummary
    question_summary: TestSyncSummary | None = None
    variant_summary: TestSyncSummary | None = None


class TestSyncDiffEntityResponse(BaseModel):
    """Diff counts for a single entity type (questions or variants)."""

    local_count: int = 0
    db_count: int = 0
    new_count: int = 0
    deleted_count: int = 0
    unchanged_count: int = 0
    has_changes: bool = False


class TestSyncDiffResponse(BaseModel):
    """Response for test-level sync diff (DB status)."""

    environment: str
    has_changes: bool = False
    questions: TestSyncDiffEntityResponse = Field(
        default_factory=TestSyncDiffEntityResponse,
    )
    variants: TestSyncDiffEntityResponse = Field(
        default_factory=TestSyncDiffEntityResponse,
    )
    error: str | None = None


class TestSyncExecuteResponse(BaseModel):
    """Response for test-level sync execution."""

    created: int
    updated: int
    skipped: int
    details: list[dict] = Field(default_factory=list)
