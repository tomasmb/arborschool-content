# Question Variants Pipeline

Pipeline for generating hard PAES variants from official source questions.

## Package structure

- `contracts/`: construct-contract inference, family catalog, prompt rules, guardrails.
- `io/`: source loading, artifact persistence, provider/network preflight.
- `postprocess/`: generation parsing, presentation normalization, family-specific repairs.
- `pipeline.py`: orchestration across loading, planning, generation, postprocess, validation and persistence.
- `variant_planner.py`: blueprint planning for non-mechanizable variants.
- `variant_generator.py`: QTI generation from source + blueprint.
- `variant_validator.py`: deterministic gates + semantic validation.
- `run_variant_generation.py`: CLI entrypoint.

## Core design

1. Build a `construct_contract` from the official source item.
2. Plan variants that preserve construct, difficulty band and evidence mode.
3. Generate one variant per LLM call.
4. Normalize presentation and apply family-specific repairs.
5. Validate with deterministic gates first, then semantic LLM validation.
6. Persist source snapshots, plans, approved/rejected variants and reports.

## Canonical stack

- Planning: Gemini
- Generation: Gemini
- Semantic gate: OpenAI `gpt-5.4`

Those are the intended defaults for the hard-variants pipeline. Debugging runs may override them explicitly from the CLI.

## Artifact layout

Each run under `app/data/pruebas/hard_variants/` is organized as:

```text
[test]/
  [question]/
    source/
    variants/
```

`source/` keeps the original item snapshot and `construct_contract.json`.
`variants/` keeps planning artifacts, approved/rejected variants and `generation_report.json`.

## Local audits

- `python -m app.question_variants.audit_contract_coverage`
  verifies that the family catalog resolves official finalized questions.
- `python -m app.question_variants.run_structural_regressions`
  runs deterministic structural regressions on curated approved/rejected artifacts,
  without calling external providers.
