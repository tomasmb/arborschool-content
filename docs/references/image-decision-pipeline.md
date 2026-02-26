# Image Decision Pipeline

How we decide what visual content each question needs, which images can be
generated, and how each image type is produced or sourced.

## Overview

Image decisions happen at **two levels**:

1. **Atom-level tagging** — an offline analysis step that records what image
   types each atom's questions might need (`required_image_types` field in
   `atoms.json`).
2. **Question-level decision** — a per-question LLM call during Phase 3
   (Image Enrichment) that decides whether *this specific question* needs an
   image, and if so, which type.

The atom-level tags inform planning and coverage reporting. The question-level
decision drives the actual generation/search workflow.

---

## Phase 0: Atom-Level Image Tagging

**Module**: `app/kg/applicators/image_type_analyzer.py`

Before any questions are generated, every atom is analyzed by GPT-5.1 to
determine which image types its questions could benefit from.

### How it works

1. GPT-5.1 receives the atom's title, description, grades, difficulty levels,
   and `visual_benefit` hint.
2. It returns an array of image type strings drawn from the full taxonomy
   (both generatable and non-generatable types).
3. The result is written to the atom's `required_image_types` field in
   `atoms.json`.

### Example output

```json
{
  "atom_id": "3-PS2-4_atom_1",
  "title": "Identify needs solvable by magnets",
  "visual_benefit": "positive",
  "required_image_types": ["photo_realistic", "comparison_image"]
}
```

An atom with `visual_benefit: "negative"` or `"neutral"` typically receives
an empty array — text-only questions are sufficient.

### Generatability classification

Each tagged type is classified against `image_capabilities.json`:

| Status | Meaning |
|--------|---------|
| **Fully generatable** | All required types are in the `generatable` set |
| **Partially generatable** | Some types generatable, some require image bank |
| **Not generatable** | All required types need the image bank |
| **No images needed** | Empty array — text-only is sufficient |

This classification drives coverage dashboards and lets us see where image
bank gaps exist before running the pipeline.

---

## Phase 3: Per-Question Image Decision

**Module**: `app/questions/image_type_decision.py`

During question generation, Phase 3 (Image Enrichment) processes each
question plan individually. The decision is made by a **single LLM call**
— no hardcoded keyword matching.

### Decision flow

```
Question Plan + Atom
        │
        ▼
┌─────────────────────────┐
│  TableDetector Pre-Check │  ← Fast keyword + LLM fallback
└────────────┬────────────┘
             │
     ┌───────┴───────┐
     │ is_tabular?   │
     └───┬───────┬───┘
         │       │
    YES  │       │  NO
         ▼       ▼
   Return "none" ┌──────────────────────────┐
   (use QTI XML  │ ImageTypeDecider (LLM)   │  ← Single GPT-5.1 call
    <table>)     │ with image_capabilities  │
                 └────────────┬─────────────┘
                              │
                              ▼
                    ImageTypeDecision
                    ├─ needs_image: bool
                    ├─ image_type: string
                    ├─ generation_method: string
                    └─ description_hint: string
```

### Decision outputs

The LLM returns one of these `image_type` values:

| `image_type` | `generation_method` | What happens next |
|---|---|---|
| `coordinate_plane` | `generate` | SVG rendered programmatically |
| `gemini_compositional` | `generate` | Labeled diagram via Gemini |
| `photo_realistic` | `generate` | Photorealistic image via Gemini |
| `comparison_image` | `generate` | Side-by-side image via Gemini |
| `image_bank` | `search` | Search CCC API image bank |
| `none` | `none` | No image — text-only question |

### What the LLM considers

The decision prompt includes:

- **Our generation capabilities** — loaded from `image_capabilities.json`,
  listing what we *can* and *cannot* generate.
- **Decision rules** — only recommend images that genuinely help
  understanding; match image type to educational goal.
- **Table prohibition** — tabular content must be QTI XML `<table>`,
  never a generated image.
- **Completeness requirement** — if an image shows multiple options
  (A, B, C, D), all must be visible.

---

## Table Detection (Pre-Check)

**Module**: `app/diagrams/image_quality_validator.py` → `TableDetector`

Tables are **never** generated as images. They belong in QTI XML as
`<table>` elements. This is enforced by a two-stage pre-check that runs
*before* the image type LLM call.

### Stage 1: Fast keyword filter (no LLM)

Catches obvious cases immediately:

- "compare the properties"
- "data table" / "fill in the table" / "complete the table"
- "match each"
- "which has the highest/lowest"
- "list of characteristics"
- "properties table"
- "data showing"

If any of these appear in the combined plan + atom text, the decision is
`none` with reason "use QTI XML table instead". No LLM call needed.

### Stage 2: LLM verification (ambiguous cases only)

If softer keywords appear ("compare", "comparison", "classify",
"categories", "organize") but no strong match, an LLM call (low reasoning
effort) verifies whether the content is tabular or visual.

### Result

When tabular content is detected, the pipeline returns:

