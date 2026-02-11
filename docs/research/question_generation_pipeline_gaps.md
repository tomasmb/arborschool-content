# Question Generation Pipeline -- Gap Analysis & Remaining Work

Status: **Core pipeline complete, pending real-data testing.**
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

## 3. Image Generation -- Does Not Exist

**Priority: HIGH -- entire capability missing**

No image generation module exists anywhere in the codebase. Some PAES
questions require diagrams, graphs, geometric figures, or data tables
as images. Currently:

- The variant pipeline reuses images from source questions
- The feedback pipeline handles existing image URLs
- No pipeline can generate new images from scratch

### What needs to be built

1. **New module**: `app/question_generation/image_generator.py`
   - Uses Gemini (the one exception to GPT-5.1 rule) for image generation
   - Input: description of the image needed (from plan slot or generation phase)
   - Output: generated image URL (uploaded to S3) or local file path

2. **Plan slot extension**: Add an `image_required` field to `PlanSlot`
   that indicates whether the item needs a generated image, and an
   `image_description` field for the prompt.

3. **Generation phase integration**: After Phase 4 generates base QTI,
   items with `image_required=True` go through image generation before
   proceeding to Phase 5.

4. **S3 upload**: Images need to be uploaded to S3 (existing `app/sync/s3_client.py`)
   and the URL embedded in the QTI XML `<img>` tag.

### Gemini image generation details

- Model to use: needs research (Gemini's Imagen API or similar)
- Must produce clean mathematical diagrams suitable for PAES
- Must handle: coordinate planes, geometric figures, data tables,
  statistical charts, function graphs

---

## 4. ~~Near-Duplicate Detection (Phase 5)~~ DONE

**Priority: MEDIUM** -- Completed 2026-02-11

Current implementation uses SHA-256 fingerprinting on normalized XML.
This catches exact duplicates but NOT:

- Commuted option order (A/B/C/D rearranged)
- Trivial numeric perturbations (5 changed to 6, same structure)
- Same mathematical structure with different variable names

### What needs to happen

1. Normalize option order before fingerprinting (sort choices
   alphabetically or by their text content).
2. Add structural comparison that extracts the mathematical
   operation pattern and compares skeletons.
3. Consider adding an LLM-based similarity check for borderline
   cases (would use GPT-5.1 with `reasoning_effort="low"`).

---

## 5. ~~Exemplar Distance Checking~~ DONE

**Priority: MEDIUM** -- Completed 2026-02-11

Current `_check_exemplar_copy()` only detects identical fingerprints.
The spec (section 3.2) requires items to be "sufficiently far" from
exemplars -- not just non-identical.

### What needs to happen

1. Implement structural distance calculation between generated item
   and exemplar (compare operation skeletons, numeric profiles,
   context types).
2. Use the `distance_level` field from `PlanSlot` (near/medium/far)
   to set the threshold.
3. Consider using an LLM-based comparison for nuanced cases.

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

### What needs to happen

1. Save intermediate phase results to disk after each phase completes.
2. On pipeline start, check for existing phase outputs in the
   output directory.
3. Skip phases whose outputs already exist and are valid.
4. Add a `--resume` flag to the CLI.

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

## Summary: Prioritized Work Items

| # | Item | Priority | Effort | Status |
|---|---|---|---|---|
| 1 | Switch LLM from Gemini to GPT-5.1 | HIGH | Small | DONE |
| 2 | Implement solvability check (Phase 6) | HIGH | Medium | DONE |
| 3 | Build image generation module | HIGH | Large | Excluded (not in scope) |
| 4 | Improve near-duplicate detection | MEDIUM | Medium | DONE |
| 5 | Implement exemplar distance checking | MEDIUM | Medium | DONE |
| 6 | Populate question_set_id in sync | MEDIUM | Small | DONE |
| 7 | Add pipeline resume support | LOW | Medium | DONE |
| 8 | Prompt tuning after real testing | LOW | Ongoing | Excluded (iterative) |
| 9 | Frontend: question generation page | HIGH | Large | DONE |
| 10 | API + CLI: pipeline registration & phases | HIGH | Medium | DONE |
