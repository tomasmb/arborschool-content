# Prerequisite Atoms Pipeline — Handoff Guide

Owner: Dayanara
Budget: **$500 USD OpenAI** (Gemini for images is a separate budget)

---

## 0. Engineering principles (READ FIRST)

### SOLID / DRY — non-negotiable

Any code changes made during this pipeline **must** follow SOLID
and DRY principles. The M1 question generation pipeline produced
high-quality results precisely because shared components (prompts,
validators, helpers) are centralized and reused. Specific rules:

- **Do NOT duplicate logic.** If a function already exists in a
  shared module (`app/atoms/`, `app/utils/`, `app/question_generation/helpers.py`),
  import and reuse it. Never copy-paste and tweak.
- **Do NOT create parallel implementations.** If you need to extend
  existing behavior (e.g., `load_atom()`), extend the original
  function — do not create a `load_prereq_atom()` alongside it.
- **Do NOT inline rules or prompts.** All atom generation rules
  live in `app/atoms/prompts/atom_rules.py` (`ATOM_GENERATION_RULES`)
  and `app/atoms/prompts/atom_final_instruction.py`
  (`build_final_instruction()`). These are the proven, shared
  components. Import them — never duplicate or simplify them.

### Prompt consistency — why it matters

The prerequisite atoms were generated using the **exact same**
`ATOM_GENERATION_RULES` (25 rules) and `build_final_instruction()`
(20+ item checklist) as the M1 atoms. This was a deliberate fix
after an earlier run produced over-granular atoms due to "prompt
drift" — simplified inline rules that diverged from the proven
M1 prompts.

**If you modify any prompt or pipeline step:**

1. Check whether the same prompt component is shared with M1.
   If so, change the shared version (not a local copy).
2. Verify the change does not regress M1 quality by spot-checking
   a few M1 atoms through the modified pipeline.
3. Keep `reasoning_effort` settings consistent with what worked:
   `"high"` for generation, `"medium"` for validation, `"low"`
   for enrichment. Do not lower these to save cost — the quality
   difference is significant and rework costs more than the
   token savings.

### Code over documentation

If you find that documentation and code disagree, **the code is
the source of truth**. Update the docs to match the code. Never
silently change code to match outdated docs.

---

## 1. Atom inventory and priority layers

### Current state

| Metric | Count |
|--------|------:|
| Total prerequisite atoms | 1,135 |
| Reachable from M1 (via BFS) | 368 |
| Unreachable (no path to M1) | 767 |
| M1 atoms with prereq connections | 52 / 238 |

Only the **368 reachable atoms** matter for the M1 pipeline.
The 767 unreachable atoms were generated for completeness across
EB1–EM1 curricula but have no path to any M1 atom.

### BFS layers from M1

| Layer | Atoms | Grade breakdown |
|------:|------:|-----------------|
| 1 | 54 | EB3:1, EB4:4, EB5:9, EB6:8, EB7:14, EB8:14, EM1:4 |
| 2 | 91 | EB1:3, EB2:4, EB3:14, EB4:5, EB5:16, EB6:24, EB7:14, EB8:9, EM1:2 |
| 3 | 90 | EB1:12, EB2:18, EB3:12, EB4:4, EB5:17, EB6:13, EB7:6, EB8:7, EM1:1 |
| 4 | 70 | EB1:16, EB2:12, EB3:18, EB4:7, EB5:6, EB6:8, EB7:2, EB8:1 |
| 5 | 31 | EB1:13, EB2:4, EB3:10, EB4:1, EB5:2, EB6:1 |
| 6 | 17 | EB1:6, EB2:1, EB3:8, EB6:2 |
| 7 | 13 | EB1:10, EB3:3 |
| 8 | 2 | EB1:2 |

**Layer 1** = direct prerequisites of M1 atoms (highest priority).
Each subsequent layer is one step further from M1.

### Prioritization strategy

1. **Start with Layer 1** (54 atoms). These are the immediate gaps
   students hit when they can't do M1 content.
2. **Then Layer 2** (91 atoms) until budget runs out.
3. Layers 3+ have diminishing returns; only tackle them if
   Layers 1–2 finish under budget.

### Generating the prioritized atom lists

See `extract_priority_layers.py` in the repo root. Run:

```bash
python3 extract_priority_layers.py
# Produces: layer_1_atoms.txt, layer_2_atoms.txt, ..., priority_atoms_all.txt
```

---

## 2. Pre-flight: atom quality check

