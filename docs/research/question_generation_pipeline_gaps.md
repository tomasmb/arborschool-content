# Question Generation Pipeline -- Gap Analysis & Remaining Work

Status: **All gaps resolved. Pending real-data testing + prompt tuning.**
Date: 2026-02-11 (updated)

This document lists every known gap, required change, and missing feature
in `app/question_generation/` before the pipeline is ready for real use.

---

## 1. ~~LLM Client: Switch from Gemini to GPT-5.1~~ DONE

**Priority: HIGH -- affects 3 files** -- Completed 2026-02-11

The pipeline was built using `GeminiService` for Phases 1, 2, and 4.
Per project decision, **all text generation must use GPT-5.1** via
`OpenAIClient`. Gemini should only be used for image generation.

### Files to change

| File | Current client | Required client | Reasoning effort |
|---|---|---|---|
| `enricher.py` | `GeminiService` | `OpenAIClient` | `"low"` -- structured JSON output, not deep reasoning |
| `planner.py` | `GeminiService` | `OpenAIClient` | `"medium"` -- needs pedagogical reasoning for plan diversity |
| `generator.py` | `GeminiService` | `OpenAIClient` | `"medium"` -- needs math reasoning to build valid QTI |
| `validators.py` | `GeminiService` (injected, unused) | `OpenAIClient` | `"high"` -- independent solve requires strong reasoning |
| `pipeline.py` | Injects `GeminiService` into all components | Should inject `OpenAIClient` | N/A (orchestrator) |

### What needs to happen

1. Replace `GeminiService` imports with `OpenAIClient` / `load_default_openai_client`
   in `enricher.py`, `planner.py`, `generator.py`, `validators.py`.
2. Update `pipeline.py` constructor to create an `OpenAIClient` instead of
   `GeminiService` and pass it to all components.
3. Set appropriate `reasoning_effort` per phase (see table above).
4. Replace `response_mime_type="application/json"` with the OpenAI equivalent
   (`response_format={"type": "json_object"}` -- already handled inside
   `OpenAIClient.generate_text` when `response_mime_type="application/json"`).
5. Remove `temperature` parameter from calls where `reasoning_effort != "none"`
   (GPT-5.1 rejects temperature when reasoning is active).

### Reference implementation

`app/question_feedback/enhancer.py` lines 69-70 show the correct pattern:

```python
_ENHANCE_REASONING = "low"
# ...
response_text = self._client.call_with_images(
    prompt, images, reasoning_effort=_ENHANCE_REASONING, max_tokens=8000,
)
```

---

## 2. ~~Solvability Check (Phase 6)~~ DONE

**Priority: HIGH -- spec-required validation missing** -- Completed 2026-02-11

The spec (section 8, Phase 6) requires:
> "Solvability: independent solve matches declared correct option"

Currently `BaseValidator._validate_single()` only runs:
- XSD validation
- PAES structural compliance (4 options, 1 correct)
- Exemplar non-copy check

**Missing**: An LLM call that independently solves each question and
verifies the answer matches the declared correct option. This is
critical -- without it, items with wrong answers can pass through.

### What needs to happen

1. Add a `_check_solvability()` method to `BaseValidator` that:
   - Sends the QTI XML to GPT-5.1 with `reasoning_effort="high"`
   - Asks the model to solve the problem step-by-step
   - Compares the model's answer to the declared correct option
   - Returns pass/fail with the model's calculation steps
2. Wire it into `_validate_single()` between the XSD check and
   the exemplar check.
3. Store the solve result in `pipeline_meta.validators.solve_check`.

### Reasoning effort

Must be `"high"` -- this is the most important validation step and
requires genuine mathematical reasoning.

---

## 3. ~~Image Generation~~ DONE

**Priority: HIGH** -- Completed 2026-02-11

Full image generation pipeline built with two-level decision making
(atom-level type tagging + per-question image decisions).

### What was built

1. **`image_types.py`**: Rich `ImageTypeSpec` dataclass taxonomy with
   12+ image types (function graphs, geometric figures, statistical
   charts, etc.). Each type has `name_es`, `description`, `examples`,
   `when_to_use`, and `generatable` flag. `build_image_type_catalog()`
   formats the taxonomy for LLM prompt injection.

2. **`image_generator.py`**: `ImageGenerator` class orchestrating
   Phase 4b -- uses GPT-5.1 for detailed image descriptions, Gemini
   (`GeminiImageClient`) for image generation, S3 for upload, and
   embeds URLs into QTI XML. Excludes failed items gracefully.

3. **`prompts/image_generation.py`**: Separated prompts --
   `IMAGE_DESCRIPTION_PROMPT` (GPT-5.1, what to draw) and
   `GEMINI_IMAGE_GENERATION_PROMPT` (visual style rules).

