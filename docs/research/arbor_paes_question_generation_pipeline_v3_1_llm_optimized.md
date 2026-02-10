# Arbor PAES Atom Question Generation Pipeline (QTI 3.0, MCQ-only) — v3.1

This spec defines the **end-to-end pipeline** that generates **PAES-style** question pools per atom as **QTI 3.0 XML**, validates them, enriches them with **inline feedback + worked solution**, re-validates, and **syncs only fully validated items** to the DB.

This file is written to be **LLM-optimized**: clear segmentation, explicit MUST rules, no contradictions, minimal redundancy.

---

## 0) Canonical API Schema (Source of Truth)

The live API schema is always available here:

```bash
curl https://preu.arbor.school/api/schema
```

Use it to confirm any request/response shapes referenced in this document.

---

## 1) Non-Negotiables (Hard Constraints)

### 1.1 Item Type Constraints (PAES M1)
Every generated item MUST be:
- **Multiple-choice (MCQ)** only
- **Exactly 4 options (A–D)**
- **Exactly 1 correct option**
- **Spanish (Chile)**
- **PAES-consistent notation** (e.g., decimal separators, formatting conventions)
- **QTI 3.0 XML** as the authoritative representation

### 1.2 Rendering Constraints
- All math MUST render correctly via **MathML-first** inside the QTI XML.
- The pipeline MUST NOT rely on “fix later” formatting steps.

### 1.3 Inventory Constraints
- Only **final, fully validated, enriched** items are eligible to be synced to DB and served.
- Base-only items are never serveable inventory.

---

## 2) Key Definitions

- **Atom**: smallest mastery unit (Math Academy granularity).
- **Exemplar**: a real PAES item used internally to define target competence and guardrails. **Never served** and never paraphrased.
- **Plan Slot**: a single planned item specification (difficulty, context, skeleton, etc.) that will be materialized into QTI XML.
- **operation_skeleton_ast**: canonical structure describing the mathematical operation pattern (used for diversity + anti-duplication).
- **pipeline_meta**: non-QTI metadata stored alongside the QTI item for analytics, dedupe, coverage, and debugging.

---

## 3) Exemplar Policy (Use Real Items Safely)

### 3.1 What exemplars are allowed to do
Exemplars MAY be used to derive:
- Scope boundaries (“this requires other atoms”)
- Typical representations and contexts
- Common misconceptions / error families
- Real-PAES “future target” capability (what this atom enables later)

### 3.2 What exemplars must NEVER do
Exemplars MUST NOT be:
- Served to students
- Paraphrased into student-facing items
- Used as direct textual templates
- Used to generate near-isomorphic numeric variants that preserve surface structure

### 3.3 Anchoring rule (when exemplars exist)
If an atom has exemplars, then **every Plan Slot MUST be anchored** to exactly one target exemplar (or one exemplar family, if your schema supports families).

Plan Validation MUST FAIL if exemplars exist and any slot is missing:
- `target_exemplar_id` (or `exemplar_family_id`)
- `distance_level` (how far the new item departs structurally from the exemplar)

---

## 4) Scope + Difficulty Semantics

### 4.1 Scope
Each item MUST be:
- In-scope for the atom
- Not requiring unmastered prerequisite atoms (unless explicitly permitted by scope guardrails)

### 4.2 Difficulty (within-atom)
Difficulty is defined **within the atom**, not global PAES difficulty.

Canonical levels:
- `easy`
- `medium`
- `hard`

The difficulty rubric MUST specify what changes across levels for this atom (e.g., algebraic manipulation steps, representation complexity, distractor subtlety, etc.).

---

## 5) Mandatory Atom Enrichment (Non-Blocking Output)

### 5.1 Intent
**Atom Enrichment is a mandatory pipeline phase.** The pipeline MUST attempt to produce an enrichment object for each atom to increase instructional consistency (scope, difficulty, misconceptions, representations).

### 5.2 Non-blocking output rule
The enrichment phase is **mandatory to run**, but its output is **not required to proceed**:
- If enrichment is present: the planner and validators MUST use it.
- If enrichment generation fails or enrichment is missing: the pipeline MUST proceed using the atom’s canonical fields, and mark `enrichment_status = "missing"` (or equivalent).

This preserves the principle: **every phase is intentional and mandatory**, while allowing forward progress when enrichment cannot be produced.

### 5.3 Minimum enrichment schema (recommended canonical fields)
When enrichment exists, it SHOULD include at minimum:
- `scopeGuardrails` (what is allowed / forbidden, prerequisites)
- `difficultyRubric` (easy/medium/hard definition)
- `ambiguityAvoid` (known phrasing/formatting pitfalls)

