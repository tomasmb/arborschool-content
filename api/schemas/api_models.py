"""Pydantic models for API responses.

These models define the shape of data returned by the API endpoints.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# -----------------------------------------------------------------------------
# Overview models
# -----------------------------------------------------------------------------


class SubjectStats(BaseModel):
    """Statistics for a single subject."""

    temario_exists: bool = Field(description="Whether temario JSON exists")
    standards_count: int = Field(description="Number of standards")
    atoms_count: int = Field(description="Number of atoms")
    tests_count: int = Field(description="Number of tests")
    questions_count: int = Field(description="Number of finalized questions")
    variants_count: int = Field(description="Number of approved variants")
    tagging_completion: float = Field(description="Percentage of questions tagged (0-100)")
    # Enrichment & validation completion (0-100)
    enrichment_completion: float = Field(
        0.0, description="Percentage of questions enriched (0-100)"
    )
    validation_completion: float = Field(
        0.0, description="Percentage of questions validated (0-100)"
    )


class SubjectBrief(BaseModel):
    """Brief subject info for overview cards."""

    id: str
    name: str
    full_name: str
    year: int
    stats: SubjectStats


class OverviewResponse(BaseModel):
    """Response for GET /api/overview."""

    subjects: list[SubjectBrief]



class StandardBrief(BaseModel):
    """Brief standard info for lists."""

    id: str
    eje: str
    title: str
    atoms_count: int = Field(description="Number of atoms under this standard")


class AtomBrief(BaseModel):
    """Brief atom info for lists."""

    id: str
    eje: str
    standard_ids: list[str]
    tipo_atomico: str
    titulo: str
    question_set_count: int = Field(
        0, description="Number of questions in question set",
    )
    has_lesson: bool = Field(
        False, description="Whether lesson exists",
    )
    last_completed_phase: int | None = Field(
        None,
        description=(
            "Highest pipeline phase completed (1=enrichment, "
            "3=plan, 4=generation, 6=validation, 8=feedback). "
            "None if pipeline never ran."
        ),
    )
    # Image handling status from enrichment
    image_status: str = Field(
        "not_enriched",
        description=(
            "Image handling: not_enriched, no_images, "
            "images_supported, images_unsupported"
        ),
    )
    required_image_types: list[str] = Field(
        default_factory=list,
        description="Image types needed (from enrichment)",
    )
    # Question coverage from PAES tests
    question_coverage: str = Field(
        "none",
        description=(
            "PAES question coverage: direct, transitive, none"
        ),
    )
    direct_question_count: int = Field(
        0, description="Number of direct PAES questions",
    )


class AtomDetail(BaseModel):
    """Full atom detail for slide-over panel."""

    id: str
    eje: str
    standard_ids: list[str]
    habilidad_principal: str
    habilidades_secundarias: list[str]
    tipo_atomico: str
    titulo: str
    descripcion: str
    criterios_atomicos: list[str]
    ejemplos_conceptuales: list[str]
    prerrequisitos: list[str]
    notas_alcance: list[str]
    # Derived fields
    dependent_atoms: list[str] = Field(
        default_factory=list,
        description="Atoms that have this as a prerequisite"
    )
    linked_questions: list[str] = Field(
        default_factory=list,
        description="Question IDs tagged with this atom"
    )
    question_set_count: int = 0
    has_lesson: bool = False


class TestBrief(BaseModel):
    """Brief test info for lists."""

    id: str
    name: str
    admission_year: int | None
    application_type: str | None
    # Pipeline status counts
    raw_pdf_exists: bool
    split_count: int = Field(description="Number of split PDFs")
    qti_count: int = Field(description="Number of QTI files")
    finalized_count: int = Field(description="Number of finalized questions")
    tagged_count: int = Field(description="Number of tagged questions")
    enriched_count: int = Field(0, description="Number of enriched questions")
    validated_count: int = Field(0, description="Number of validated questions")
    variants_count: int = Field(description="Number of approved variants")
    # Variant-level enrichment/validation
    enriched_variants_count: int = Field(
        0, description="Number of enriched variants"
    )
    validated_variants_count: int = Field(
        0, description="Number of validated variants"
    )


class QuestionBrief(BaseModel):
    """Brief question info for test detail tables."""

    id: str
    question_number: int
    # Pipeline status
    has_split_pdf: bool
    has_qti: bool
    is_finalized: bool
    is_tagged: bool
    is_enriched: bool = Field(False, description="Has feedback been added")
    is_validated: bool = Field(False, description="Has passed LLM validation")
    atoms_count: int = Field(description="Number of linked atoms")
    variants_count: int = Field(description="Number of approved variants")


class AtomTag(BaseModel):
    """Atom tag information for a question."""

    atom_id: str
    titulo: str
    eje: str
    relevance: float = Field(1.0, description="Relevance score 0-1")


class VariantBrief(BaseModel):
    """Brief variant info for question detail."""

    id: str
    variant_number: int
    folder_name: str
    has_qti: bool = True
    has_metadata: bool = False
    is_enriched: bool = Field(False, description="Has feedback been added to variant")
    is_validated: bool = Field(False, description="Has variant passed LLM validation")


class QuestionDetail(BaseModel):
    """Full question detail for slide-over panel.

    Note: correct_answer and feedback are now embedded in qti_xml and parsed
    at display time by the frontend.
    """

    id: str
    test_id: str
    question_number: int
    # Pipeline status
    has_split_pdf: bool
    has_qti: bool
    is_finalized: bool
    is_tagged: bool
    # Content
    qti_xml: str | None = Field(None, description="Raw QTI XML content")
    qti_stem: str | None = Field(None, description="Extracted question stem text")
    qti_options: list[dict] | None = Field(None, description="Answer options")
    # Metadata
    difficulty: str | None = None
    source_info: dict | None = Field(default_factory=dict)
    # Atom tags
    atom_tags: list[AtomTag] = Field(default_factory=list)
    # Variants
    variants: list[VariantBrief] = Field(default_factory=list)
    # Paths for debugging
    qti_path: str | None = None
    pdf_path: str | None = None
    # Enrichment/validation status (added in Phase 3)
    is_enriched: bool = Field(False, description="Has feedback been added")
    is_validated: bool = Field(False, description="Has passed LLM validation")
    can_sync: bool = Field(False, description="Ready to sync to database")
    sync_status: str | None = Field(
        None,
        description="Sync status: not_in_db, in_sync, local_changed, not_validated"
    )
    validation_result: dict | None = Field(
        None, description="Detailed validation result if validated"
    )


class TestDetail(BaseModel):
    """Full test detail with questions."""

    id: str
    name: str
    admission_year: int | None
    application_type: str | None
    # Pipeline status
    raw_pdf_exists: bool
    split_count: int
    qti_count: int
    finalized_count: int
    tagged_count: int
    enriched_count: int = 0
    validated_count: int = 0
    variants_count: int
    # Variant-level enrichment/validation stats
    enriched_variants_count: int = 0
    validated_variants_count: int = 0
    failed_validation_variants_count: int = 0
    # Questions
    questions: list[QuestionBrief]


class SubjectDetail(BaseModel):
    """Full subject detail for subject page."""

    id: str
    name: str
    full_name: str
    year: int
    # Temario status
    temario_exists: bool
    temario_file: str | None
    # Standards and atoms
    standards: list[StandardBrief]
    atoms_count: int
    # Tests
    tests: list[TestBrief]


class GraphNode(BaseModel):
    """Node in the knowledge graph (React Flow format)."""

    id: str
    type: str = "atom"
    position: dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})
    data: dict = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """Edge in the knowledge graph (React Flow format)."""

    id: str
    source: str
    target: str
    type: str = "default"


class GraphData(BaseModel):
    """Full graph data for React Flow."""

    nodes: list[GraphNode]
    edges: list[GraphEdge]
    stats: dict = Field(default_factory=dict)



class PipelineDefinition(BaseModel):
    """Definition of an available pipeline."""

    id: str
    name: str
    description: str
    has_ai_cost: bool = True
    requires: list[str] = Field(default_factory=list, description="Prerequisites")
    produces: str = Field(description="What this pipeline outputs")


class PipelineParam(BaseModel):
    """A parameter for a pipeline."""

    name: str
    type: str = Field(description="string | number | boolean | select")
    label: str
    required: bool = True
    default: str | int | bool | None = None
    options: list[str] | None = Field(None, description="For select type")
    description: str | None = None


class CostEstimate(BaseModel):
    """Estimated cost for running a pipeline."""

    pipeline_id: str
    model: str
    input_tokens: int
    output_tokens: int
    estimated_cost_min: float = Field(description="Lower bound estimate in USD")
    estimated_cost_max: float = Field(description="Upper bound estimate in USD")
    breakdown: dict = Field(default_factory=dict, description="Per-item breakdown")
    stale_artifacts: dict | None = Field(
        None,
        description="Downstream artifacts that will be deleted on run",
    )


class FailedItem(BaseModel):
    """Information about a failed item in a job."""

    id: str
    error: str
    timestamp: str | None = None


class JobStatus(BaseModel):
    """Status of a pipeline job."""

    job_id: str
    pipeline_id: str
    status: str = Field(description="pending | running | completed | failed | cancelled")
    params: dict = Field(default_factory=dict)
    started_at: str | None = None
    completed_at: str | None = None
    # Progress tracking
    total_items: int = 0
    completed_items: int = 0
    failed_items: int = 0
    current_item: str | None = Field(None, description="Currently processing item")
    # Detailed item tracking for resume
    completed_item_ids: list[str] = Field(default_factory=list)
    failed_item_details: list[FailedItem] = Field(default_factory=list)
    remaining_items: int = 0
    # Results
    error: str | None = None
    cost_actual: float | None = Field(None, description="Actual cost incurred")
    logs: list[str] = Field(default_factory=list)
    # Resume capability
    can_resume: bool = Field(False, description="Whether this job can be resumed")


class JobResumeRequest(BaseModel):
    """Request to resume a failed/cancelled job."""

    mode: str = Field(
        "remaining",
        description="Resume mode: 'remaining' (all not completed) or 'failed_only'"
    )


class JobListResponse(BaseModel):
    """Response for listing jobs."""

    jobs: list[JobStatus]


class RunPipelineRequest(BaseModel):
    """Request to run a pipeline."""

    pipeline_id: str
    params: dict = Field(default_factory=dict)
    confirmation_token: str | None = Field(
        None, description="Token from cost estimate to confirm user saw the cost"
    )


class RunPipelineResponse(BaseModel):
    """Response after starting a pipeline."""

    job_id: str
    status: str
    message: str


# Valid sync entity types ("question_atoms" syncs tagging without question content)
VALID_SYNC_ENTITIES = [
    "standards", "atoms", "tests", "questions", "variants",
    "question_atoms",
]

# Valid sync environments
VALID_SYNC_ENVIRONMENTS = ["local", "staging", "prod"]


class SyncEntityCounts(BaseModel):
    """Counts for a single entity type."""

    total: int = Field(description="Total items to sync")
    official: int | None = Field(None, description="Official questions (source=official)")
    variants: int | None = Field(None, description="Variant questions (source=alternate)")


class SyncPreviewRequest(BaseModel):
    """Request for sync preview (dry run)."""

    entities: list[str] = Field(
        default_factory=lambda: ["standards", "atoms", "tests", "questions"],
        description="Entity types to sync: standards, atoms, tests, questions, variants"
    )
    environment: str = Field(
        "local",
        description="Target environment: local, staging, or prod"
    )


class SyncTableSummary(BaseModel):
    """Summary of what will be affected for a single table."""

    table: str
    total: int = Field(description="Total rows to upsert")
    breakdown: dict = Field(default_factory=dict, description="Additional breakdown")


class SyncPreviewResponse(BaseModel):
    """Response from sync preview."""

    tables: list[SyncTableSummary]
    summary: dict = Field(default_factory=dict, description="Overall summary counts")
    warnings: list[str] = Field(default_factory=list, description="Any warnings")
    environment: str = Field("local", description="Target environment")


class SyncExecuteRequest(BaseModel):
    """Request to execute sync."""

    entities: list[str] = Field(
        default_factory=lambda: ["standards", "atoms", "tests", "questions"],
        description="Entity types to sync: standards, atoms, tests, questions, variants"
    )
    environment: str = Field(
        "local",
        description="Target environment: local, staging, or prod"
    )
    confirm: bool = Field(False, description="Must be True to execute")


class SyncExecuteResponse(BaseModel):
    """Response from sync execution."""

    success: bool
    results: dict = Field(default_factory=dict, description="Rows affected per table")
    message: str
    errors: list[str] = Field(default_factory=list)
    environment: str = Field("local", description="Target environment used")


class UnlockStatus(BaseModel):
    """Status of unlock conditions for question sets and lessons."""

    all_questions_tagged: bool = Field(
        description="Whether ALL finalized questions are tagged"
    )
    tagged_count: int = Field(description="Number of tagged questions")
    total_count: int = Field(description="Total finalized questions")
    completion_percentage: float = Field(
        description="Percentage complete (0-100)"
    )
    # Per-test breakdown
    tests_status: dict[str, dict] = Field(
        default_factory=dict,
        description="Tagging status per test: {test_id: {tagged, total}}"
    )
