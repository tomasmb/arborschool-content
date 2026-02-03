# Frontend Redesign: Course-Centric Architecture

This document outlines the changes needed to transform the frontend from a
pipeline-centric/global-view architecture to a **course-centric** architecture.

---

## Implementation Status (Updated 2026-02-03)

### Completed

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | URL Restructure (`/subjects` → `/courses`) | ✅ Done |
| Phase 2 | Remove global pages (`/pipelines`, `/sync`) | ✅ Done |
| Phase 3 | Course Overview Enhancement (pipeline cards, sync status, inline buttons) | ✅ Done |
| Phase 4 | New Course Pages (`/standards`, `/tests`, `/settings`) | ✅ Done |
| Phase 6 | Dynamic Sidebar (context-aware navigation) | ✅ Done |

### Remaining Work (Backend)

| Task | Description | Priority |
|------|-------------|----------|
| Course-scoped sync endpoint | `POST /api/courses/{course_id}/sync` | Medium |
| Course-scoped generation endpoints | `POST /api/courses/{course_id}/generate/standards`, etc. | Medium |
| Auto-upload images during QTI generation | Upload to S3 during generation, not as separate step | Low |
| Sync diff tracking | Track local vs remote counts per course | Low |

### Current State

**Frontend:**
- All URLs now use `/courses/` instead of `/subjects/`
- Sidebar is dynamic: shows Dashboard on home, course-specific nav when inside a course
- Course overview shows Knowledge Graph Pipeline status with placeholder [Generate] buttons
- New pages: Standards list, Tests list, Settings (with sync placeholder)
- Old global pages (`/pipelines`, `/sync`) removed

**Backend:**
- API still uses `/api/subjects/` endpoints (frontend calls these)
- No changes needed yet - frontend works with existing APIs
- Generation buttons are placeholders (show alerts)
- Sync in Settings is a placeholder

### Next Steps to Make Generation Work

1. Wire up [Generate Standards] button to call existing pipeline API
2. Wire up [Generate Atoms] button to call existing pipeline API
3. Add loading states and progress indicators
4. Show toast notifications on success/failure

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

## Current State (Problems)

| Page | Problem |
|------|---------|
| `/pipelines` | Global page, not course-specific. User must know which pipeline to run. |
| `/sync` | Global page with checkboxes. Confusing UX. |
| `/subjects/[id]/atoms` | Good - already course-scoped |
| Sidebar | Hardcoded "PAES M1 2026" link. Has global "Pipelines" and "Sync" links. |
| S3 Images | Separate manual step instead of auto-upload during generation |

---

## New Architecture

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

### Sidebar Changes

**Remove:**
- "Pipelines" link
- "Sync" link
- Hardcoded "PAES M1 2026" link
- "Atoms" global link

**Keep:**
- "Dashboard" link

**Add (dynamic, when inside a course):**
- Course name as header
- "Overview" link
- "Standards" link
- "Atoms" link
- "Tests" link
- "Settings" link
- "← Back to Dashboard" link

---

## Pages to Remove

| Page | Reason |
|------|--------|
| `/pipelines` | Replaced by inline generation in course overview |
| `/sync` | Replaced by sync status + actions in course settings |
| `/subjects/[id]/atoms` | Rename to `/courses/[id]/atoms` |
| `/subjects/[id]` | Rename to `/courses/[id]` |
| `/subjects/[id]/tests/[testId]` | Rename to `/courses/[id]/tests/[testId]` |

---

## Pages to Create/Modify

### 1. Dashboard (`/`)

**Keep as-is but enhance:**
- Show all courses as cards
- Each card shows: name, year, pipeline completion %, sync status indicator
- Click → navigates to `/courses/[courseId]`

### 2. Course Overview (`/courses/[courseId]`)

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

### 3. Course Standards (`/courses/[courseId]/standards`)

- List of all standards for this course
- Grouped by eje (axis): Números, Álgebra, Geometría, Probabilidad
- Each standard shows: code, description, atom count
- Filter/search functionality

### 4. Course Atoms (`/courses/[courseId]/atoms`)

- **Move existing `/subjects/[id]/atoms` here**
- List of all atoms for this course
- Filter by: eje, standard, status
- Each atom shows: title, standard link, question count

### 5. Course Tests (`/courses/[courseId]/tests`)

- List of all tests for this course
- Shows pipeline status for each test
- Quick actions: Split, Generate QTI, etc.

### 6. Test Detail (`/courses/[courseId]/tests/[testId]`)

- **Move existing page here**
- Questions table with:
  - Question number, preview, status
  - Atom tags
  - Variant count
  - Actions: Generate variants, Tag atoms, View/Edit

### 7. Course Settings (`/courses/[courseId]/settings`)

**Contains:**
- Full sync controls (what was in `/sync` but scoped to this course)
- Course configuration
- Danger zone (reset, delete)

---

## Backend Changes Needed

### 1. Auto-upload images during QTI generation

**Current:** Images stay local, user must manually sync to S3.

**New:** When generating QTI questions, automatically upload images to S3 and
update the XML with S3 URLs.

**Files to modify:**
- `app/qti/generation.py` (or wherever QTI is generated)
- Call `ImageUploader.upload()` during generation, not as separate step

### 2. Course-scoped sync endpoint

**Current:** `/api/sync` syncs everything based on checkboxes.

**New:** `/api/courses/{course_id}/sync` syncs only that course's data.

**Endpoint behavior:**
- Automatically determines what needs syncing (diff local vs DB)
- Returns preview of changes
- Accepts confirmation to execute

### 3. Course-scoped pipeline endpoints

**Current:** Pipelines might be global or require manual course specification.

