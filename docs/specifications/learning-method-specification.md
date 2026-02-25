# Arbor Learning Method

## Overview

Build personalized courses from a Knowledge Graph where each atom is
taught and mastery is proven before advancing.

```
Diagnostic (MST-16) → Learning Plan → Teach Atom → PP100 → Next Atom or Gap-Fill
```

Each atom = 1 mini-class + 1 PP100 question set. Mastery is binary.
Failed atoms trigger prerequisite diagnosis.

---

## Atom Structure

| Component    | Description |
|--------------|-------------|
| Mini-class   | See `mini-class-specification.md` |
| Question Set | PP100 questions at 3 difficulty levels (minimum 14E/18M/14H = 46 total) |
| Prerequisites | Links to atoms whose steps are required but taught elsewhere |

Mini-class is generated AFTER question set to ensure alignment.

---

## PP100 Algorithm

### Core Mastery Rule

The student must answer **3 questions in a row correctly**, with
**at least 2 of those at HARD difficulty**.

### Failure Rule

The student **fails** and is redirected to prerequisite review if:
- 3 incorrect answers in a row, OR
- 10 total questions attempted with <70% accuracy

### Question Limit

- After 10 questions with no mastery or failure: continue up to
  **20 questions total**
- If mastery occurs at any point: mastered
- If by question 20 there is still no 3-in-a-row with 2 hard: **fail**
- No "provisional mastery" — mastery requires clear streak-based evidence

### Difficulty Progression

| Current Level | After 2 Correct | After 2 Wrong |
|---------------|-----------------|---------------|
| Easy          | Medium          | Stay at Easy  |
| Medium        | Hard            | Easy          |
| Hard          | Stay at Hard    | Medium        |

- Students always **start at Easy**
- Progression and regression are **streak-based** (not one-off answers)

### Question Selection

1. Select from current difficulty level for this atom
2. Prefer never-seen questions
3. Else use least-recently-seen

### Question Pool Per Atom

Derived from worst-case mastery path:
- Max **20 questions per attempt**
- Students can attempt each atom up to **2 times** with unique questions
- No repeat questions across attempts

| Difficulty | Max per Attempt | Needed (x2) | Recommended |
|------------|-----------------|-------------|-------------|
| Easy       | 6               | 12          | **14**      |
| Medium     | 8               | 16          | **18**      |
| Hard       | 6               | 12          | **14**      |
| **Total**  | —               | —           | **46**      |

### Research Basis

- **3-in-a-row (3CCR)**: widely used (ASSISTments, Mathia), reduces
  guess-based false positives
- **Requiring HARD items**: avoids shallow mastery, promotes transfer
- **Failure rule**: wheel-spinning literature shows 3 consecutive errors
  or <70% accuracy over 10+ attempts reliably predicts prerequisite gaps
- **Streak-based transitions**: reduce noise vs. one-off; used in ALEKS
  and Direct Instruction
- **No provisional pass**: mastery = clarity. If they can't hit the bar
  in 20 questions, they need support

---

## Diagnostic (MST-16)

| Stage   | Questions | Selection |
|---------|-----------|-----------|
| Stage 1 | 8 | Fixed set covering key atoms |
| Stage 2 | 8 | Adaptive based on Stage 1 |

Outcome per atom:
- Correct → `mastered` with `mastery_source = 'diagnostic'`
- Incorrect → `not_started`

After diagnostic: generate learning plan ordered by priority and
prerequisites.

---

## Learning Loop

```
1. TEACH: Present mini-class
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

Triggered when PP100 fails (3 wrong in a row or <70% accuracy over 10+
questions).

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

Auto-unfreeze: when all prerequisites become mastered,
frozen → in_progress.

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
| <70% over 10+ items or 3 wrong in a row | Freeze; diagnose; gap-fill; reteach |

---

## Priority Scoring

Use question-to-atom mappings to prioritize atoms.

```
score = direct_questions + (indirect_questions × decay)
```

- `direct_questions`: test questions with this atom as PRIMARY
- `indirect_questions`: test questions with dependent atoms as PRIMARY
- `decay`: 0.5 per level up the graph

Selection: filter to atoms with prerequisites mastered, sort by score
descending.

Rationale: biggest wins for smallest time — atoms unlocking more test
questions are prioritized.

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
| `question_set` | PP100 (14E/18M/14H = 46 per atom) |
| `lesson` | Mini-class content (see `mini-class-specification.md`) |
