# Arbor Content Dashboard - Full Plan

> Admin dashboard for managing the PAES M1 content pipeline.  
> Design reference: Linear / Notion (clean, minimal, functional)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Next.js Frontend                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ Subjects │ │ Pipeline │ │  Tests   │ │   Sync   │           │
│  │ Overview │ │  Runner  │ │  Viewer  │ │ Controls │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST API
┌────────────────────────────▼────────────────────────────────────┐
│                     FastAPI Backend                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │  /data   │ │/pipelines│ │  /costs  │ │  /sync   │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└────────────────────────────┬────────────────────────────────────┘
                             │ File System (source of truth)
┌────────────────────────────▼────────────────────────────────────┐
│                      app/data/                                  │
│  temarios/ → standards/ → atoms/ → pruebas/ → finalizadas/      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Concept: Pipeline Dependencies

The dashboard enforces a natural workflow where each phase unlocks the next.
Status is derived from **file existence** (no separate state DB needed).

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Temario   │────▶│  Standards  │────▶│    Atoms    │
│   (PDF→JSON)│     │ (per eje)   │     │(knowledge   │
└─────────────┘     └─────────────┘     │   graph)    │
                                        └──────┬──────┘
                                               │
        ┌──────────────────────────────────────┘
        │ Knowledge Graph Ready
        ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Raw Test   │────▶│ PDF Split   │────▶│  PDF→QTI    │
