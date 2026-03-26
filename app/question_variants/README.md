# Question Variants Pipeline

Pipeline for generating hard PAES variants from official source questions.

## Stack

All LLM phases use **OpenAI gpt-5.1** via the **Batch API** (50% cost discount).
Phase 6 (feedback enrichment) defaults to **gpt-5.4** via sync calls.
Image generation is a separate post-step using Gemini (not part of this pipeline).

## Architecture (v3.0)

```text
Phase 1: Plan        (Batch API, 1 req per source question)
Phase 2: Generate    (Batch API, 1 req per blueprint/variant)
Phase 3: Postprocess + deterministic checks (local, no LLM)
Phase 4: Validate    (Batch API, simplified 3-gate LLM validation)
Phase 5: Solvability (Batch API, independent solve + compare)
Phase 6: Enrichment  (Sync parallel, feedback pipeline: enhance + review + correct)
Phase 7: Final Valid. (Batch API, comprehensive 5-check validation)
```

Phases 5-7 can be skipped with `--skip-enrichment` for quick iterations.
Each phase checkpoints to `.batch_runs/{job_id}/batch_state.json`.
Resume with `--job-id <id>` to skip completed phases.

Checkpoint keys: `phase_1_plan`, `phase_2_generate`, `phase_4_validate`,
`phase_5_solvability`, `phase_6_enrichment`, `phase_7_final_validate`.

## Validation gates

**Deterministic** (Phase 3, no LLM cost):
1. Valid XML (parse check)
2. XSD schema validation
3. PAES structure (4 choices, correct response declaration)
4. Choice interaction integrity (QTI wiring)
5. Visual completeness (mentions figure → must exist)

**LLM semantic** (Phase 4, 3 essential gates):
1. `respuesta_correcta` — is the marked answer mathematically correct?
2. `concepto_alineado` — does it test the same concept?
3. `es_diferente` — is it genuinely different from the original?

**Solvability** (Phase 5): Model independently solves the question;
its answer must match the declared correct option.

**Feedback enrichment** (Phase 6): Full feedback pipeline (enhance,
XSD validate, review, correction loop up to 2 retries).

**Final validation** (Phase 7, 5 checks):
1. Correct answer verification
2. Feedback quality review
3. Content quality (typos, characters, clarity)
4. Image references (if applicable)
5. Math validity

## Package structure

- `contracts/`: construct-contract inference, family catalog, prompt rules.
- `io/`: source loading, artifact persistence.
- `postprocess/`: generation parsing, presentation normalization, family-specific repairs.
- `pipeline.py`: orchestration (BatchVariantPipeline + SyncVariantPipeline).
- `pipeline_helpers.py`: shared postprocessing, dedup, checkpoint helpers.
- `quality_phases.py`: phases 5-7 runners (sync + batch).
- `batch_request_builders.py`: builds BatchRequest objects for each phase.
- `batch_response_processors.py`: parses BatchResponse objects back to domain models.
- `variant_planner.py`: blueprint planning (prompt + sync class).
- `variant_generator.py`: QTI generation (prompt + sync class).
- `variant_validator.py`: deterministic checks + LLM validation (prompt + sync class).
- `variant_solvability.py`: solvability gate (Phase 5).
- `variant_enrichment.py`: parallel feedback enrichment (Phase 6).
- `llm_service.py`: OpenAI/Gemini adapter for sync mode only.
- `run_variant_generation.py`: CLI entrypoint.

## CLI usage

```bash
# Full batch run (default, all 7 phases)
python -m app.question_variants.run_variant_generation \
    --source-test "prueba-invierno-2025" \
    --variants-per-question 10

# Sync debug / pilot (no Batch API)
python -m app.question_variants.run_variant_generation \
    --source-test "prueba-invierno-2025" \
    --questions "Q1,Q11,Q12" \
    --variants-per-question 3 \
    --no-batch

# Resume a previous batch run
python -m app.question_variants.run_variant_generation \
    --source-test "prueba-invierno-2025" \
    --job-id "abc123"

# Phases 1-4 only (skip solvability, enrichment, final validation)
python -m app.question_variants.run_variant_generation \
    --source-test "prueba-invierno-2025" \
    --skip-enrichment

# Custom enrichment model
python -m app.question_variants.run_variant_generation \
    --source-test "prueba-invierno-2025" \
    --enrichment-model "gpt-5.1"
```

## Artifact layout

Each run under `app/data/pruebas/hard_variants/` is organized as:

```text
[test]/
  [question]/
    source/
    variants/
```

`source/` keeps the original item snapshot and `construct_contract.json`.
`variants/` keeps planning artifacts, approved/rejected variants and
`generation_report.json`.

## Cost estimate (full run)

All phases use `reasoning_effort="medium"`. Reasoning tokens are billed
as output tokens. Estimates include reasoning overhead.

| Phase        | Requests | Cost (Batch API) |
|--------------|----------|------------------|
| Plan         | 202      | ~$5              |
| Generate     | 2,020    | ~$83             |
| Validate     | ~1,800   | ~$28             |
| Solvability  | ~1,500   | ~$20             |
| Enrichment   | ~1,200   | ~$50 (sync)      |
| Final Valid.  | ~1,000   | ~$15             |
| **Total**    |          | **~$201**        |

## Batch vs Sync comparison

| Phase | Batch mode | Sync mode |
|-------|-----------|-----------|
| 1-Plan | Batch API | Sync LLM call |
| 2-Generate | Batch API | Sync LLM call |
| 3-Postprocess | Local | Local |
| 4-Validate | Batch API | Sync LLM call |
| 5-Solvability | Batch API | Sync LLM call |
| 6-Enrichment | Sync parallel (ThreadPool) | Sync parallel (ThreadPool) |
| 7-Final Valid. | Batch API | Sync LLM call |