```python
ImageTypeDecision(
    needs_image=False,
    image_type="none",
    generation_method="none",
    reason="Tabular content (data) - use QTI XML table instead",
    description_hint="<suggested XML structure>",
)
```

The `description_hint` field carries a suggested XML table structure that
Phase 4 (QTI Generation) can use.

---

## Image Types: Full Taxonomy

### Generatable types

These are defined in `data/knowledge-graph/image_capabilities.json` under
`generatable` and are produced by our pipeline.

#### 1. `coordinate_plane` — Programmatic SVG

**Renderer**: `app/diagrams/enricher.py` → `DiagramEnricher`

- **What**: X-Y graphs, wave patterns, distance-time plots, amplitude /
  wavelength diagrams, data visualizations.
- **How**: LLM generates a diagram specification with actual data values.
  `CoordinatePlaneRenderer` converts the spec into a clean SVG.
- **Output**: SVG uploaded to S3.
- **Not AI-generated** — these are programmatically rendered from specs,
  so they are precise and consistent.

#### 2. `gemini_compositional` — Labeled Diagrams

**Renderer**: `app/diagrams/gemini_enricher.py` → `GeminiDiagramEnricher`

- **What**: Labeled part-whole diagrams — cells, anatomy, plant structures,
  earth layers, ecosystems, life cycles, food chains/webs, measurement tools
  (scales, balances, graduated cylinders, thermometers), lab equipment with
  readings, cross-sections.
- **Model**: `gemini-3-pro-image-preview`
- **Style**: Minimal — no titles, no headers, no explanatory text. Only
  essential labels pointing to parts.
- **Categories** (for prompt guidance and caching):
  `biology_cellular`, `anatomy`, `plant_structure`, `earth_science`,
  `ecosystem`, `life_cycle`, `measurement`, `labeled_diagram` (general).

#### 3. `photo_realistic` — Photorealistic Images

**Renderer**: `app/diagrams/photorealistic_enricher.py` → `PhotoRealisticEnricher`

- **What**: Professional nature/science photographs — animals, plants,
  landscapes, objects, weather phenomena.
- **Model**: `gemini-3-pro-image-preview`
- **Style**: No text, no labels, no watermarks. Clear composition, natural
  lighting, scientifically accurate.

#### 4. `comparison_image` — Side-by-Side Comparisons

**Renderer**: `app/diagrams/comparison_enricher.py` → `ComparisonEnricher`

- **What**: Before/after or side-by-side images showing two states, objects,
  or conditions — weathering/erosion, growth stages, species comparisons,
  contrasting conditions.
- **Model**: `gemini-3-pro-image-preview`
- **Style**: Simple labels (e.g. "Before / After", "A / B"). Both compared
  elements **must** be visible — automatic validation fail if one is missing.

### Non-generatable types

These are defined under `not_generatable` in `image_capabilities.json`.
Gemini cannot reliably produce them; the pipeline falls back to the image
bank or text-only.

| Type | Description | Why not generatable |
|---|---|---|
| `force_diagram` | Free-body diagrams, push/pull arrows, friction, tension, gravity vectors | Gemini unreliable for relational/force-based diagrams with arrows |
| `circuit_diagram` | Electrical circuits with batteries, wires, bulbs, switches | Requires precise schematic symbols and connections |
| `vector_diagram` | Velocity arrows, acceleration vectors, resultant vectors | Gemini unreliable for directional/magnitude-dependent diagrams |
| `ray_diagram` | Light paths, reflection angles, refraction, lens/mirror diagrams | Requires precise geometric relationships and angles |
| `chemical_reaction` | Molecular diagrams, bond formation, electron transfer | Requires accurate molecular representations |
| `momentum_diagram` | Collision diagrams, before/after motion, energy transfer arrows | Requires precise before/after relationships with arrows |

**Common thread**: all require exact geometric positioning, standardized
symbols, or precise angular relationships that generative models cannot
reliably produce.

---

## Generation Flow (Gemini Types)

All three Gemini image types (`gemini_compositional`, `photo_realistic`,
`comparison_image`) share the same base infrastructure.

**Base class**: `app/diagrams/base_gemini_enricher.py` → `BaseGeminiEnricher`

### Three-step process

```
1. Description Generation (GPT-5.1, medium reasoning)
   └─ Produces: title, description, alt_text, key_labels, forbidden_elements

2. Image Generation (Gemini 3.1 Pro)
   └─ Produces: base64-encoded PNG/JPEG

3. Validation (GPT-5.1 Vision, high reasoning)
   └─ Checks: accuracy, completeness, clarity, educational_value
   └─ All scores must be ≥ 7/10
```

### Retry logic

- **Max retries**: 1 (initial attempt + 1 retry)
- If validation fails, the description is augmented with the specific issues
  found, and generation is retried.
- If both attempts fail, the image type returns `None` and the orchestrator
  falls back (see below).

---

## Image Bank (Search Fallback)

**Module**: `app/questions/image_fetcher.py` → `ImageFetcher`

The image bank is the CCC API's collection of pre-analyzed educational
images. It serves two roles:

