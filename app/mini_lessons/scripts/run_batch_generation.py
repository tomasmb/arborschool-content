"""Batch mini-lesson generation via OpenAI Batch API (50% cost).

Uses the 5-state checkpoint lifecycle so any interruption is fully
recoverable: pending -> file_uploaded -> submitted ->
results_downloaded -> completed.

Usage:
    python -m app.mini_lessons.scripts.run_batch_generation
    python -m app.mini_lessons.scripts.run_batch_generation \
        --max-atoms 10 --job-id ml_batch_20260226_abc123
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.mini_lessons.batch_request_builders import (
    build_plan_request,
    build_quality_gate_request,
    build_section_request,
)
from app.mini_lessons.generator import _build_generation_jobs
from app.mini_lessons.helpers import (
    build_lesson_context,
    deserialize_plan,
    get_output_dir,
    load_atom,
    load_checkpoint,
    load_enrichment,
    load_sample_questions,
    save_checkpoint,
)
from app.mini_lessons.models import LessonContext, LessonPlan
from app.mini_lessons.planner import validate_plan
from app.mini_lessons.validators import (
    _deterministic_section_checks,
    assemble_lesson,
)
from app.question_generation.batch_api import (
    BatchRequest,
    BatchResponse,
    OpenAIBatchSubmitter,
)
from app.question_generation.batch_checkpoint import (
    get_active_atoms,
    get_phase,
    is_phase_completed,
    load_run_state,
    mark_atoms_failed,
    new_run_state,
    save_run_state,
    update_phase,
)
from app.utils.logging_config import setup_logging
from app.utils.paths import MINI_LESSONS_DIR

logger = logging.getLogger(__name__)
_BATCH_DIR = MINI_LESSONS_DIR / ".batch"


# ------------------------------------------------------------------
# Generic batch phase runner (DRY)
# ------------------------------------------------------------------

def _run_batch_phase(
    sub: OpenAIBatchSubmitter,
    state: dict,
    ckpt: Path,
    phase_key: str,
    requests: list[BatchRequest],
) -> list[BatchResponse]:
    """Execute one batch phase through the 5-state lifecycle.

    Returns the list of BatchResponse objects. Handles file upload,
    submission, orphan detection, polling, and checkpoint updates.
    """
    phase = get_phase(state, phase_key)
    status = phase.get("status", "pending")

    if status == "pending":
        if not requests:
            update_phase(
                state, phase_key, ckpt, status="completed",
            )
            return []
        jsonl = _BATCH_DIR / f"{phase_key}.jsonl"
        sub.write_jsonl(requests, jsonl)
        update_phase(
            state, phase_key, ckpt,
            status="file_uploaded",
            input_jsonl=str(jsonl),
            request_count=len(requests),
        )
        status = "file_uploaded"

    if status == "file_uploaded":
        jsonl = Path(phase["input_jsonl"])
        file_id = sub.upload_file(jsonl)
        batch_id = sub.create_batch(file_id)
        update_phase(
            state, phase_key, ckpt,
            status="submitted",
            file_id=file_id,
            batch_id=batch_id,
        )
        status = "submitted"

    if status == "submitted":
        batch_id = phase.get("batch_id")
        if not batch_id:
            orphan = sub.find_orphan_batch(
                file_id=phase.get("file_id"),
            )
            if orphan:
                batch_id = orphan["id"]
                update_phase(
                    state, phase_key, ckpt,
                    batch_id=batch_id,
                )
            else:
                update_phase(
                    state, phase_key, ckpt, status="pending",
                )
                return _run_batch_phase(
                    sub, state, ckpt, phase_key, requests,
                )
        responses = sub.poll_and_download(batch_id)
        update_phase(
            state, phase_key, ckpt,
            status="results_downloaded",
        )
        return responses

    return []


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def main() -> None:
    """CLI entry point."""
    args = _parse_args()
    setup_logging(verbose=args.verbose)

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("Error: OPENAI_API_KEY not set.")
        sys.exit(1)

    sub = OpenAIBatchSubmitter(
        api_key=api_key,
        poll_interval=args.poll_interval,
        max_wait=args.max_wait,
    )

    job_id = args.job_id or _gen_job_id()
    ckpt = _BATCH_DIR / f"{job_id}.json"

    state = load_run_state(ckpt)
    if state:
        print(f"Resuming job: {job_id}")
    else:
        atoms = _load_eligible_atoms()
        if args.max_atoms:
            atoms = atoms[:args.max_atoms]
        if not atoms:
            print("No eligible atoms.")
            sys.exit(0)
        ids = [a["id"] for a in atoms]
        state = new_run_state(job_id, ids)
        save_run_state(ckpt, state)
        print(f"New job: {job_id} ({len(ids)} atoms)")

    ctxs = _build_contexts(get_active_atoms(state))
    plans = _phase_1(sub, state, ckpt, ctxs)
    secs = _phase_2(sub, state, ckpt, ctxs, plans)
    asm = _phases_3_4(state, ckpt, ctxs, plans, secs)
    res = _phase_5(sub, state, ckpt, ctxs, asm)

    ok = sum(1 for v in res.values() if v)
    print(f"\nDone: {ok}/{len(res)} publishable")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Batch mini-lesson generation (Batch API).",
    )
    p.add_argument("--max-atoms", type=int)
    p.add_argument("--job-id", help="Resume a previous job")
    p.add_argument("--poll-interval", type=int, default=30)
    p.add_argument("--max-wait", type=int, default=86400)
    p.add_argument("--verbose", "-v", action="store_true")
    return p.parse_args()


def _gen_job_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"ml_batch_{ts}_{uuid.uuid4().hex[:6]}"


def _load_eligible_atoms() -> list[dict]:
    from app.atoms.models import CanonicalAtomsFile
    from app.utils.paths import ATOMS_DIR
    atoms: list[dict] = []
    for f in ATOMS_DIR.glob("*_atoms.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            ca = CanonicalAtomsFile.model_validate(data)
            for atom in ca.atoms:
                html = MINI_LESSONS_DIR / atom.id / "mini-class.html"
                if not html.exists():
                    atoms.append({"id": atom.id})
        except Exception as exc:
            logger.warning("Error loading %s: %s", f, exc)
    return atoms


def _build_contexts(
    ids: list[str],
) -> dict[str, LessonContext]:
    ctxs: dict[str, LessonContext] = {}
    for aid in ids:
        atom = load_atom(aid)
        if not atom:
            continue
        ctx = build_lesson_context(
            atom, load_enrichment(aid),
            load_sample_questions(aid),
        )
        if ctx:
            ctxs[aid] = ctx
    return ctxs


# ------------------------------------------------------------------
# Phase 1 — Planning
# ------------------------------------------------------------------

def _phase_1(
    sub: OpenAIBatchSubmitter, state: dict,
    ckpt: Path, ctxs: dict[str, LessonContext],
) -> dict[str, LessonPlan]:
    pk = "phase_1"
    if is_phase_completed(state, pk):
        return _reload_plans(ctxs)

    reqs = [build_plan_request(c) for c in ctxs.values()]
    responses = _run_batch_phase(sub, state, ckpt, pk, reqs)

    plans: dict[str, LessonPlan] = {}
    failed: dict[str, str] = {}
    for resp in responses:
        aid = resp.custom_id.split(":", 1)[1]
        if resp.error:
            failed[aid] = resp.error
            continue
        try:
            plan = LessonPlan.model_validate(json.loads(resp.text))
            ctx = ctxs.get(aid)
            if ctx:
                errs = validate_plan(plan, ctx)
                if errs:
                    failed[aid] = "; ".join(errs)
                    continue
            plans[aid] = plan
            save_checkpoint(
                get_output_dir(aid), 1, "plan",
                {"plan": plan.model_dump()},
            )
        except Exception as exc:
            failed[aid] = str(exc)

    if failed:
        mark_atoms_failed(state, failed, ckpt)
    update_phase(state, pk, ckpt, status="completed")
    print(f"Phase 1: {len(plans)} plans")
    return plans


def _reload_plans(
    ctxs: dict[str, LessonContext],
) -> dict[str, LessonPlan]:
    plans: dict[str, LessonPlan] = {}
    for aid in ctxs:
        c = load_checkpoint(get_output_dir(aid), 1, "plan")
        if c:
            plans[aid] = deserialize_plan(c.get("plan", c))
    return plans


# ------------------------------------------------------------------
# Phase 2 — Section generation
# ------------------------------------------------------------------

def _phase_2(
    sub: OpenAIBatchSubmitter, state: dict, ckpt: Path,
    ctxs: dict[str, LessonContext],
    plans: dict[str, LessonPlan],
) -> dict[str, list[dict]]:
    pk = "phase_2"
    if is_phase_completed(state, pk):
        return _reload_sections(plans)

    reqs: list[BatchRequest] = []
    for aid, plan in plans.items():
        ctx = ctxs.get(aid)
        if not ctx:
            continue
        for bn, idx in _build_generation_jobs(plan):
            reqs.append(build_section_request(ctx, plan, bn, idx))

    responses = _run_batch_phase(sub, state, ckpt, pk, reqs)
    smap: dict[str, list[dict]] = {}
    for resp in responses:
        aid = resp.custom_id.split(":")[1] if ":" in resp.custom_id else ""
        if resp.error:
            continue
        try:
            smap.setdefault(aid, []).append(json.loads(resp.text))
        except Exception:
            continue

    update_phase(state, pk, ckpt, status="completed")
    print(f"Phase 2: {len(smap)} atoms with sections")
    return smap


def _reload_sections(
    plans: dict[str, LessonPlan],
) -> dict[str, list[dict]]:
    smap: dict[str, list[dict]] = {}
    for aid in plans:
        c = load_checkpoint(get_output_dir(aid), 2, "sections")
        if c and "sections" in c:
            smap[aid] = c["sections"]
    return smap


# ------------------------------------------------------------------
# Phases 3-4 — Local validation + assembly
# ------------------------------------------------------------------

def _phases_3_4(
    state: dict, ckpt: Path,
    ctxs: dict[str, LessonContext],
    plans: dict[str, LessonPlan],
    smap: dict[str, list[dict]],
) -> dict[str, str]:
    pk = "phase_3_4"
    if is_phase_completed(state, pk):
        return _reload_assembled(plans)

    from app.mini_lessons.html_validator import count_words
    from app.mini_lessons.models import LessonSection

    assembled: dict[str, str] = {}
    failed: dict[str, str] = {}
    for aid, raws in smap.items():
        ctx = ctxs.get(aid)
        if not ctx:
            continue
        secs = [
            LessonSection(
                block_name=r.get("block_name", ""),
                index=r.get("index"),
                html=r.get("html", ""),
                word_count=count_words(r.get("html", "")),
            ) for r in raws
        ]
        valid = [
            s for s in secs
            if not _deterministic_section_checks(s)
        ]
        for s in valid:
            s.validation_status = "passed"
        if not valid:
            failed[aid] = "No sections passed validation"
            continue
        pr, html = assemble_lesson(valid, aid, ctx.template_type)
        if pr.success:
            assembled[aid] = html
            save_checkpoint(
                get_output_dir(aid), 4, "assembled",
                {"html": html},
            )
        else:
            failed[aid] = "; ".join(pr.errors)

    if failed:
        mark_atoms_failed(state, failed, ckpt)
    update_phase(state, pk, ckpt, status="completed")
    print(f"Phase 3-4: {len(assembled)} atoms assembled")
    return assembled


def _reload_assembled(
    plans: dict[str, LessonPlan],
) -> dict[str, str]:
    asm: dict[str, str] = {}
    for aid in plans:
        c = load_checkpoint(get_output_dir(aid), 4, "assembled")
        if c and "html" in c:
            asm[aid] = c["html"]
    return asm


# ------------------------------------------------------------------
# Phase 5 — Quality gate
# ------------------------------------------------------------------

def _phase_5(
    sub: OpenAIBatchSubmitter, state: dict, ckpt: Path,
    ctxs: dict[str, LessonContext],
    assembled: dict[str, str],
) -> dict[str, bool]:
    pk = "phase_5"
    if is_phase_completed(state, pk):
        return _reload_quality(assembled)

    reqs: list[BatchRequest] = []
    for aid, html in assembled.items():
        ctx = ctxs.get(aid)
        if ctx:
            reqs.append(build_quality_gate_request(html, ctx, aid))

    responses = _run_batch_phase(sub, state, ckpt, pk, reqs)
    results: dict[str, bool] = {}
    for resp in responses:
        aid = resp.custom_id.split(":", 1)[1]
        if resp.error:
            results[aid] = False
            continue
        try:
            data = json.loads(resp.text)
            pub = data.get("publishable", False)
            results[aid] = pub
            out = get_output_dir(aid)
            save_checkpoint(out, 5, "quality", {"report": data})
            html = assembled.get(aid, "")
            if html:
                out.mkdir(parents=True, exist_ok=True)
                fname = (
                    "mini-class.html" if pub
                    else "mini-class.rejected.html"
                )
                (out / fname).write_text(html, encoding="utf-8")
        except Exception as exc:
            logger.warning("Phase 5 error %s: %s", aid, exc)
            results[aid] = False

    update_phase(state, pk, ckpt, status="completed")
    ok = sum(1 for v in results.values() if v)
    print(f"Phase 5: {ok}/{len(results)} publishable")
    return results


def _reload_quality(
    assembled: dict[str, str],
) -> dict[str, bool]:
    results: dict[str, bool] = {}
    for aid in assembled:
        c = load_checkpoint(get_output_dir(aid), 5, "quality")
        if c and "report" in c:
            results[aid] = c["report"].get("publishable", False)
    return results


if __name__ == "__main__":
    main()
