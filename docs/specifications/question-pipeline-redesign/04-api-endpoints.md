# Task 04: API Endpoints

> **Type**: Implementation Task
> **Prerequisites**: [02-backend-core.md](./02-backend-core.md) completed
> **Estimated Sessions**: 2-3

## Context

Add API endpoints for:
1. Enrichment (add feedback to questions)
2. Validation (run final LLM validation)
3. Test-level sync with diff/preview

## Acceptance Criteria

- [ ] `POST /api/subjects/{id}/tests/{test_id}/enrich` endpoint works
- [ ] `GET /api/subjects/{id}/tests/{test_id}/enrich/status/{job_id}` returns progress
- [ ] `POST /api/subjects/{id}/tests/{test_id}/validate` endpoint works
- [ ] `GET /api/subjects/{id}/tests/{test_id}/validate/status/{job_id}` returns progress
- [ ] `POST /api/subjects/{id}/tests/{test_id}/sync/preview` shows diff
- [ ] `POST /api/subjects/{id}/tests/{test_id}/sync/execute` performs sync
- [ ] Question detail endpoints include enrichment/validation status
- [ ] All endpoints have proper error handling

---

## Files to Modify

- `api/routers/tests.py` (or create new `api/routers/enrichment.py`)
- `api/schemas/api_models.py`
- `api/routers/questions.py` (update question detail)

## Files to Create

- `api/services/enrichment_service.py`
- `api/services/validation_service.py`
- `api/services/sync_service.py`

---

## Endpoint Specifications

### 4.1 Enrichment Endpoints

#### POST /api/subjects/{subject_id}/tests/{test_id}/enrich

Start enrichment job for questions.

**Request Body:**
```json
{
  "question_ids": ["Q1", "Q2"],  // Optional - specific questions
  "all_tagged": true,            // Optional - all tagged questions
  "skip_already_enriched": true  // Optional - skip questions with feedback
}
```

**Response:**
```json
{
  "job_id": "enrich-abc123",
  "status": "started",
  "questions_to_process": 40,
  "estimated_cost_usd": 0.96
}
```

#### GET /api/subjects/{subject_id}/tests/{test_id}/enrich/status/{job_id}

Get enrichment job status.

**Response:**
```json
{
  "job_id": "enrich-abc123",
  "status": "in_progress",  // "started" | "in_progress" | "completed" | "failed"
  "progress": {
    "total": 40,
    "completed": 15,
    "successful": 12,
    "failed": 3
  },
  "current_question": "Q16",
  "results": [
    {"question_id": "Q1", "status": "success"},
    {"question_id": "Q2", "status": "success"},
    {"question_id": "Q3", "status": "failed", "error": "XSD validation failed"}
  ],
  "started_at": "2026-02-04T12:30:00Z",
  "completed_at": null
}
```

---

### 4.2 Validation Endpoints

#### POST /api/subjects/{subject_id}/tests/{test_id}/validate

Start validation job for questions.

**Request Body:**
```json
{
  "question_ids": ["Q1", "Q2"],  // Optional - specific questions
  "all_enriched": true,          // Optional - all enriched questions
  "revalidate_passed": false     // Optional - include already-passed questions
}
```

**Response:**
```json
{
  "job_id": "validate-xyz789",
  "status": "started",
  "questions_to_process": 37,
  "estimated_cost_usd": 0.56
}
```

#### GET /api/subjects/{subject_id}/tests/{test_id}/validate/status/{job_id}

Get validation job status.

**Response:**
```json
{
  "job_id": "validate-xyz789",
  "status": "completed",
  "progress": {
    "total": 37,
    "completed": 37,
    "passed": 32,
    "failed": 5
  },
  "results": [
    {
      "question_id": "Q1",
      "status": "pass"
    },
    {
      "question_id": "Q7",
      "status": "fail",
      "failed_checks": ["correct_answer_check"],
      "issues": ["The marked answer ChoiceB yields 15, but the stem asks for maximum which is 19"]
    }
  ],
  "started_at": "2026-02-04T12:35:00Z",
  "completed_at": "2026-02-04T12:40:00Z"
}
```

---

### 4.3 Sync Endpoints

#### POST /api/subjects/{subject_id}/tests/{test_id}/sync/preview

Preview what will be synced to database.

**Request Body:**
```json
{
  "include_variants": true,
  "upload_images": true
}
```

