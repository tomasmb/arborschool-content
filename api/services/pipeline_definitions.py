"""Pipeline definitions and parameters.

Contains the static definitions for all pipelines and their configuration parameters.
Separated from pipeline_runner.py to keep files under 500 lines.
"""

from __future__ import annotations

from api.schemas.api_models import PipelineDefinition, PipelineParam

# -----------------------------------------------------------------------------
# Pipeline definitions
# -----------------------------------------------------------------------------

PIPELINES: dict[str, PipelineDefinition] = {
    "standards_gen": PipelineDefinition(
        id="standards_gen",
        name="Standards Generation",
        description="Generate standards from temario",
        has_ai_cost=True,
        requires=["temario"],
        produces="standards/*.json",
    ),
    "atoms_gen": PipelineDefinition(
        id="atoms_gen",
        name="Atoms Generation",
        description="Generate atoms from standards",
        has_ai_cost=True,
        requires=["standards"],
        produces="atoms/*.json",
    ),
    "pdf_split": PipelineDefinition(
        id="pdf_split",
        name="PDF Split",
        description="Split test PDF into individual questions",
        has_ai_cost=True,
        requires=["raw_pdf"],
        produces="procesadas/{test}/pdf/*.pdf",
    ),
    "pdf_to_qti": PipelineDefinition(
        id="pdf_to_qti",
        name="PDF to QTI",
        description="Convert question PDFs to QTI XML format",
        has_ai_cost=True,
        requires=["split_pdfs"],
        produces="procesadas/{test}/qti/*/question.xml",
    ),
    "finalize": PipelineDefinition(
        id="finalize",
        name="Finalize Questions",
        description="Copy validated QTI to finalizadas/",
        has_ai_cost=False,
        requires=["qti"],
        produces="finalizadas/{test}/qti/*",
    ),
    "tagging": PipelineDefinition(
        id="tagging",
        name="Question Tagging",
        description="Tag questions with relevant atoms",
        has_ai_cost=True,
        requires=["atoms", "finalized_questions"],
        produces="finalizadas/{test}/qti/*/metadata_tags.json",
    ),
    "variant_gen": PipelineDefinition(
        id="variant_gen",
        name="Variant Generation",
        description="Generate alternative versions of questions",
        has_ai_cost=True,
        requires=["tagged_questions"],
        produces="alternativas/{test}/Q*/approved/*",
    ),
    "question_gen": PipelineDefinition(
        id="question_gen",
        name="Question Generation",
        description="Generate PAES-style question pools per atom (PP100)",
        has_ai_cost=True,
        requires=["atoms", "all_tagged"],
        produces="question-generation/{atom_id}/*.json",
    ),
    "batch_question_gen": PipelineDefinition(
        id="batch_question_gen",
        name="Batch Question Generation",
        description=(
            "Run the full question generation pipeline for all "
            "covered atoms sequentially (resume-safe)"
        ),
        has_ai_cost=True,
        requires=["atoms", "all_tagged"],
        produces="question-generation/{atom_id}/*.json",
    ),
    "batch_question_gen_api": PipelineDefinition(
        id="batch_question_gen_api",
        name="Batch Question Generation (Batch API)",
        description=(
            "Run the full question generation pipeline via the "
            "OpenAI Batch API (50% cost discount, slower)"
        ),
        has_ai_cost=True,
        requires=["atoms", "all_tagged"],
        produces="question-generation/{atom_id}/*.json",
    ),
    "lessons": PipelineDefinition(
        id="lessons",
        name="Lessons",
        description="Generate micro-lessons for atoms",
        has_ai_cost=True,
        requires=["atoms", "question_sets_or_all_tagged"],
        produces="lessons/{atom_id}.json",
    ),
}

# -----------------------------------------------------------------------------
# Pipeline parameters
# -----------------------------------------------------------------------------