1. **Primary source** for non-generatable types (force diagrams, circuits,
   etc.) when the LLM explicitly chooses `image_bank`.
2. **Fallback** when a Gemini generation attempt fails.

### How search works

1. Infer subject branch from atom content (physics, biology, chemistry,
   earth_science).
2. Query the CCC API (`api.commoncorecrawl.com/graphql`) for images matching
   the scenario keywords.
3. Return top 5 candidates ranked by relevance score.
4. `ImageValidator` uses an LLM to select the best match and validates it
   with vision (or description matching).

---

## Fallback Chain

When the primary generation path doesn't succeed, the orchestrator
(`ImageEnricher`) follows a strict fallback chain:

```
1. Primary generator (based on image_type decision)
   │
   ├─ Success → Validate → Upload to S3 → Done
   │
   └─ Failure ──┐
                │
2. Image bank search (if not already the primary)
   │
   ├─ Success → LLM selects best → Vision validates → Done
   │
   └─ Failure ──┐
                │
3. Text-only fallback
   └─ If plan references visuals → LLM rewrites to remove visual refs
   └─ If plan is already text-compatible → mark as text-only
```

### Text-only rewriting

**Module**: `app/questions/image_validator.py` → `ImageValidator`

When falling back to text-only, the system checks if the question plan
contains visual references ("diagram", "picture", "shows", "look at", etc.).
If so, an LLM rewrites the scenario and question descriptions to be fully
self-contained without any visual references:

- "Look at the diagram showing the digestive system" →
  "When you eat a sandwich, it travels through your digestive system..."
- "Two drawings show arrows pointing from food..." →
  "A sandwich is eaten. Where does the body break down food?"

The rewritten plan is flagged with `rewritten_for_text_only: true` so
downstream phases know it was adjusted.

---

## Orchestration

**Module**: `app/questions/image_enricher.py` → `ImageEnricher`

The `ImageEnricher` class owns the full enrichment flow for a batch of
question plans:

1. Processes plans in parallel (`ThreadPoolExecutor`, default 5 workers).
2. For each plan:
   - Calls `ImageTypeDecider.decide_image_type()` (single LLM decision).
   - Routes to the appropriate generator via `_route_to_generator()`.
   - On failure, tries image bank.
   - On total failure, falls back to text-only.
3. Uploads generated images to S3.
4. Returns enriched plans with image URLs, alt text, and metadata.

### Generator routing

| `image_type` | Generator class | Output |
|---|---|---|
| `coordinate_plane` | `DiagramEnricher` | SVG (programmatic) |
| `gemini_compositional` | `GeminiDiagramEnricher` | PNG/JPEG (Gemini) |
| `photo_realistic` | `PhotoRealisticEnricher` | PNG/JPEG (Gemini) |
| `comparison_image` | `ComparisonEnricher` | PNG/JPEG (Gemini) |
| `image_bank` | `ImageFetcher` + `ImageValidator` | Existing URL |
| `none` | — | No image |

Each generator can be toggled via constructor flags
(`enable_diagram_generation`, `enable_gemini_diagrams`,
`enable_photorealistic`, `enable_comparison`).

---

## Validation Standards

### Gemini-generated images

All scores must be **≥ 7/10**:

| Criterion | What it checks |
|---|---|
| **Accuracy** | Scientifically correct content |
| **Completeness** | All required elements visible (all labels, all options) |
| **Clarity** | Clean composition, easy to read |
| **Educational value** | Genuinely helps understanding |

Additional checks:
- All required labels present, no duplicates.
- No forbidden elements (titles, headers, explanatory text).
- For comparison images: both compared elements must be visible.

### Image bank images

Validated by `ImageValidator` using:
- LLM selection of best candidate from search results.
- Vision-based relevance check (or description-based fallback).
- Relevance score, visual match score, educational value score.

---

## Key Files

| File | Purpose |
|---|---|
| `data/knowledge-graph/image_capabilities.json` | Defines generatable vs non-generatable types |
| `app/kg/applicators/image_type_analyzer.py` | Atom-level image type tagging |
| `app/questions/image_type_decision.py` | Per-question LLM decision |
| `app/diagrams/image_quality_validator.py` | Table detection pre-check |
| `app/questions/image_enricher.py` | Phase 3 orchestrator |
| `app/diagrams/base_gemini_enricher.py` | Base class for all Gemini enrichers |
| `app/diagrams/gemini_enricher.py` | Compositional diagram generation |
| `app/diagrams/photorealistic_enricher.py` | Photorealistic image generation |
| `app/diagrams/comparison_enricher.py` | Comparison image generation |
| `app/diagrams/enricher.py` | Coordinate plane SVG generation |
| `app/questions/image_fetcher.py` | Image bank API client |
| `app/questions/image_validator.py` | Image validation + text-only fallback |
| `app/diagrams/gemini_prompts.py` | Prompt templates for Gemini generation |
| `app/diagrams/gemini_detection.py` | Category mappings for cache/prompt guidance |
