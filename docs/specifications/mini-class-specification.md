# Mini-Class Specification

> **Status**: Normative — this is the single source of truth for mini-class
> structure, content, HTML contract, and quality gates.
> All other docs reference this file; they do not restate its content.

Date: 2026-02-25
Owner: Max (Chief of Staff)
Spec version: 1.0

---

## 1) Executive decision

For Arbor, the best mini-class format is **short, structured, interactive,
and immediately followed by adaptive practice**.

**Fixed sequence:**

1. Goal + relevance (why this atom matters for PAES score)
2. Minimal concept explanation
3. 2 worked examples (step-by-step)
4. 1–2 quick checks with immediate explanatory feedback
5. Error patterns + exam strategy
6. Transition to adaptive set

Evidence base: worked examples for novices, retrieval practice / testing
effect, explanatory feedback, cognitive load management, adolescent
motivation (autonomy / competence / relatedness), spacing / interleaving
for long-term retention.

---

## 2) Research-backed design principles

### A. Worked examples first, then independent solving

**Why:** novices learn better from worked examples than pure
discovery / problem-solving first.
**Product rule:** every mini-class includes at least 2 worked examples
before the adaptive set.

### B. Keep cognitive load low (coherence + signaling + chunking)

**Why:** extra noise hurts learning; signaling key steps helps
low-knowledge learners.
**Product rule:** short sections, explicit step labels, no decorative text,
one idea per block.

### C. Retrieval practice early and often

**Why:** testing / retrieval strengthens long-term retention more than
re-reading.
**Product rule:** 1–2 in-lesson "quick checks" (micro-MCQ) before
adaptive practice.

### D. Explanatory feedback > binary correctness

**Why:** elaborative / corrective feedback has stronger effects than just
right / wrong or grade-only.
**Product rule:** every quick check must return:

- why the correct option is correct,
- why each distractor is tempting / wrong,
- what to do next time.

### E. Motivation for 17-year-olds: autonomy + competence + progress

**Why:** SDT evidence supports autonomy / competence / relatedness for
sustained motivation.
**Product rule:**

- clear "you can do this" framing,
- transparent progress,
- optional path choice when equal expected score lift.

### F. Retention plan (spacing + interleaving)

**Why:** spaced and interleaved retrieval improves durable performance.
**Product rule:** mini-class output tags concepts / skills for future
spaced-review insertion.

---

## 3) Content architecture: required vs optional sections

Each mini-class uses a **modular structure** with a required core and
atom-dependent optional modules.

### Required sections (all atoms)

1. **Objective**
   - "Al terminar esta mini-clase podrás…"
   - 1 measurable verb + 1 PAES relevance line.
2. **Concept in 60–120 seconds**
   - Minimal theory; definitions / notation only if needed.
3. **Worked Example 1 (guided)**
   - Fully scaffolded steps + why each step.
4. **Worked Example 2 (faded guidance)**
   - Fewer hints than Example 1.
5. **Quick Check(s)**
   - 1–2 ABCD questions with immediate explanatory feedback.
6. **Common errors + exam tip**
   - Top 2 traps + one PAES tactical cue.
7. **Bridge to adaptive practice**
   - Explicit transition: "Ahora pasas al set adaptativo."

### Optional sections (only when atom needs it)

- **Prerequisite refresh micro-block** (if high prerequisite risk)
- **Visual intuition block** (graphs / geometry-heavy atoms)
- **Formula card** (if formula recall is truly required)
- **Counterexample block** (for misconceptions)
- **Real-context hook** (only if it reduces abstraction friction)

Rule: optional sections must be justified by atom type, not added
by default.

---

## 4) Atom type templates

### Mapping from `atom_type` enum to template

| `atom_type` value        | Template |
|--------------------------|----------|
| `procedimiento`          | P        |
| `concepto`               | C        |
| `representacion`         | C        |
| `argumentacion`          | C        |
| `concepto_procedimental` | M        |
| `modelizacion`           | M        |

