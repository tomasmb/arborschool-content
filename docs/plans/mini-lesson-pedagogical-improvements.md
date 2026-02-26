# Plan: Best-in-Class Mini-Lessons

> **Date**: 2026-02-26
> **Goal**: Pipeline produces the best possible semantic HTML per atom;
> a React renderer displays it interactively and consistently.
> **Principle**: HTML is content truth. Renderer is presentation.
> One `mini-class.html` per atom, one renderer for all atoms.

---

## 1. Target student experience

What a 17-year-old PAES student sees (React renderer):

```
[Objective]  — always visible, 2 lines
   ↓
[Concept]    — micro-blocks revealed one at a time (h3 sub-blocks)
   ↓          includes "Trampa PAES" non-example when relevant
[WE1]        — problem visible; steps revealed one by one on tap
   ↓          closes with "Si obtuviste -31, vas bien"
[WE2]        — problem visible; fewer annotations, mental-fill cues
   ↓          student predicts before revealing each step (fading)
[QC1]        — simple, 20-30s; tap option → instant feedback
   ↓          feedback ends with reusable "Regla de oro"
[QC2]        — integrative, 45-60s; same interaction
   ↓
[Errors]     — scannable list + 3-item PAES checklist (✅ format)
   ↓
[Transition] — "Ahora pasas al set adaptativo" → button to practice
```

Total time: 4-7 minutes. Every screen has ONE job.

---

## 2. Diagnosis: what the current pipeline gets wrong

14/14 rubric score, yet expert DI review found 8 structural problems:

| # | Problem | Root cause |
|---|---------|-----------|
| 1 | Concept = wall of text (4+ ideas) | Prompt says "1 idea/paragraph" but no sub-headings |
| 2 | WE1 and WE2 identically scaffolded | Same `_WORKED_EXAMPLE_RULES` for both indices |
| 3 | Only 1 QC (P-template spec says ×2) | Planner allows 1-2 without preference |
| 4 | WE2 jumps 3+ difficulty axes at once | No planner constraint on gradual complexity |
| 5 | Feedback lacks reusable if-then rule | "next-step cue" too vague |
| 6 | PAES tip = paragraph, not checklist | No format requirement |
| 7 | No non-example for common traps | Counterexample section never activated |
| 8 | No micro-reinforcement after WEs | Not in prompt |
| 9 | Steps shown all at once (no reveal) | HTML is flat `<ol>`, no disclosure |
| 10 | QC not interactive (answer visible) | No option-selection interaction |

---

## 3. Key design decisions

### 3.1 One HTML file, one React renderer

- Pipeline outputs `mini-class.html`: semantic, style-free, no JS.
- React renderer interprets `data-*` attributes and `<details>`
  elements to provide full interactivity.
- Without a renderer, `<details>/<summary>` gives a decent fallback.

### 3.2 Progressive disclosure via `<details>/<summary>`

The spec already allows `details` and `summary` tags. We use them
for two purposes:

**Worked-example steps** — each step wrapped:
```html
<ol data-role="steps">
  <li>
    <details>
      <summary><strong>Paso 1:</strong> Sustituye...</summary>
      <p>Reemplaza cada x por (-3)...</p>
    </details>
  </li>
  <li>
    <details>
      <summary><strong>Paso 2:</strong> Potencia...</summary>
      <p>(-3)² = 9 porque...</p>
    </details>
  </li>
</ol>
```

**QC feedback** — hidden until interaction:
```html
<div data-role="feedback" data-feedback-type="explanatory">
  <details>
    <summary>Ver explicación</summary>
    <p data-correct-option="A">...</p>
    <ul data-role="distractor-rationale">...</ul>
  </details>
</div>
```

React renderer **overrides** `<details>` with richer behavior
(option click → reveal, step animations). Without renderer,
native `<details>` still works.

### 3.3 No new section types

