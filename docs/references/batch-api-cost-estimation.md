# Batch API Question Generation — Cost Estimation

Reference for estimating costs when running the batch question generation
pipeline via the OpenAI Batch API (`run_batch_api_generation.py`).

## Model and pricing

| | Standard | Batch API (50% off) |
|-|----------|---------------------|
| **Model** | gpt-5.1 | gpt-5.1 |
| **Input** | $1.25 / 1M tokens | $0.625 / 1M tokens |
| **Output** | $10.00 / 1M tokens | $5.00 / 1M tokens |

> Output tokens include **reasoning (thinking) tokens**, which are billed
> at the same rate as visible output. The reasoning overhead depends on the
> `reasoning_effort` setting per phase.

## Pipeline phases and reasoning effort

| Phase | Description | Reasoning | Calls per atom |
|-------|-------------|-----------|---------------:|
| P0 | Load inputs | local | 0 |
| P1 | Enrichment | `low` | 1 |
| P2 | Plan generation | `medium` | 1 |
| P3 | Plan validation | local | 0 |
| P4 | QTI generation | `medium` | 62 (slots) |
| P5 | Deduplication | local | 0 |
| P6 | Solvability check | `medium` | ~56 (post-dedup) |
| P7 | Enhancement | `low` | ~56 |
| P8 | Review + correction | none / `low` | ~56 + retries |
| P9 | Final validation | `medium` | ~53 |

**Slots per atom:** 62 (19 Easy + 24 Medium + 19 Hard, after 1.3x buffer).

**Reasoning token overhead estimates:**

- `low` → reasoning tokens ≈ 0.3–1x visible output (total billed: 1.3–2x)
- `medium` → reasoning tokens ≈ 1–3x visible output (total billed: 2–4x)
- `none` (temperature mode) → no reasoning tokens (total billed: 1x)

## Per-atom token breakdown

| Phase | Min input | Max input | Min output (billed) | Max output (billed) |
|-------|----------:|----------:|--------------------:|--------------------:|
| P1 Enrichment | 2K | 4.5K | 1K | 4K |
| P2 Plan | 2K | 4K | 3K | 14K |
| P4 Generation | 124K | 279K | 99K | 446K |
| P4 XSD retries | 0 | 60K | 0 | 86K |
| P6 Solvability | 80K | 148K | 32K | 142K |
| P7 Enhancement | 106K | 177K | 69K | 236K |
| P8 Review + corr. | 80K | 346K | 16K | 57K |
| P9 Final valid. | 75K | 138K | 30K | 132K |
| **Per-atom total** | **~469K** | **~1,156K** | **~250K** | **~1,262K** |

## Per-atom cost range (Batch API)

| | Min | Max |
|-|----:|----:|
| Input cost | $0.29 | $0.72 |
| Output cost | $1.25 | $6.31 |
| **Total** | **$1.54** | **$7.03** |

## Sensitivity table

| Atoms | Absolute min | Realistic range | Absolute max |
|------:|-------------:|----------------:|-------------:|
| 1 | $1.54 | $3 – $5 | $7.03 |
| 50 | $77 | $130 – $210 | $352 |
| 200 | $308 | $520 – $840 | $1,406 |

## Without Batch API (synchronous pipeline)

The synchronous pipeline (`run_batch_generation.py`) uses the same model at
standard pricing — exactly **2x** the Batch API cost:

| Atoms | Realistic range (sync) |
|------:|-----------------------:|
| 1 | $6 – $10 |
| 50 | $260 – $420 |
| 200 | $1,040 – $1,680 |

## Key cost drivers

1. **Phase 4 (generation)** — 62 calls per atom at `medium` reasoning.
   This single phase accounts for ~40-50% of total cost.
2. **Reasoning tokens** — `medium` effort phases (P4, P6, P9) generate
   2–4x the visible output in thinking tokens, roughly doubling the
   naive output-only estimate.
3. **Phase 7-8 (feedback loop)** — enhancement + review + correction
   can add 20-30% depending on review failure rate.

## CLI command

```bash
# 50 atoms, skip images, verbose logging
python -m app.question_generation.scripts.run_batch_api_generation \
  --skip-images \
  --max-atoms 50 \
  --poll-interval 30 \
  -v

# Resume an interrupted run
python -m app.question_generation.scripts.run_batch_api_generation \
  --job-id <JOB_ID>
```

## Safety guarantees

The batch pipeline uses a **5-state checkpoint lifecycle** per phase:

```
pending → file_uploaded → submitted → results_downloaded → completed
```

- All state writes are **atomic** (temp file + rename).
- **Orphan batch recovery** re-attaches to in-flight OpenAI batches
  by matching `file_id` or metadata on resume.
- Per-atom checkpoints are saved after each phase completes.
- **No API spend is ever lost** — any crash is fully recoverable
  via `--job-id`.
- macOS `caffeinate` integration prevents sleep during polling.