### Template P — Procedural atoms

Algebraic manipulation, equation solving.

- Objective
- Concept micro-explanation
- Worked Example 1 (fully guided)
- Worked Example 2 (faded)
- Quick Check x2
- Error patterns + checklist
- Transition

### Template C — Conceptual atoms

Functions meaning, interpretation, model selection.

- Objective
- Concept contrast table (what it is / what it is not)
- Worked Example 1 (interpretation)
- Worked Example 2 (decision choice)
- Quick Check x1–2
- Misconception correction
- Transition

### Template M — Mixed atoms

Concept + procedure.

- Objective
- Concept anchor
- Procedural worked example
- Conceptual worked example
- Quick Check x2
- Error map + next-step rule
- Transition

---

## 5) UX constraints for the mini-class renderer

- Target duration: **as short as possible**, default operating window
  **4–7 minutes** for most atoms.
- Hard rule: if the atom can be taught well in less time, prefer shorter.
  Duration is an outcome constraint, not a fixed script length.
- Max text density per block: short paragraphs + bullets.
- Every major step labeled (Paso 1, Paso 2…).
- Feedback panels should be collapsible / expandable.
- Keep interaction friction low (tap / click, instant response).
- No heavy animation that competes with cognitive focus.

---

## 6) LLM output contract (HTML without styles)

### Allowed tags

`section`, `header`, `h1`–`h4`, `p`, `ul`, `ol`, `li`, `table`, `thead`,
`tbody`, `tr`, `th`, `td`, `strong`, `em`, `code`, `math`
(or LaTeX inline markers), `details`, `summary`, `blockquote`, `hr`.

### Disallowed

Inline styles, `<style>`, `<script>`, external embeds.

### Semantic attributes for rendering logic

`data-block`, `data-atom-id`, `data-difficulty`, `data-prereq`,
`data-feedback-type`.

### Required root structure

```html
<article data-kind="mini-class"
         data-atom-id="A-M1-ALG-01-01"
         data-template="P|C|M">
  <header data-block="objective">
    <h1>Mini-clase: ...</h1>
    <p data-role="learning-objective">...</p>
    <p data-role="paes-relevance">...</p>
  </header>

  <section data-block="concept">...</section>
  <section data-block="worked-example" data-index="1">...</section>
  <section data-block="worked-example" data-index="2">...</section>

  <section data-block="quick-check" data-index="1"
           data-format="mcq-abcd">
    <h3>Quick Check 1</h3>
    <p data-role="question-stem">...</p>
    <ol data-role="options" data-option-format="ABCD">
      <li data-option="A">...</li>
      <li data-option="B">...</li>
      <li data-option="C">...</li>
      <li data-option="D">...</li>
    </ol>
    <div data-role="feedback" data-feedback-type="explanatory">
      <p data-correct-option="B">...</p>
      <ul data-role="distractor-rationale">
        <li data-option="A">...</li>
        <li data-option="C">...</li>
        <li data-option="D">...</li>
      </ul>
    </div>
  </section>

  <section data-block="error-patterns">...</section>
  <section data-block="transition-to-adaptive">...</section>
</article>
```

---

## 7) Quality rubric (gate before publish)

Score 0–2 each dimension (pass threshold: >= 12/14):

1. Objective clarity + measurability
2. Cognitive load control (no fluff)
3. Worked example correctness
4. Step rationale clarity (not just procedures)
5. Quick check quality (non-trivial distractors)
6. Feedback quality (explanatory, actionable)
7. Transition readiness to adaptive set

**Automatic fail conditions:**

- Incorrect math
- Contradiction between explanation and answer key
- Vague / non-actionable feedback
- Missing worked examples

---

## 8) What should vary by atom (and what should not)

**Should vary:** template type (P/C/M), optional modules,
notation / examples context, quick-check difficulty.