Optional but strongly recommended:
- `errorFamilies`
- `futureTargets`
- `representationVariants`
- `numbersProfiles`

---

## 6) Diversity & Anti-Duplicate Strategy (Educational Validity)

### 6.1 Planning-driven diversity (primary)
The planner MUST produce diversity by construction via:
- Distinct `operation_skeleton_ast` across slots
- Varied surface contexts (`surface_context`)
- Varied `numbers_profile` (where applicable)

### 6.2 Skeleton repetition cap
Within a pool for a given atom:
- The same `operation_skeleton_ast` MUST appear **no more than 2 times**.

Plan Validation MUST FAIL if this cap is exceeded.

### 6.3 Deterministic near-duplicate gate (secondary)
After base generation, a deterministic fingerprint gate MUST detect duplicates/near-duplicates, including:
- same structure with minor wording changes
- commuted option order
- trivial numeric perturbations that preserve isomorphism

If duplicates are detected:
- The pipeline MUST mark the offending items as invalid and exclude them from downstream enrichment/sync.

---

## 7) QTI as the Source of Truth + Metadata Separation

### 7.1 QTI authoritative fields
All student-visible content MUST live in QTI XML:
- stem
- options (A–D)
- correct response
- per-option feedback
- worked solution (short, correct, PAES-aligned)

### 7.2 pipeline_meta (non-QTI)
Non-QTI metadata MUST be stored as `pipeline_meta`, e.g.:
- `component_tag` (exactly 1 per item)
- `difficulty_level` (easy/medium/hard)
- `operation_skeleton_ast` (canonical)
- `surface_context` (controlled vocab)
- `numbers_profile` (controlled vocab)
- dedupe fingerprint(s)
- validator reports / reasons

---

## 8) Pipeline Overview (Phases + Gates)

**All phases below are mandatory steps in the pipeline.** Some phases may be *non-blocking* in output (as explicitly stated).

### Phase 0 — Inputs
Inputs required:
- Atom definition (canonical fields)
- Optional exemplars
- Component definition(s) for the atom (for `component_tag`)
- Existing inventory summary (for coverage + dedupe context)

Outputs:
- `atom_context`

---

### Phase 1 — Atom Enrichment (MANDATORY PHASE, NON-BLOCKING OUTPUT)
Action:
- Attempt to produce/update `Atom.enrichment` according to schema.

Outputs:
- `enrichment_status` ∈ {`present`, `missing`, `failed`}
- `atom_enrichment` when present

Hard requirements:
- Phase must run.
- Failure does NOT stop the pipeline.

---

### Phase 2 — Plan Generation (MANDATORY + BLOCKING)
Action:
- Generate a plan of N slots (target pool size) with explicit diversity controls.

Each plan slot MUST contain:
- `difficulty_level`
- `component_tag`
- `operation_skeleton_ast`
- `surface_context`
- `numbers_profile` (if applicable)
- Exemplar anchoring fields (if exemplars exist)

Outputs:
- `plan[]`

Hard gate:
- Plan Validation MUST PASS before proceeding.

---

### Phase 3 — Plan Validation (MANDATORY + BLOCKING)
Validate:
- PAES constraints: MCQ-only, 4 options, single correct (at plan intent level)
- Scope compliance (atom-only)
- Difficulty rubric adherence (use enrichment if present)
- Exemplar anchoring rule (if exemplars exist)
- Diversity requirements + skeleton repetition cap
- Clarity requirements (no ambiguous stems, no multiple-correct patterns)

Outputs:
- `plan_validation_report`

Hard gate:
- Any failure stops the pipeline for that atom until operator fixes the plan inputs.

---

### Phase 4 — Base QTI Generation (MANDATORY + BLOCKING)
Action:
- Materialize each plan slot into a **base** QTI 3.0 XML item (stem + options + correct response).
- Do NOT add per-option feedback or worked solution yet.

Outputs:
- `base_items[]` (QTI XML)

---

### Phase 5 — Deterministic Duplicate Gate (MANDATORY + BLOCKING)
Action:
- Compute fingerprints and detect duplicates/near-duplicates within:
  - this batch
  - existing inventory for the atom (if available)

Outputs:
- `dedupe_report`
- `base_items_filtered[]`

Hard gate:
- Items flagged as duplicates MUST be excluded from downstream steps.

---

### Phase 6 — Base Validation (MANDATORY + BLOCKING)
Validate each base item:
- QTI 3.0 XML validity (schema/XSD)
- Solvability: independent solve matches declared correct option
- PAES compliance: exactly 4 options, exactly 1 correct, appropriate Spanish style
- Scope: does not require out-of-scope prerequisites
- Exemplar non-copy rule: sufficiently far from any exemplar (if exemplars exist)