The prerequisite pipeline already ran a full validation cycle
(Phase 4) and a dedicated fix pipeline (140/143 fixes succeeded).
Before generating questions, do a quick sanity check:

### 2.1 Review validation results

Open `app/data/prerequisites/validation_result.json`. The top-level
summary shows:

- `total_prereq_atoms`: 1,095 (post-dedup count at validation time)
- `passed`: true
- `llm_validation_results`: per-standard evaluations

Spot-check 5–10 Layer 1 atoms in `app/data/prerequisites/atoms.json`.
For each atom verify:

- [ ] `titulo` and `descripcion` are pedagogically coherent
- [ ] `criterios_atomicos` are specific and measurable (3–5 items)
- [ ] `habilidad_principal` matches the content (representar,
  resolver, argumentar, modelar)
- [ ] `prerrequisitos` point to atoms that logically come before
- [ ] `ejemplos_conceptuales` are age-appropriate for the `grade_level`

### 2.2 If issues are found

Re-run the fix pipeline on specific standards:

```bash
python3 -m app.prerequisites.fixing
```

This reads `validation_result.json`, parses issues, and applies
LLM-driven fixes (split, merge, content fixes, etc.). Results
are saved to `app/data/prerequisites/fix_results/`.

---

## 3. Step-by-step pipeline

### Important: pipeline compatibility

| Pipeline | Prereq atom support? | Notes |
|----------|:-------------------:|-------|
| Question gen (sync) | Yes | `load_atom` checks `PREREQ_ATOMS_FILE` |
| Question gen (batch API) | **No** | Hardcoded to M1 atoms only |
| Mini-lessons | **No** | `load_atom` only checks M1 `ATOMS_DIR` |

**The sync question generation script is the only pipeline that
currently supports prerequisite atoms.** Before running mini-lessons,
you must update `app/mini_lessons/helpers.py` `load_atom()` to also
check `app/data/prerequisites/atoms.json` (same pattern used in
`app/question_generation/helpers.py` `load_atom()`).

---

### Step 1: Generate prioritized atom ID list

```bash
python3 extract_priority_layers.py
```

This produces `layer_1_atoms.txt` (54 atoms) and
`layer_2_atoms.txt` (91 atoms).

---

### Step 2: Atom enrichment (Phase 0–1)

Enrichment generates pedagogical metadata per atom: difficulty
calibration, error families, image type requirements.

```bash
python3 -m app.question_generation.scripts.run_generation \
  --atoms-file layer_1_atoms.txt \
  --phase enrich \
  --skip-images \
  --resume \
  -v
```

**Output:** `app/data/question-generation/{atom_id}/checkpoints/phase_1_enrichment.json`

**Quality gate:**
- [ ] Open 3–5 enrichment JSONs and verify:
  - Difficulty tiers make sense for the grade level
  - Error families are realistic student mistakes
  - Image type decisions are reasonable

---

### Step 3: Question generation (Phases 2–9)

Generate the full question pool per atom using the sync pipeline.
The script processes atoms sequentially.

```bash
python3 -m app.question_generation.scripts.run_generation \
  --atoms-file layer_1_atoms.txt \
  --skip-images \
  --resume \
  -v
```

> `--resume` skips already-completed phases per atom, so you can
> safely re-run if interrupted.

**Phase groups available** (use `--phase` to run selectively):

| Group | Phases | Description |
|-------|--------|-------------|
| `all` | 0–9 | Full pipeline (default) |
| `enrich` | 0–1 | Inputs + enrichment |
| `plan` | 2–3 | Plan generation + validation |
| `generate` | 4 | Base QTI generation |
| `validate` | 5–6 | Deduplication + base validation |
| `feedback` | 7–8 | Feedback enrichment + review |
| `final_validate` | 9 | Final LLM validation |

**Output:** `app/data/question-generation/{atom_id}/items/*.xml`

**Estimated cost per atom (sync):** $6–$10

**Estimated cost for Layer 1 (54 atoms, sync):** $324–$540