The macro sequence stays fixed. Improvements are WITHIN sections:
- Concept: `<h3>` sub-blocks
- WE: `<details>` steps + fading for WE2
- QC: `<details>` feedback wrapper
- Errors: checklist format with `✅`

---

## 4. Part A — Pipeline changes (prompts, planner, validator)

### A1. Reference examples rewrite (highest leverage)

**File**: `prompts/reference_examples.py`

The LLM pattern-matches reference examples more than rules. All
three templates (P/C/M) must demonstrate the target patterns:

- **Concept**: `<h3>` sub-blocks (Regla #1, Regla #2, Trampa PAES)
- **WE1**: steps in `<details>/<summary>`, full scaffolding,
  verification step, micro-reinforcement closing line
- **WE2**: steps in `<details>/<summary>`, faded annotations,
  1-2 "¿cuánto da?" mental-fill cues, no verification step,
  micro-reinforcement closing line
- **QC1** (P-template): simple, single-concept
- **QC2** (P-template): integrative, multi-concept
- **QC feedback**: golden-rule closing ("Regla: si X, entonces Y")
- **Error patterns**: `<ul>` errors + `<p>` with ✅ checklist

### A2. Index-aware worked-example rules

**Files**: `prompts/shared.py`, `prompts/generation.py`

Split `_WORKED_EXAMPLE_RULES` into:

**`_WE1_RULES`** (full scaffolding — "I do"):
```
- Pasos numerados dentro de <details>/<summary>.
- <summary> tiene "Paso N:" + 1 frase corta del objetivo.
- Contenido del <details>: 1-2 oraciones con cálculo + "por qué".
- Último paso: verificación (comprobar resultado por otro camino).
- Cierra con micro-refuerzo: "Si obtuviste [X], vas bien — el
  punto clave fue [Y]."
- ~{budget} palabras.
```

**`_WE2_RULES`** (faded scaffolding — "We do"):
```
- Misma estructura <details>/<summary> que WE1.
- Menos anotaciones "por qué" — solo en el paso clave.
- Incluye 1-2 cues de predicción: "¿Cuánto da [subcálculo]?
  Piénsalo antes de abrir el siguiente paso."
- SIN paso de verificación (el estudiante lo hace solo).
- Cierra con micro-refuerzo.
- ~{budget} palabras.
```

Wire in `build_generation_rules(section_type, index)`:
- `"worked-example"` + index 1 → `_WE1_RULES`
- `"worked-example"` + index 2 → `_WE2_RULES`

### A3. Concept chunking rules

**File**: `prompts/shared.py`

Update `_CONCEPT_RULES`:
```
- Divide el concepto en micro-bloques con <h3> subtítulos.
- Cada <h3> cubre UNA sola idea o regla.
- Formato: <h3>título corto</h3> seguido de 1-2 oraciones +
  opcional mini-ejemplo de 1 línea.
- Si las familias de error incluyen confusiones de signos o
  notación, incluye un bloque <h3>Trampa PAES</h3> con
  ejemplo correcto vs incorrecto (2 líneas).
- ~{budget} palabras total entre todos los bloques.
```

### A4. Quick-check rules with golden rule + details wrapper

**File**: `prompts/shared.py`

Update `_QUICK_CHECK_RULES`:
```
- Feedback dentro de <details><summary>Ver explicación</summary>.
- El <p data-correct-option> DEBE terminar con "Regla: Si
  [situación], entonces [acción]."
- Cada <li> de distractor-rationale cierra con qué revisar
  la próxima vez.
- (resto de reglas existentes se mantiene)
```

### A5. Error patterns checklist format

**File**: `prompts/shared.py`

Update `_ERROR_PATTERNS_RULES`:
```
- Errores en <ul><li> (existente).
- Reemplaza el Tip PAES en prosa por un Checklist PAES:
  <p><strong>Checklist PAES</strong></p>
  <ul data-role="paes-checklist">
    <li>✅ [verificación 1]</li>
    <li>✅ [verificación 2]</li>
    <li>✅ [verificación 3]</li>
  </ul>
  Exactamente 3 ítems. Cada uno es 1 línea que el estudiante
  puede aplicar en 10 segundos bajo presión.
```

### A6. Planner: template-specific QC count + gradual complexity

**Files**: `prompts/planning.py`, `planner.py`, `models.py`

Planning prompt additions:
```
Per-template QC rules:
- P-template: EXACTAMENTE 2 quick-checks.
  QC1 = rápido, un solo concepto (20-30s).
  QC2 = integrador, combina conceptos (45-60s).
- C-template: 1-2 quick-checks.
- M-template: 2 quick-checks (1 procedimental + 1 conceptual).

Gradual complexity:
- WE2 agrega máximo UNA dimensión de dificultad nueva vs WE1.
  Dimensiones: tipo de número, número de variables, tipo de
  expresión, presencia de potencias. NO 3+ cambios de golpe.
```

Model change: `QuickCheckSpec.difficulty: str = "simple"` field.

Validation: `validate_plan()` warns if P-template has < 2 QCs.

### A7. Quality gate rubric updates

**File**: `prompts/validation.py`

Add sub-criteria:
- `brevity_cognitive_load`: "0 si concepto es un bloque sin
  sub-títulos h3"
- `step_rationale_clarity`: "0 si WE2 tiene la misma cantidad
  de anotaciones que WE1 (debe mostrar fading)"
- `feedback_quality`: "0 si feedback de QC no incluye 'Regla'"
- `quick_check_quality`: "Para P-template, penalizar si hay
  solo 1 QC cuando 2 son apropiados"

### A8. Structural validator updates

**File**: `html_validator.py`

- Concept section must contain >= 2 `<h3>` tags (new check).
- WE steps should use `<details>` wrappers (warning if absent).
- QC feedback should be inside `<details>` (warning if absent).
- P-template: warn if only 1 QC.

---

## 5. Part B — HTML interactivity contract additions

New data attributes and patterns the pipeline produces
(additions to spec section 6):

### New semantic attributes

| Attribute | Element | Purpose |
|-----------|---------|---------|
| `data-role="steps"` | `<ol>` in WE | Marks step list for renderer |
| `data-role="paes-checklist"` | `<ul>` in errors | Marks checklist for styling |
| `data-role="micro-reinforcement"` | `<p>` after WE steps | Self-check closing line |
| `data-role="prediction-cue"` | `<p>` in WE2 step | Mental-fill prompt |

### Progressive disclosure pattern

Every `<details>` in the HTML is a **renderer hint**:
- **Without renderer**: native browser toggle works
- **With React renderer**: renderer replaces `<details>` with
  controlled components (step-by-step reveal, option-click
  feedback)

The renderer identifies interactive regions by:
1. `section[data-block="worked-example"]` → step reveal mode
2. `section[data-block="quick-check"]` → MCQ interaction mode
3. `section[data-block="concept"] h3` → micro-block pagination
4. `details` anywhere → progressive disclosure

---

## 6. Part C — React renderer spec (separate workstream)

The renderer is a React component (`<MiniClassRenderer>`) that
takes `mini-class.html` as input and outputs an interactive lesson.

### Core behavior

```
<MiniClassRenderer
  html={miniClassHtml}
  onComplete={(analytics) => ...}
/>
```

### Section rendering modes

| `data-block` | Renderer behavior |
|--------------|-------------------|
| `objective` | Always visible. No interaction. |
| `concept` | Show one `<h3>` block at a time. "Continue" to next. |
| `worked-example` | Show problem statement. Steps revealed one-by-one via button or swipe. WE2 shows prediction cue before revealing answer. |
| `quick-check` | Options are clickable buttons. On selection: highlight correct/wrong, reveal feedback panel, disable further selection. |
| `error-patterns` | Fully visible. Checklist items styled distinctly. |
| `transition-to-adaptive` | Visible + "Start practice" CTA button. |

### QC interaction flow

1. Stem + 4 option buttons rendered. Feedback hidden.
2. Student taps option.
3. If correct: option turns green, feedback panel slides in.
   If wrong: selected turns red, correct turns green, feedback
   slides in showing distractor rationale for selected option.
4. "Regla de oro" line highlighted/boxed.
5. Options disabled after selection.

### WE step-reveal flow

1. Problem statement visible. First `<details>` auto-opens.
2. "Next step" button (or swipe) opens next `<details>`.
3. For WE2: prediction cue (`data-role="prediction-cue"`)
   shown as a prompt before the step answer reveals.
4. After all steps: micro-reinforcement line
   (`data-role="micro-reinforcement"`) highlighted.

### Analytics emitted

```typescript
interface LessonAnalytics {
  atom_id: string;
  total_time_seconds: number;
  steps_revealed: number;
  qc_responses: Array<{
    qc_index: number;
    selected_option: string;
    correct: boolean;
    time_to_answer_ms: number;
  }>;
  sections_viewed: string[];
}
```

### Renderer sizing

Estimated complexity: **~200-300 lines of React** (one component
with sub-components per section type). No external dependencies
beyond React. Parses the HTML with `DOMParser`, walks the tree,
renders React components based on `data-*` attributes.

---

## 7. Implementation order

```
Phase A: Pipeline prompt + reference changes
  A1. Rewrite reference examples (P/C/M) with all new patterns
  A2. Split WE rules (WE1 full / WE2 faded) in shared.py
  A3. Update concept rules (h3 chunking + Trampa PAES)
  A4. Update QC rules (golden rule + details wrapper)
  A5. Update error-patterns rules (checklist format)
  A6. Wire index-aware rules in generation.py
  A7. Add micro-reinforcement + prediction-cue rules

Phase B: Planner + model changes
  B1. Template-specific QC count in planning.py
  B2. Gradual complexity constraint in planning.py
  B3. QuickCheckSpec.difficulty field in models.py
  B4. validate_plan() P-template QC warning

Phase C: Validator + quality gate
  C1. Concept h3 count check in html_validator.py
  C2. details wrapper warnings in html_validator.py
  C3. Rubric sub-criteria in validation.py
  C4. P-template QC count warning

Phase D: Regenerate + verify
  D1. Regenerate A-M1-ALG-01-02
  D2. Diff old vs new lesson
  D3. Verify new rubric catches old version's problems

Phase E: React renderer (separate workstream)
  E1. <MiniClassRenderer> component skeleton
  E2. Section router (data-block → render mode)
  E3. QC interaction (option click → feedback)
  E4. WE step reveal (details → controlled)
  E5. Concept micro-block pagination
  E6. Analytics emission
  E7. Mobile responsive styling
```

Phases A-D are pipeline work (this workstream).
Phase E is frontend work (can start in parallel after A1).

---

## 8. Files touched

| File | Changes |
|------|---------|
| `prompts/reference_examples.py` | Full rewrite of P/C/M templates |
| `prompts/shared.py` | WE1/WE2 rules, concept, QC, error rules |
| `prompts/generation.py` | Index-aware rules, task details |
| `prompts/planning.py` | Template QC count, complexity constraint |
| `prompts/validation.py` | Rubric sub-criteria |
| `models.py` | QuickCheckSpec.difficulty |
| `planner.py` | Plan validation updates |
| `html_validator.py` | h3 check, details warnings, QC count |

No new pipeline files. No spec changes (all within allowed tags
and attributes). No new dependencies.

---

## 9. Risk assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Concept grows beyond 150-word budget | Low | Budget enforced; h3 blocks redistribute words |
| LLM ignores `<details>` wrapping | Med | Reference examples are strongest anchor |
| 2 QCs push duration past 7 min | Low | QC1 is 20-30s; net +1 min |
| Fading cues feel artificial | Low | LLM varies phrasing naturally |
| Rubric too strict post-update | Med | Start as warnings, promote to hard-fail |
| Renderer scope creep | Med | Spec is fixed above; ship MVP first |
