"""Phase 2 — Section-by-section generation (parallel).

Generates each mini-lesson section with a focused, single-
responsibility LLM call. Uses ThreadPoolExecutor for parallelism.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.llm_clients import LLMResponse, OpenAIClient
from app.mini_lessons.html_validator import count_words
from app.mini_lessons.models import (
    LessonContext,
    LessonPlan,
    LessonSection,
    PhaseResult,
)
from app.mini_lessons.prompts.generation import (
    build_section_prompt,
    extract_plan_section_for_block,
)
from app.mini_lessons.prompts.shared import build_lesson_context_section

logger = logging.getLogger(__name__)

_MAX_WORKERS = 8

_HIGH_REASONING_BLOCKS = frozenset({
    "worked-example",
})


def reasoning_for_block(block_name: str) -> str:
    """Return the reasoning effort appropriate for *block_name*."""
    if block_name in _HIGH_REASONING_BLOCKS:
        return "high"
    return "medium"


class SectionGenerator:
    """Generates mini-lesson sections in parallel."""

    def __init__(self, client: OpenAIClient):
        self._client = client

    def generate_sections(
        self,
        ctx: LessonContext,
        plan: LessonPlan,
        only: list[tuple[str, int | None]] | None = None,
    ) -> tuple[PhaseResult, list[LessonSection]]:
        """Run Phase 2: parallel section generation.

        Args:
            ctx: Lesson context with atom + enrichment data.
            plan: The lesson plan to generate sections from.
            only: If provided, generate only these (block_name, index)
                  pairs. Used by refinement to regenerate weak sections
                  without re-generating everything.

        Returns:
            Tuple of (PhaseResult, list of generated sections).
        """
        context_section = build_lesson_context_section(ctx)
        plan_data = plan.model_dump()
        all_jobs = build_generation_jobs(plan)
        jobs = (
            [j for j in all_jobs if j in only]
            if only else all_jobs
        )

        sections: list[LessonSection] = []
        errors: list[str] = []

        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
            futures = {
                pool.submit(
                    self._generate_one,
                    context_section,
                    plan_data,
                    ctx.atom_id,
                    ctx.template_type,
                    block_name,
                    index,
                ): (block_name, index)
                for block_name, index in jobs
            }

            for future in as_completed(futures):
                block_name, index = futures[future]
                label = (
                    f"{block_name}[{index}]"
                    if index else block_name
                )
                try:
                    section = future.result()
                    if section:
                        sections.append(section)
                        logger.info("Generated section: %s", label)
                    else:
                        errors.append(f"Failed to generate {label}")
                except Exception as exc:
                    errors.append(f"Error generating {label}: {exc}")
                    logger.error(
                        "Exception generating %s: %s", label, exc,
                    )

        sections.sort(key=_section_sort_key)

        return PhaseResult(
            phase_name="generation",
            success=len(errors) == 0,
            data={"section_count": len(sections)},
            errors=errors,
        ), sections

    def _generate_one(
        self,
        context_section: str,
        plan_data: dict,
        atom_id: str,
        template_type: str,
        block_name: str,
        index: int | None,
    ) -> LessonSection | None:
        """Generate a single section via LLM."""
        plan_section = extract_plan_section_for_block(
            plan_data, block_name, index,
        )
        prompt = build_section_prompt(
            context_section=context_section,
            plan_section=plan_section,
            block_name=block_name,
            atom_id=atom_id,
            template_type=template_type,
            index=index,
        )

        effort = reasoning_for_block(block_name)
        try:
            resp: LLMResponse = self._client.call(
                prompt,
                response_format={"type": "json_object"},
                reasoning_effort=effort,
            )
            data = json.loads(resp.text)
            html = data.get("html", "")
            word_count = count_words(html)

            return LessonSection(
                block_name=block_name,
                index=data.get("index", index),
                html=html,
                word_count=word_count,
            )
        except Exception as exc:
            logger.warning(
                "Section generation failed for %s: %s",
                block_name, exc,
            )
            return None


# ---------------------------------------------------------------------------
# Job building helpers
# ---------------------------------------------------------------------------

_BLOCK_ORDER = [
    "objective",
    "prerequisite-refresh",
    "concept",
    "worked-example",
]


def build_generation_jobs(
    plan: LessonPlan,
) -> list[tuple[str, int | None]]:
    """Build the list of (block_name, index) jobs from the plan."""
    jobs: list[tuple[str, int | None]] = [
        ("objective", None),
    ]

    if plan.include_prerequisite_refresh:
        jobs.append(("prerequisite-refresh", None))

    jobs.append(("concept", None))
    jobs.append(("worked-example", 1))

    return jobs


def _section_sort_key(
    section: LessonSection,
) -> tuple[int, int]:
    """Sort key for ordering sections in assembly order."""
    try:
        order = _BLOCK_ORDER.index(section.block_name)
    except ValueError:
        order = len(_BLOCK_ORDER)
    return (order, section.index or 0)