> This exceeds the $500 budget if every atom hits the high end.
> To stay safe, run 10 atoms first, check actual spend on the
> [OpenAI usage dashboard](https://platform.openai.com/usage),
> compute average cost per atom, then decide how many more to run.

---

### Step 4: Question quality review (MUST PASS before lessons)

After question generation completes, verify quality before
proceeding to mini-lessons.

**4a. Check pipeline reports**

Each atom's output has `pipeline_report.json`. Quick scan:

```bash
for dir in app/data/question-generation/A-E*/; do
  atom=$(basename "$dir"); report="$dir/pipeline_report.json"
  [ -f "$report" ] && echo "$atom: $(python3 -c \
    "import json; print(json.load(open('$report')).get('final_item_count','?'))"
  ) items"
done
```

**4b. Quality criteria**

For each atom check:

- [ ] Final item count >= 40 (target is ~46 per difficulty distribution)
- [ ] Phase 9 pass rate >= 80%
- [ ] No atoms with 0 final items (pipeline failure)
- [ ] Difficulty distribution is balanced (Easy, Medium, Hard)

**4c. Spot-check QTI XML**

Open 5–10 XML files from different atoms and difficulties:

- [ ] Question stems are grade-appropriate
- [ ] Answer options are plausible (no trivially wrong distractors)
- [ ] Correct answer is indeed correct
- [ ] Feedback text (if present) explains the right approach

**4d. Flag and re-run failures**

If an atom has < 80% pass rate or < 30 final items:

```bash
# Re-run just that atom from the failing phase
python3 -m app.question_generation.scripts.run_generation \
  --atom-id A-EB7-NUM-01-03 \
  --phase feedback \
  --resume \
  -v
```

---

### Step 5: Mini-lesson generation (only after questions pass)

> **Prerequisite:** Step 4 quality gate must be satisfied.
> Mini-lessons use generated questions as anchoring examples.
> If questions are missing or low quality, lessons will be poor.

> **Code change required:** Before running, update
> `app/mini_lessons/helpers.py` `load_atom()` to also check
> `app/data/prerequisites/atoms.json`. See the pattern in
> `app/question_generation/helpers.py` `load_atom()`.

```bash
python3 -m app.mini_lessons.scripts.run_generation \
  --atoms-file layer_1_atoms.txt \
  --skip-images \
  --workers 4 \
  --resume \
  -v
```

**Phase groups available** (use `--phase`):

| Group | Phases | Description |
|-------|--------|-------------|
| `all` | 0–6 | Full pipeline (default) |
| `plan` | 0–1 | Lesson planning |
| `generate` | 2–3 | Section generation + validation |
| `assemble` | 4 | HTML assembly |
| `quality` | 5 | Quality scoring |
| `output` | 6 | Final output |

**Output:** `app/data/mini-lessons/{atom_id}/mini-class.html`

**Quality gate:**
- [ ] Check `.meta.json` for quality score (aim for >= 7/10)
- [ ] Open 3–5 HTML files in a browser — verify layout,
  pedagogical flow, age-appropriate language
- [ ] Verify lesson references match the atom's criteria

**Estimated additional cost:** ~$1–$2 per atom

---

### Step 6: Image generation (Gemini only — separate budget)

Run this **last**, after all text content is finalized.
Image generation uses Gemini for creation and GPT-5.1 vision
for validation, but the Gemini cost is dominant and comes from
a separate budget.

**For questions:**

```bash
python3 -m app.question_generation.scripts.generate_missing_images \
  --dry-run
# Review estimate, then:
python3 -m app.question_generation.scripts.generate_missing_images \
  --limit 50
# Or for specific atoms:
python3 -m app.question_generation.scripts.generate_missing_images \
  --atoms A-EB7-NUM-01-01 A-EB8-ALG-01-02
```

**For mini-lessons:** Re-run the mini-lesson pipeline without
`--skip-images` on atoms that need images.

---

## 4. Cost tracking and budget management

### Per-atom cost reference (sync pipeline, GPT-5.1)

| Component | Min | Realistic | Max |
|-----------|----:|----------:|----:|
| Question generation (P0–P9) | $3.08 | $6–$10 | $14.06 |
| Mini-lesson generation (P0–P6) | $0.50 | $1–$2 | $3.00 |
| **Total per atom** | **$3.58** | **$7–$12** | **$17.06** |

> Sync pipeline costs are 2x Batch API costs. The question gen
> costs above are sync (standard pricing). If Batch API support
> is added for prereq atoms, divide question gen costs by 2.

### Budget projection

| Scenario | Atoms | Est. cost (questions only) | + Lessons |
|----------|------:|---------------------------:|----------:|
| Layer 1 only | 54 | $324–$540 | $378–$648 |
| Layer 1 + partial L2 | ~70 | $420–$700 | $490–$840 |
| Layer 1 + full L2 | 145 | $870–$1,450 | $1,015–$1,740 |

**Recommendation:** With a $500 budget for questions only:

1. Run 10 Layer 1 atoms first as a calibration batch.
2. Check actual spend on the
   [OpenAI usage dashboard](https://platform.openai.com/usage).
3. Compute: `actual_cost / 10 = cost_per_atom`.
4. Calculate: `remaining_budget / cost_per_atom = atoms_left`.
5. Run the next batch accordingly.
6. Reserve ~$50–$80 for mini-lessons on successfully generated atoms.

### Decision points

- **After 10 atoms:** Calibrate cost per atom. If > $8/atom,
  consider reducing scope to Layer 1 only.
- **After Layer 1 (54 atoms):** Assess remaining budget.
  If < $150 left, skip Layer 2 and move to mini-lessons.
- **Before mini-lessons:** Ensure you have enough budget for
  ~$1–$2 per atom for lessons on all question-generated atoms.

---

## 5. File and code references

### Key data files

| File | Description |
|------|-------------|
| `app/data/prerequisites/atoms.json` | All 1,135 prereq atoms |
| `app/data/prerequisites/connections.json` | M1-to-prereq links |
| `app/data/prerequisites/standards.json` | Prereq standards |
| `app/data/prerequisites/validation_result.json` | Validation results |
| `app/data/prerequisites/fix_results/` | Fix pipeline results |
| `app/data/question-generation/{atom_id}/` | Per-atom QG output |
| `app/data/mini-lessons/{atom_id}/` | Per-atom lesson output |

### Key scripts

| Script | Purpose |
|--------|---------|
| `app/question_generation/scripts/run_generation.py` | Sync QG pipeline (supports prereq atoms) |
| `app/question_generation/scripts/run_batch_api_generation.py` | Batch QG pipeline (M1 only) |
| `app/question_generation/scripts/generate_missing_images.py` | Image generation |
| `app/mini_lessons/scripts/run_generation.py` | Mini-lesson pipeline |
| `app/prerequisites/fixing/__init__.py` | Prereq fix pipeline |

### Key source modules

| Module | What it does |
|--------|--------------|
| `app/question_generation/helpers.py` | `load_atom()` — loads M1 and prereq atoms |
| `app/mini_lessons/helpers.py` | `load_atom()` — **M1 only, needs update for prereqs** |
| `app/question_generation/models.py` | `PHASE_GROUPS`, `PipelineConfig` |
| `app/mini_lessons/models.py` | `PHASE_GROUPS` for lessons |
| `app/prerequisites/constants.py` | ID regex patterns |
| `app/utils/paths.py` | Centralized path constants |

### Environment variables

| Variable | Required by |
|----------|-------------|
| `OPENAI_API_KEY` | Question gen, mini-lessons, fix pipeline |
| `GEMINI_API_KEY` | Image generation only |

### Resuming interrupted runs

Both pipelines support `--resume` which skips completed phases
per atom based on checkpoint files in the output directory:

```bash
# Resume question generation
python3 -m app.question_generation.scripts.run_generation \
  --atoms-file layer_1_atoms.txt --resume -v

# Resume mini-lessons
python3 -m app.mini_lessons.scripts.run_generation \
  --atoms-file layer_1_atoms.txt --resume -v
```

---

## 6. Known issues and required code changes

> **Reminder:** All code changes below must follow the SOLID/DRY
> principles from Section 0. Extend existing functions — do not
> create parallel copies. Keep prompts and reasoning_effort
> settings identical to the proven M1 pipeline.

### 6.1 Mini-lessons `load_atom()` does not support prereq atoms

**File:** `app/mini_lessons/helpers.py`, function `load_atom()`

Only searches `app/data/atoms/` (M1). Add the same prereq-checking
block used in `app/question_generation/helpers.py` `load_atom()` —
import `PrereqAtomsFile` from `app.prerequisites.models` and
`PREREQ_ATOMS_FILE` from `app.utils.paths`, then iterate
`prereq_file.atoms` after the M1 search loop.

### 6.2 Batch API script does not support prereq atoms

**File:** `app/question_generation/scripts/run_batch_api_generation.py`

`_load_all_atoms()` is hardcoded to M1 via
`get_atoms_file("paes_m1_2026")`. For now use the sync pipeline.
If budget is tight, adding `--atoms-file` to the batch script
would halve question generation costs.

---

## 7. Documentation to keep in sync

| Document | What to check |
|----------|---------------|
| `docs/references/batch-api-cost-estimation.md` | Cost numbers remain accurate after any model changes |
| `docs/specifications/repo-structure-and-modules.md` | Update if new modules/directories are created |

**Principle:** Code is the source of truth. If documentation
and code disagree, update the documentation to match the code.
