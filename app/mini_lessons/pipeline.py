"""Mini-lesson pipeline orchestrator (Phases 0-6, with resume & cost tracking)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.llm_clients import (
    OpenAIClient,
    clear_cost_accumulator,
    set_cost_accumulator,
)
from app.mini_lessons.generator import SectionGenerator
from app.mini_lessons.helpers import (
    atom_requires_images,
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
from app.mini_lessons.image_generator import (
    LessonImageGenerator,
    strip_failed_image_placeholders,
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
    identify_weak_sections,
)
from app.question_generation.progress import CostAccumulator

logger = logging.getLogger(__name__)


class MiniLessonPipeline:
    """Orchestrates Phases 0-6: load, plan, generate, validate, assemble, QG, output."""

    def __init__(
        self,
        client: OpenAIClient,
        *,
        skip_images: bool = False,
        max_retries: int = 1,
    ):
        self._client = client
        self._planner = LessonPlanner(client, max_retries=max_retries)
        self._generator = SectionGenerator(client)
        self._image_gen = LessonImageGenerator(client)
        self._section_validator = SectionValidator(
            client, max_retries=max_retries,
        )
        self._quality_gate = QualityGate(client)
        self._skip_images = skip_images

    def run(self, config: LessonConfig) -> LessonResult:
        """Run the pipeline for a single atom."""
        result = LessonResult(atom_id=config.atom_id)

        if self._skip_images and atom_requires_images(config.atom_id):
            msg = f"Atom {config.atom_id} requires images — skipped (--skip-images)"
            result.phase_results.append(PhaseResult(
                phase_name="skip_images", success=False,
                errors=[msg],
            ))
            logger.info("Skipping %s: requires images", config.atom_id)
            return result

        cost_acc = CostAccumulator()
        set_cost_accumulator(cost_acc)

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
        full_html, quality = self._execute_phases(
            start, end, config, output_dir, result,
        )

        result.success = all(
            p.success for p in result.phase_results
        )
        result.html = full_html
        result.quality_report = quality
        result.cost_usd = cost_acc.total_cost_usd
        cost_acc.report()
        clear_cost_accumulator()
        return result

    def _execute_phases(
        self,
        start: int,
        end: int,
        config: LessonConfig,
        output_dir: Path,
        result: LessonResult,
    ) -> tuple[str, QualityReport | None]:
        """Dispatch and execute pipeline phases *start* through *end*."""
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
                if ctx:
                    sections = self._phase_2b_images(
                        sections, ctx.atom_id, result,
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
                plan = plan or self._load_plan(output_dir)
                full_html = full_html or self._load_html(output_dir)
                if ctx:
                    quality = self._phase_5_qg(
                        full_html, ctx, plan, sections,
                        config, output_dir, result,
                    )
            elif phase == 6:
                ctx = ctx or self._restore_ctx(config, result)
                plan = plan or self._load_plan(output_dir)
                quality = quality or self._load_quality(output_dir)
                full_html = full_html or self._load_html(output_dir)
                if ctx and plan:
                    self._phase_6_out(
                        full_html, ctx, plan, quality,
                        sections, output_dir, result,
                    )

            if result.phase_results and not result.phase_results[-1].success:
                if phase < 5:
                    break

        return full_html, quality

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
        ctx = build_lesson_context(
            atom, enrichment, load_sample_questions(config.atom_id),
        )
        if ctx is None:
            result.phase_results.append(PhaseResult(
                phase_name="input_loading", success=False,
                errors=[f"Unknown tipo_atomico for {config.atom_id}"],
            ))
            return None
        result.phase_results.append(PhaseResult(
            phase_name="input_loading", success=True,
            data={"template_type": ctx.template_type},
        ))
        logger.info("Phase 0: %s (template %s)", config.atom_id, ctx.template_type)
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

    def _phase_2b_images(
        self,
        sections: list[LessonSection],
        atom_id: str,
        result: LessonResult,
    ) -> list[LessonSection]:
        """Phase 2b: Generate images, strip failed placeholders."""
        warnings: list[str] = []
        try:
            sections = self._image_gen.generate_for_sections(
                sections, atom_id,
            )
        except Exception as exc:
            logger.warning("Phase 2b image gen failed: %s", exc)
            warnings.append(f"Image generation error: {exc}")

        stripped = strip_failed_image_placeholders(sections)
        if stripped:
            warnings.extend(
                f"Image failed for {b}" for b in stripped
            )

        result.phase_results.append(PhaseResult(
            phase_name="image_generation",
            success=True,
            warnings=warnings,
        ))
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
            logger.info("Phase 3: %d/%d passed", len(validated), len(sections))
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
        img_fails = [
            s.block_name for s in sections if s.image_failed
        ]
        phase_result, report = self._quality_gate.evaluate(
            full_html, ctx, plan=plan,
            image_failures=img_fails or None,
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
                    refined, ctx, plan=plan,
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
        """Phase 5b: regenerate weak sections, re-image, re-validate."""
        weak = identify_weak_sections(report, sections)
        if not weak:
            return None
        weak_keys = [(s.block_name, s.index) for s in weak]
        logger.info(
            "Refining %d sections: %s",
            len(weak), [s.block_name for s in weak],
        )
        _, regenerated = self._generator.generate_sections(
            ctx, plan, only=weak_keys,
        )
        regen_map = {(s.block_name, s.index): s for s in regenerated}
        refined = [
            regen_map.get((s.block_name, s.index), s)
            for s in sections
        ]
        if not self._skip_images:
            refined = self._image_gen.generate_for_sections(
                refined, ctx.atom_id,
            )
            strip_failed_image_placeholders(refined)
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
        sections: list[LessonSection],
        output_dir: Path, result: LessonResult,
    ) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        publishable = quality.publishable if quality else False

        html_name = "mini-class.html" if publishable else "mini-class.rejected.html"
        (output_dir / html_name).write_text(full_html, encoding="utf-8")
        rejected = output_dir / "mini-class.rejected.html"
        if publishable and rejected.exists():
            rejected.unlink()
        elif not publishable:
            logger.warning("Phase 6: quality gate NOT passed — wrote %s", html_name)

        meta = build_lesson_meta(
            ctx.atom_id, ctx.template_type, ctx, plan,
            html=full_html, sections=sections,
        )
        _write_json(output_dir / "mini-class.meta.json", meta)
        qa: dict[str, Any] = (
            {**quality.model_dump(), "atom_id": ctx.atom_id}
            if quality else {"atom_id": ctx.atom_id, "publishable": False}
        )
        _write_json(output_dir / "mini-class.qa.json", qa)
        save_checkpoint(output_dir, 6, "final", {"publishable": publishable})
        result.phase_results.append(PhaseResult(
            phase_name="final_output", success=publishable,
            data={"output_dir": str(output_dir), "publishable": publishable},
        ))
        result.html, result.meta = full_html, meta
        logger.info("Phase 6: %s (publishable=%s)", output_dir, publishable)

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
        num = {"sections": 2, "validated": 3}.get(phase_name, 2)
        ckpt = load_checkpoint(output_dir, num, phase_name)
        return deserialize_sections(ckpt["sections"]) if ckpt and "sections" in ckpt else []

    def _load_html(self, output_dir: Path) -> str:
        ckpt = load_checkpoint(output_dir, 4, "assembled")
        return ckpt.get("html", "") if ckpt else ""

    def _load_quality(self, output_dir: Path) -> QualityReport | None:
        ckpt = load_checkpoint(output_dir, 5, "quality")
        if ckpt and "report" in ckpt:
            return QualityReport.model_validate(ckpt["report"])
        return None


def _write_json(path: Path, data: dict) -> None:
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8",
    )
