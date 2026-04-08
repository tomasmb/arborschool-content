# Prerequisite Atoms — ARCHIVED (April 2026)

> **STATUS: EXPERIMENTAL / NOT IN PRODUCTION**
>
> This folder contains the prerequisite atom pipeline and its generated
> data. It was archived because we decided to focus exclusively on M1
> content for now. Everything here MUST be thoroughly reviewed before
> reactivation. Do NOT sync, import, or use any of this content in
> production without completing the review checklist below.

---

## What this is

An AI pipeline that generated **1,135 foundational atoms** spanning
grades EB1 through EM1 (Chilean curriculum). The goal was to provide
remediation paths for students who lack prerequisites for M1 content.

The pipeline ran through phases 0-4 (demand analysis, standards
generation, atom generation, graph connection, validation) and a
fix cycle (140/143 fixes applied). The generated atoms were never
used for question generation or synced to production.

## Archive date and branch

- **Archived:** 2026-04-08
- **Snapshot branch:** `archive/prerequisites-v1` (full repo state
  at the moment of archiving, before any cleanup)

## What's in this folder

```
_archive/prerequisites/
├── README.md              ← you are here
├── code/
│   ├── prerequisites/     ← full app/prerequisites/ package
│   │   ├── pipeline.py
│   │   ├── models.py, constants.py
│   │   ├── demand_analysis.py, standards_generation.py
│   │   ├── atoms_generation.py, graph_connection.py
│   │   ├── validation.py
│   │   ├── prompts/       ← prompt builders for each phase
│   │   └── fixing/        ← fix pipeline (issue parser, executor)
│   └── extract_priority_layers.py  ← BFS layer extraction script
├── data/
│   └── prerequisites/     ← full app/data/prerequisites/ output
│       ├── atoms.json          (1,135 atoms, ~2.4 MB)
│       ├── standards.json      (prereq standards)
│       ├── connections.json    (M1-to-prereq graph links)
│       ├── demand_analysis.json
│       ├── validation_result.json
│       └── fix_results/
└── docs/
    └── prerequisite-atoms-pipeline-handoff.md  ← operational guide
```

## Why it was archived (not deleted)

We will likely revisit prerequisite remediation in a few months.
The pipeline code and generated data represent significant work
(~$15-20 in API costs, several iterations of prompt tuning and
validation). Deleting would mean redoing all of it.

However, **none of this was production-tested**. The atoms were
generated but never:
- Had questions generated for them
- Had mini-lessons created
- Were synced to the student app database
- Were reviewed by a human subject-matter expert

---

## REVIEW CHECKLIST (complete before reactivation)

Every single item below must be verified before any of this content
or code is used in production. Do not skip items.

### Data quality

- [ ] **Atom content review**: Spot-check at least 20 atoms per
  grade level (EB3-EM1). Verify `titulo`, `descripcion`, and
  `criterios_atomicos` are pedagogically sound and age-appropriate.
- [ ] **Prerequisite graph**: Verify prerequisite chains make
  pedagogical sense. A student following the graph should encounter
  concepts in a logical order.
- [ ] **Grade-level accuracy**: Verify atoms are assigned to the
  correct Chilean curriculum grade level.
- [ ] **Connection to M1**: The `connections.json` file links prereq
  atoms to M1 atoms. Verify these links are correct — only 52/238
  M1 atoms had connections at archive time.
- [ ] **Completeness**: Only 368/1,135 atoms are reachable from M1
  via BFS. Decide whether unreachable atoms should be kept or pruned.
- [ ] **Validation results**: Re-review `validation_result.json` —
  the pipeline self-reported "passed" but LLM self-validation has
  known blind spots.

### Code quality

- [ ] **Pipeline phases**: Each phase (demand_analysis, standards,
  atoms, graph_connection, validation) must be re-tested end-to-end.
- [ ] **Prompt drift**: The atom generation prompts were aligned with
  M1 prompts at archive time. If M1 prompts have changed since then,
  prereq prompts need re-alignment.
- [ ] **Model compatibility**: Pipeline was built for GPT-5.1 with
  specific `reasoning_effort` settings. Verify these still apply to
  whatever model is current.
- [ ] **Fix pipeline**: The fixing/ subpackage parsed validation
  issues and applied LLM-driven fixes. Re-validate that fixes are
  still correct.

### Integration

- [ ] **Re-wire imports**: At archive time, `load_atom()` in
  `app/question_generation/helpers.py` supported prereq atoms.
  That import was removed during archival. It must be re-added
  and tested.
- [ ] **Path constants**: `PREREQ_*` constants were removed from
  `app/utils/paths.py`. Re-add them.
- [ ] **Mini-lesson support**: `app/mini_lessons/helpers.py` never
  supported prereq atoms. It needs the same `load_atom()` extension.
- [ ] **Batch API support**: The batch question generation script
  was hardcoded to M1 atoms only.
- [ ] **Sync pipeline**: Prereq atoms were never synced. The sync
  pipeline needs explicit support for EB1-EM1 atom IDs.
- [ ] **Graph disconnection**: The M1 atom `prerrequisitos` field
  does NOT reference prereq atom IDs. The two graphs are
  disconnected. `connections.json` was the intended bridge but was
  never wired into the atom data.

### Cost estimation

- [ ] **Question generation**: ~797-984 atoms need questions at
  ~$6-10 per atom (sync pipeline). Budget: $5,000-$10,000.
- [ ] **Mini-lessons**: ~$1-2 per atom additional.
- [ ] **Re-validate before spending**: Run a 5-atom pilot batch
  first to calibrate actual costs with current model pricing.
