"""Batch pipeline orchestrator — phases 0-4 and the batch submission lifecycle.

Phases 5-9 live in ``batch_pipeline_stages``.  Every LLM phase uses the
5-state checkpoint lifecycle (see ``batch_checkpoint``) so any interruption
is fully recoverable and no API spend is ever lost.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

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
    validate_checkpoint_consistency,
)
from app.question_generation.batch_phase_processors import (
    build_xsd_retry_requests,
    process_enrichment_responses,
    process_generation_responses,
    process_plan_responses,
)
from app.question_generation.batch_request_builders import (
    build_enrichment_request,
    build_generation_request,
    build_plan_request,
)
from app.question_generation.batch_pipeline_stages import (
    run_phase_5,
    run_phase_6,
    run_phase_78,
    run_phase_9,
)
from app.question_generation.prompts.generation import (
    build_context_section,
)
from app.question_generation.helpers import (
    load_atom,
    load_checkpoint,
    save_checkpoint,
    serialize_items,
)
from app.question_generation.models import (
    AtomContext,
    AtomEnrichment,
    GeneratedItem,
    PlanSlot,
    compute_planned_distribution,
    DEFAULT_TARGET_DISTRIBUTION,
)
from app.question_generation.planner import validate_plan
from app.question_generation.exemplars import load_exemplars_for_atom
from app.utils.paths import QUESTION_GENERATION_DIR

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gpt-5.1"
_DEFAULT_BUFFER_RATIO = 1.3
_MAX_XSD_RETRY_ROUNDS = 2


class BatchAtomPipeline:
    """Orchestrates all pipeline phases across atoms via the Batch API."""

    def __init__(
        self,
        job_id: str,
        atom_ids: list[str],
        *,
        model: str = _DEFAULT_MODEL,
        skip_images: bool = False,
        batch_dir: Path | None = None,
        poll_interval: int = 30,
        max_wait: int = 86400,
    ) -> None:
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required")

        self._model = model
        self._skip_images = skip_images
        self._job_id = job_id
        self._submitter = OpenAIBatchSubmitter(
            api_key, poll_interval, max_wait,
        )

        self._batch_dir = batch_dir or (
            QUESTION_GENERATION_DIR / ".batch_runs" / job_id
        )
        self._batch_dir.mkdir(parents=True, exist_ok=True)
        self._ckpt_path = self._batch_dir / "batch_state.json"

        self._distribution = compute_planned_distribution(
            DEFAULT_TARGET_DISTRIBUTION, _DEFAULT_BUFFER_RATIO,
        )

        self._contexts: dict[str, AtomContext] = {}
        self._enrichments: dict[str, AtomEnrichment | None] = {}
        self._plans: dict[str, list[PlanSlot]] = {}
        self._context_sections: dict[str, str] = {}
        self._items: dict[str, list[GeneratedItem]] = {}

        existing = load_run_state(self._ckpt_path)
        if existing and existing.get("job_id") == job_id:
            self._state = existing
            logger.info(
                "Resumed batch run %s (%d active atoms)",
                job_id, len(get_active_atoms(existing)),
            )
        else:
            self._state = new_run_state(job_id, atom_ids)
            save_run_state(self._ckpt_path, self._state)

    def run(self) -> dict[str, Any]:
        """Run the full batch pipeline.  Returns a summary dict."""
        errs = validate_checkpoint_consistency(self._state)
        if errs:
            logger.error("Checkpoint inconsistency: %s", errs)

        self._run_phase_0()
        self._run_phase_1()
        self._run_phase_2_3()
        self._run_phase_4()
        fn = self._submit_and_wait
        self._items = run_phase_5(self._state, self._ckpt_path, self._items)
        self._items = run_phase_6(self._state, self._ckpt_path, self._items, self._model, fn)
        self._items = run_phase_78(self._state, self._ckpt_path, self._items, self._model, fn)
        self._items = run_phase_9(self._state, self._ckpt_path, self._items, self._model, fn)
        return self._build_summary()

    # -- Phase 0: Inputs (local) ---

    def _run_phase_0(self) -> None:
        if is_phase_completed(self._state, "phase_0"):
            self._load_contexts(get_active_atoms(self._state))
            return

        logger.info("Phase 0: Loading inputs for all atoms")
        failed: dict[str, str] = {}
        for atom_id in get_active_atoms(self._state):
            ctx = _build_atom_context(atom_id)
            if ctx:
                self._contexts[atom_id] = ctx
            else:
                failed[atom_id] = "Atom not found"

        if failed:
            mark_atoms_failed(
                self._state, failed, self._ckpt_path,
            )
        update_phase(
            self._state, "phase_0", self._ckpt_path,
            status="completed",
        )
        logger.info(
            "Phase 0: %d loaded, %d failed",
            len(self._contexts), len(failed),
        )

    def _load_contexts(self, atom_ids: list[str]) -> None:
        for atom_id in atom_ids:
            if atom_id not in self._contexts:
                ctx = _build_atom_context(atom_id)
                if ctx:
                    self._contexts[atom_id] = ctx

    # -- Phase 1: Enrichment (batch) ---

    def _run_phase_1(self) -> None:
        if is_phase_completed(self._state, "phase_1"):
            self._reload_enrichments()
            return

        logger.info("Phase 1: Enrichment for all atoms")
        reqs = [build_enrichment_request(c, self._model) for c in self._contexts.values()]
        if not reqs:
            update_phase(self._state, "phase_1", self._ckpt_path, status="completed", request_count=0)
            return
        self._enrichments = process_enrichment_responses(self._submit_and_wait("phase_1", reqs))
        for aid, enr in self._enrichments.items():
            save_checkpoint(QUESTION_GENERATION_DIR / aid, 1, "enrichment", {
                "has_enrichment": enr is not None,
                "enrichment_data": enr.model_dump() if enr else None,
            })
        update_phase(self._state, "phase_1", self._ckpt_path, status="completed")

    def _reload_enrichments(self) -> None:
        for aid in get_active_atoms(self._state):
            if aid not in self._enrichments:
                ckpt = load_checkpoint(
                    QUESTION_GENERATION_DIR / aid, 1, "enrichment",
                )
                data = (ckpt or {}).get("enrichment_data")
                self._enrichments[aid] = (
                    AtomEnrichment.model_validate(data)
                    if data else None
                )

    # -- Phases 2-3: Plan + Validation ---

    def _run_phase_2_3(self) -> None:
        if is_phase_completed(self._state, "phase_3"):
            self._reload_plans()
            return

        if not is_phase_completed(self._state, "phase_2"):
            self._run_phase_2()
        else:
            self._reload_plans()

        self._run_phase_3_validation()

    def _run_phase_2(self) -> None:
        logger.info("Phase 2: Plan generation for all atoms")
        reqs: list[BatchRequest] = []
        for aid in get_active_atoms(self._state):
            ctx = self._contexts.get(aid)
            if ctx:
                reqs.append(build_plan_request(ctx, self._enrichments.get(aid), self._distribution, self._model))
        if not reqs:
            update_phase(self._state, "phase_2", self._ckpt_path, status="completed", request_count=0)
            return
        plans, failures = process_plan_responses(self._submit_and_wait("phase_2", reqs))
        self._plans = plans
        if failures:
            mark_atoms_failed(self._state, failures, self._ckpt_path)
        update_phase(self._state, "phase_2", self._ckpt_path, status="completed")

    def _run_phase_3_validation(self) -> None:
        logger.info("Phase 3: Validating plans")
        failed: dict[str, str] = {}
        for atom_id, slots in list(self._plans.items()):
            ctx = self._contexts.get(atom_id)
            if not ctx:
                continue
            result = validate_plan(
                slots, ctx, self._distribution,
            )
            if not result.success:
                failed[atom_id] = "; ".join(result.errors)
            else:
                out_dir = QUESTION_GENERATION_DIR / atom_id
                save_checkpoint(out_dir, 3, "plan", {
                    "slots": [s.model_dump() for s in slots],
                })

        if failed:
            for aid in failed:
                self._plans.pop(aid, None)
            mark_atoms_failed(
                self._state, failed, self._ckpt_path,
            )
        update_phase(
            self._state, "phase_3", self._ckpt_path,
            status="completed",
        )

    def _reload_plans(self) -> None:
        for aid in get_active_atoms(self._state):
            if aid not in self._plans:
                ckpt = load_checkpoint(
                    QUESTION_GENERATION_DIR / aid, 3, "plan",
                )
                if ckpt and ckpt.get("slots"):
                    self._plans[aid] = [
                        PlanSlot.model_validate(s)
                        for s in ckpt["slots"]
                    ]

    # -- Phase 4: Generation (batch, multi-round XSD retry) ---

    def _run_phase_4(self) -> None:
        if is_phase_completed(self._state, "phase_4"):
            self._reload_items(4, "generation")
            return

        logger.info("Phase 4: Generating items for all atoms")
        for atom_id in get_active_atoms(self._state):
            ctx = self._contexts.get(atom_id)
            enr = self._enrichments.get(atom_id)
            if ctx:
                self._context_sections[atom_id] = (
                    build_context_section(ctx, enr)
                )

        slot_maps: dict[str, dict[int, PlanSlot]] = {}
        requests: list[BatchRequest] = []
        for atom_id, slots in self._plans.items():
            ctx_section = self._context_sections.get(atom_id, "")
            slot_map = {s.slot_index: s for s in slots}
            slot_maps[atom_id] = slot_map
            for slot in slots:
                requests.append(build_generation_request(
                    slot, ctx_section, atom_id, self._model,
                ))

        if not requests:
            update_phase(
                self._state, "phase_4", self._ckpt_path,
                status="completed", request_count=0,
            )
            return

        responses = self._submit_and_wait("phase_4", requests)
        succeeded, xsd_failed = process_generation_responses(
            responses, slot_maps,
        )
        self._items = succeeded

        for rnd in range(1, _MAX_XSD_RETRY_ROUNDS + 1):
            total_retry = sum(
                len(s) for s in xsd_failed.values()
            )
            if total_retry == 0:
                break
            logger.info(
                "Phase 4 XSD retry round %d: %d slots",
                rnd, total_retry,
            )
            retry_reqs = build_xsd_retry_requests(
                xsd_failed, self._context_sections,
                {}, rnd, self._model,
            )
            if not retry_reqs:
                break
            retry_resp = self._submit_and_wait(
                f"phase_4_r{rnd}", retry_reqs,
            )
            new_ok, xsd_failed = process_generation_responses(
                retry_resp, slot_maps,
            )
            for aid, items in new_ok.items():
                self._items.setdefault(aid, []).extend(items)

        for atom_id, items in self._items.items():
            out_dir = QUESTION_GENERATION_DIR / atom_id
            save_checkpoint(out_dir, 4, "generation", {
                "item_count": len(items),
                "items": serialize_items(items),
            })

        update_phase(
            self._state, "phase_4", self._ckpt_path,
            status="completed",
        )

    # -- Batch submission lifecycle (5-state checkpoint) ---

    def _submit_and_wait(
        self,
        phase_key: str,
        requests: list[BatchRequest],
    ) -> list[BatchResponse]:
        """Execute the full 5-state batch lifecycle for one phase."""
        p = get_phase(self._state, phase_key)
        st = p.get("status", "pending")
        meta = {"job_id": self._job_id, "phase": phase_key}

        if st == "pending":
            jp = self._batch_dir / f"{phase_key}_input.jsonl"
            jp, sha = self._submitter.write_jsonl(requests, jp)
            update_phase(
                self._state, phase_key, self._ckpt_path,
                input_jsonl=str(jp), jsonl_sha256=sha,
                request_count=len(requests),
            )
            fid = self._submitter.upload_file(jp)
            update_phase(
                self._state, phase_key, self._ckpt_path,
                status="file_uploaded", file_id=fid,
            )
            st = "file_uploaded"

        if st == "file_uploaded":
            fid = p.get("file_id", "")
            orph = self._submitter.find_orphan_batch(
                file_id=fid, metadata_match=meta,
            )
            bid = orph["id"] if orph else (
                self._submitter.create_batch(fid, meta)
            )
            if orph:
                logger.info("Re-attached orphan batch %s", bid)
            update_phase(
                self._state, phase_key, self._ckpt_path,
                status="submitted", batch_id=bid, metadata=meta,
            )
            st = "submitted"

        if st == "submitted":
            bid = p.get("batch_id", "")
            obj = self._submitter.poll_until_done(bid)
            if obj.get("status") != "completed":
                efid = obj.get("error_file_id")
                msg = f"Batch {bid}: {obj.get('status')}"
                if efid:
                    ep = self._batch_dir / f"{phase_key}_errors.jsonl"
                    self._submitter.download_file(efid, ep)
                    msg += f" (errors: {ep})"
                raise RuntimeError(msg)
            ofid = obj.get("output_file_id", "")
            rp = self._batch_dir / f"{phase_key}_results.jsonl"
            self._submitter.download_file(ofid, rp)
            update_phase(
                self._state, phase_key, self._ckpt_path,
                status="results_downloaded", results_jsonl=str(rp),
            )

        rp = Path(p.get("results_jsonl", ""))
        resp = self._submitter.parse_results_file(rp)
        exp = p.get("request_count", 0)
        if len(resp) < exp:
            logger.warning(
                "%s: %d/%d results", phase_key, len(resp), exp,
            )
        return resp

    def _reload_items(
        self, phase_num: int, phase_name: str,
    ) -> None:
        from app.question_generation.helpers import deserialize_items
        for atom_id in get_active_atoms(self._state):
            if atom_id in self._items:
                continue
            out_dir = QUESTION_GENERATION_DIR / atom_id
            ckpt = load_checkpoint(out_dir, phase_num, phase_name)
            if ckpt and ckpt.get("items"):
                self._items[atom_id] = deserialize_items(
                    ckpt["items"],
                )

    def _build_summary(self) -> dict[str, Any]:
        total = sum(len(v) for v in self._items.values())
        return {
            "job_id": self._job_id,
            "total_atoms": (
                len(self._state.get("active_atom_ids", []))
                + len(self._state.get("failed_atoms", {}))
            ),
            "active_atoms": len(get_active_atoms(self._state)),
            "failed_atoms": dict(
                self._state.get("failed_atoms", {}),
            ),
            "total_final_items": total,
            "items_per_atom": {
                a: len(v) for a, v in self._items.items()
            },
        }


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _build_atom_context(atom_id: str) -> AtomContext | None:
    """Load an atom and its exemplars into an AtomContext."""
    atom = load_atom(atom_id)
    if not atom:
        return None
    exs = load_exemplars_for_atom(atom_id)
    return AtomContext(
        atom_id=atom.id,
        atom_title=atom.titulo,
        atom_description=atom.descripcion,
        eje=atom.eje,
        standard_ids=atom.standard_ids,
        tipo_atomico=atom.tipo_atomico,
        criterios_atomicos=atom.criterios_atomicos,
        ejemplos_conceptuales=atom.ejemplos_conceptuales,
        notas_alcance=atom.notas_alcance,
        exemplars=exs,
    )
