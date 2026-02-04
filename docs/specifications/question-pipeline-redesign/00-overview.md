# Question Pipeline Redesign - Overview

> **Type**: Reference Document (read-only context for sessions)
> **Last Updated**: 2026-02-04

## Goals

This redesign aims to:

1. **Simplify data model**: QTI XML is the single source of truth for question content
2. **Embed feedback in QTI XML**: LLM generates complete XML with feedback embedded
3. **XSD validation after every XML change**: Validate immediately after any modification
4. **LLM final validation**: Comprehensive quality check before sync is allowed
5. **Enforce quality**: Only fully validated questions can be synced to the database

---

## Model Strategy: GPT 5.1

We use **GPT 5.1** for all LLM tasks, adjusting `reasoning_effort` based on task complexity:

| Task | reasoning_effort | Rationale |
|------|------------------|-----------|
| Feedback generation | `medium` | Requires understanding question + generating pedagogical content |
| Final validation | `high` | Critical quality gate, needs deep analysis of math/content accuracy |
| Simple extraction | `low` | Straightforward parsing tasks |

### GPT 5.1 Specifications

| Property | Value |
|----------|-------|
| Context window | 400K tokens |
| Speed | 77 tokens/second, 0.80s median latency |
| Capabilities | Vision + Tools + Caching |

### Pricing (as of November 2025)

| Token Type | Cost per 1M tokens |
|------------|-------------------|
| Input | $1.25 |
| Output | $10.00 |
| Cached input | $0.125 |

### Cost Optimization Strategies

1. **Use cached inputs**: System prompts and static context → 10x cheaper
2. **Match reasoning_effort to task**: Don't use `high` for simple tasks
3. **Structured outputs**: Reduce output tokens with JSON schemas
4. **Batch similar questions**: Share context across questions in same test

---

## Data Model

### Current State (Redundant)

```python
# CURRENT - Has redundancy
@dataclass
class QuestionRow:
    id: str
    qti_xml: str              # Source of truth
    correct_answer: str       # REDUNDANT: in QTI XML
    title: str | None         # REDUNDANT: in QTI XML
    feedback_general: str     # REDUNDANT: should be in QTI XML
    feedback_per_option: dict # REDUNDANT: should be in QTI XML
    # ... other fields
```

### Target State (Clean)

```python
# TARGET - No redundancy
@dataclass
class QuestionRow:
    # Core content - QTI XML is the single source of truth
    id: str
    qti_xml: str  # Contains: stem, options, correct answer, feedback, worked solution
    
    # True metadata (not derivable from QTI)
    source: QuestionSource  # official | alternate | question_set
    difficulty_level: DifficultyLevel
    difficulty_score: float | None
    
    # Relationships
    parent_question_id: str | None  # For variants
    question_set_id: str | None
    
    # Provenance
    source_test_id: str | None
    source_question_number: int | None
```

### Fields to Remove

| Field | Reason |
|-------|--------|
| `correct_answer` | Parse from `<qti-correct-response>` in QTI XML |
| `title` | Parse from `title` attribute in QTI XML |
| `feedback_general` | Now embedded as `<qti-feedback-block>` in QTI XML |
| `feedback_per_option` | Now embedded as `<qti-feedback-inline>` in QTI XML |
| `difficulty_analysis` | Keep in `metadata_tags.json` only (not synced) |
| `general_analysis` | Keep in `metadata_tags.json` only (not synced) |

---

## Pipeline Architecture

### Key Principle

**XSD validation happens immediately after ANY modification to QTI XML.**

This applies to:
- After feedback enhancement (Stage 1)
- After any future XML transformations
- After manual edits (if applicable)

### Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    QUESTION PROCESSING PIPELINE                  │
└─────────────────────────────────────────────────────────────────┘

