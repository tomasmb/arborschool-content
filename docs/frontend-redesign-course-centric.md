# Frontend Redesign: Course-Centric Architecture

This document outlines the course-centric frontend architecture.

---

## Implementation Status (Updated 2026-02-03)

### All Phases Complete ✅

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | URL Restructure (`/subjects` → `/courses`) | ✅ Done |
| Phase 2 | Remove global pages (`/pipelines`, `/sync`) | ✅ Done |
| Phase 3 | Course Overview Enhancement (pipeline cards, sync status, inline buttons) | ✅ Done |
| Phase 4 | New Course Pages (`/standards`, `/tests`, `/settings`) | ✅ Done |
| Phase 5 | Generation Buttons Functional (with cost modal, progress, toasts) | ✅ Done |
| Phase 6 | Dynamic Sidebar (context-aware navigation) | ✅ Done |
| Phase 7 | Course-scoped Sync (Settings page with full sync flow) | ✅ Done |
| Cleanup | Remove dead code (legacy components, unused API functions) | ✅ Done |

### Current State

**Frontend (complete):**
- All URLs use `/courses/` pattern
- Sidebar is dynamic: shows Dashboard on home, course-specific nav when inside a course
- Course overview shows Knowledge Graph Pipeline with working [Generate] buttons
- Generation triggers `GeneratePipelineModal` with cost estimation, confirmation, progress
- Toast notifications on success/failure, data auto-refreshes
- New pages: Standards list, Tests list, Settings
- Settings page has full sync flow: preview → confirm → execute
- Legacy code removed: `JobsTable`, `PipelineForm`, `JobStatusBadge`, unused global sync functions

**Backend (complete):**
- API uses `/api/subjects/` endpoints (works fine, just internal naming)
- Pipeline API works for generation
- Course-scoped sync endpoints: `POST /api/subjects/{subject_id}/sync/preview` and `/execute`
- Extractors accept `subject_id` to scope data to specific course

### Optional Future Enhancements

| Task | Description | Priority |
|------|-------------|----------|
| Auto-upload images during QTI | Upload to S3 during generation, not as separate step | Low |
| Rename API routes | `/api/subjects/` → `/api/courses/` for consistency | Low |

---

## Core Principle

> **Everything happens within a course context.**
> Users navigate INTO a course, and all actions, views, and statuses are scoped to that course.

No more:
- Global "Pipelines" page that runs pipelines across all courses
- Global "Sync" page with checkboxes for all entity types
- Global "Atoms" page showing atoms from all courses
- Sidebar links to global pages

Instead:
- Dashboard shows course cards → click to enter a course
- Inside a course: see status, run generation pipelines, sync, view atoms/tests/questions
- All actions are contextual to the current course

---

## Architecture

### Navigation Structure

```
Dashboard (/)
└── Course Card (e.g., "PAES M1 2026")
    └── Click → Enter Course (/courses/[courseId])
        ├── Overview Tab (default)
        │   ├── Knowledge Graph Pipeline Status
        │   │   └── Temario → Standards → Atoms (with inline generation buttons)
        │   ├── Tests Summary
        │   └── Sync Status
        ├── Standards Tab (/courses/[courseId]/standards)
        ├── Atoms Tab (/courses/[courseId]/atoms)
        ├── Tests Tab (/courses/[courseId]/tests)
        │   └── Test Detail (/courses/[courseId]/tests/[testId])
        │       └── Questions, Variants, Tagging
        └── Settings Tab (/courses/[courseId]/settings)
            └── Sync actions, configuration
```

---

## Pages

### Dashboard (`/`)

- Shows all courses as cards
- Each card shows: name, year, pipeline completion %, sync status indicator
- Click → navigates to `/courses/[courseId]`

### Course Overview (`/courses/[courseId]`)

**This is the main course page. Shows:**

#### Section A: Knowledge Graph Pipeline