**Response:**
```json
{
  "questions": {
    "to_create": [
      {"question_id": "Q41", "question_number": 41, "status": "create"}
    ],
    "to_update": [
      {
        "question_id": "Q3",
        "question_number": 3,
        "status": "update",
        "changes": {
          "qti_xml_changed": true,
          "feedback_added": true,
          "feedback_changed": false
        }
      }
    ],
    "unchanged": [
      {"question_id": "Q1", "question_number": 1, "status": "unchanged"}
    ],
    "skipped": [
      {"question_id": "Q2", "question_number": 2, "status": "skipped", "reason": "not_validated"}
    ]
  },
  "summary": {
    "create": 5,
    "update": 12,
    "unchanged": 15,
    "skipped": 13
  }
}
```

#### POST /api/subjects/{subject_id}/tests/{test_id}/sync/execute

Execute sync to database.

**Request Body:**
```json
{
  "include_variants": true,
  "upload_images": true
}
```

**Response:**
```json
{
  "created": 5,
  "updated": 12,
  "skipped": 13,
  "details": [
    {"question_id": "Q3", "action": "updated"},
    {"question_id": "Q41", "action": "created"},
    {"question_id": "Q2", "action": "skipped", "reason": "not_validated"}
  ]
}
```

---

### 4.4 Updated Question Detail Endpoint

#### GET /api/subjects/{subject_id}/tests/{test_id}/questions/{question_num}

**Updated Response Fields:**
```json
{
  "id": "prueba-invierno-2025-Q6",
  "question_number": 6,
  "has_split_pdf": true,
  "has_qti": true,
  "is_finalized": true,
  "is_tagged": true,
  "atoms_count": 2,
  "variants_count": 3,
  
  "is_enriched": true,
  "is_validated": true,
  "can_sync": true,
  "sync_status": "local_changed",
  
  "validation_result": {
    "validation_result": "pass",
    "correct_answer_check": {"status": "pass"},
    "feedback_check": {"status": "pass"},
    "content_quality_check": {"status": "pass"},
    "image_check": {"status": "not_applicable"},
    "math_validity_check": {"status": "pass"}
  }
}
```

**sync_status values:**
- `not_in_db` - Question not yet in database
- `in_sync` - Local and DB versions match
- `local_changed` - Local version has changes (e.g., feedback added)
- `not_validated` - Cannot sync because validation failed/missing

---

## Implementation Details

### Enrichment Service

```python
# api/services/enrichment_service.py
from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.question_feedback.pipeline import QuestionPipeline
from app.question_feedback.utils.image_utils import extract_image_urls


@dataclass
class EnrichmentJob:
    job_id: str
    status: str  # started, in_progress, completed, failed
    total: int
    completed: int
    successful: int
    failed: int
    results: list[dict]
    started_at: datetime
    completed_at: datetime | None = None
    current_question: str | None = None


# In-memory job storage (use Redis in production)
_jobs: dict[str, EnrichmentJob] = {}


def _get_questions_to_enrich(
    test_id: str,
    question_ids: list[str] | None = None,
    all_tagged: bool = False,
    skip_already_enriched: bool = True
) -> list[dict]:
    """Get list of questions to enrich from the test folder.
    
    Returns list of dicts with: id, qti_xml, image_urls, output_dir
    """
    base_path = Path(f"app/data/pruebas/finalizadas/{test_id}/qti")
    questions = []
    
    # Get all Q* folders
    q_folders = sorted(base_path.glob("Q*"), key=lambda p: int(p.name[1:]))
    
    for q_folder in q_folders:
        question_num = q_folder.name  # e.g., "Q6"
        question_id = f"{test_id}-{question_num}"
        
        # Filter by specific question_ids if provided
        if question_ids and question_num not in question_ids:
            continue
        
        # Check if tagged (metadata_tags.json exists with selected_atoms)
        metadata_path = q_folder / "metadata_tags.json"
        if not metadata_path.exists():
            continue
        
        with open(metadata_path) as f:
            metadata = json.load(f)
        
        # Skip if not tagged (no atoms selected)
        if all_tagged and not metadata.get("selected_atoms"):
            continue
        
        # Check if already enriched
        validated_xml_path = q_folder / "question_validated.xml"
        if skip_already_enriched and validated_xml_path.exists():
            continue
        
        # Read original QTI XML
        qti_path = q_folder / "question.xml"
        if not qti_path.exists():
            continue
        
        with open(qti_path) as f:
            qti_xml = f.read()
        
        # Extract image URLs from QTI
        image_urls = extract_image_urls(qti_xml)
        
        questions.append({
            "id": question_id,
            "qti_xml": qti_xml,
            "image_urls": image_urls if image_urls else None,
            "output_dir": str(q_folder)
        })
    
    return questions


async def start_enrichment_job(
    test_id: str,
    question_ids: list[str] | None = None,
    all_tagged: bool = False,
    skip_already_enriched: bool = True
) -> str:
    """Start async enrichment job."""
    job_id = f"enrich-{uuid.uuid4().hex[:8]}"
    
    # Get questions to process
    questions = _get_questions_to_enrich(
        test_id, question_ids, all_tagged, skip_already_enriched
    )
    
    job = EnrichmentJob(
        job_id=job_id,
        status="started",
        total=len(questions),
        completed=0,
        successful=0,
        failed=0,
        results=[],
        started_at=datetime.now(timezone.utc)
    )
    _jobs[job_id] = job
    
    # Start background task
    asyncio.create_task(_run_enrichment(job_id, questions))
    
    return job_id


async def _run_enrichment(job_id: str, questions: list[dict]) -> None:
    """Run enrichment in background.
    
    Note: Uses asyncio.to_thread() to run sync pipeline.process() 
    without blocking the event loop.
    """
    job = _jobs[job_id]
    job.status = "in_progress"
    pipeline = QuestionPipeline()
    
    for q in questions:
        job.current_question = q["id"]
        
        # Run sync pipeline in thread pool to avoid blocking
        result = await asyncio.to_thread(
            pipeline.process,
            question_id=q["id"],
            qti_xml=q["qti_xml"],
            image_urls=q.get("image_urls"),
            output_dir=Path(q["output_dir"])
        )
        
        job.completed += 1
        if result.success:
            job.successful += 1
            job.results.append({"question_id": q["id"], "status": "success"})
        else:
            job.failed += 1
            job.results.append({
                "question_id": q["id"],
                "status": "failed",
                "error": result.error
            })
    
    job.status = "completed"
    job.current_question = None
    job.completed_at = datetime.now(timezone.utc)


def get_job_status(job_id: str) -> EnrichmentJob | None:
    """Get job status."""
    return _jobs.get(job_id)


def get_enrichment_cost_estimate(question_count: int) -> float:
    """Calculate estimated cost for enrichment.
    
    Based on GPT 5.1 pricing:
    - ~3,000 input tokens @ $1.25/1M = $0.00375
    - ~2,000 output tokens @ $10.00/1M = $0.02
    - Total per question: ~$0.024
    """
    cost_per_question = 0.024
    return round(question_count * cost_per_question, 2)
```