[Input] QTI XML (base, no feedback)
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│  STAGE 1: FEEDBACK ENHANCEMENT                                   │
│  ─────────────────────────────────────────────────────────────── │
│  • LLM (GPT 5.1, reasoning_effort=medium) receives:              │
│    - Original QTI XML                                            │
│    - Images (if any)                                             │
│    - Instructions for PAES context                               │
│                                                                  │
│  • LLM outputs: COMPLETE QTI XML with feedback embedded          │
│    (not separate JSON → injection, but full XML directly)        │
└──────────────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│  GATE 1: XSD VALIDATION                                          │
│  ─────────────────────────────────────────────────────────────── │
│  • Validate complete QTI XML against QTI 3.0 XSD schema          │
│  • Uses external validator service                               │
│                                                                  │
│  FAIL → Return to Stage 1 with error feedback (max 2 retries)    │
│  PASS → Continue to Stage 2                                      │
└──────────────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│  STAGE 2: FINAL VALIDATION                                       │
│  ─────────────────────────────────────────────────────────────── │
│  • LLM (GPT 5.1, reasoning_effort=high) validates:               │
│    - Factual accuracy of correct answer                          │
│    - Mathematical validity                                       │
│    - Feedback quality and accuracy                               │
│    - Content quality (typos, characters)                         │
│    - Image alignment with stem                                   │
│                                                                  │
│  FAIL → Block sync, log detailed issues                          │
│  PASS → Question is validated                                    │
└──────────────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│  STAGE 3: SYNC TO DATABASE                                       │
│  ─────────────────────────────────────────────────────────────── │
│  • Only questions with validation_status = "pass" can sync       │
│  • Store validated QTI XML (with feedback) in database           │
└──────────────────────────────────────────────────────────────────┘
```

---

## Cost Estimates

### Per Question

| Stage | reasoning_effort | Input tokens | Output tokens | Est. Cost |
|-------|------------------|--------------|---------------|-----------|
| Feedback Enhancement | medium | ~3,000 | ~2,000 | ~$0.024 |
| Final Validation | high | ~4,000 | ~1,000 | ~$0.015 |
| **Total per question** | | ~7,000 | ~3,000 | **~$0.039** |

### Batch Estimates

| Questions | Est. Total Cost |
|-----------|-----------------|
| 100 | ~$4 |
| 500 | ~$20 |
| 1,000 | ~$40 |

---

## File Structure (New Module)

```
app/question_feedback/
├── __init__.py
├── enhancer.py           # FeedbackEnhancer class (Stage 1)
├── validator.py          # FinalValidator class (Stage 2)
├── pipeline.py           # QuestionPipeline orchestrator
├── prompts.py            # PAES-specific prompts (Spanish)
├── schemas.py            # JSON schemas for structured output
├── models.py             # Pydantic models for results
└── utils/
    ├── __init__.py
    ├── qti_parser.py     # Extract info from QTI XML
    └── image_utils.py    # Image URL handling
```

---

## Validation Result Storage

### File Structure Per Question

```
app/data/pruebas/finalizadas/{test_id}/qti/Q{num}/
├── question.xml              # Original QTI XML (before feedback)
├── question_validated.xml    # Validated QTI XML (with feedback) - NEW
├── metadata_tags.json        # Atom tags, difficulty, etc.
└── validation_result.json    # Pipeline validation results - NEW
```

### validation_result.json Schema

```json
{
  "question_id": "prueba-invierno-2025-Q6",
  "pipeline_version": "2.0",
  "timestamp": "2026-02-04T12:30:00Z",
  "stages": {
    "feedback_enhancement": {
      "status": "success",
      "model": "gpt-5.1",
      "reasoning_effort": "medium",
      "attempts": 1
    },
    "xsd_validation": {
      "status": "pass",
      "warnings": []
    },
    "final_validation": {
      "status": "pass",
      "model": "gpt-5.1",
      "reasoning_effort": "high",
      "checks": {
        "correct_answer_check": "pass",
        "feedback_check": "pass",
        "content_quality_check": "pass",
        "image_check": "not_applicable",
        "math_validity_check": "pass"
      }
    }
  },
  "can_sync": true,
  "validated_qti_path": "question_validated.xml",
  "cost_estimate_usd": 0.039
}
```

---

## Design Decisions

### Tagging vs Feedback: Complete Separation

| Module | Responsibility | Output |
|--------|---------------|--------|
| `app/tagging/` | Assign atoms to questions | `metadata_tags.json` with `selected_atoms`, `difficulty`, `habilidad_principal` |
| `app/question_feedback/` | Generate educational feedback | QTI XML with embedded feedback |

**Tagging does NOT generate feedback anymore.**

### Variant Generation Includes Feedback

When generating alternate questions (variants), feedback is generated immediately:

```
Variant Generation Pipeline:
  1. Generate variant QTI XML (new question content)
  2. Generate feedback (embedded in same XML)
  3. XSD validation
  4. LLM final validation
  5. Save only if all validations pass
```

### Clean Old Feedback Data

Remove the `feedback` field from all existing `metadata_tags.json` files.
The old feedback was generated incorrectly. We start fresh with feedback embedded in QTI XML.

---

## Appendix: Example QTI XML with Feedback

See [Appendix-A-example-qti.xml](./Appendix-A-example-qti.xml) for a complete example.
