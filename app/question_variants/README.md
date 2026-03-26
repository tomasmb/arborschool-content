# Question Variants Pipeline

Pipeline for generating hard PAES variants from official source questions.

## Stack

All LLM phases use **OpenAI gpt-5.1** via the **Batch API** (50% cost discount).
Image generation is a separate post-step using Gemini (not part of this pipeline).

## Architecture

```text
Phase 1: Plan     (Batch API, 1 req per source question)
Phase 2: Generate (Batch API, 1 req per blueprint/variant)
Phase 3: Postprocess + deterministic checks (local, no LLM)
Phase 4: Validate (Batch API, simplified 3-gate LLM validation)
```

Each phase checkpoints to `.batch_runs/{job_id}/batch_state.json`.
Resume with `--job-id <id>` to skip completed phases.

## Validation gates

**Deterministic** (no LLM cost):
1. Valid XML
2. Choice interaction integrity (QTI wiring)
3. Visual completeness (mentions figure → must exist)

**LLM semantic** (3 essential gates):
1. `respuesta_correcta` — is the marked answer mathematically correct?
2. `concepto_alineado` — does it test the same concept?
3. `es_diferente` — is it genuinely different from the original?

## Package structure

- `contracts/`: construct-contract inference, family catalog, prompt rules.
- `io/`: source loading, artifact persistence.
- `postprocess/`: generation parsing, presentation normalization, family-specific repairs.
- `pipeline.py`: orchestration (BatchVariantPipeline + SyncVariantPipeline).
- `pipeline_helpers.py`: shared postprocessing, dedup, checkpoint helpers.
- `batch_request_builders.py`: builds BatchRequest objects for each phase.
- `batch_response_processors.py`: parses BatchResponse objects back to domain models.
- `variant_planner.py`: blueprint planning (prompt + sync class).
- `variant_generator.py`: QTI generation (prompt + sync class).
- `variant_validator.py`: deterministic checks + LLM validation (prompt + sync class).
- `llm_service.py`: OpenAI/Gemini adapter for sync mode only.
- `run_variant_generation.py`: CLI entrypoint.

## CLI usage

```bash
# Full batch run (default)
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

| Phase    | Requests | Cost (Batch API) |
|----------|----------|------------------|
| Plan     | 202      | ~$5              |
| Generate | 2,020    | ~$83             |
| Validate | ~1,800   | ~$28             |
| **Total**|          | **~$116**        |