4. **Model extensions**:
   - `AtomEnrichment.required_image_types: list[str]` -- atom-level
     image type tagging during Phase 1 enrichment.
   - `PlanSlot.image_required`, `.image_type`, `.image_description`
     -- per-question image decisions during Phase 2 planning.

5. **Generatability gate**: Pipeline blocks QTI generation if an atom
   requires image types that cannot be generated (only Gemini-generated
   types are supported; programmatic SVG / image bank excluded).

6. **`GeminiImageClient`** added to `app/llm_clients.py` for native
   Gemini image generation.

7. **Enrichment + planning prompts** updated to inject the full image
   type catalog and `NOT_IMAGES_DESCRIPTION` (tables/data are HTML,
   not images).

---

## 4. ~~Near-Duplicate Detection (Phase 5)~~ DONE

**Priority: MEDIUM** -- Completed 2026-02-11

Current implementation uses SHA-256 fingerprinting on normalized XML.
This catches exact duplicates but NOT:

- Commuted option order (A/B/C/D rearranged)
- Trivial numeric perturbations (5 changed to 6, same structure)
- Same mathematical structure with different variable names

### What was built

1. **Option order normalization**: `_sort_choices()` sorts
   `<qti-simple-choice>` blocks alphabetically before hashing,
   so commuted option order produces the same fingerprint.
2. **Plan skeleton cap**: `is_skeleton_near_duplicate()` limits items
   per planner-assigned `operation_skeleton_ast` to 2 per pool.
3. **QTI structural skeleton**: `extract_qti_skeleton()` derives a
   structural pattern from the actual generated QTI XML (numbers
   replaced with `N`, tags stripped, normalized). `DuplicateGate`
   caps items sharing the same QTI skeleton at 2, catching items
   with identical mathematical structure but different numbers.
4. **Numeric signature**: `compute_numeric_signature()` hashes the
   sorted numeric values from QTI content, available for distance
   comparisons.