**Should stay fixed (for consistency):** macro sequence,
semantic HTML contract, feedback format, transition handoff to
adaptive set.

---

## 9) Implementation outputs

Each atom produces:

1. `mini-class.html` — semantic, style-free HTML
2. `mini-class.meta.json` — atom id, template, prereq flags, spaced
   repetition tags
3. `mini-class.qa.json` — self-check against rubric

---

## 10) Audited reference evidence

- **Worked examples / novice guidance:**
  Sweller & Cooper (1985); Kirschner, Sweller & Clark (2006)
- **Cognitive load + signaling / coherence:**
  Mayer (2009); Schneider et al. (2018)
- **Retrieval practice / testing effect:**
  Roediger & Karpicke (2006); Adesope, Trevisan & Sundararajan (2017)
- **Feedback quality:**
  Hattie & Timperley (2007); Wisniewski, Zierer & Hattie (2020)
- **Spacing + interleaving:**
  Cepeda et al. (2006); Rohrer & Taylor (2007)
- **Adolescent motivation / SDT:**
  Ryan & Deci (2020); Vasconcellos et al. (2020)

Note: the evidence base combines seminal experiments with later
meta-analyses / syntheses; direct PAES-specific RCT evidence is limited,
so transfer requires contextual validation in Arbor product analytics.

---

## Appendix A — Evidence matrix

| Product claim | Strong source(s) | Evidence strength | Key limitations |
|---|---|---|---|
| Start with guided worked examples for novices | Sweller & Cooper (1985); Kirschner et al. (2006) | **High** (seminal + synthesis) | Attenuates with expertise; requires fading design |
| Keep cognitive load low via coherence / signaling / chunking | Mayer (2009); Schneider et al. (2018) | **Moderate–High** | Depends on prior knowledge and media format |
| Include early retrieval checks (testing effect) | Roediger & Karpicke (2006); Adesope et al. (2017) | **High** (seminal + meta-analysis) | Stronger for delayed retention; item quality matters |
| Provide explanatory feedback, not only right / wrong | Hattie & Timperley (2007); Wisniewski et al. (2020) | **High** | Effects are heterogeneous; timing matters |
| SDT motivation (autonomy + competence + relatedness) | Ryan & Deci (2020); Vasconcellos et al. (2020) | **Moderate–High** | Much evidence observational; validate in-product |
| Spacing for durable retention | Cepeda et al. (2006) | **High** | Lab paradigms; intervals need domain calibration |
| Interleave problem types in adaptive practice | Rohrer & Taylor (2007) | **Moderate** | Fewer classroom RCTs; can reduce short-term fluency |
| Fixed macro-sequence | Integrative design inference | **Moderate (synthesis)** | Not tested as bundle; A/B test within Arbor |

### Practical confidence labels

- **Ship now (high confidence):** worked examples, retrieval checks,
  explanatory feedback.
- **Ship with monitoring:** signaling / chunking details, SDT framing.
- **Ship + experiment:** spacing / interleaving schedule, macro-sequence
  variants by atom type.

---

## Appendix B — Risk stress test

### Executive summary

Spec is strong pedagogically, but **implementation risk is medium-high**
because the contract is underspecified for machine validation, renderer
behavior, and anti-repeat enforcement.

**Top risks to fix before production:**

1. Contract ambiguity (required vs optional at attribute / cardinality
   level).
2. MCQ / feedback schema not strict enough for deterministic parsing.
3. No explicit anti-repeat protocol (within lesson, across retries,
   across student history).
4. Renderer mismatch risk (MathML / LaTeX handling, sanitizer behavior,
   accessibility fallback).
5. Rubric not directly automatable (several criteria subjective).

### Stress-test findings

#### A. HTML contract risks

- **A1.** Required structure is example-like, not normative. Missing:
  exact required blocks per template, allowed multiplicity, ordering
  constraints for optional blocks, required attrs per block.