PIPELINE_PARAMS: dict[str, list[PipelineParam]] = {
    "standards_gen": [
        PipelineParam(
            name="temario_file",
            type="select",
            label="Temario",
            required=True,
            options=[
                "temario-paes-m1-invierno-y-regular-2026.json",
            ],
        ),
        PipelineParam(
            name="eje",
            type="select",
            label="Eje (optional)",
            required=False,
            options=[
                "numeros",
                "algebra_y_funciones",
                "geometria",
                "probabilidad_y_estadistica",
            ],
            description="Leave empty to generate all ejes",
        ),
    ],
    "atoms_gen": [
        PipelineParam(
            name="standards_file",
            type="select",
            label="Standards File",
            required=True,
            options=["paes_m1_2026.json"],
        ),
        PipelineParam(
            name="eje",
            type="select",
            label="Eje (optional)",
            required=False,
            options=[
                "numeros",
                "algebra_y_funciones",
                "geometria",
                "probabilidad_y_estadistica",
            ],
            description="Leave empty to generate all ejes",
        ),
        PipelineParam(
            name="standard_ids",
            type="string",
            label="Standard IDs (optional)",
            required=False,
            description=(
                "Comma-separated list (e.g., M1-NUM-01,M1-NUM-02). "
                "Leave empty for all."
            ),
        ),
    ],
    "pdf_split": [
        PipelineParam(
            name="pdf_path",
            type="string",
            label="PDF Path",
            required=True,
            description="Path to the test PDF file (relative to app/data/pruebas/raw/)",
        ),
        PipelineParam(
            name="output_dir",
            type="string",
            label="Output Directory (optional)",
            required=False,
            description="Output directory for split PDFs",
        ),
    ],
    "pdf_to_qti": [
        PipelineParam(
            name="test_id",
            type="select",
            label="Test",
            required=True,
            options=[],  # Populated dynamically
            description="Select the test to process",
        ),
        PipelineParam(
            name="question_ids",
            type="string",
            label="Question IDs (optional)",
            required=False,
            description="Comma-separated list (e.g., Q1,Q2,Q3). Leave empty for all.",
        ),
    ],
    "finalize": [
        PipelineParam(
            name="test_id",
            type="select",
            label="Test",
            required=True,
            options=[],  # Populated dynamically
        ),
        PipelineParam(
            name="question_ids",
            type="string",
            label="Question IDs (optional)",
            required=False,
            description="Comma-separated list (e.g., Q1,Q2,Q3). Leave empty for all.",
        ),
    ],
    "tagging": [
        PipelineParam(
            name="test_id",
            type="select",
            label="Test",
            required=True,
            options=[],  # Populated dynamically
        ),
        PipelineParam(
            name="question_ids",
            type="string",
            label="Question IDs (optional)",
            required=False,
            description="Comma-separated list (e.g., Q1,Q2,Q3). Leave empty for all.",
        ),
    ],
    "variant_gen": [
        PipelineParam(
            name="test_id",
            type="select",
            label="Source Test",
            required=True,
            options=[],  # Populated dynamically
        ),
        PipelineParam(
            name="question_ids",
            type="string",
            label="Question IDs",
            required=True,
            description="Comma-separated list (e.g., Q1,Q2,Q3)",
        ),
        PipelineParam(
            name="variants_per_question",
            type="number",
            label="Variants per Question",
            required=False,
            default=3,
        ),
    ],
    "question_gen": [
        PipelineParam(
            name="atom_id",
            type="string",
            label="Atom ID",
            required=True,
            description="Single atom ID (e.g. A-M1-ALG-01-02)",
        ),
        PipelineParam(
            name="phase",
            type="select",
            label="Phase",
            required=False,
            options=[
                "all", "enrich", "plan", "generate",
                "validate", "feedback", "final_validate",
            ],
            description="Phase group to run (default: all)",
        ),
        PipelineParam(
            name="dry_run",
            type="select",
            label="Dry Run",
            required=False,
            options=["false", "true"],
            description="Skip DB sync if true",
        ),
    ],
    "batch_question_gen": [
        PipelineParam(
            name="mode",
            type="select",
            label="Mode",
            required=False,
            options=["pending_only", "all"],
            default="pending_only",
            description=(
                "pending_only: skip fully-generated atoms. "
                "all: re-run every covered atom."
            ),
        ),
        PipelineParam(
            name="skip_images",
            type="select",
            label="No-image atoms only",
            required=False,
            options=["false", "true"],
            default="false",
            description=(
                "Only process atoms that don't require images "
                "(skips atoms with required_image_types)"
            ),
        ),
        PipelineParam(
            name="max_atoms",
            type="number",
            label="Max atoms (optional)",
            required=False,
            description=(
                "Limit to first N atoms. "
                "Leave empty for all."
            ),
        ),
    ],
    "batch_question_gen_api": [
        PipelineParam(
            name="mode",
            type="select",
            label="Mode",
            required=False,
            options=["pending_only", "all"],
            default="pending_only",
            description=(
                "pending_only: skip fully-generated atoms. "
                "all: re-run every covered atom."
            ),
        ),
        PipelineParam(
            name="skip_images",
            type="select",
            label="No-image atoms only",
            required=False,
            options=["false", "true"],
            default="false",
            description=(
                "Only process atoms that don't require images "
                "(skips atoms with required_image_types)"
            ),
        ),
        PipelineParam(
            name="max_atoms",
            type="number",
            label="Max atoms (optional)",
            required=False,
            description=(
                "Limit to first N atoms. "
                "Leave empty for all."
            ),
        ),
    ],
    "lessons": [],
}