LLM-based similarity for borderline cases deferred to prompt-tuning
phase (gap #8) -- the structural checks cover the most common cases.

---

## 5. ~~Exemplar Distance Checking~~ DONE

**Priority: MEDIUM** -- Completed 2026-02-11

Current `_check_exemplar_copy()` only detects identical fingerprints.
The spec (section 3.2) requires items to be "sufficiently far" from
exemplars -- not just non-identical.

### What was built

`check_exemplar_distance()` now enforces graduated thresholds
based on `distance_level` from `PlanSlot`:

- **"near"**: reject only identical fingerprints (lenient -- item
  should resemble the exemplar in style, just not be a copy).
- **"medium"**: also reject items with the same QTI structural
  skeleton (numbers replaced with N, via `is_qti_structurally_similar`).
- **"far"**: also reject items sharing the same numeric signature
  (via `compute_numeric_signature`), ensuring genuine difference.
- **None/unset**: behaves like "near" for backward compatibility.

LLM-based comparison for nuanced cases deferred to prompt-tuning
phase (gap #8).

---

## 6. ~~`question_set_id` Not Populated in DB Sync~~ DONE

**Priority: MEDIUM** -- Completed 2026-02-11

When syncing to DB, `QuestionRow.question_set_id` is not set. This
field links questions to their atom's question set, which is needed
for the PP100 adaptive algorithm to serve questions correctly.

### What needs to happen

1. Before sync, look up or create the `question_set` record for the
   atom in the DB.
2. Set `question_set_id` on each `QuestionRow` to link items to the
   atom's question set.
3. May require a new `upsert_question_sets()` method in `DBClient`
   or a pre-sync step.

---

## 7. ~~Pipeline Resume Support~~ DONE

**Priority: LOW** -- Completed 2026-02-11

The pipeline saves results to disk after completion, but cannot
resume from a failed phase. If Phase 7 fails after Phase 4 generated
good items, the entire pipeline must re-run from scratch.

### What was built

1. **Checkpoints**: `save_checkpoint()` persists phase results to
   disk after each phase completes (phases 1, 3, 4, 6, 8).
2. **Checkpoint loading**: `load_checkpoint()` and `load_phase_state()`
   reconstruct enrichment, plan slots, and items from disk.
3. **`--resume` flag**: CLI flag in `run_generation.py`, stored in
   `PipelineConfig.resume`.
4. **Auto-skip in `pipeline.py`**: When `--resume` and `--phase all`,
   `find_resume_phase_group()` scans checkpoints, finds the highest
   completed phase, and sets `start` to the next phase group.
   Prerequisites are validated and prior state is loaded from
   checkpoints before the resumed phase begins.
5. **Per-phase resume**: Running a specific phase group (e.g.
   `--phase plan`) already checks prerequisites and loads state.

---

## 8. Prompt Tuning -- Untested Against Real Data

**Priority: LOW (but will become HIGH on first real run)**

All prompts in `prompts/enrichment.py`, `prompts/planning.py`, and
`prompts/generation.py` are written to spec but have not been tested
against real atom data with a real LLM. They will likely need
iterative refinement based on actual output quality.

### Key risks

- JSON parsing failures if the model doesn't respect the schema
- QTI XML structural issues (missing namespaces, malformed MathML)
- Plan diversity issues (model may not produce sufficiently varied
  skeletons)
- Difficulty calibration (model's "easy" may not match PAES "easy")

---

## 9. ~~Frontend: Question Generation Page~~ DONE

**Priority: HIGH** -- Completed 2026-02-11

No frontend existed to trigger or monitor question generation.

### What was built

1. **New route**: `frontend/app/courses/[id]/question-generation/page.tsx`
2. **OverviewTab**: Summary stats (total atoms, generated count, pending),
   progress bar, clickable atom list with cross-tab navigation.
3. **GenerationTab**: Filterable atom table (All / Pending / Generated) with
   per-atom Generate or Regenerate buttons. Expandable rows show individual
   phase controls (Enrich, Plan, Generate QTI, Validate, Feedback, Finalize).
4. **ResultsTab**: Atoms grouped by eje, question counts, per-atom
   Regenerate action on hover.
5. **QuestionGenTabs**: Tab navigation with status badges.
6. **Confirmation modal**: `GeneratePipelineModal` updated with a
   "Run Configuration" summary showing atom name + phase before cost
   estimate and confirm.

---

## 10. ~~API + CLI: Pipeline Registration & Phase Groups~~ DONE

**Priority: HIGH** -- Completed 2026-02-11

The question generation pipeline was not registered as a runnable
pipeline in the API, and the CLI had no way to run individual phases.

### What was built

1. **`api/services/pipeline_definitions.py`**: Registered `question_gen`
   with params `atom_id`, `phase`, `pool_size`, `dry_run`.
2. **`api/services/pipeline_runner.py`**: Added `_cmd_question_gen()`
   command builder and registered it in `_build_command()` dispatcher.
   Added `question_gen` to `resumable_pipelines`.
3. **`app/question_generation/scripts/run_generation.py`**: Added
   `--phase` flag (choices: enrich, plan, generate, validate, feedback,
   finalize, all) and `--resume` flag.
4. **`app/question_generation/models.py`**: Added `PHASE_GROUPS` dict
   and `PHASE_GROUP_CHOICES` list. Added `phase` field to
   `PipelineConfig`.
5. **`app/question_generation/pipeline.py`**: `run()` respects phase
   group boundaries, loading checkpoints for prior phases.

---

## 11. ~~Sequential Phase Enforcement + Frontend Gating~~ DONE

**Priority: MEDIUM** -- Completed 2026-02-11

Pipeline phases were not enforced as sequential -- any phase could be
run regardless of whether its prerequisites had completed.

### What was built

1. **`PHASE_PREREQUISITES`** mapping in `helpers.py`: defines which
   checkpoint files must exist before each phase group can run.
2. **`check_prerequisites()`**: validates required checkpoints exist
   on disk before allowing a phase to start.
3. **`load_phase_state()`**: loads `AtomEnrichment`, `list[PlanSlot]`,
   or `list[GeneratedItem]` from checkpoint files when resuming.
4. **`get_last_completed_phase()`**: scans checkpoint directory and
   returns the highest phase number, exposed via the atoms API as
   `AtomBrief.last_completed_phase`.
5. **Frontend phase gating**: `PhaseControls` in `GenerationTab.tsx`
   disables buttons whose prerequisite phase hasn't completed. Shows
   a lock icon and "Complete the previous phase first" tooltip.
   "Enrich" (phase 1) is always enabled.

---

## Summary: Prioritized Work Items

| # | Item | Priority | Effort | Status |
|---|---|---|---|---|
| 1 | Switch LLM from Gemini to GPT-5.1 | HIGH | Small | DONE |
| 2 | Implement solvability check (Phase 6) | HIGH | Medium | DONE |
| 3 | Build image generation module | HIGH | Large | DONE |
| 4 | Improve near-duplicate detection (QTI skeleton) | MEDIUM | Medium | DONE |
| 5 | Exemplar distance with distance_level thresholds | MEDIUM | Medium | DONE |
| 6 | Populate question_set_id in sync | MEDIUM | Small | DONE |
| 7 | Pipeline resume (--resume wired to pipeline.py) | LOW | Medium | DONE |
| 8 | Prompt tuning after real testing | LOW | Ongoing | Pending (iterative) |
| 9 | Frontend: question generation page | HIGH | Large | DONE |
| 10 | API + CLI: pipeline registration & phases | HIGH | Medium | DONE |
| 11 | Sequential phase enforcement + frontend gating | MEDIUM | Medium | DONE |