---

### Validation Service

```python
# api/services/validation_service.py
from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.question_feedback.validator import FinalValidator
from app.question_feedback.utils.image_utils import extract_image_urls


@dataclass
class ValidationJob:
    job_id: str
    status: str
    total: int
    completed: int
    passed: int
    failed: int
    results: list[dict]
    started_at: datetime
    completed_at: datetime | None = None


_validation_jobs: dict[str, ValidationJob] = {}


def _get_questions_to_validate(
    test_id: str,
    question_ids: list[str] | None = None,
    all_enriched: bool = False,
    revalidate_passed: bool = False
) -> list[dict]:
    """Get list of questions to validate."""
    base_path = Path(f"app/data/pruebas/finalizadas/{test_id}/qti")
    questions = []
    
    for q_folder in sorted(base_path.glob("Q*"), key=lambda p: int(p.name[1:])):
        question_num = q_folder.name
        question_id = f"{test_id}-{question_num}"
        
        if question_ids and question_num not in question_ids:
            continue
        
        # Must have validated XML (enriched)
        validated_xml_path = q_folder / "question_validated.xml"
        if not validated_xml_path.exists():
            continue
        
        # Check existing validation result
        validation_result_path = q_folder / "validation_result.json"
        if validation_result_path.exists() and not revalidate_passed:
            with open(validation_result_path) as f:
                existing = json.load(f)
            if existing.get("can_sync"):
                continue  # Already passed, skip
        
        with open(validated_xml_path) as f:
            qti_xml = f.read()
        
        image_urls = extract_image_urls(qti_xml)
        
        questions.append({
            "id": question_id,
            "qti_xml": qti_xml,
            "image_urls": image_urls if image_urls else None,
            "output_dir": str(q_folder)
        })
    
    return questions


async def start_validation_job(
    test_id: str,
    question_ids: list[str] | None = None,
    all_enriched: bool = False,
    revalidate_passed: bool = False
) -> str:
    """Start async validation job."""
    job_id = f"validate-{uuid.uuid4().hex[:8]}"
    
    questions = _get_questions_to_validate(
        test_id, question_ids, all_enriched, revalidate_passed
    )
    
    job = ValidationJob(
        job_id=job_id,
        status="started",
        total=len(questions),
        completed=0,
        passed=0,
        failed=0,
        results=[],
        started_at=datetime.now(timezone.utc)
    )
    _validation_jobs[job_id] = job
    
    asyncio.create_task(_run_validation(job_id, questions))
    
    return job_id


async def _run_validation(job_id: str, questions: list[dict]) -> None:
    """Run validation in background."""
    job = _validation_jobs[job_id]
    job.status = "in_progress"
    validator = FinalValidator()
    
    for q in questions:
        result = await asyncio.to_thread(
            validator.validate,
            qti_xml_with_feedback=q["qti_xml"],
            image_urls=q.get("image_urls")
        )
        
        job.completed += 1
        
        if result.validation_result == "pass":
            job.passed += 1
            job.results.append({"question_id": q["id"], "status": "pass"})
            
            # Update validation_result.json with can_sync=True
            _update_validation_result(q["output_dir"], result, can_sync=True)
        else:
            job.failed += 1
            failed_checks = [
                k for k, v in {
                    "correct_answer_check": result.correct_answer_check.status,
                    "feedback_check": result.feedback_check.status,
                    "content_quality_check": result.content_quality_check.status,
                    "image_check": result.image_check.status,
                    "math_validity_check": result.math_validity_check.status,
                }.items() if v == "fail"
            ]
            
            # Collect all issues
            issues = []
            issues.extend(result.correct_answer_check.issues)
            issues.extend(result.feedback_check.issues)
            issues.extend(result.math_validity_check.issues)
            
            job.results.append({
                "question_id": q["id"],
                "status": "fail",
                "failed_checks": failed_checks,
                "issues": issues[:3]  # Limit to 3 issues
            })
            
            _update_validation_result(q["output_dir"], result, can_sync=False)
    
    job.status = "completed"
    job.completed_at = datetime.now(timezone.utc)


def _update_validation_result(output_dir: str, result, can_sync: bool) -> None:
    """Update validation_result.json with final validation results."""
    path = Path(output_dir) / "validation_result.json"
    
    # Load existing or create new
    if path.exists():
        with open(path) as f:
            data = json.load(f)
    else:
        data = {}
    
    data["stages"]["final_validation"] = {
        "status": result.validation_result,
        "model": "gpt-5.1",
        "reasoning_effort": "high",
        "checks": {
            "correct_answer_check": result.correct_answer_check.status,
            "feedback_check": result.feedback_check.status,
            "content_quality_check": result.content_quality_check.status,
            "image_check": result.image_check.status,
            "math_validity_check": result.math_validity_check.status,
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    data["can_sync"] = can_sync
    
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_validation_job_status(job_id: str) -> ValidationJob | None:
    return _validation_jobs.get(job_id)


def get_validation_cost_estimate(question_count: int) -> float:
    """$0.015 per question for validation (high reasoning)."""
    return round(question_count * 0.015, 2)
```

