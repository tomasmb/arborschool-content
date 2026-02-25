"""Main orchestrator for the mini-lesson generation pipeline.

Connects Phases 0-6 with checkpoint/resume support.
Each phase calls its specialized module (single responsibility).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.llm_clients import OpenAIClient
from app.mini_lessons.generator import SectionGenerator
from app.mini_lessons.helpers import (
    build_lesson_context,
    check_prerequisites,
    deserialize_plan,
    deserialize_sections,
    find_resume_phase_group,
    get_output_dir,
    load_atom,
    load_checkpoint,
    load_enrichment,
    load_sample_questions,
    save_checkpoint,
    serialize_sections,
)
from app.mini_lessons.models import (
    PHASE_GROUPS,
    LessonConfig,
    LessonContext,
    LessonPlan,
    LessonResult,
    LessonSection,
    PhaseResult,
    QualityReport,
)
from app.mini_lessons.planner import LessonPlanner
from app.mini_lessons.validators import (
    QualityGate,
    SectionValidator,
    assemble_lesson,
    build_lesson_meta,
)

logger = logging.getLogger(__name__)


class MiniLessonPipeline:
    """Orchestrates the full mini-lesson generation pipeline.

    Phases 0-6: load -> plan -> generate -> validate sections
    -> assemble -> quality gate -> final output.
    """

    def __init__(self, client: OpenAIClient):
        self._client = client
        self._planner = LessonPlanner(client)
        self._generator = SectionGenerator(client)
        self._section_validator = SectionValidator(client)
        self._quality_gate = QualityGate(client)

    def run(self, config: LessonConfig) -> LessonResult:
        """Run the pipeline for a single atom."""
        result = LessonResult(atom_id=config.atom_id)
        output_dir = get_output_dir(
            config.atom_id, config.output_dir,
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        phase_group = config.phase
        if config.resume:
            resumed = find_resume_phase_group(output_dir)
            if resumed:
                phase_group = resumed
                logger.info("Resuming from: %s", phase_group)

        ok, missing = check_prerequisites(phase_group, output_dir)
        if not ok:
            result.phase_results.append(PhaseResult(
                phase_name="prerequisites",
                success=False, errors=missing,
            ))
            return result

        start, end = PHASE_GROUPS.get(phase_group, (0, 6))
        ctx: LessonContext | None = None
        plan: LessonPlan | None = None
        sections: list[LessonSection] = []
        full_html = ""
        quality: QualityReport | None = None

        for phase in range(start, end + 1):
            if phase == 0:
                ctx = self._phase_0_load(config, result)
            elif phase == 1:
                ctx = ctx or self._restore_ctx(config, result)
                plan = self._phase_1_plan(
                    ctx, config, output_dir, result,
                ) if ctx else None
            elif phase == 2:
                ctx, plan = self._ensure(
                    ctx, plan, config, output_dir, result,
                )
                if ctx and plan:
                    sections = self._phase_2_gen(
                        ctx, plan, output_dir, result,
                    )
            elif phase == 3:
                ctx, plan = self._ensure(
                    ctx, plan, config, output_dir, result,
                )
                sections = sections or self._load_sections(
                    output_dir,
                )
                if ctx and plan:
                    sections = self._phase_3_val(
                        sections, ctx, plan, output_dir, result,
                    )
            elif phase == 4:
                ctx = ctx or self._restore_ctx(config, result)
                sections = sections or self._load_sections(
                    output_dir, "validated",
                )
                if ctx:
                    full_html = self._phase_4_asm(
                        sections, ctx, output_dir, result,
                    )
            elif phase == 5:
                ctx = ctx or self._restore_ctx(config, result)
                full_html = full_html or self._load_html(output_dir)
                if ctx:
                    quality = self._phase_5_qg(
                        full_html, ctx, plan, sections,
                        config, output_dir, result,
                    )
            elif phase == 6:
                ctx = ctx or self._restore_ctx(config, result)
                plan = plan or self._load_plan(output_dir)
                if ctx and plan:
                    self._phase_6_out(
                        full_html, ctx, plan,
                        quality, output_dir, result,
                    )

            # Early exit on failed phase
            if result.phase_results and not result.phase_results[-1].success:
                if phase < 5:
                    return result

        result.success = all(
            p.success for p in result.phase_results
        )
        result.html = full_html
        result.quality_report = quality
        return result

    def _phase_0_load(
        self, config: LessonConfig, result: LessonResult,
    ) -> LessonContext | None:
        atom = load_atom(config.atom_id)
        if atom is None:
            result.phase_results.append(PhaseResult(
                phase_name="input_loading", success=False,
                errors=[f"Atom {config.atom_id} not found"],
            ))
            return None
        enrichment = load_enrichment(config.atom_id)
        samples = load_sample_questions(config.atom_id)
        ctx = build_lesson_context(atom, enrichment, samples)
        if ctx is None:
            result.phase_results.append(PhaseResult(
                phase_name="input_loading", success=False,
                errors=[
                    f"Unknown tipo_atomico '{atom.tipo_atomico}' "
                    f"for atom {config.atom_id}",
                ],
            ))
            return None
        result.phase_results.append(PhaseResult(
            phase_name="input_loading", success=True,
            data={"template_type": ctx.template_type},
        ))
        logger.info(
            "Phase 0: Loaded %s (template %s)",
            config.atom_id, ctx.template_type,
        )
        return ctx

    def _phase_1_plan(
        self, ctx: LessonContext, config: LessonConfig,
        output_dir: Path, result: LessonResult,
    ) -> LessonPlan | None:
        existing = load_checkpoint(output_dir, 1, "plan")
        if existing and config.resume:
            plan = deserialize_plan(existing.get("plan", existing))
            result.phase_results.append(PhaseResult(
                phase_name="planning", success=True,
                data=plan.model_dump(),
            ))
            return plan
        phase_result, plan = self._planner.generate_plan(ctx)
        result.phase_results.append(phase_result)
        if plan:
            save_checkpoint(
                output_dir, 1, "plan",
                {"plan": plan.model_dump()},
            )
        return plan

    def _phase_2_gen(
        self, ctx: LessonContext, plan: LessonPlan,
        output_dir: Path, result: LessonResult,
    ) -> list[LessonSection]:
        phase_result, sections = (
            self._generator.generate_sections(ctx, plan)
        )
        result.phase_results.append(phase_result)
        if sections:
            save_checkpoint(
                output_dir, 2, "sections",
                {"sections": serialize_sections(sections)},
            )
            logger.info("Phase 2: %d sections", len(sections))
        return sections

    def _phase_3_val(
        self, sections: list[LessonSection],
        ctx: LessonContext, plan: LessonPlan,
        output_dir: Path, result: LessonResult,
    ) -> list[LessonSection]:
        phase_result, validated = (
            self._section_validator.validate_sections(
                sections, ctx, plan,
            )
        )
        result.phase_results.append(phase_result)
        if validated:
            save_checkpoint(
                output_dir, 3, "validated",
                {"sections": serialize_sections(validated)},
            )
            logger.info(
                "Phase 3: %d/%d passed",
                len(validated), len(sections),
            )
        return validated

    def _phase_4_asm(
        self, sections: list[LessonSection],
        ctx: LessonContext,
        output_dir: Path, result: LessonResult,
    ) -> str:
        phase_result, html = assemble_lesson(
            sections, ctx.atom_id, ctx.template_type,
        )
        result.phase_results.append(phase_result)
        if phase_result.success:
            save_checkpoint(
                output_dir, 4, "assembled", {"html": html},
            )
        return html if phase_result.success else ""

    def _phase_5_qg(
        self, full_html: str, ctx: LessonContext,
        plan: LessonPlan | None,
        sections: list[LessonSection],
        config: LessonConfig,
        output_dir: Path, result: LessonResult,
    ) -> QualityReport:
        phase_result, report = self._quality_gate.evaluate(
            full_html, ctx,
        )
        result.phase_results.append(phase_result)

        salvageable = (
            not report.publishable
            and not report.auto_fail_triggered
            and report.total_score >= 8
            and plan is not None
        )
        if salvageable and config.max_retries > 0:
            logger.info(
                "Phase 5: %d/14, refining...", report.total_score,
            )
            refined = self._refine(
                report, sections, ctx, plan, result,
            )
            if refined:
                pr2, report = self._quality_gate.evaluate(
                    refined, ctx,
                )
                result.phase_results.append(pr2)
                if report.publishable:
                    save_checkpoint(
                        output_dir, 4, "assembled",
                        {"html": refined},
                    )

        save_checkpoint(
            output_dir, 5, "quality",
            {"report": report.model_dump()},
        )
        return report

    def _refine(
        self, report: QualityReport,
        sections: list[LessonSection],
        ctx: LessonContext, plan: LessonPlan,
        result: LessonResult,
    ) -> str | None:
        """Phase 5b: regenerate only weak sections, re-validate."""
        weak = _identify_weak_sections(report, sections)
        if not weak:
            return None
        weak_keys = [
            (s.block_name, s.index) for s in weak
        ]
        logger.info(
            "Refining %d sections: %s",
            len(weak), [s.block_name for s in weak],
        )
        _, regenerated = self._generator.generate_sections(
            ctx, plan, only=weak_keys,
        )
        regen_map = {
            (s.block_name, s.index): s for s in regenerated
        }
        refined = [
            regen_map.get((s.block_name, s.index), s)
            for s in sections
        ]
        _, validated = self._section_validator.validate_sections(
            refined, ctx, plan,
        )
        if not validated:
            return None
        pr, html = assemble_lesson(
            validated, ctx.atom_id, ctx.template_type,
        )
        return html if pr.success else None

    def _phase_6_out(
        self, full_html: str, ctx: LessonContext,
        plan: LessonPlan, quality: QualityReport | None,
        output_dir: Path, result: LessonResult,
    ) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "mini-class.html").write_text(
            full_html, encoding="utf-8",
        )
        meta = build_lesson_meta(
            ctx.atom_id, ctx.template_type, ctx, plan,
            html=full_html,
        )
        (output_dir / "mini-class.meta.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        qa: dict[str, Any] = {
            "atom_id": ctx.atom_id, "publishable": False,
        }
        if quality:
            qa = quality.model_dump()
            qa["atom_id"] = ctx.atom_id
        (output_dir / "mini-class.qa.json").write_text(
            json.dumps(qa, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        save_checkpoint(
            output_dir, 6, "final",
            {"publishable": qa.get("publishable", False)},
        )
        result.phase_results.append(PhaseResult(
            phase_name="final_output", success=True,
            data={"output_dir": str(output_dir)},
        ))
        result.html = full_html
        result.meta = meta
        logger.info("Phase 6: Saved to %s", output_dir)

    def _restore_ctx(
        self, config: LessonConfig, result: LessonResult,
    ) -> LessonContext | None:
        return self._phase_0_load(config, result)

    def _ensure(
        self, ctx: LessonContext | None,
        plan: LessonPlan | None,
        config: LessonConfig, output_dir: Path,
        result: LessonResult,
    ) -> tuple[LessonContext | None, LessonPlan | None]:
        if ctx is None:
            ctx = self._restore_ctx(config, result)
        if plan is None:
            plan = self._load_plan(output_dir)
        return ctx, plan

    def _load_plan(self, output_dir: Path) -> LessonPlan | None:
        ckpt = load_checkpoint(output_dir, 1, "plan")
        return deserialize_plan(ckpt.get("plan", ckpt)) if ckpt else None

    def _load_sections(
        self, output_dir: Path, phase_name: str = "sections",
    ) -> list[LessonSection]:
        phase_map = {"sections": 2, "validated": 3}
        num = phase_map.get(phase_name, 2)
        ckpt = load_checkpoint(output_dir, num, phase_name)
        if ckpt and "sections" in ckpt:
            return deserialize_sections(ckpt["sections"])
        return []

    def _load_html(self, output_dir: Path) -> str:
        ckpt = load_checkpoint(output_dir, 4, "assembled")
        return ckpt.get("html", "") if ckpt else ""


def _identify_weak_sections(
    report: QualityReport,
    sections: list[LessonSection],
) -> list[LessonSection]:
    """Map low-scoring rubric dimensions to their sections."""
    dimension_to_blocks: dict[str, list[str]] = {
        "objective_clarity": ["objective"],
        "brevity_cognitive_load": [
            "concept", "worked-example", "error-patterns",
        ],
        "worked_example_correctness": ["worked-example"],
        "step_rationale_clarity": ["worked-example"],
        "quick_check_quality": ["quick-check"],
        "feedback_quality": ["quick-check"],
        "transition_readiness": ["transition-to-adaptive"],
    }
    weak_blocks: set[str] = set()
    for dim, score in report.dimension_scores.items():
        if score < 2:
            weak_blocks.update(
                dimension_to_blocks.get(dim, []),
            )
    return [s for s in sections if s.block_name in weak_blocks]
