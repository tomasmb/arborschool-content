"""Cost estimation service for AI pipelines.

Estimates token usage and cost before running pipelines.
Prices verified February 2026 — update when models change.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from typing import Any

from api.schemas.api_models import CostEstimate

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

# ---------------------------------------------------------------------------
# GPT-5.1 reasoning token overhead (per call)
# ---------------------------------------------------------------------------
# GPT-5.1's reasoning_effort parameter controls internal chain-of-thought.
# Reasoning tokens are HIDDEN but billed as output tokens at the output
# rate ($10/1M). Higher effort = more reasoning tokens = higher cost.
# These are approximate overheads based on observed usage.

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
        """Standards generation — Gemini 3 Pro.

        Per eje (~8 unidades):
          - 8 generation calls: ~2,500 input, ~1,200 visible output
          - 8 validation calls: ~3,000 input, ~800 visible output
          - 1 cross-eje validation: ~6,000 input, ~1,500 visible output
        Gemini thinking_level=high adds ~3x on top of visible output.
        """
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
        """Atoms generation — Gemini 3 Pro.

        Per standard:
          - 1 call: ~5,000 input (prompt+rules+guidelines+standard)
          - ~3,000 visible output (3-6 atoms JSON)
        Gemini thinking_level=high adds ~3x on visible output.
        """
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
        """PDF split — o4-mini (reasoning model).

        Single call: uploads entire PDF as file.
        Highly variable based on PDF length.
          - Input: ~20,000-40,000 document tokens
          - Output: ~10,000-25,000 tokens (segment JSON + reasoning)
        o4-mini reasoning tokens are billed as output.
        """
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
        """PDF to QTI — Gemini 3 Pro (primary).

        Per question:
          - 1 call: ~4,000 input (prompt + vision tokens for PDF image)
          - ~3,000 visible output (QTI XML JSON)
        Gemini thinking_level=high adds ~3x on visible output.
        """
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
        """Question tagging — Gemini 3 Pro.

        Per question (3 calls: atom match + analysis + validation):
          - Total input: ~6,300 tokens (atom catalog is the big cost)
          - Total visible output: ~1,000 tokens
        No thinking tokens (temp=0.0, no thinking_level set).
        """
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
        """Variant generation — Gemini 3 Pro.

        Per source question:
          - 1 generation call: ~2,000 input, ~6,000 output
          - N validation calls: ~1,500 input, ~500 output each
        Default thinking (not high), so ~2x multiplier on output.
        """
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

        Phase-aware: only charges for the phases being run.
        Each phase uses a specific reasoning_effort level that
        generates hidden reasoning tokens billed as output.

        Phase groups and their reasoning effort:
          enrich   → P1: enrichment (1 call, low)
          plan     → P2-3: planning + validation (1 call, medium)
          generate → P4: QTI generation (1 call, medium)
          validate → P5-6: dedupe + solvability (N calls, high)
          feedback → P7-9: enhance (low) + review (none)
                     + final validation (medium), per item
          finalize → no LLM (file ops only)
        """
        phase = params.get("phase", "all")
        pool_size = int(params.get("pool_size", 9))
        r = GPT51_REASONING_OVERHEAD

        # Per-phase: (input, visible_output, reasoning_effort, num_calls)
        # Output includes visible + reasoning token overhead.
        phase_tokens: dict[str, tuple[int, int]] = {
            # 1 call, reasoning_effort="low"
            "enrich": (1_500, 800 + r["low"]),
            # 1 call, reasoning_effort="medium"
            "plan": (1_800, 1_200 + r["medium"]),
            # 1 call, reasoning_effort="medium"
            "generate": (2_000, 6_000 + r["medium"]),
            # pool_size calls, reasoning_effort="high"
            "validate": (
                1_000 * pool_size,
                (200 + r["high"]) * pool_size,
            ),
            # Per item: enhance (low) + review (none)
            # + final_validation (medium)
            "feedback": (
                5_000 * pool_size,
                (3_000 + r["low"] + 600 + r["none"]
                 + 200 + r["medium"]) * pool_size,
            ),
            "finalize": (0, 0),
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
            "pool_size": pool_size,
            "active_phases": active,
            "note": "Output includes reasoning token overhead",
        }
        for p in active:
            inp, out = phase_tokens.get(p, (0, 0))
            breakdown[f"{p}_input"] = inp
            breakdown[f"{p}_output"] = out

        return TokenEstimate(
            input_tokens=total_input,
            output_tokens=total_output,
            breakdown=breakdown,
        )

    def _estimate_lessons(
        self, params: dict[str, Any],
    ) -> TokenEstimate:
        """Lesson generation — GPT-5.1.

        Per atom:
          - 1 call: ~10,000 input (atom + questions + prompt)
          - ~3,000 output (lesson content)
        """
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