Visual pipeline with status and actions:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Temario   │ → │  Standards  │ → │    Atoms    │
│     ✓ 1     │    │   ✗ 0/45    │    │   ✗ 0/120   │
│             │    │ [Generate]  │    │  (blocked)  │
└─────────────┘    └─────────────┘    └─────────────┘
```

- Each step shows: status (✓/✗), count, and action button
- Action button is:
  - **Enabled** if prerequisites are met
  - **Disabled** (grayed out) if prerequisites missing
  - Shows tooltip explaining why disabled
- Clicking "Generate" opens a modal with options and runs the pipeline

#### Section B: Tests & Questions Summary

Table showing all tests with their pipeline status:

| Test | PDF | Split | QTI | Tagged | Variants | Actions |
|------|-----|-------|-----|--------|----------|---------|
| Prueba Invierno 2025 | ✓ | ✓ 45 | ✓ 45 | 40/45 | 120 | [View] |
| Forma 123 | ✓ | ✗ 0 | — | — | — | [Split] |

- Actions are contextual: shows next available action
- Click test name → goes to test detail page

#### Section C: Sync Status

Shows current sync state:

```
┌─────────────────────────────────────────────────────┐
│ Sync Status                                         │
├─────────────────────────────────────────────────────┤
│ Standards: ✓ Synced (45/45)                         │
│ Atoms: ⚠ Pending (120 local, 100 in DB)            │
│ Questions: ⚠ Pending (5 new variants)              │
│ Images: ✓ All uploaded                              │
│                                                     │
│ Last sync: 2026-02-01 14:30                        │
│                                        [Sync Now]   │
└─────────────────────────────────────────────────────┘
```

### Course Standards (`/courses/[courseId]/standards`)

- List of all standards for this course
- Grouped by eje (axis): Números, Álgebra, Geometría, Probabilidad
- Each standard shows: code, description, atom count

### Course Atoms (`/courses/[courseId]/atoms`)

- List of all atoms for this course
- Filter by: eje, standard, status
- Each atom shows: title, standard link, question count

### Course Tests (`/courses/[courseId]/tests`)

- List of all tests for this course
- Shows pipeline status for each test

### Test Detail (`/courses/[courseId]/tests/[testId]`)

- Questions table with: question number, preview, status, atom tags, variant count
- Actions: Generate variants, Tag atoms, View/Edit

### Course Settings (`/courses/[courseId]/settings`)

- Configuration status: Database and S3 connection status
- Course-scoped sync with full flow:
  1. Select entities to sync (standards, atoms, tests, questions)
  2. Options: include variants, upload images to S3
  3. Preview what will be synced (dry run)
  4. Confirm and execute sync
  5. Show results (rows affected per table)
- Course information display

---

## Key Components

### Sidebar (`components/layout/Sidebar.tsx`)

Dynamic based on context:
- On dashboard: shows only "Dashboard" link
- Inside a course: shows course-specific navigation (Overview, Standards, Atoms, Tests, Settings) plus "← Dashboard" back link

### GeneratePipelineModal (`components/pipelines/GeneratePipelineModal.tsx`)

Handles the full generation flow:
1. Fetches cost estimate from `/api/pipelines/estimate`
2. Shows cost and requires user confirmation
3. Gets confirmation token and runs pipeline
4. Polls job status and shows progress
5. Displays success/failure and triggers data refresh

### Toast (`components/ui/Toast.tsx`)

Simple toast notification system with `ToastProvider` context and `useToast` hook.

---

## Design Principles

1. **No orphan pages**: Every page is either Dashboard or inside a course
2. **Contextual actions**: Buttons appear where they make sense, enabled/disabled based on state
3. **Progressive disclosure**: Show summary first, details on demand
4. **Clear status**: Always show what's done, what's pending, what's blocked
5. **No manual orchestration**: User shouldn't need to know pipeline dependencies

---

## Design Decisions (Resolved)

1. **Course creation**: Courses are created by uploading a temario. Either:
   - Upload via UI (future feature) which places the temario in the correct folder
   - Manually place the temario PDF in `app/data/temarios/pdf/`
   - No explicit "Create Course" button needed—the temario defines the course.

2. **Multi-course operations**: No. All operations are always scoped to a single course.
   No bulk sync or bulk generation across multiple courses.

3. **Course deletion**: Out of scope. Not needed for current use case.

4. **Permissions**: Single user system, no authentication or role-based access control needed.