**New:** All generation endpoints are course-scoped:
- `POST /api/courses/{course_id}/generate/standards`
- `POST /api/courses/{course_id}/generate/atoms`
- `POST /api/courses/{course_id}/tests/{test_id}/split`
- `POST /api/courses/{course_id}/tests/{test_id}/generate-qti`
- `POST /api/courses/{course_id}/tests/{test_id}/generate-variants`

### 4. Course status endpoint

**New endpoint:** `GET /api/courses/{course_id}/status`

Returns comprehensive status for the course overview page:

```json
{
  "course_id": "paes-m1-2026",
  "knowledge_graph": {
    "temario": { "status": "complete", "count": 1 },
    "standards": { "status": "complete", "count": 45 },
    "atoms": { "status": "pending", "count": 0, "can_generate": true }
  },
  "tests": [
    {
      "test_id": "prueba-invierno-2025",
      "name": "Prueba Invierno 2025",
      "pdf": true,
      "split_count": 45,
      "qti_count": 45,
      "tagged_count": 40,
      "variant_count": 120
    }
  ],
  "sync": {
    "standards": { "local": 45, "remote": 45, "pending": 0 },
    "atoms": { "local": 120, "remote": 100, "pending": 20 },
    "questions": { "local": 45, "remote": 45, "pending": 0 },
    "variants": { "local": 120, "remote": 115, "pending": 5 },
    "images": { "pending": 0 }
  },
  "last_sync": "2026-02-01T14:30:00Z"
}
```

---

## URL Structure Changes

| Old | New |
|-----|-----|
| `/subjects/[id]` | `/courses/[id]` |
| `/subjects/[id]/atoms` | `/courses/[id]/atoms` |
| `/subjects/[id]/tests/[testId]` | `/courses/[id]/tests/[testId]` |
| `/pipelines` | **(removed)** |
| `/sync` | **(removed)** |
| — | `/courses/[id]/standards` **(new)** |
| — | `/courses/[id]/tests` **(new)** |
| — | `/courses/[id]/settings` **(new)** |

---

## Component Changes

### Sidebar (`components/layout/Sidebar.tsx`)

**Current:** Static links to global pages.

**New:** Dynamic based on context:
- If on dashboard: show only "Dashboard"
- If inside a course: show course navigation

```tsx
// Pseudo-code
if (isInsideCourse) {
  return (
    <>
      <BackLink to="/">← Dashboard</BackLink>
      <CourseHeader>{courseName}</CourseHeader>
      <NavLink to={`/courses/${courseId}`}>Overview</NavLink>
      <NavLink to={`/courses/${courseId}/standards`}>Standards</NavLink>
      <NavLink to={`/courses/${courseId}/atoms`}>Atoms</NavLink>
      <NavLink to={`/courses/${courseId}/tests`}>Tests</NavLink>
      <NavLink to={`/courses/${courseId}/settings`}>Settings</NavLink>
    </>
  );
} else {
  return <NavLink to="/">Dashboard</NavLink>;
}
```

### New Component: PipelineStatus

Reusable component showing a pipeline step:

```tsx
interface PipelineStepProps {
  name: string;
  status: 'complete' | 'pending' | 'blocked';
  count: number;
  total?: number;
  canGenerate: boolean;
  onGenerate: () => void;
}
```

### New Component: SyncStatus

Shows sync state for a course:

```tsx
interface SyncStatusProps {
  courseId: string;
  standards: { local: number; remote: number };
  atoms: { local: number; remote: number };
  questions: { local: number; remote: number };
  variants: { local: number; remote: number };
  lastSync: string | null;
  onSync: () => void;
}
```

---

## Implementation Order

### Phase 1: URL Restructure ✅ DONE
1. ✅ Rename `/subjects` to `/courses`
2. ✅ Update all internal links
3. ✅ Update API calls (frontend still calls `/api/subjects/` - that's fine)

### Phase 2: Remove Global Pages ✅ DONE
1. ✅ Delete `/pipelines/page.tsx`
2. ✅ Delete `/sync/page.tsx`
3. ✅ Remove from sidebar

### Phase 3: Course Overview Enhancement ✅ DONE
1. ✅ Create `PipelineCard` component (inline in page)
2. ✅ Create `SyncItem` component (inline in page)
3. ✅ Add inline generation buttons (placeholders)
4. ✅ Add sync status section

### Phase 4: New Course Pages ✅ DONE
1. ✅ Create `/courses/[id]/standards`
2. ✅ Create `/courses/[id]/tests` (list view)
3. ✅ Create `/courses/[id]/settings`

### Phase 5: Backend Changes ⏳ PENDING
1. ⏳ Add course-scoped status endpoint (optional - current API works)
2. ⏳ Add course-scoped sync endpoint (optional)
3. ⏳ Auto-upload images during generation

### Phase 6: Dynamic Sidebar ✅ DONE
1. ✅ Detect if inside course context
2. ✅ Show appropriate navigation
3. ✅ Add "Back to Dashboard" when in course

---

## Design Principles

1. **No orphan pages**: Every page is either Dashboard or inside a course
2. **Contextual actions**: Buttons appear where they make sense, enabled/disabled based on state
3. **Progressive disclosure**: Show summary first, details on demand
4. **Clear status**: Always show what's done, what's pending, what's blocked
5. **No manual orchestration**: User shouldn't need to know pipeline dependencies

---

## Open Questions

1. **Course creation**: Where does creating a new course happen? (Dashboard or separate admin?)
2. **Multi-course operations**: Is there ever a need to sync/generate across all courses at once?
3. **Course deletion**: What's the flow for removing a course and its data?
4. **Permissions**: Will there be different user roles with different access levels per course?
