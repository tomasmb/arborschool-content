# Task 07: Database Migration

> **Type**: Implementation Task
> **Prerequisites**: All previous tasks completed, tested
> **Estimated Sessions**: 1

## Context

After the new pipeline is working and validated, remove redundant columns from the
database. This is a one-way migration - ensure all data is properly migrated before
executing.

## Acceptance Criteria

- [ ] Backup of current database taken
- [ ] Redundant columns identified and verified as truly redundant
- [ ] Migration script created and tested on staging
- [ ] Migration executed on production
- [ ] Verify no data loss for needed fields
- [ ] Application works correctly after migration

---

## Pre-Migration Checklist

**CRITICAL: Complete ALL of these before running migration**

```
[ ] New pipeline is deployed and working
[ ] All questions have been re-enriched through new pipeline
[ ] All questions have valid QTI XML with embedded feedback
[ ] Database backup taken
[ ] Staging environment tested with migration
```

---

## Columns to Remove

| Column | Reason | Verification |
|--------|--------|--------------|
| `correct_answer` | Parse from `<qti-correct-response>` in QTI XML | Verify parser works |
| `title` | Parse from `title` attribute in QTI XML | Verify parser works |
| `feedback_general` | Embedded in QTI XML as `<qti-feedback-block>` | Verify extraction works |
| `feedback_per_option` | Embedded in QTI XML as `<qti-feedback-inline>` | Verify extraction works |
| `difficulty_analysis` | Kept in local `metadata_tags.json` only | Confirm not needed in DB |
| `general_analysis` | Kept in local `metadata_tags.json` only | Confirm not needed in DB |

---

## Migration Script

### Step 1: Verify Data Can Be Extracted

Before removing columns, verify the application can extract this data from QTI XML:

```python
"""Verify QTI XML contains all necessary data before migration."""
from __future__ import annotations

import json
from xml.etree import ElementTree as ET

from app.sync.db_client import get_all_questions


def verify_qti_data() -> dict:
    """Verify all questions have extractable data from QTI XML."""
    questions = get_all_questions()
    
    results = {
        "total": len(questions),
        "missing_correct_answer": [],
        "missing_title": [],
        "missing_feedback": [],
        "ready_for_migration": []
    }
    
    for q in questions:
        qti_xml = q.get("qti_xml", "")
        question_id = q.get("id")
        
        # Check correct answer
        if not extract_correct_answer(qti_xml):
            results["missing_correct_answer"].append(question_id)
            continue
        
        # Check title
        if not extract_title(qti_xml):
            results["missing_title"].append(question_id)
            continue
        
        # Check feedback (optional for migration, but warn)
        if not has_feedback(qti_xml):
            results["missing_feedback"].append(question_id)
        
        results["ready_for_migration"].append(question_id)
    
    return results


def extract_correct_answer(qti_xml: str) -> str | None:
    """Extract correct answer from QTI XML."""
    try:
        root = ET.fromstring(qti_xml)
        ns = {"qti": "http://www.imsglobal.org/xsd/imsqtiasi_v3p0"}
        correct = root.find(".//qti:qti-correct-response/qti:qti-value", ns)
        return correct.text if correct is not None else None
    except ET.ParseError:
        return None


def extract_title(qti_xml: str) -> str | None:
    """Extract title from QTI XML."""
    try:
        root = ET.fromstring(qti_xml)
        return root.get("title")
    except ET.ParseError:
        return None


def has_feedback(qti_xml: str) -> bool:
    """Check if QTI XML has feedback elements."""
    return "<qti-feedback-inline" in qti_xml or "<qti-feedback-block" in qti_xml


if __name__ == "__main__":
    results = verify_qti_data()
    print(json.dumps(results, indent=2))
    
    if results["missing_correct_answer"] or results["missing_title"]:
        print("\n⚠️  MIGRATION BLOCKED: Some questions missing required data")
        print(f"   Missing correct_answer: {len(results['missing_correct_answer'])}")
        print(f"   Missing title: {len(results['missing_title'])}")
    else:
        print(f"\n✓ Ready for migration: {len(results['ready_for_migration'])} questions")
        if results["missing_feedback"]:
            print(f"   Note: {len(results['missing_feedback'])} questions missing feedback")
```

### Step 2: Create Backup

```sql
-- Create backup table before migration
CREATE TABLE questions_backup_20260204 AS SELECT * FROM questions;

-- Verify backup
SELECT COUNT(*) FROM questions_backup_20260204;
```

### Step 3: Remove Redundant Columns

```sql
-- Migration script
-- Run ONLY after verification passes and backup is confirmed

BEGIN;

-- Remove redundant columns
ALTER TABLE questions DROP COLUMN IF EXISTS correct_answer;
ALTER TABLE questions DROP COLUMN IF EXISTS title;
ALTER TABLE questions DROP COLUMN IF EXISTS feedback_general;
ALTER TABLE questions DROP COLUMN IF EXISTS feedback_per_option;
ALTER TABLE questions DROP COLUMN IF EXISTS difficulty_analysis;
ALTER TABLE questions DROP COLUMN IF EXISTS general_analysis;

COMMIT;

-- Verify columns removed
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'questions'
ORDER BY ordinal_position;
```

### Step 4: Update Application Code

Ensure all code that previously read these columns now extracts from QTI XML:

```python
# Before (reading from DB column)
correct_answer = question_row.correct_answer

# After (parsing from QTI XML)
from app.question_feedback.utils.qti_parser import extract_correct_answer
correct_answer = extract_correct_answer(question_row.qti_xml)
```

---

## Rollback Plan

If issues are discovered after migration:

```sql
-- Restore from backup (within 30 days)
-- This requires manual data reconciliation if new questions were added

-- 1. Rename current table
ALTER TABLE questions RENAME TO questions_post_migration;

-- 2. Restore backup
ALTER TABLE questions_backup_20260204 RENAME TO questions;

-- 3. Investigate issues
-- ...

-- 4. After fixing, reconcile new data and re-migrate
```

---

## Post-Migration Verification

```python
"""Verify application works correctly after migration."""
from __future__ import annotations

import requests


def verify_post_migration() -> None:
    """Run verification checks after migration."""
    
    # 1. Verify questions endpoint works
    response = requests.get("/api/subjects/paes-m1/tests/prueba-invierno-2025/questions")
    assert response.status_code == 200
    questions = response.json()
    
    # 2. Verify question detail works (should parse from QTI)
    for q in questions[:5]:
        detail = requests.get(f"/api/questions/{q['id']}")
        assert detail.status_code == 200
        data = detail.json()
        
        # These should now be parsed from QTI XML
        assert "correct_answer" not in data or data.get("correct_answer") is not None
    
    # 3. Verify sync still works
    # ...
    
    print("✓ Post-migration verification passed")


if __name__ == "__main__":
    verify_post_migration()
```

---

## Summary Checklist

```
[ ] 7.1 Run verification script to confirm QTI has required data
[ ] 7.2 Take database backup
[ ] 7.3 Test migration on staging environment
[ ] 7.4 Execute migration on production
[ ] 7.5 Run post-migration verification
[ ] 7.6 Monitor application for 24-48 hours
[ ] 7.7 After confirmation, cleanup backup (after 30 days)
```