- **A2.** Attribute semantics incomplete (`data-prereq`,
  `data-difficulty`, `data-feedback-type` mentioned but format undefined).
- **A3.** Quick-check not fully closed: no rule for option count in
  validator terms, no explicit `data-correct-option` location strategy.
- **A4.** Accessibility / i18n constraints not formalized.

#### B. Atom-type edge cases

- **P:** overlong step chains (>8–10 steps), abrupt fading between
  Example 1 and 2, atoms with heavy prerequisite gaps.
- **C:** concept contrast tables becoming definition dumps, hard to
  generate non-trivial distractors without procedural anchor.
- **M:** concept + procedure duplicates examples with cosmetic changes,
  incoherent sequence if conceptual example requires unseen procedure.
- **Cross-template:** optional blocks can reorder cognition incorrectly.

#### C. Anti-repeat risks

- Intra-lesson: same numbers / context reused across worked examples and
  quick checks.
- Inter-attempt (same atom): learner retries and gets near-identical
  mini-class.
- Cross-atom: neighbor atoms reuse identical stems / contexts.

#### D. Renderer constraints

- Math rendering ambiguity (MathML vs LaTeX, no canonical fallback).
- Sanitizer profile not testable enough.
- `details/summary` default-open state undefined.
- No constraints on malformed nesting or duplicate IDs.

### Recommended spec improvements (v1.1)

#### A. Make contract machine-verifiable

- **Root:** exactly one `article[data-kind="mini-class"]`.
- Required attrs: `data-atom-id`
  (regex: `^A-M\d+-[A-Z]{3}-\d{2}-\d{2}$`),
  `data-template` in `{P,C,M}`, `data-version`.
- **Required block order (strict):**
  1. `objective`
  2. `concept`
  3. `worked-example[data-index="1"]`
  4. `worked-example[data-index="2"]`
  5. `quick-check[data-index="1"]`
  6. `error-patterns`
  7. `transition-to-adaptive`
- Optional blocks allowed only in pre-declared insertion points.

#### B. Close quick-check schema

For each `quick-check`:

- Exactly 4 options A/B/C/D.
- Exactly one correct option.
- Required rationale for all 3 distractors.
- Required "next-time rule" sentence.
- Forbid option-text duplication.

Additional fields: `data-skill-tag`, `data-bloom-level`,
`data-novelty-seed` (for anti-repeat control).

#### C. Formal anti-repeat protocol

1. **Within one mini-class (hard fail):** no identical stems across
   worked examples / checks. Numeric tuple overlap <= 40% between
   Example 1 and Example 2.
2. **Across attempts of same atom (hard fail unless fallback):** at least
   one changed worked-example context and one changed quick-check stem.
   Same correct option letter cannot repeat in all checks across attempts.
3. **Across adjacent atoms in same unit (soft fail / warning):** context
   similarity threshold (embedding / Jaccard) below configured limit.

#### D. Renderer compatibility profile

Define: preferred math format (choose one primary), fallback behavior,
sanitizer allowlist with explicit attr matrix, max nesting depth (4),
max table size, max block character limits.

#### E. Rubric automation upgrade

Split into: **structural checks** (deterministic, hard gate),
**pedagogical checks** (LLM + human sampling), **math correctness
checks** (symbolic / numeric validation where possible).

### Pass / fail criteria (implementation gate)

**Gate 1 — Contract validity (hard fail):**
One root article with required attrs, all mandatory blocks present
exactly once, worked examples = 2, quick-check count in [1,2], all
required enums valid, no disallowed tags.

**Gate 2 — Quick-check integrity (hard fail):**
4 unique options per check, one correct, explanatory feedback with
correct rationale + 3 distractor rationales + next-step cue.

**Gate 3 — Anti-repeat (mixed):**
Hard fail on exact stem duplication within mini-class or isomorphic
worked examples. Warning on cross-atom repetition above threshold.

