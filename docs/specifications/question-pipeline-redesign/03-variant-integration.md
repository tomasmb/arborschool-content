# Task 03: Variant Generation Integration

> **Type**: Implementation Task
> **Prerequisites**: [02-backend-core.md](./02-backend-core.md) completed
> **Estimated Sessions**: 1-2

## Context

Update the variant generator to include feedback generation immediately after creating
variant QTI XML. Variants should go through the same validation pipeline as original
questions.

## Acceptance Criteria

- [ ] Variant generation includes feedback enhancement step
- [ ] Variants are XSD validated after feedback addition
- [ ] Variants go through final LLM validation
- [ ] Only variants passing all validations are saved
- [ ] Failed variants are logged with details
- [ ] `validation_result.json` saved for each variant

---

## Files to Modify

- `app/question_variants/variant_generator.py`

---

## Current Flow (Before)

```
Generate Variant QTI XML
         │
         ▼
   Save Variant Files
```

## Target Flow (After)

```
Generate Variant QTI XML
         │
         ▼
┌─────────────────────────────┐
│  Feedback Enhancement       │
│  (GPT 5.1, medium)          │
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  XSD Validation             │
│  FAIL → discard variant     │
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  Final LLM Validation       │
│  (GPT 5.1, high)            │
│  FAIL → discard variant     │
└─────────────────────────────┘
         │
         ▼
   Save Variant Files
   (only if all passed)
```

---

## Implementation

### Option A: Use QuestionPipeline Directly

```python
# In variant_generator.py

from app.question_feedback.pipeline import QuestionPipeline

class VariantGenerator:
    def __init__(self):
        self.pipeline = QuestionPipeline()
        # ... existing init
    
    def generate_variant(
        self,
        parent_question_id: str,
        parent_qti_xml: str,
        # ... other params
    ) -> VariantResult:
        # 1. Generate variant QTI XML (existing logic)
        variant_qti_raw = self._generate_variant_content(parent_qti_xml)
        
        # 2. Process through feedback pipeline
        variant_id = f"{parent_question_id}-variant-{self._generate_variant_number()}"
        
        pipeline_result = self.pipeline.process(
            question_id=variant_id,
            qti_xml=variant_qti_raw,
            image_urls=self._extract_image_urls(variant_qti_raw),
            output_dir=self._get_variant_output_dir(parent_question_id, variant_id)
        )
        
        if not pipeline_result.success:
            logger.warning(
                f"Variant {variant_id} failed pipeline: "
                f"stage={pipeline_result.stage_failed}, "
                f"error={pipeline_result.error}"
            )
            return VariantResult(
                success=False,
                variant_id=variant_id,
                error=pipeline_result.error,
                stage_failed=pipeline_result.stage_failed
            )
        
        # 3. Save variant files (only if pipeline passed)
        self._save_variant_files(
            variant_id=variant_id,
            qti_xml=pipeline_result.qti_xml_final,
            parent_question_id=parent_question_id
        )
        
        return VariantResult(
            success=True,
            variant_id=variant_id,
            qti_xml=pipeline_result.qti_xml_final
        )
```

### Option B: Separate Enrichment Step

If variant generation is expensive and you want to decouple it from feedback:

```python
class VariantGenerator:
    def generate_variant(self, ...) -> VariantResult:
        # Generate QTI XML without feedback
        variant_qti_raw = self._generate_variant_content(parent_qti_xml)
        
        # Save raw variant
        self._save_raw_variant(variant_id, variant_qti_raw)
        
        return VariantResult(
            success=True,
            variant_id=variant_id,
            qti_xml=variant_qti_raw,
            needs_enrichment=True  # Flag for later processing
        )

# Then use "Enrich Feedback" action from UI to process variants
```

**Recommendation**: Use Option A (integrated pipeline) for consistency.

---

## Variant Result Model

Add to `app/question_variants/models.py` or update existing:

```python
@dataclass
class VariantResult:
    success: bool
    variant_id: str
    qti_xml: str | None = None
    error: str | None = None
    stage_failed: str | None = None
    validation_details: dict | None = None
```

---

## Update Variant Storage

Variant folders should now include:

```
app/data/pruebas/finalizadas/{test_id}/qti/Q{num}/variants/{variant_id}/
├── question.xml              # Validated QTI XML (with feedback)
├── validation_result.json    # Pipeline validation results
└── metadata.json             # Variant metadata (parent_id, etc.)
```

---

## Summary Checklist

```
[ ] Update variant_generator.py to use QuestionPipeline
[ ] Add VariantResult model with validation fields
[ ] Update variant storage to include validation_result.json
[ ] Add logging for failed variants
[ ] Test variant generation with feedback pipeline
[ ] Verify failed variants are not saved
```
