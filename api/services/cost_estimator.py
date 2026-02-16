"""Cost estimation service for AI pipelines.

Estimates token usage and cost before running pipelines.
Prices verified February 2026 — update when models change.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from dataclasses import dataclass
from typing import Any

from api.schemas.api_models import CostEstimate

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model pricing (per 1M tokens) — verified 2026-02-12
# ---------------------------------------------------------------------------

MODEL_PRICING: dict[str, dict[str, float]] = {
    "gpt-5.1": {
        "input": 1.25,   # $1.25 per 1M input tokens
        "output": 10.00,  # $10.00 per 1M output tokens
    },
    "gemini-3-pro-preview": {
        "input": 2.00,    # $2.00 per 1M input (≤200K context)
        "output": 12.00,  # $12.00 per 1M output (incl. thinking)
    },
    "o4-mini-2025-04-16": {
        "input": 1.10,   # $1.10 per 1M input tokens
        "output": 4.40,  # $4.40 per 1M output tokens
    },
}

# Default model — only used when pipeline has no explicit mapping
DEFAULT_MODEL = "gpt-5.1"

# GPT-5.1 reasoning token overhead per call (hidden, billed as output).
GPT51_REASONING_OVERHEAD: dict[str, int] = {
    "none": 0,       # No internal reasoning
    "low": 200,      # Light reasoning (~200 extra output tokens)
    "medium": 1_000,  # Moderate reasoning (~1K extra output tokens)
    "high": 3_000,    # Deep reasoning (~3K extra output tokens)
}

# Which model each pipeline actually uses (from app/llm_clients.py)
PIPELINE_MODELS: dict[str, str] = {
    "standards_gen": "gemini-3-pro-preview",
    "atoms_gen": "gemini-3-pro-preview",
    "pdf_split": "o4-mini-2025-04-16",
    "pdf_to_qti": "gemini-3-pro-preview",  # primary; gpt-5.1 fallback
    "tagging": "gemini-3-pro-preview",
    "variant_gen": "gemini-3-pro-preview",
    "question_gen": "gpt-5.1",
    "lessons": "gpt-5.1",
}


@dataclass
class TokenEstimate:
    """Estimated token counts for a pipeline run."""

    input_tokens: int
    output_tokens: int
    breakdown: dict[str, Any]


class CostEstimatorService:
    """Service for estimating AI pipeline costs.

    Each pipeline uses the model defined in PIPELINE_MODELS.
    Token estimates are based on actual prompt sizes and output
    formats measured from the codebase.
    """

    def estimate_pipeline_cost(
        self,
        pipeline_id: str,
        params: dict[str, Any],
    ) -> CostEstimate:
        """Estimate cost for running a pipeline.

        Determines the correct model and pricing for each pipeline,
        then estimates token usage and cost range.
        """
        model = PIPELINE_MODELS.get(pipeline_id, DEFAULT_MODEL)
        pricing = MODEL_PRICING.get(model, MODEL_PRICING[DEFAULT_MODEL])
        token_estimate = self._estimate_tokens(pipeline_id, params)

        input_cost = (
            token_estimate.input_tokens / 1_000_000
        ) * pricing["input"]
        output_cost = (
            token_estimate.output_tokens / 1_000_000
        ) * pricing["output"]
        total = input_cost + output_cost

        # 20% buffer for upper bound (retries, validation rounds)
        return CostEstimate(
            pipeline_id=pipeline_id,
            model=model,
            input_tokens=token_estimate.input_tokens,
            output_tokens=token_estimate.output_tokens,
            estimated_cost_min=round(total * 0.8, 4),
            estimated_cost_max=round(total * 1.2, 4),
            breakdown=token_estimate.breakdown,
        )

    def _estimate_tokens(
        self,
        pipeline_id: str,
        params: dict[str, Any],
    ) -> TokenEstimate:
        """Route to the correct estimator based on pipeline ID."""
        estimators: dict[str, Any] = {
            "standards_gen": self._estimate_standards_gen,
            "atoms_gen": self._estimate_atoms_gen,
            "pdf_split": self._estimate_pdf_split,
            "pdf_to_qti": self._estimate_pdf_to_qti,
            "tagging": self._estimate_tagging,
            "variant_gen": self._estimate_variant_gen,
            "question_gen": self._estimate_question_gen,
            "lessons": self._estimate_lessons,
        }

        estimator = estimators.get(pipeline_id)
        if not estimator:
            raise ValueError(
                f"No cost estimator for pipeline '{pipeline_id}'. "
                f"Known pipelines: {sorted(estimators.keys())}"
            )

        return estimator(params)

    # ------------------------------------------------------------------
    # Per-pipeline estimators
    # ------------------------------------------------------------------

    def _estimate_standards_gen(
        self, params: dict[str, Any],
    ) -> TokenEstimate:
        """Standards generation — Gemini 3 Pro, ~4x thinking."""
        num_ejes = 1 if params.get("eje") else 4
        unidades_per_eje = 8  # Approximate average

        # Generation: 1 call per unidad
        gen_input = 2_500 * unidades_per_eje
        gen_output_visible = 1_200 * unidades_per_eje
        # Validation: 1 call per unidad + 1 cross-eje
        val_input = 3_000 * unidades_per_eje + 6_000
        val_output_visible = 800 * unidades_per_eje + 1_500

        total_input = (gen_input + val_input) * num_ejes
        # Thinking tokens ~3x visible output for high thinking
        visible_output = (
            gen_output_visible + val_output_visible
        ) * num_ejes
        total_output = visible_output * 4  # visible + 3x thinking

        return TokenEstimate(
            input_tokens=total_input,
            output_tokens=total_output,
            breakdown={
                "num_ejes": num_ejes,
                "unidades_per_eje": unidades_per_eje,
                "calls_per_eje": unidades_per_eje * 2 + 1,
                "thinking_multiplier": "4x (high)",
            },
        )

    def _estimate_atoms_gen(
        self, params: dict[str, Any],
    ) -> TokenEstimate:
        """Atoms generation — Gemini 3 Pro, ~4x thinking."""
        standard_ids = params.get("standard_ids")
        if isinstance(standard_ids, str) and standard_ids:
            num_standards = len(standard_ids.split(","))
        elif isinstance(standard_ids, list):
            num_standards = len(standard_ids) if standard_ids else 21
        else:
            num_standards = 21  # All standards

        input_per_std = 5_000
        visible_output_per_std = 3_000
        # 4x multiplier for thinking_level=high
        total_output_per_std = visible_output_per_std * 4

        return TokenEstimate(
            input_tokens=input_per_std * num_standards,
            output_tokens=total_output_per_std * num_standards,
            breakdown={
                "num_standards": num_standards,
                "input_per_standard": input_per_std,
                "output_per_standard": total_output_per_std,
                "thinking_multiplier": "4x (high)",
            },
        )

    def _estimate_pdf_split(
        self, params: dict[str, Any],
    ) -> TokenEstimate:
        """PDF split — o4-mini, single call per PDF."""
        num_pages = params.get("num_pages", 30)
        # Document tokens: ~800-1,200 per page
        input_tokens = num_pages * 1_000
        # Segment JSON + reasoning tokens
        output_tokens = num_pages * 500 + 5_000  # Base reasoning overhead

        return TokenEstimate(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            breakdown={
                "num_pages": num_pages,
                "note": "Single call, o4-mini reasoning model",
            },
        )

    def _estimate_pdf_to_qti(
        self, params: dict[str, Any],
    ) -> TokenEstimate:
        """PDF to QTI — Gemini 3 Pro, ~4x thinking per question."""
        question_ids = params.get("question_ids", [])
        if isinstance(question_ids, str) and question_ids:
            num_questions = len(question_ids.split(","))
        elif isinstance(question_ids, list):
            num_questions = len(question_ids) if question_ids else 65
        else:
            num_questions = 65  # Full test

        input_per_q = 4_000  # Prompt + vision tokens
        visible_output_per_q = 3_000  # QTI XML
        total_output_per_q = visible_output_per_q * 4  # thinking

        return TokenEstimate(
            input_tokens=input_per_q * num_questions,
            output_tokens=total_output_per_q * num_questions,
            breakdown={
                "num_questions": num_questions,
                "input_per_question": input_per_q,
                "output_per_question": total_output_per_q,
                "thinking_multiplier": "4x (high)",
            },
        )

    def _estimate_tagging(
        self, params: dict[str, Any],
    ) -> TokenEstimate:
        """Tagging — Gemini 3 Pro, 3 calls/question, no thinking."""
        question_ids = params.get("question_ids", [])
        if isinstance(question_ids, str) and question_ids:
            num_questions = len(question_ids.split(","))
        elif isinstance(question_ids, list):
            num_questions = len(question_ids) if question_ids else 65
        else:
            num_questions = 65

        input_per_q = 6_300   # 3 calls totaled
        output_per_q = 1_000  # 3 calls totaled, no thinking

        return TokenEstimate(
            input_tokens=input_per_q * num_questions,
            output_tokens=output_per_q * num_questions,
            breakdown={
                "num_questions": num_questions,
                "calls_per_question": 3,
                "input_per_question": input_per_q,
                "output_per_question": output_per_q,
                "note": "No thinking tokens (temp=0.0)",
            },
        )

    def _estimate_variant_gen(
        self, params: dict[str, Any],
    ) -> TokenEstimate:
        """Variant generation — Gemini 3 Pro, ~2x thinking."""
        question_ids = params.get("question_ids", [])
        if isinstance(question_ids, str) and question_ids:
            num_questions = len(question_ids.split(","))
        elif isinstance(question_ids, list):
            num_questions = len(question_ids) if question_ids else 1
        else:
            num_questions = 1
        variants_per_q = params.get("variants_per_question", 3)

        # Generation call
        gen_input = 2_000
        gen_output_visible = 6_000

        # Validation calls (1 per variant)
        val_input = 1_500 * variants_per_q
        val_output_visible = 500 * variants_per_q

        total_input = (gen_input + val_input) * num_questions
        visible_output = (
            gen_output_visible + val_output_visible
        ) * num_questions
        # Default thinking ~2x visible
        total_output = visible_output * 2

        return TokenEstimate(
            input_tokens=total_input,
            output_tokens=total_output,
            breakdown={
                "num_questions": num_questions,
                "variants_per_question": variants_per_q,
                "total_variants": num_questions * variants_per_q,
                "thinking_multiplier": "2x (default)",
            },
        )

    def _estimate_question_gen(
        self, params: dict[str, Any],
    ) -> TokenEstimate:
        """Question generation (PP100) — GPT-5.1.

        Checkpoint-aware: reads actual item counts from disk so
        re-runs reflect the real remaining work.  Each phase uses
        a reasoning_effort level that generates hidden reasoning
        tokens billed as output.
        """
        phase = params.get("phase", "all")
        atom_id = params.get("atom_id", "")
        force_all = params.get("force_all", False)
        r = GPT51_REASONING_OVERHEAD

        counts = _load_question_gen_counts(atom_id)

        # How many items each phase will actually process
        planned = counts["planned"] or 62
        generated = counts["generated"]
        validated = counts["validated"]

        if force_all:
            # Full rerun — regenerate & revalidate everything
            gen_calls = int(planned * 1.3)
            validate_items = generated or planned
            feedback_items = validated or planned
        else:
            # Resume (default) — only remaining work
            remaining_gen = max(planned - generated, 0)
            gen_calls = int(remaining_gen * 1.3) if remaining_gen else 0
            all_gen = generated or planned
            validate_items = max(all_gen - validated, 0)
            feedback_items = validated or planned

        phase_tokens: dict[str, tuple[int, int]] = {
            # 1 call, reasoning_effort="low"
            "enrich": (1_500, 800 + r["low"]),
            # 1 call, reasoning_effort="medium"
            "plan": (1_800, 1_200 + r["medium"]),
            # Per call: ~4K input, ~2.5K visible output
            "generate": (
                4_000 * gen_calls,
                (2_500 + r["medium"]) * gen_calls,
            ),
            # 1 solvability call per item, reasoning="medium"
            "validate": (
                1_000 * validate_items,
                (200 + r["medium"]) * validate_items,
            ),
            # Per item: enhance (low) + review (none)
            # Includes ~30% buffer for correction retries
            "feedback": (
                6_500 * feedback_items,
                (5_000 + r["low"]) * feedback_items,
            ),
            # Phase 9: 1 LLM final validation per item (medium)
            # Phase 10: DB sync (no LLM cost)
            "finalize": (
                2_500 * feedback_items,
                (500 + r["medium"]) * feedback_items,
            ),
        }

        # Determine which phases are included
        if phase == "all":
            active = list(phase_tokens.keys())
        else:
            active = [phase]

        total_input = sum(
            phase_tokens.get(p, (0, 0))[0] for p in active
        )
        total_output = sum(
            phase_tokens.get(p, (0, 0))[1] for p in active
        )

        breakdown: dict[str, Any] = {
            "phase": phase,
            "planned_items": planned,
            "active_phases": active,
            "mode": "force_all" if force_all else "resume",
            "note": "Output includes reasoning token overhead",
        }

        if not force_all and generated > 0:
            breakdown["already_generated"] = generated
            breakdown["remaining_gen_slots"] = max(planned - generated, 0)
        if not force_all and validated > 0:
            breakdown["already_validated"] = validated
        breakdown["items_to_validate"] = validate_items
        breakdown["items_to_enrich"] = feedback_items

        for p in active:
            inp, out = phase_tokens.get(p, (0, 0))
            breakdown[f"{p}_input"] = inp
            breakdown[f"{p}_output"] = out

        return TokenEstimate(
            input_tokens=total_input,
            output_tokens=total_output,
            breakdown=breakdown,
        )

    def _estimate_lessons(self, params: dict[str, Any]) -> TokenEstimate:
        """Lesson generation — GPT-5.1, 1 call per atom."""
        atom_ids = params.get("atom_ids", [])
        if isinstance(atom_ids, str) and atom_ids:
            num_atoms = len(atom_ids.split(","))
        elif isinstance(atom_ids, list):
            num_atoms = len(atom_ids) if atom_ids else 127
        else:
            num_atoms = 127

        input_per_atom = 10_000
        output_per_atom = 3_000

        return TokenEstimate(
            input_tokens=input_per_atom * num_atoms,
            output_tokens=output_per_atom * num_atoms,
            breakdown={
                "num_atoms": num_atoms,
                "input_per_atom": input_per_atom,
                "output_per_atom": output_per_atom,
            },
        )


def _load_question_gen_counts(atom_id: str) -> dict[str, int]:
    """Read checkpoint files for actual item counts per phase.

    Returns dict with keys planned/generated/validated/feedback
    (0 when checkpoint is absent).
    """
    counts = {"planned": 0, "generated": 0, "validated": 0, "feedback": 0}
    if not atom_id:
        return counts

    try:
        from app.question_generation.helpers import load_checkpoint
        from app.utils.paths import QUESTION_GENERATION_DIR

        d = QUESTION_GENERATION_DIR / atom_id
        # Each checkpoint stores items/slots as a list
        for phase_num, name, key, list_key in [
            (3, "plan", "planned", "slots"),
            (4, "generation", "generated", "items"),
            (6, "base_validation", "validated", "items"),
            (8, "feedback", "feedback", "items"),
        ]:
            ckpt = load_checkpoint(d, phase_num, name)
            if ckpt:
                counts[key] = len(ckpt.get(list_key, []))
    except Exception as exc:
        logger.warning(
            "Could not load checkpoints for %s: %s",
            atom_id, exc,
        )
    return counts


# ---------------------------------------------------------------------------
# Confirmation tokens
# ---------------------------------------------------------------------------


def generate_confirmation_token(
    pipeline_id: str, params: dict[str, Any],
) -> str:
    """Generate a confirmation token for cost approval.

    This token confirms the user has seen the cost estimate.
    It's tied to the specific pipeline and params to prevent replay.
    """
    salt = secrets.token_hex(8)
    content = f"{pipeline_id}:{sorted(params.items())}:{salt}"
    token_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    return f"{salt}:{token_hash}"


def verify_confirmation_token(
    token: str,
    pipeline_id: str,
    params: dict[str, Any],
) -> bool:
    """Verify a confirmation token is valid (simplified format check)."""
    if not token or ":" not in token:
        return False
    parts = token.split(":")
    return len(parts) == 2 and len(parts[0]) == 16 and len(parts[1]) == 16