**Gate 4 — Renderer safety (hard fail):**
Sanitizer output stable, no scriptable payloads, math renders or
degrades gracefully, no broken nesting, mobile overflow / tap-target
checks pass.

**Gate 5 — Pedagogical quality (score gate):**
Overall >= 12/14, minimum 1/2 per dimension, auto-fail overrides
retained. Additional auto-fail: example / check tests different skill
than objective, feedback says "correct" without explanation, transition
text missing explicit action.

### Edge-case test suite (minimum)

1. P-template with long algebraic derivation (step explosion).
2. C-template with misconception-heavy atom (distractor quality stress).
3. M-template where conceptual example depends on unseen operation.
4. Geometry atom with table + MathML + list nesting.
5. Atom with optional prereq-refresh inserted.
6. Two quick-check variant with one intentionally malformed feedback.
7. Duplicate option labels or duplicated `data-index`.
8. Sanitizer attack payload (`onerror`, `javascript:` URL, nested SVG).
9. Retry generation for same atom (anti-repeat enforcement).
10. Low-content atom forcing 1 quick-check only (boundary condition).

### Suggested validator outputs

For each generated mini-class:

- `mini-class.structural.json` — schema validity, block map, enum checks,
  sanitizer report.
- `mini-class.pedagogical.json` — rubric scores + rationale + confidence.
- `mini-class.anti_repeat.json` — intra-lesson similarity +
  prior-attempt delta + cross-atom warning.

Final publish decision:
`publishable = structural_pass && correctness_pass &&
anti_repeat_hard_pass && rubric_score >= 12`

### Risk verdict

- Pedagogical direction: **strong**
- Engineering contract readiness: **partial**
- Production reliability without revisions: **not yet**

**Recommendation:** implement v1.1 contract hardening + validator gates
before scaling generation.

---

## Appendix C — Bibliography (APA 7)

Adesope, O. O., Trevisan, D. A., & Sundararajan, N. (2017). Rethinking
the use of tests: A meta-analysis of practice testing. *Review of
Educational Research, 87*(3), 659–701.

Cepeda, N. J., Pashler, H., Vul, E., Wixted, J. T., & Rohrer, D.
(2006). Distributed practice in verbal recall tasks: A review and
quantitative synthesis. *Psychological Bulletin, 132*(3), 354–380.

Hattie, J., & Timperley, H. (2007). The power of feedback. *Review of
Educational Research, 77*(1), 81–112.

Kirschner, P. A., Sweller, J., & Clark, R. E. (2006). Why minimal
guidance during instruction does not work. *Educational Psychologist,
41*(2), 75–86.

Mayer, R. E. (2009). *Multimedia learning* (2nd ed.). Cambridge
University Press.

Roediger, H. L., III, & Karpicke, J. D. (2006). Test-enhanced learning:
Taking memory tests improves long-term retention. *Psychological Science,
17*(3), 249–255.

Rohrer, D., & Taylor, K. (2007). The shuffling of mathematics problems
improves learning. *Instructional Science, 35*(6), 481–498.

Ryan, R. M., & Deci, E. L. (2020). Intrinsic and extrinsic motivation
from a self-determination theory perspective. *Contemporary Educational
Psychology, 61*, Article 101860.

Schneider, S., Beege, M., Nebel, S., & Rey, G. D. (2018). A
meta-analysis of how signaling affects learning with media. *Educational
Research Review, 23*, 1–24.

Sweller, J., & Cooper, G. A. (1985). The use of worked examples as a
substitute for problem solving in learning algebra. *Cognition and
Instruction, 2*(1), 59–89.

Vasconcellos, D., Parker, P. D., Hilland, T., et al. (2020).
Self-determination theory applied to physical education: A systematic
review and meta-analysis. *Journal of Educational Psychology, 112*(7),
1444–1469.

Wisniewski, B., Zierer, K., & Hattie, J. (2020). The power of feedback
revisited: A meta-analysis of educational feedback research. *Frontiers
in Psychology, 10*, Article 3087.