Outputs:
- `base_validation_report`
- `base_items_valid[]`

Hard gate:
- Only passing items proceed.

---

### Phase 7 — Feedback Enrichment (MANDATORY + BLOCKING)
Action:
- Add:
  - per-option feedback (brief, pedagogically helpful)
  - short worked solution (correct, minimal, PAES-aligned)
- All content must be embedded in QTI XML.

Outputs:
- `enriched_items[]` (QTI XML)

---

### Phase 8 — Feedback Validation (MANDATORY + BLOCKING)
Validate:
- Feedback correctness (no incorrect explanations)
- Feedback consistency with correct answer
- Solution correctness and minimality
- Tone and clarity (non-patronizing, direct)

Outputs:
- `feedback_validation_report`
- `enriched_items_valid[]`

Hard gate:
- Only passing items proceed.

---

### Phase 9 — Final Validation (MANDATORY + BLOCKING)
Re-run full validation on enriched XML:
- QTI XSD
- Independent solve
- Full PAES constraints
- Scope
- Deduplication sanity (optional re-check)

Outputs:
- `final_validation_report`
- `final_items[]`

Hard gate:
- Only final_items are eligible for sync.

---

### Phase 10 — DB Sync (MANDATORY + BLOCKING)
Action:
- Write `final_items[]` into DB as serveable inventory.
- Store `pipeline_meta` and all validator reports for traceability.

Outputs:
- `sync_report`

Hard gate:
- If sync fails, no items are considered produced.

---

## 9) Operator Controls (Human-in-the-Loop)

### 9.1 No silent retry loops
The pipeline MUST NOT auto-regenerate indefinitely.

Allowed operator actions:
- Re-run Phase 1 enrichment generation
- Edit enrichment fields (if stored)
- Adjust plan parameters and regenerate the plan
- Targeted “Fix with LLM” on a specific failing item

### 9.2 Fix acceptance rule
Any fixed item MUST:
- pass Base/Feedback/Final validations again
- pass dedupe gate
- remain non-copy vs exemplars

---

## 10) Required Schemas (Spec-Level)

### 10.1 Atom.enrichment (recommended shape)
```json
{
  "scopeGuardrails": {
    "inScope": ["..."],
    "outOfScope": ["..."],
    "prerequisites": ["A-M1-..."],
    "commonTraps": ["..."]
  },
  "difficultyRubric": {
    "easy": ["..."],
    "medium": ["..."],
    "hard": ["..."]
  },
  "ambiguityAvoid": ["..."],
  "errorFamilies": [
    { "name": "...", "description": "...", "howToAddress": "..." }
  ],
  "futureTargets": ["..."],
  "representationVariants": ["..."],
  "numbersProfiles": ["small_integers", "fractions", "mixed", "decimals"]
}
```

### 10.2 Plan Slot (minimum required fields)
```json
{
  "component_tag": "ALGEBRA.LINEAR_EQUATIONS",
  "difficulty_level": "medium",
  "operation_skeleton_ast": "(= (+ (* a x) b) c) -> solve x",
  "surface_context": "pure_math",
  "numbers_profile": "small_integers",
  "target_exemplar_id": "PAES2023_M1_Q12",
  "distance_level": "medium"
}
```

### 10.3 pipeline_meta (minimum required fields)
```json
{
  "atom_id": "A-M1-ALG-01-02",
  "component_tag": "ALGEBRA.LINEAR_EQUATIONS",
  "difficulty_level": "medium",
  "operation_skeleton_ast": "(= (+ (* a x) b) c) -> solve x",
  "surface_context": "pure_math",
  "numbers_profile": "small_integers",
  "fingerprint": "sha256:...",
  "validators": {
    "xsd": "pass",
    "solve_check": "pass",
    "scope": "pass",
    "exemplar_copy_check": "pass",
    "feedback": "pass"
  }
}
```

---

## 11) Compliance Checklist (Per Item)

An item is eligible for DB sync iff:
- [ ] QTI 3.0 XSD valid
- [ ] 4 options (A–D)
- [ ] exactly 1 correct
- [ ] independent solve matches declared correct
- [ ] in-scope for atom
- [ ] non-copy vs exemplars (if exemplars exist)
- [ ] passes dedupe gate
- [ ] includes per-option feedback
- [ ] includes a short worked solution
- [ ] has complete pipeline_meta

---

## 12) Version Notes

- v3.1 clarifies: **Atom Enrichment is a mandatory pipeline phase** while its **output is non-blocking**.
- Adds canonical API schema endpoint for shape verification.