│    PDF      │     │(per question│     │(per question│
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                                        ┌──────▼──────┐
                                        │ Finalization│
                                        │(copy to     │
                                        │finalizadas/)│
                                        └──────┬──────┘
                                               │
        ┌──────────────────────────────────────┘
        │ Requires Atoms + Finalized Questions
        ▼
┌─────────────┐     ┌─────────────┐
│  Tagging    │────▶│  Variants   │
│(atoms→Q)    │     │(AI-generated│
└──────┬──────┘     │alternatives)│
       │            └─────────────┘
       │
       │ ALL questions tagged unlocks:
       ▼
┌─────────────┐     ┌─────────────┐
│Question Sets│────▶│   Lessons   │
│(~60 per atom│     │(1 per atom) │
│ low/med/hi) │     │             │
└─────────────┘     └──────┬──────┘
       │                   │
       └─────────┬─────────┘
                 ▼
          ┌─────────────┐
          │   DB Sync   │
          │(to prod app)│
          └─────────────┘
```

**Key unlock conditions:**
- **Question Sets**: Requires the atom to be defined AND all test questions tagged
- **Lessons**: Requires atom + (question set exists OR all test questions tagged)

### Dependency Matrix

| Pipeline | Requires | Produces |
|----------|----------|----------|
| Temario Parse | Raw PDF | `temarios/json/*.json` |
| Standards Gen | Temario JSON | `standards/*.json` |
| Atoms Gen | Standards JSON | `atoms/*.json` |
| PDF Split | Raw test PDF | `procesadas/{test}/pdf/*.pdf` |
| PDF→QTI | Split PDFs | `procesadas/{test}/qti/*/question.xml` |
| Finalize | Validated QTI | `finalizadas/{test}/qti/*` |
| Tagging | Atoms + Finalized Q | `finalizadas/{test}/qti/*/metadata_tags.json` |
| Variants | Tagged Questions | `alternativas/{test}/Q*/approved/*` |
| Question Sets | Atom + ALL questions tagged | `question_sets/{atom_id}/*.json` |
| Lessons | Atom + (Q Set OR all tagged) | `lessons/{atom_id}.json` |
| DB Sync | All finalized content | PostgreSQL + S3 |

**⚠️ Backend Gaps Identified:**

| Gap | Description | Status |
|-----|-------------|--------|
| **Variant Sync** | `app/sync/extractors.py` only extracts from `finalizadas/`, not `alternativas/`. Variants exist but are never synced to DB. | ✅ **Implemented** (use `--include-variants` flag) |
| **Question Sets** | No generation pipeline exists yet. | Future |
| **Lessons** | No generation pipeline exists yet. | Future |

---

## 3. Page Structure

### 3.1 Home / Dashboard

**Purpose:** Quick overview of content status across all subjects.

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  Arbor Content Dashboard                        [Sync ▾]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │   PAES M1       │  │   PAES M2       │  (future)        │
│  │   2026          │  │   (Coming)      │                  │
│  │   ─────────     │  │                 │                  │
│  │   ✓ Temario     │  │   🔒 Locked     │                  │
│  │   ✓ Standards   │  │                 │                  │
│  │   ✓ Atoms (127) │  │                 │                  │
│  │   ─────────     │  │                 │                  │
│  │   4 Tests       │  │                 │                  │
│  │   176 Questions │  │                 │                  │
│  │   ─────────     │  │                 │                  │
│  │   [Enter →]     │  │                 │                  │
│  └─────────────────┘  └─────────────────┘                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Stats shown per subject:**
- Temario status (exists / missing)
- Standards count
- Atoms count
- Tests count
- Questions count (finalized)
- Tagging completion %

---

### 3.2 Subject Detail Page (`/subjects/paes-m1-2026`)

**Purpose:** Central hub for a single subject. Shows pipeline progress and actions.

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  ← Back    PAES M1 2026                    [Knowledge Graph]│
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  KNOWLEDGE GRAPH PIPELINE                                   │
│  ════════════════════════                                   │
│                                                             │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐          │
│  │ 1. Temario │──▶│2. Standards│──▶│  3. Atoms  │          │
│  │ ✓ Complete │   │ ✓ Complete │   │ ✓ Complete │          │
│  │            │   │   21 stds  │   │  127 atoms │          │
│  │ [View JSON]│   │[View] [+]  │   │[View] [+]  │          │
│  └────────────┘   └────────────┘   └────────────┘          │
│                                                             │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  TESTS & QUESTIONS                                          │
│  ════════════════                                           │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Test                    │ Raw │Split│ QTI │Tag │Var  │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │ prueba-invierno-2025    │  ✓  │ 65  │ 65  │ 57 │ 14  │  │
│  │ prueba-invierno-2026    │  ✓  │ 65  │ 42  │  0 │  0  │  │
│  │ seleccion-regular-2025  │  ✓  │ 45  │ 45  │ 25 │ 19  │  │
│  │ seleccion-regular-2026  │  ✓  │ 45  │ 32  │  0 │  0  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  [+ Add New Test]                                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Interactions:**
- Click test row → Test detail page
- `[Knowledge Graph]` button → Opens graph modal/drawer
- `[+]` buttons → Run generation pipeline for that phase

---

### 3.3 Knowledge Graph View (Modal/Drawer)

**Purpose:** Visualize atoms and their prerequisite relationships.

**Features:**
- Nodes = Atoms (color by `tipo_atomico` or `eje`)
- Edges = `prerrequisitos` relationships (directed arrows)
- Click node → Show atom details sidebar
- Filter by eje (tabs or dropdown)
- Zoom/pan controls
- Stats panel:
  - Total atoms
  - Atoms per eje
  - Atoms per standard (table)
  - Total prerequisite links
  - Orphan atoms (no prereqs, not prereq of anything)

**Library:** React Flow (best for interactive node graphs)

---

### 3.4 Test Detail Page (`/subjects/paes-m1-2026/tests/prueba-invierno-2025`)

**Purpose:** Manage individual test questions through the pipeline.

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  ← Back    prueba-invierno-2025                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Pipeline Status                                            │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐   │
│  │Raw PDF │▶│ Split  │▶│PDF→QTI │▶│Finalize│▶│  Tag   │   │
│  │   ✓    │ │ 65/65  │ │ 65/65  │ │ 57/65  │ │ 57/57  │   │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘   │
│                                                             │
│  Actions: [Run PDF Split] [Run QTI Conv] [Run Tagging]      │
│                                                             │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  Questions                              Filter: [All ▾]     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Q# │ Split │ QTI │ Final │ Tagged │ Atoms    │ Vars  │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │ Q1 │   ✓   │  ✓  │   ✓   │   ✓    │ 2 atoms  │  2    │  │
│  │ Q2 │   ✓   │  ✓  │   ✓   │   ✓    │ 1 atom   │  0    │  │
│  │ Q3 │   ✓   │  ✓  │   ✗   │   -    │ -        │  -    │  │
│  │ ...│       │     │       │        │          │       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Selected: 3 questions   [Generate Variants] [View QTI]     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Interactions:**
- Click question row → Question detail panel
- Checkbox multi-select for batch operations
- Action buttons are disabled when prerequisites not met

---

### 3.5 Question Detail Panel (Slide-over)

**Purpose:** View/edit individual question details.

**Sections:**
1. **QTI Preview** - Rendered question (stem + options)
2. **Metadata** - Difficulty, correct answer, source info
3. **Atom Tags** - Linked atoms with relevance
4. **Feedback** - Per-option feedback
5. **Variants** - List of approved variants with:
   - Variant ID (e.g., Q1_v1, Q1_v2)
   - Preview button (renders variant QTI)
   - Sync status (synced to DB / pending)
   - Change description from `metadata_tags.json`
6. **Actions** - Re-tag, Generate Variants, etc.

**Variant Sub-panel (when clicking a variant):**
- Side-by-side comparison: Original ↔ Variant
- Validation result (APROBADA/RECHAZADA)
- Calculation steps from validation
- Option to delete variant (with confirmation)

---

### 3.6 Atoms Page (`/subjects/paes-m1-2026/atoms`)

**Purpose:** Browse atoms and manage Question Sets / Lessons generation.

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  ← Back    Atoms (127)                   [Generate All Q Sets]│
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Filter: [All Ejes ▾]  [All Standards ▾]   Search: [____]   │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ ID          │ Title              │ Eje  │Q Set│Lesson│  │
│  ├──────────────────────────────────────────────────────┤  │
│  │A-M1-ALG-01-01│Traducción bidir... │ ALG  │ 60  │  ✓   │  │
│  │A-M1-ALG-01-02│Evaluación de exp...│ ALG  │ 60  │  ✓   │  │
│  │A-M1-ALG-01-03│Reducción términos..│ ALG  │  -  │  -   │  │
│  │ ...          │                    │      │     │      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Selected: 5 atoms    [Generate Q Sets] [Generate Lessons]  │
│                                                             │
│  ─────────────────────────────────────────────────────────  │
│  Unlock Status:                                             │
│  ✓ All test questions tagged (176/176)                     │
│  → Question Sets & Lessons generation enabled               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- Filter by eje, standard
- Search by title/ID
- Show Q Set count (0 = not generated, 60 = complete)
- Show Lesson status (✓ = exists, - = not generated)
- Multi-select for batch operations
- Bulk "Generate All" button
- Shows unlock status (are all questions tagged?)

**Atom Detail (slide-over when clicking row):**
- Full atom data (description, criteria, examples)
- Prerequisites list (with links)
- Dependent atoms (what uses this as prereq)
- Question Set status & generation button
- Lesson status & generation button
- Linked test questions (from tagging)

---

### 3.7 Pipeline Runner Page (`/pipelines`)

**Purpose:** Central place to run any pipeline with parameter controls.

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  Pipeline Runner                                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Select Pipeline: [Standards Generation ▾]                  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Standards Generation                                 │   │
│  │                                                      │   │
│  │ Temario:  [temario-paes-m1-invierno-y-regular ▾]    │   │
│  │ Eje:      [algebra_y_funciones ▾]                   │   │
│  │ Options:  ☐ Skip per-unidad validation              │   │
│  │           ☐ Skip per-eje validation                 │   │
│  │                                                      │   │
│  │ ─────────────────────────────────────────────────── │   │
│  │ Estimated Cost                                       │   │
│  │                                                      │   │
│  │ Model: gemini-3-pro-preview                         │   │
│  │ Input tokens: ~15,000                               │   │
│  │ Output tokens: ~8,000                               │   │
│  │ Estimated: $0.35 - $0.50                            │   │
│  │                                                      │   │
│  │ [Run Pipeline]                                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Recent Runs                                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Pipeline          │ Started     │ Status   │ Cost   │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ Variant Gen Q1-Q5 │ 2 min ago   │ Running  │ $0.12  │   │
│  │ Tagging batch     │ 15 min ago  │ Complete │ $0.45  │   │
│  │ PDF→QTI Q42-Q65   │ 1 hour ago  │ Complete │ $0.78  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### 3.8 Sync Page (`/sync`)

**Purpose:** Control database synchronization.

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  Database Sync                                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ⚠️  This will modify the production database.              │
│                                                             │
│  Entities to sync:                                          │
│  ☑ Standards (21)                                          │
│  ☑ Atoms (127)                                             │
│  ☑ Tests (4)                                               │
│  ☑ Questions - Official (176)                              │
│  ☑ Questions - Variants (89)                               │
│  ☐ Upload images to S3                                     │
│                                                             │
│  [Preview Changes (Dry Run)]                                │
│                                                             │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  Preview Results:                                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Table          │ Insert │ Update │ Delete │ Total   │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ subjects       │   0    │   0    │   0    │    1    │   │
│  │ standards      │   2    │   0    │   0    │   21    │   │
│  │ atoms          │   5    │   3    │   0    │  127    │   │
│  │ questions      │  12    │   0    │   0    │  176    │   │
│  │ question_atoms │  24    │   0    │   0    │  312    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [Execute Sync]  ← Requires confirmation modal              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. API Endpoints

### 4.1 Data Reading

```
GET  /api/overview
     → { subjects: [...], stats: {...} }

GET  /api/subjects/{subject_id}
     → { temario, standards, atoms, tests }

GET  /api/subjects/{subject_id}/temario
     → Temario JSON content

GET  /api/subjects/{subject_id}/standards
     → Standards list with atom counts

GET  /api/subjects/{subject_id}/atoms
     → Atoms list with filters (eje, standard_id)
     → Includes question_set_count, has_lesson for each atom

GET  /api/subjects/{subject_id}/atoms/{atom_id}
     → Full atom detail with prereqs, dependents, linked questions

GET  /api/subjects/{subject_id}/atoms/graph
     → { nodes: [...], edges: [...] } for React Flow

GET  /api/subjects/{subject_id}/atoms/unlock-status
     → { all_questions_tagged: bool, tagged_count, total_count }

GET  /api/subjects/{subject_id}/tests
     → Test list with pipeline status

GET  /api/subjects/{subject_id}/tests/{test_id}
     → Detailed test status with all questions

GET  /api/subjects/{subject_id}/tests/{test_id}/questions/{q_id}
     → Full question data (QTI, metadata, variants)
```

### 4.2 Pipeline Execution

```
POST /api/pipelines/estimate
     Body: { pipeline: "variant_gen", params: {...} }
     → { model, input_tokens, output_tokens, estimated_cost }

POST /api/pipelines/run
     Body: { pipeline: "...", params: {...}, confirmation_token: "..." }
     → { job_id, status: "started" }

GET  /api/pipelines/jobs
     → List of recent jobs with status

GET  /api/pipelines/jobs/{job_id}
     → { status, progress, completed_items, failed_items, logs, result, cost }

POST /api/pipelines/jobs/{job_id}/resume
     Body: { mode: "remaining" | "failed_only" }
     → { job_id, status: "resumed", items_to_process: [...] }

DELETE /api/pipelines/jobs/{job_id}
     → Cancels running job or clears completed job from history
```

### 4.3 Sync

```
POST /api/sync/preview
     Body: { 
       entities: ["atoms", "questions", "variants"], 
       upload_images: false 
     }
     → { tables: [...], summary: {...} }

POST /api/sync/execute
     Body: { entities: [...], upload_images: bool, confirm: true }
     → { results: {...} }
```

**Note:** `variants` are questions with `source: "alternate"` and `parent_question_id` set.
They inherit atom tags from their parent official question.

---

## 5. Pipeline Definitions

### 5.1 Temario Parse

| Field | Value |
|-------|-------|
| **ID** | `temario_parse` |
| **Requires** | Raw PDF in `temarios/pdf/` |
| **Produces** | JSON in `temarios/json/` |
| **AI Cost** | No |
| **Parameters** | `pdf_path` |

### 5.2 Standards Generation

| Field | Value |
|-------|-------|
| **ID** | `standards_gen` |
| **Requires** | Temario JSON |
| **Produces** | Standards JSON |
| **AI Cost** | Yes (Gemini) |
| **Parameters** | `temario_path`, `eje` (optional, all if omitted) |

### 5.3 Atoms Generation

| Field | Value |
|-------|-------|
| **ID** | `atoms_gen` |
| **Requires** | Standards JSON |
| **Produces** | Atoms JSON |
| **AI Cost** | Yes (Gemini) |
| **Parameters** | `standards_path`, `standard_ids` (optional) |

### 5.4 PDF Split

| Field | Value |
|-------|-------|
| **ID** | `pdf_split` |
| **Requires** | Raw test PDF in `pruebas/raw/` |
| **Produces** | Individual PDFs in `procesadas/{test}/pdf/` |
| **AI Cost** | Yes (OpenAI for segmentation) |
| **Parameters** | `test_id`, `pdf_path` |

### 5.5 PDF → QTI

| Field | Value |
|-------|-------|
| **ID** | `pdf_to_qti` |
| **Requires** | Split PDFs |
| **Produces** | QTI XML in `procesadas/{test}/qti/` |
| **AI Cost** | Yes (Gemini) |
| **Parameters** | `test_id`, `question_ids` (optional) |

### 5.6 Finalization

| Field | Value |
|-------|-------|
| **ID** | `finalize` |
| **Requires** | Validated QTI |
| **Produces** | Files in `finalizadas/{test}/qti/` |
| **AI Cost** | No |
| **Parameters** | `test_id`, `question_ids` |

### 5.7 Question Tagging

| Field | Value |
|-------|-------|
| **ID** | `tagging` |
| **Requires** | Atoms JSON + Finalized questions |
| **Produces** | `metadata_tags.json` per question |
| **AI Cost** | Yes (Gemini) |
| **Parameters** | `test_id`, `question_ids` (optional - tags all if omitted) |
| **Batch** | Yes - can tag all questions or a selected subset |

**Batch modes:**
- Tag all untagged questions in a test
- Tag selected questions (multi-select in UI)
- Re-tag specific questions (overwrites existing tags)

### 5.8 Variant Generation

| Field | Value |
|-------|-------|
| **ID** | `variant_gen` |
| **Requires** | Tagged questions |
| **Produces** | Variants in `alternativas/{test}/Q*/approved/` |
| **AI Cost** | Yes (Gemini) |
| **Parameters** | `test_id`, `question_ids`, `variants_per_question` |

**Output structure per variant:**
```
alternativas/{test_id}/Q{n}/approved/Q{n}_v{m}/
├── question.xml         # QTI 3.0 XML
├── variant_info.json    # Source reference: { source_question_id, source_test_id }
└── metadata_tags.json   # Inherits atoms from parent, has validation info
```

**Variant ID format:** `alt-{parent_question_id}-{seq}` (e.g., `alt-prueba-invierno-2025-Q1-001`)

### 5.9 Question Sets (PP100)

Generates ~60 practice questions per atom distributed across difficulty levels.

| Field | Value |
|-------|-------|
| **ID** | `question_sets` |
| **Requires** | Atom defined + ALL test questions parsed & tagged (across all tests) |
| **Produces** | `question_sets/{atom_id}/*.json` (~60 questions: low/medium/high) |
| **AI Cost** | Yes (Gemini) |
| **Parameters** | `atom_ids` (single or bulk), `questions_per_difficulty` (default: 20) |
| **Batch** | Yes - can generate for single atom or bulk (all atoms) |

**Output per atom:**
- ~20 low difficulty questions
- ~20 medium difficulty questions  
- ~20 high difficulty questions

**Unlock condition:**
- The specific atom must be defined in `atoms/*.json`
- ALL finalized test questions must be tagged (not just for this atom)
- This ensures the AI has context from real exam questions when generating

### 5.10 Lessons

Generates one micro-lesson per atom with worked examples.

| Field | Value |
|-------|-------|
| **ID** | `lessons` |
| **Requires** | Atom defined + (Question Set generated OR same prereqs as Question Sets) |
| **Produces** | `lessons/{atom_id}.json` (worked example, explanation) |
| **AI Cost** | Yes (Gemini) |
| **Parameters** | `atom_ids` (single or bulk) |
| **Batch** | Yes - can generate for single atom or bulk |

**Unlock condition (either):**
- Question Set for this atom already generated, OR
- ALL test questions parsed & tagged (same prereq as Question Sets)

This allows lessons to be generated in parallel with or after question sets.

---

## 6. Risk Controls & Error Recovery

### 6.1 Cost Confirmation Modal

Triggered for any AI pipeline. Shows:
- Model name
- Estimated token usage
- Estimated cost range
- "Proceed" / "Cancel" buttons

### 6.2 Dangerous Action Modal

Triggered for:
- Database sync (non-dry-run)
- Overwriting existing content
- Deleting files

Shows warning with explicit confirmation checkbox.

### 6.3 Blocked Actions

The UI disables buttons when:
- Prerequisites not met (e.g., can't tag if no atoms)
- Content already exists (shows "Overwrite?" option)

### 6.4 Partial Progress & Resume

**Critical requirement:** Never lose completed work when a pipeline fails midway.

**Implementation:**
- Each pipeline saves progress after each item (question, atom, etc.)
- Progress is persisted to a job state file: `app/data/.jobs/{job_id}.json`
- If a job fails or is interrupted, the partial results are preserved

**Job state file structure:**
```json
{
  "job_id": "tag-2026-01-15-abc123",
  "pipeline": "tagging",
  "status": "failed",
  "started_at": "2026-01-15T10:30:00Z",
  "failed_at": "2026-01-15T10:45:00Z",
  "params": { "test_id": "prueba-invierno-2025", "question_ids": ["Q1", "Q2", ...] },
  "progress": {
    "total": 65,
    "completed": 42,
    "failed": 1,
    "remaining": 22
  },
  "completed_items": ["Q1", "Q2", ..., "Q42"],
  "failed_items": [{ "id": "Q43", "error": "JSON parse error" }],
  "error": "API rate limit exceeded"
}
```

**UI for resume:**
- Show "Resume" button next to failed/interrupted jobs
- Resume skips already-completed items
- Display which items were completed vs. remaining
- Option to retry failed items only

```
┌─────────────────────────────────────────────────────────────┐
│  ⚠️ Job Failed: Tagging prueba-invierno-2025                │
│                                                             │
│  Progress: 42/65 completed (1 failed)                       │
│  Error: API rate limit exceeded                             │
│                                                             │
│  [Resume Remaining (22)] [Retry Failed (1)] [View Details]  │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Next.js 14+ (App Router), TypeScript |
| **Styling** | Tailwind CSS + shadcn/ui |
| **Graph** | React Flow |
| **Tables** | TanStack Table |
| **Backend** | FastAPI, Pydantic v2 |
| **Process** | Python subprocess (simple polling) |
| **State** | File-based (no additional DB) |

---

## 8. Project Structure

```
arborschool-content/
├── app/                        # Existing Python code
│   ├── data/                   # All data files
│   ├── atoms/
│   ├── standards/
│   ├── tagging/
│   ├── question_variants/
│   ├── pruebas/
│   ├── sync/
│   └── ...
│
├── api/                        # NEW: FastAPI backend
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry
│   ├── config.py               # Settings, paths
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── overview.py         # GET /api/overview
│   │   ├── subjects.py         # Subject/temario/standards/atoms
│   │   ├── tests.py            # Tests and questions
│   │   ├── pipelines.py        # Pipeline execution
│   │   └── sync.py             # DB sync
│   ├── services/
│   │   ├── __init__.py
│   │   ├── status_tracker.py   # Compute status from files
│   │   ├── cost_estimator.py   # Estimate AI costs
│   │   └── pipeline_runner.py  # Execute pipelines
│   └── schemas/
│       ├── __init__.py
│       └── api_models.py       # Pydantic response models
│
├── frontend/                   # NEW: Next.js app
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx            # Dashboard home
│   │   ├── subjects/
│   │   │   └── [id]/
│   │   │       ├── page.tsx    # Subject detail
│   │   │       ├── atoms/
│   │   │       │   └── page.tsx  # Atoms list + Q Set/Lesson mgmt
│   │   │       └── tests/
│   │   │           └── [testId]/
│   │   │               └── page.tsx
│   │   ├── pipelines/
│   │   │   └── page.tsx
│   │   └── sync/
│   │       └── page.tsx
│   ├── components/
│   │   ├── ui/                 # shadcn components
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   └── Header.tsx
│   │   ├── dashboard/
│   │   │   ├── SubjectCard.tsx
│   │   │   └── StatsGrid.tsx
│   │   ├── knowledge-graph/
│   │   │   ├── GraphView.tsx
│   │   │   └── AtomNode.tsx
│   │   ├── atoms/
│   │   │   ├── AtomsTable.tsx
│   │   │   ├── AtomDetailPanel.tsx
│   │   │   └── UnlockStatus.tsx
│   │   ├── tests/
│   │   │   ├── TestTable.tsx
│   │   │   └── QuestionPanel.tsx
│   │   ├── pipelines/
│   │   │   ├── PipelineForm.tsx
│   │   │   ├── CostModal.tsx
│   │   │   └── JobResumeCard.tsx
│   │   └── sync/
│   │       └── SyncPreview.tsx
│   ├── lib/
│   │   ├── api.ts              # API client
│   │   └── utils.ts
│   ├── package.json
│   ├── tailwind.config.ts
│   └── tsconfig.json
│
├── docs/
│   └── specifications/
│       └── frontend-dashboard-plan.md  # This file
│
└── pyproject.toml
```

---

## 9. Backend Work Required

Before the frontend can fully function, these backend gaps need to be addressed:

### 9.1 Variant Extraction & Sync ✅ IMPLEMENTED

**Problem:** Variants are generated to `alternativas/` but never synced to DB.

**Solution implemented (2026-02-03):**

- `app/sync/extractors.py`: Added `ExtractedVariant` dataclass and `extract_variants()` function
- `app/sync/transformers.py`: Added `transform_variant()` function, updated `build_sync_payload()`
- `app/sync/scripts/sync_to_db.py`: Added `--include-variants` flag

**Usage:**
```bash
# Sync with variants
python -m app.sync.scripts.sync_to_db --include-variants

# Dry run first
python -m app.sync.scripts.sync_to_db --include-variants --dry-run

# Sync only variants
python -m app.sync.scripts.sync_to_db --only variants
```

**Variant ID format:** `alt-{test_id}-Q{n}-{seq:03d}` (e.g., `alt-prueba-invierno-2025-Q1-001`)

### 9.2 Question Sets Pipeline (FUTURE)

**Not yet implemented.** Will need:
- `app/question_sets/` module
- Generation prompts for creating PP100 questions
- Validation pipeline
- Output to `app/data/question_sets/{atom_id}/`

### 9.3 Lessons Pipeline (FUTURE)

**Not yet implemented.** Will need:
- `app/lessons/` module
- Generation prompts for worked examples
- Output to `app/data/lessons/{atom_id}.json`

---

## 10. Implementation Phases

### Phase 0: Backend Prerequisites ✅ COMPLETE
- [x] Implement `extract_variants()` in `app/sync/extractors.py`
- [x] Update `transformers.py` to handle variants with `parent_question_id`
- [x] Update sync script to include variants (`--include-variants` flag)
- [ ] Test variant sync with dry-run

### Phase 1: Foundation (API + Scaffold) ✅ COMPLETE
- [x] FastAPI skeleton with config (`api/`)
- [x] `GET /api/overview` - basic stats from files
- [x] `GET /api/subjects/{id}` - read temario/standards/atoms
- [x] Next.js scaffold with routing (`frontend/`)
- [x] Basic layout (sidebar, header)
- [x] Home page with subject cards

### Phase 2: Content Browsing ✅ MOSTLY COMPLETE
- [x] Subject detail page
- [x] Standards list view (embedded in subject detail)
- [x] Atoms list view with filters
- [x] Tests table with status columns
- [ ] Question detail slide-over (placeholder only)

### Phase 3: Knowledge Graph ✅ COMPLETE
- [x] React Flow integration (endpoint exists: `GET /api/subjects/{id}/atoms/graph`)
- [x] Graph data endpoint
- [x] Node styling by type (color-coded by eje, type badges)
- [x] Stats panel (total atoms, connections, orphans, atoms by eje)
- [x] Modal/drawer wrapper (full-screen modal with escape key support)

### Phase 4: Pipeline Runner
- [x] Pipeline forms UI (placeholder)
- [ ] Cost estimation service
- [ ] Confirmation modals
- [ ] Job execution (subprocess)
- [ ] Status polling + refresh button

### Phase 5: Sync & Polish
- [x] Sync page UI (placeholder)
- [ ] Sync preview endpoint
- [ ] Sync execution with confirmation
- [ ] Risk warning modals
- [ ] Responsive tweaks
- [ ] Error handling improvements

---

## 11. Design Guidelines

### Colors (Linear-inspired)
- Background: `#0a0a0a` (near-black)
- Surface: `#141414` (cards, panels)
- Border: `#262626` (subtle dividers)
- Text primary: `#fafafa`
- Text secondary: `#a3a3a3`
- Accent: `#6366f1` (indigo)
- Success: `#22c55e`
- Warning: `#f59e0b`
- Error: `#ef4444`

### Typography
- Font: Inter or system-ui
- Headings: Semibold
- Body: Regular
- Monospace for IDs, code: JetBrains Mono

### Components
- Use shadcn/ui as base
- Cards with subtle borders, no shadows
- Tables with hover states
- Modals with backdrop blur
- Toast notifications for actions

---

## 12. Resolved Design Decisions

1. **Question Sets pipeline** → Build UI placeholder with proper unlock conditions
   - Generates ~60 questions per atom (20 low / 20 medium / 20 high)
   - Unlocks when: atom defined + ALL test questions parsed & tagged
   - Supports per-atom or bulk generation

2. **Lessons pipeline** → Build UI placeholder
   - Generates 1 micro-lesson per atom
   - Unlocks when: question set exists OR same prereqs as question sets
   - Can run in parallel with question set generation

3. **Error recovery** → Save partial progress, show resume button
   - Progress saved after each item to `app/data/.jobs/{job_id}.json`
   - UI shows "Resume Remaining" and "Retry Failed" buttons
   - Never lose completed work

4. **Batch operations** → Yes, fully supported
   - Tagging: all questions or selected subset
   - Question Sets: single atom or bulk (all atoms)
   - Lessons: single atom or bulk

5. **Export** → Not needed for now

---

## 13. Scope Questions

1. **Diagnostic Tests** - There's a `app/data/diagnostico/variantes/` folder with diagnostic test variants in a different structure. Should these be included in the dashboard?
   - They use `test_type: "diagnostic"` in DB
   - Currently flat structure: `diagnostico/variantes/Q{n}_v{m}/`
   - May need separate handling

---

## 14. Next Steps

1. ~~Review this plan, answer open questions~~ ✓ Done
2. ~~**Phase 0**: Implement variant sync backend~~ ✓ Done (2026-02-03)
3. ~~Create `api/` folder with FastAPI skeleton~~ ✓ Done (2026-02-03)
4. ~~Create `frontend/` folder with Next.js scaffold~~ ✓ Done (2026-02-03)
5. ~~Implement Phase 1 (foundation)~~ ✓ Done (2026-02-03)
6. Test the dashboard locally (see instructions below)
7. ~~Complete Phase 3: Wire up React Flow for knowledge graph~~ ✓ Done (2026-02-03)
8. Complete Phase 4: Implement pipeline execution backend
9. Complete Phase 5: Implement sync endpoints

### Running the Dashboard

```bash
# Terminal 1: Start FastAPI backend
pip install -e ".[dashboard]"
uvicorn api.main:app --reload --port 8000

# Terminal 2: Start Next.js frontend
cd frontend
npm install
npm run dev
```

Then open http://localhost:3000