---

### Sync Service

```python
# api/services/sync_service.py
from __future__ import annotations

import json
from pathlib import Path

from app.sync.db_client import get_question_by_id, upsert_question
from app.question_feedback.utils.qti_parser import has_feedback


def get_sync_preview(
    test_id: str,
    include_variants: bool = True
) -> dict:
    """Generate sync preview showing what will be created/updated/skipped."""
    base_path = Path(f"app/data/pruebas/finalizadas/{test_id}/qti")
    
    to_create = []
    to_update = []
    unchanged = []
    skipped = []
    
    for q_folder in sorted(base_path.glob("Q*"), key=lambda p: int(p.name[1:])):
        question_num = q_folder.name
        question_id = f"{test_id}-{question_num}"
        
        # Check validation status
        validation_path = q_folder / "validation_result.json"
        if not validation_path.exists():
            skipped.append({
                "question_id": question_id,
                "question_number": int(question_num[1:]),
                "status": "skipped",
                "reason": "not_enriched"
            })
            continue
        
        with open(validation_path) as f:
            validation = json.load(f)
        
        if not validation.get("can_sync"):
            skipped.append({
                "question_id": question_id,
                "question_number": int(question_num[1:]),
                "status": "skipped",
                "reason": "validation_failed"
            })
            continue
        
        # Get local QTI XML
        validated_xml_path = q_folder / "question_validated.xml"
        with open(validated_xml_path) as f:
            local_qti = f.read()
        
        # Check if exists in DB
        db_question = get_question_by_id(question_id)
        
        if db_question is None:
            to_create.append({
                "question_id": question_id,
                "question_number": int(question_num[1:]),
                "status": "create"
            })
        else:
            # Compare QTI XML
            db_qti = db_question.get("qti_xml", "")
            
            if _normalize_xml(local_qti) == _normalize_xml(db_qti):
                unchanged.append({
                    "question_id": question_id,
                    "question_number": int(question_num[1:]),
                    "status": "unchanged"
                })
            else:
                to_update.append({
                    "question_id": question_id,
                    "question_number": int(question_num[1:]),
                    "status": "update",
                    "changes": {
                        "qti_xml_changed": True,
                        "feedback_added": has_feedback(local_qti) and not has_feedback(db_qti),
                        "feedback_changed": has_feedback(local_qti) and has_feedback(db_qti)
                    }
                })
    
    return {
        "questions": {
            "to_create": to_create,
            "to_update": to_update,
            "unchanged": unchanged,
            "skipped": skipped
        },
        "summary": {
            "create": len(to_create),
            "update": len(to_update),
            "unchanged": len(unchanged),
            "skipped": len(skipped)
        }
    }


def execute_sync(
    test_id: str,
    include_variants: bool = True,
    upload_images: bool = True
) -> dict:
    """Execute sync to database."""
    preview = get_sync_preview(test_id, include_variants)
    
    created = 0
    updated = 0
    details = []
    
    base_path = Path(f"app/data/pruebas/finalizadas/{test_id}/qti")
    
    # Process creates and updates
    for q in preview["questions"]["to_create"] + preview["questions"]["to_update"]:
        question_id = q["question_id"]
        q_folder = base_path / f"Q{q['question_number']}"
        
        validated_xml_path = q_folder / "question_validated.xml"
        with open(validated_xml_path) as f:
            qti_xml = f.read()
        
        # TODO: Upload images to S3 if upload_images=True
        
        # Upsert to database
        success = upsert_question(question_id, qti_xml)
        
        if success:
            if q["status"] == "create":
                created += 1
                details.append({"question_id": question_id, "action": "created"})
            else:
                updated += 1
                details.append({"question_id": question_id, "action": "updated"})
    
    # Add skipped to details
    for q in preview["questions"]["skipped"]:
        details.append({
            "question_id": q["question_id"],
            "action": "skipped",
            "reason": q["reason"]
        })
    
    return {
        "created": created,
        "updated": updated,
        "skipped": len(preview["questions"]["skipped"]),
        "details": details
    }


def _normalize_xml(xml: str) -> str:
    """Normalize XML for comparison (remove whitespace variations)."""
    import re
    # Remove extra whitespace between tags
    normalized = re.sub(r'>\s+<', '><', xml)
    # Normalize line endings
    normalized = normalized.replace('\r\n', '\n').replace('\r', '\n')
    # Strip
    return normalized.strip()
```

