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


# -----------------------------------------------------------------------------
# Subject detail models
# -----------------------------------------------------------------------------


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
    question_set_count: int = Field(0, description="Number of questions in question set")
    has_lesson: bool = Field(False, description="Whether lesson exists")


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
    variants_count: int = Field(description="Number of approved variants")


class QuestionBrief(BaseModel):
    """Brief question info for test detail tables."""

    id: str
    question_number: int
    # Pipeline status
    has_split_pdf: bool
    has_qti: bool
    is_finalized: bool
    is_tagged: bool
    atoms_count: int = Field(description="Number of linked atoms")
    variants_count: int = Field(description="Number of approved variants")


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
    variants_count: int
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


# -----------------------------------------------------------------------------
# Knowledge graph models
# -----------------------------------------------------------------------------


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


# -----------------------------------------------------------------------------
# Pipeline models
# -----------------------------------------------------------------------------


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
    # Results
    error: str | None = None
    cost_actual: float | None = Field(None, description="Actual cost incurred")
    logs: list[str] = Field(default_factory=list)


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
