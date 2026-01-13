# Arbor Learning Method

## Overview

Build personalized courses from a Knowledge Graph where each atom is taught and mastery is proven before advancing.

```
Diagnostic (MST-16) → Learning Plan → Teach Atom → PP100 → Next Atom or Gap-Fill
```

Each atom = 1 lesson + 1 PP100 question set. Mastery is binary. Failed atoms trigger prerequisite diagnosis.

---

## Atom Structure

| Component | Description |
|-----------|-------------|
| Lesson | 1-3 worked examples; covers every step required by atom's E/M/H items |
| Question Set | PP100 questions at 3 difficulty levels (minimum 3 per level) |
| Prerequisites | Links to atoms whose steps are required but taught elsewhere |

Lesson is generated AFTER question set to ensure alignment.

---

## PP100 Algorithm

### State

```
level: Easy | Medium | Hard (start at Easy)
streak[level]: consecutive correct at each level
total_correct: sum across all levels
```

### Question Selection

1. Select from current level for this atom
2. Prefer never-seen questions
3. Else use least-recently-seen

### On Correct

```
streak[level] += 1
total_correct += 1

if level != Hard and streak[level] >= 2:
    level = next_level_up
```

### On Wrong

```
streak[level] = 0

if level != Easy:
    level = next_level_down
```

### Mastery Criteria

All must be true:
- `total_correct >= 11`
- `correct_at_hard >= 3`
- `last_2_questions_at_hard == correct`

### Failure

If accuracy < 50%: status = `frozen`, trigger prerequisite diagnosis.

---

## Diagnostic (MST-16)

| Stage | Questions | Selection |
|-------|-----------|-----------|
| Stage 1 | 8 | Fixed set covering key atoms |
| Stage 2 | 8 | Adaptive based on Stage 1 |

Outcome per atom:
- Correct → `mastered` with `mastery_source = 'diagnostic'`
- Incorrect → `not_started`

After diagnostic: generate learning plan ordered by priority and prerequisites.

---

## Learning Loop

```
1. TEACH: Present lesson (1-3 worked examples)
           │
           ▼
2. ASSESS: Run PP100
           │
    ┌──────┴──────┐
    ▼             ▼
MASTERED     NOT MASTERED
    │             │
    ▼             ▼
Record       Diagnose prerequisites
Schedule SR  Create gap-fill plan
Advance      Complete gap-fill
             Reteach original atom
             Return to step 2
```

---

## Prerequisite Diagnosis

Triggered when PP100 fails (<50% accuracy).

```
Failed Atom
    │
    ▼
Get prerequisite chain (recursive)
    │
    ▼
For each prerequisite (bottom-up):
    ├── If mastered: skip
    └── If not mastered: add to gap-fill plan
    │
    ▼
Execute gap-fill (teach + PP100 each gap)
    │
    ▼
Reteach original failed atom
```

Auto-unfreeze: when all prerequisites become mastered, frozen → in_progress.

---

## Dynamic Plan Updates

Plan updates after every PP100 outcome.

### Signals

| Signal | Source |
|--------|--------|
| Gap detection | PP100 failure |
| SR due date | `last_demonstrated_at` |
| Sturdiness | PP100 accuracy + questions-to-master |

### Rules

| Outcome | Action |
|---------|--------|
| High accuracy, ≤13 items | Advance; SR in 7+ days |
| Modest accuracy, 14-20 items | Advance; SR in 3-5 days |
| <50% or >20 items | Freeze; diagnose; gap-fill; reteach |

---

## Priority Scoring

Use question-to-atom mappings to prioritize atoms.

```
score = direct_questions + (indirect_questions × decay)
```

- `direct_questions`: test questions with this atom as PRIMARY
- `indirect_questions`: test questions with dependent atoms as PRIMARY
- `decay`: 0.5 per level up the graph

Selection: filter to atoms with prerequisites mastered, sort by score descending.

Rationale: biggest wins for smallest time—atoms unlocking more test questions are prioritized.

---

## Spaced Repetition

### Scheduling

| Sturdiness | First Review |
|------------|--------------|
| High (≤13 items, >85%) | 7 days |
| Medium (14-17 items, 70-85%) | 5 days |
| Low (18-20 items, 50-70%) | 3 days |

### Review Construction

- Select 2-5 atoms due for review
- Pull varied questions covering typical errors
- Mix items from multiple atoms (interleaving)

### Outcomes

| Result | Action |
|--------|--------|
| Pass (≥80% per atom) | Extend interval ×1.5-2.5 |
| Fail (<80% any atom) | Shorten interval; targeted probe |

On success: update `last_demonstrated_at = NOW()`.

---

## Mastery States

| State | Meaning |
|-------|---------|
| `not_started` | No interaction |
| `in_progress` | Currently in PP100 |
| `mastered` | PP100 completed |
| `frozen` | PP100 failed; waiting for prerequisites |

```
not_started → in_progress → mastered
                   │
                   ▼
                frozen → in_progress (when prereqs mastered)
```

---

## KG Requirements

| Data | Used For |
|------|----------|
| `prerequisite_ids` | Diagnosis, gap-fill, blocking |
| `question_atoms` | Priority scoring, PP100 selection |
| `question_set` | PP100 (3+ per difficulty) |
| `lesson` | Teaching (1-3 worked examples) |