---

## API Models Updates

Add to `api/schemas/api_models.py`:

```python
from pydantic import BaseModel


class EnrichmentRequest(BaseModel):
    question_ids: list[str] | None = None
    all_tagged: bool = False
    skip_already_enriched: bool = True


class EnrichmentJobResponse(BaseModel):
    job_id: str
    status: str
    questions_to_process: int
    estimated_cost_usd: float


class EnrichmentStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: dict
    current_question: str | None
    results: list[dict]
    started_at: str
    completed_at: str | None


class ValidationRequest(BaseModel):
    question_ids: list[str] | None = None
    all_enriched: bool = False
    revalidate_passed: bool = False


class SyncPreviewRequest(BaseModel):
    include_variants: bool = True
    upload_images: bool = True


class QuestionDiff(BaseModel):
    question_id: str
    question_number: int
    status: str  # create, update, unchanged, skipped
    reason: str | None = None
    changes: dict | None = None


class SyncPreviewResponse(BaseModel):
    questions: dict  # to_create, to_update, unchanged, skipped
    summary: dict


class SyncExecuteResponse(BaseModel):
    created: int
    updated: int
    skipped: int
    details: list[dict]
```

---

## Summary Checklist

```
[ ] 4.1 Create api/services/enrichment_service.py
[ ] 4.1 Add POST /tests/{test_id}/enrich endpoint
[ ] 4.1 Add GET /tests/{test_id}/enrich/status/{job_id} endpoint
[ ] 4.2 Create api/services/validation_service.py
[ ] 4.2 Add POST /tests/{test_id}/validate endpoint
[ ] 4.2 Add GET /tests/{test_id}/validate/status/{job_id} endpoint
[ ] 4.3 Create api/services/sync_service.py
[ ] 4.3 Add POST /tests/{test_id}/sync/preview endpoint
[ ] 4.3 Add POST /tests/{test_id}/sync/execute endpoint
[ ] 4.4 Update question detail endpoint with new fields
[ ] Update api/schemas/api_models.py with new models
[ ] Add tests for all endpoints
```
