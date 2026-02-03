"""Cost estimation service for AI pipelines.

Estimates token usage and cost before running pipelines.
Prices should be verified periodically as they change frequently.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from typing import Any

from api.schemas.api_models import CostEstimate


# Model pricing (per 1M tokens) - verify these periodically
MODEL_PRICING = {
    "gemini-3-pro-preview": {
        "input": 1.25,  # $1.25 per 1M input tokens
        "output": 5.00,  # $5.00 per 1M output tokens
    },
    "gemini-2.5-pro": {
        "input": 1.25,
        "output": 10.00,
    },
    "gpt-4o": {
        "input": 2.50,
        "output": 10.00,
    },
    "gpt-4o-mini": {
        "input": 0.15,
        "output": 0.60,
    },
}

# Default model used by our pipelines
DEFAULT_MODEL = "gemini-3-pro-preview"


@dataclass
class TokenEstimate:
    """Estimated token counts for a pipeline run."""

    input_tokens: int
    output_tokens: int
    breakdown: dict[str, Any]


class CostEstimatorService:
    """Service for estimating AI pipeline costs."""

    def __init__(self, model: str = DEFAULT_MODEL):
        """Initialize with a specific model for pricing."""
        self.model = model
        self.pricing = MODEL_PRICING.get(model, MODEL_PRICING[DEFAULT_MODEL])

    def estimate_pipeline_cost(
        self,
        pipeline_id: str,
        params: dict[str, Any],
    ) -> CostEstimate:
        """Estimate cost for running a pipeline.

        Args:
            pipeline_id: The pipeline type (e.g., "tagging", "variant_gen")
            params: Pipeline parameters (e.g., test_id, question_ids)

        Returns:
            CostEstimate with token counts and cost range
        """
        token_estimate = self._estimate_tokens(pipeline_id, params)

        # Calculate costs
        input_cost = (token_estimate.input_tokens / 1_000_000) * self.pricing["input"]
        output_cost = (token_estimate.output_tokens / 1_000_000) * self.pricing["output"]
        total = input_cost + output_cost

        # Add 20% buffer for upper bound (retries, validation, etc.)
        return CostEstimate(
            pipeline_id=pipeline_id,
            model=self.model,
            input_tokens=token_estimate.input_tokens,
            output_tokens=token_estimate.output_tokens,
            estimated_cost_min=round(total * 0.8, 2),
            estimated_cost_max=round(total * 1.2, 2),
            breakdown=token_estimate.breakdown,
        )

    def _estimate_tokens(
        self,
        pipeline_id: str,
        params: dict[str, Any],
    ) -> TokenEstimate:
        """Estimate token usage based on pipeline type."""
        estimators = {
            "standards_gen": self._estimate_standards_gen,
            "atoms_gen": self._estimate_atoms_gen,
            "pdf_split": self._estimate_pdf_split,
            "pdf_to_qti": self._estimate_pdf_to_qti,
            "tagging": self._estimate_tagging,
            "variant_gen": self._estimate_variant_gen,
            "question_sets": self._estimate_question_sets,
            "lessons": self._estimate_lessons,
        }

        estimator = estimators.get(pipeline_id)
        if not estimator:
            # Default fallback for unknown pipelines
            return TokenEstimate(
                input_tokens=10000,
                output_tokens=5000,
                breakdown={"note": "Unknown pipeline, using default estimate"},
            )

        return estimator(params)

    def _estimate_standards_gen(self, params: dict[str, Any]) -> TokenEstimate:
        """Estimate tokens for standards generation.

        Input: Temario content (~5K tokens) + prompt (~1K tokens)
        Output: Standards JSON (~3K tokens per eje)
        """
        # If eje specified, only one eje; otherwise assume 4 ejes
        num_ejes = 1 if params.get("eje") else 4

        input_per_eje = 6000  # Temario section + prompt
        output_per_eje = 3000  # Standards JSON

        return TokenEstimate(
            input_tokens=input_per_eje * num_ejes,
            output_tokens=output_per_eje * num_ejes,
            breakdown={
                "num_ejes": num_ejes,
                "input_per_eje": input_per_eje,
                "output_per_eje": output_per_eje,
            },
        )

    def _estimate_atoms_gen(self, params: dict[str, Any]) -> TokenEstimate:
        """Estimate tokens for atoms generation.

        Input: Standard context (~2K tokens) + prompt (~2K tokens)
        Output: Atoms JSON (~5K tokens per standard, ~15 atoms each)
        """
        num_standards = len(params.get("standard_ids", [])) or 21  # Default all

        input_per_std = 4000
        output_per_std = 5000

        return TokenEstimate(
            input_tokens=input_per_std * num_standards,
            output_tokens=output_per_std * num_standards,
            breakdown={
                "num_standards": num_standards,
                "input_per_standard": input_per_std,
                "output_per_standard": output_per_std,
            },
        )

    def _estimate_pdf_split(self, params: dict[str, Any]) -> TokenEstimate:
        """Estimate tokens for PDF splitting (uses OpenAI vision).

        Note: This pipeline uses OpenAI for segmentation detection.
        """
        # OpenAI vision for detecting question boundaries
        # Typically ~65 pages, ~2K tokens per page for vision
        num_pages = params.get("num_pages", 65)

        return TokenEstimate(
            input_tokens=num_pages * 2000,
            output_tokens=num_pages * 100,
            breakdown={
                "num_pages": num_pages,
                "note": "Uses OpenAI vision for segmentation",
            },
        )

    def _estimate_pdf_to_qti(self, params: dict[str, Any]) -> TokenEstimate:
        """Estimate tokens for PDF to QTI conversion.

        Input: Question image + prompt (~3K tokens per question)
        Output: QTI XML (~2K tokens per question)
        """
        question_ids = params.get("question_ids", [])
        num_questions = len(question_ids) if question_ids else 65  # Default full test

        input_per_q = 3000  # Image + prompt
        output_per_q = 2000  # QTI XML

        return TokenEstimate(
            input_tokens=input_per_q * num_questions,
            output_tokens=output_per_q * num_questions,
            breakdown={
                "num_questions": num_questions,
                "input_per_question": input_per_q,
                "output_per_question": output_per_q,
            },
        )

    def _estimate_tagging(self, params: dict[str, Any]) -> TokenEstimate:
        """Estimate tokens for question tagging.

        Input: Question content (~1K) + atoms context (~10K) + prompt (~1K)
        Output: Tags JSON (~500 tokens per question)
        """
        question_ids = params.get("question_ids", [])
        num_questions = len(question_ids) if question_ids else 65

        input_per_q = 12000  # Full atom context + question + prompt
        output_per_q = 500  # Tags JSON

        return TokenEstimate(
            input_tokens=input_per_q * num_questions,
            output_tokens=output_per_q * num_questions,
            breakdown={
                "num_questions": num_questions,
                "input_per_question": input_per_q,
                "output_per_question": output_per_q,
            },
        )

    def _estimate_variant_gen(self, params: dict[str, Any]) -> TokenEstimate:
        """Estimate tokens for variant generation.

        Input: Original question (~2K) + atom context (~5K) + prompt (~2K)
        Output: Variant XML (~3K per variant) + validation (~2K per variant)
        """
        question_ids = params.get("question_ids", [])
        num_questions = len(question_ids) if question_ids else 1
        variants_per_q = params.get("variants_per_question", 3)

        input_per_variant = 9000  # Question + atoms + prompt
        output_per_variant = 5000  # Generation + validation

        total_variants = num_questions * variants_per_q

        return TokenEstimate(
            input_tokens=input_per_variant * total_variants,
            output_tokens=output_per_variant * total_variants,
            breakdown={
                "num_questions": num_questions,
                "variants_per_question": variants_per_q,
                "total_variants": total_variants,
                "input_per_variant": input_per_variant,
                "output_per_variant": output_per_variant,
            },
        )

    def _estimate_question_sets(self, params: dict[str, Any]) -> TokenEstimate:
        """Estimate tokens for question set generation (PP100).

        Input: Atom context (~5K) + example questions (~10K) + prompt (~2K)
        Output: 60 questions (~1K per question)
        """
        atom_ids = params.get("atom_ids", [])
        num_atoms = len(atom_ids) if atom_ids else 127  # All atoms

        input_per_atom = 17000  # Atom + examples + prompt
        output_per_atom = 60000  # 60 questions, ~1K each

        return TokenEstimate(
            input_tokens=input_per_atom * num_atoms,
            output_tokens=output_per_atom * num_atoms,
            breakdown={
                "num_atoms": num_atoms,
                "questions_per_atom": 60,
                "input_per_atom": input_per_atom,
                "output_per_atom": output_per_atom,
            },
        )

    def _estimate_lessons(self, params: dict[str, Any]) -> TokenEstimate:
        """Estimate tokens for lesson generation.

        Input: Atom context (~3K) + example questions (~5K) + prompt (~2K)
        Output: Lesson content (~3K per atom)
        """
        atom_ids = params.get("atom_ids", [])
        num_atoms = len(atom_ids) if atom_ids else 127

        input_per_atom = 10000
        output_per_atom = 3000

        return TokenEstimate(
            input_tokens=input_per_atom * num_atoms,
            output_tokens=output_per_atom * num_atoms,
            breakdown={
                "num_atoms": num_atoms,
                "input_per_atom": input_per_atom,
                "output_per_atom": output_per_atom,
            },
        )


def generate_confirmation_token(pipeline_id: str, params: dict[str, Any]) -> str:
    """Generate a confirmation token for cost approval.

    This token confirms the user has seen the cost estimate.
    It's tied to the specific pipeline and params to prevent replay.
    """
    # Create a hash of the pipeline config + random salt
    salt = secrets.token_hex(8)
    content = f"{pipeline_id}:{sorted(params.items())}:{salt}"
    token_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    return f"{salt}:{token_hash}"


def verify_confirmation_token(
    token: str,
    pipeline_id: str,
    params: dict[str, Any],
) -> bool:
    """Verify a confirmation token is valid.

    Note: In a real implementation, you'd store tokens server-side with expiry.
    This simplified version just checks the format is valid.
    """
    if not token or ":" not in token:
        return False
    parts = token.split(":")
    return len(parts) == 2 and len(parts[0]) == 16 and len(parts[1]) == 16
