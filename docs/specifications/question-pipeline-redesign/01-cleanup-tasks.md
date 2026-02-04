# Task 01: Cleanup Old Feedback & Redundant Code

> **Type**: Implementation Task
> **Prerequisites**: None (do this first)
> **Estimated Sessions**: 1-2

## Context

Before implementing the new feedback pipeline, we need to clean up:
1. Old feedback data in `metadata_tags.json` files (~270 files)
2. Redundant fields in sync models
3. Feedback generation code in tagging module
4. API and frontend code that reads old feedback format

## Acceptance Criteria

- [x] All `metadata_tags.json` files have `feedback` field removed
- [x] `app/sync/models.py` has redundant fields removed
- [x] `app/sync/extractors.py` has feedback/correct_answer extraction removed
- [x] `app/sync/transformers.py` has mapping for removed fields removed
- [x] `app/tagging/tagger_prompts.py` has no feedback generation prompts
- [x] `api/schemas/api_models.py` has `feedback`, `correct_answer` fields removed
- [x] `api/routers/questions.py` has old feedback reading removed
- [x] `frontend/lib/api-types.ts` has old feedback types removed
- [x] `frontend/components/questions/QuestionDetailPanel.tsx` has old feedback display removed
- [ ] All tests pass after changes

---

## Task 1.1: Create Cleanup Script for metadata_tags.json

### Files to Create

- `scripts/cleanup_old_feedback.py`

### Implementation

```python
"""Remove old feedback from metadata_tags.json files.

Usage:
    python scripts/cleanup_old_feedback.py --dry-run  # Preview changes
    python scripts/cleanup_old_feedback.py            # Execute cleanup
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def cleanup_feedback(metadata_path: Path, dry_run: bool = False) -> bool:
    """Remove feedback field from metadata_tags.json. Returns True if modified."""
    with open(metadata_path) as f:
        data = json.load(f)
    
    if "feedback" not in data:
        return False
    
    if dry_run:
        print(f"  Would remove 'feedback' from: {metadata_path}")
        return True
    
    del data["feedback"]
    
    with open(metadata_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"  Removed 'feedback' from: {metadata_path}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove old feedback from metadata files")
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")
    args = parser.parse_args()
    
    # Find all metadata_tags.json files
    base_path = Path("app/data/pruebas/finalizadas")
    metadata_files = list(base_path.glob("**/metadata_tags.json"))
    
    print(f"Found {len(metadata_files)} metadata_tags.json files")
    
    modified_count = 0
    for path in metadata_files:
        if cleanup_feedback(path, dry_run=args.dry_run):
            modified_count += 1
    
    action = "Would modify" if args.dry_run else "Modified"
    print(f"\n{action} {modified_count} files")


if __name__ == "__main__":
    main()
```

### Verification

```bash
# Preview changes
python scripts/cleanup_old_feedback.py --dry-run

# Execute (after review)
python scripts/cleanup_old_feedback.py

# Verify no feedback fields remain
grep -r '"feedback"' app/data/pruebas/finalizadas/*/qti/*/metadata_tags.json | wc -l
# Should output: 0
```

---

## Task 1.2: Clean Sync Models

### Files to Modify

- `app/sync/models.py`

### Fields to Remove

| Field | Reason |
|-------|--------|
| `correct_answer` | Will be parsed from QTI XML |
| `title` | Will be parsed from QTI XML |
| `feedback_general` | Will be in QTI XML |
| `feedback_per_option` | Will be in QTI XML |
| `difficulty_analysis` | Not synced to DB |
| `general_analysis` | Not synced to DB |

### Verification

After changes, verify the `QuestionRow` dataclass only contains:
- `id`, `qti_xml`
- `source`, `difficulty_level`, `difficulty_score`
- `parent_question_id`, `question_set_id`
- `source_test_id`, `source_question_number`

---

## Task 1.3: Clean Extractors

### Files to Modify

- `app/sync/extractors.py`

### Code to Remove

- Any function that extracts `feedback` from `metadata_tags.json`
- Any function that extracts `correct_answer` from files
- Any function that extracts `title` from files

### Code to Keep

- Atom extraction
- Difficulty extraction
- Any other metadata extraction still needed

---

## Task 1.4: Clean Transformers

### Files to Modify

- `app/sync/transformers.py`

### Code to Remove

- Mapping of `feedback_general` field
- Mapping of `feedback_per_option` field
- Mapping of `correct_answer` field
- Mapping of `title` field

---

## Task 1.5: Clean Tagging Module

### Files to Modify

- `app/tagging/tagger_prompts.py`

### Code to Remove

- Any prompts related to feedback generation
- Any schema fields for feedback output

### Code to Keep

- Atom selection prompts/logic
- Difficulty assessment prompts/logic
- Habilidad principal prompts/logic

---

## Task 1.6: Clean API

### Files to Modify

- `api/schemas/api_models.py`
- `api/routers/questions.py`

### Changes in api_models.py

Remove fields:
- `feedback` (or `feedback_general`, `feedback_per_option`)
- `correct_answer`

### Changes in questions.py

Remove:
- Any code that reads feedback from `metadata_tags.json`
- Any code that parses `correct_answer` from files

---

## Task 1.7: Clean Frontend

### Files to Modify

- `frontend/lib/api-types.ts`
- `frontend/components/questions/QuestionDetailPanel.tsx`

### Changes in api-types.ts

Remove types:
- `FeedbackGeneral` (or similar)
- `FeedbackPerOption` (or similar)
- `correct_answer` field from Question type

### Changes in QuestionDetailPanel.tsx

Remove:
- Old feedback display components/sections
- (Will add new tabbed feedback view in later task)

---

## Summary Checklist

```
[x] 1.1 Create and run cleanup_old_feedback.py script
[x] 1.2 Clean app/sync/models.py
[x] 1.3 Clean app/sync/extractors.py (+ variant_extractors.py)
[x] 1.4 Clean app/sync/transformers.py
[x] 1.5 Clean app/tagging/tagger_prompts.py
[x] 1.6 Clean api/schemas/api_models.py and api/routers/questions.py
[x] 1.7 Clean frontend/lib/api-types.ts and QuestionDetailPanel.tsx
[ ] Run tests to verify nothing broke
```
