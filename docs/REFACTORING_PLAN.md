# Code Quality Refactoring Plan

> **Branch:** `refactor/code-quality-audit`  
> **Created:** 2026-02-02  
> **Status:** In Progress

---

## Executive Summary

This plan addresses the code quality audit by splitting files exceeding 500 lines while
maintaining functionality and backward compatibility. We follow a **one-file-at-a-time**
approach with the most critical files first.

---

## Approach

1. **Order:** Start with Priority 1 files (>1000 lines), then Priority 2
2. **Scope:** One file per session, complete refactor before moving to next
3. **Method:** Extract logical modules, maintain public API, update imports
4. **Testing:** Manual testing after each file refactor

---

## Priority 1: Files > 1000 Lines

### 1.1 `app/pruebas/pdf-to-qti/modules/qti_transformer.py` (1093 lines)

**Current Structure:**
| Function | Lines | Responsibility |
|----------|-------|----------------|
| `ENCODING_FIXES` dict | 1-104 | Encoding error mappings |
| `detect_encoding_errors` | 105-134 | Find encoding issues |
| `validate_no_encoding_errors_or_raise` | 135-160 | Validate/raise on errors |
| `verify_and_fix_encoding` | 161-196 | Fix encoding in XML |
| `extract_correct_answer_from_qti` | 197-236 | Parse answer from QTI |
| `update_correct_answer_in_qti_xml` | 237-288 | Update answer in XML |
| `transform_to_qti` | 289-765 | **MAIN** - Core transformation (~476 lines) |
| `replace_data_uris_with_s3_urls` | 766-838 | Image S3 upload logic |
| `fix_qti_xml_with_llm` | 839-936 | LLM-based XML fixing |
| `parse_transformation_response` | 937-1007 | Parse LLM response |
| `parse_correction_response` | 1008-1066 | Parse correction response |
| `clean_qti_xml` | 1067-1093 | Clean XML content |

**Proposed Split:**

```
modules/
├── qti_transformer.py          (~300 lines) - Main transform_to_qti + orchestration
├── qti_encoding.py             (~200 lines) - Encoding detection/fixing
├── qti_answer_utils.py         (~100 lines) - Answer extraction/updating
├── qti_response_parsers.py     (~150 lines) - LLM response parsing
└── qti_xml_utils.py            (~150 lines) - XML cleanup, S3 replacement, LLM fixing
```

**Migration Steps:**
- [ ] Create `qti_encoding.py` with ENCODING_FIXES + encoding functions
- [ ] Create `qti_answer_utils.py` with answer extraction/update functions
- [ ] Create `qti_response_parsers.py` with parse functions
- [ ] Create `qti_xml_utils.py` with cleanup and S3 functions
- [ ] Update `qti_transformer.py` to import from new modules
- [ ] Add re-exports in `__init__.py` for backward compatibility
- [ ] Verify all imports work throughout codebase

---

### 1.2 `app/pruebas/pdf-to-qti/main.py` (1092 lines)

**Current Structure:**
| Function | Lines | Responsibility |
|----------|-------|----------------|
| `convert_base64_to_s3_manual` | 30-133 | S3 upload logic |
| `process_single_question_pdf` | 135-897 | **MASSIVE** - Full pipeline (~762 lines!) |
| `validate_with_external_service` | 898-1043 | External validation |
| `main` | 1044-1092 | CLI entry point |

**Problem:** `process_single_question_pdf` is 762 lines - a single function doing too much.

**Proposed Split:**

```
pdf-to-qti/
├── main.py                     (~100 lines) - CLI entry point only
├── pipeline.py                 (~250 lines) - process_single_question_pdf orchestration
├── pipeline_steps/
│   ├── __init__.py
│   ├── content_extraction.py   (~150 lines) - PDF extraction step
│   ├── type_detection.py       (~100 lines) - Question type detection
│   ├── qti_generation.py       (~150 lines) - QTI transformation step
│   ├── validation_step.py      (~150 lines) - Validation logic
│   └── s3_upload.py            (~100 lines) - S3/base64 handling
└── external_validation.py      (~150 lines) - External service validation
```

**Migration Steps:**
- [ ] Analyze `process_single_question_pdf` to identify logical stages
- [ ] Extract each stage as a separate function/module
- [ ] Create `pipeline.py` as orchestrator calling step functions
- [ ] Move `convert_base64_to_s3_manual` to `pipeline_steps/s3_upload.py`
- [ ] Move `validate_with_external_service` to `external_validation.py`
- [ ] Keep `main.py` thin - just CLI parsing + calling pipeline
- [ ] Update all internal imports

---

## Priority 2: Files 800-1000 Lines

### 2.1 `app/pruebas/pdf-to-qti/modules/pdf_processor.py` (997 lines)

**Proposed Split:**
- `pdf_processor.py` - Main extraction logic
- `pdf_text_extraction.py` - Text extraction helpers
- `pdf_layout_analysis.py` - Layout/structure detection

### 2.2 `app/atoms/prompts.py` (862 lines)

**Proposed Split:**
- `prompts/generation.py` - Atom generation prompts
- `prompts/validation.py` - Validation prompts
- `prompts/common.py` - Shared prompt utilities

### 2.3 `app/pruebas/pdf-to-qti/modules/image_processing/image_detection.py` (826 lines)

**Proposed Split:**
- `image_detection.py` - Detection orchestration
- `boundary_detection.py` - Edge/boundary algorithms
- `region_analysis.py` - Region identification

### 2.4 `app/pruebas/pdf-to-qti/scripts/render_qti_to_html.py` (806 lines)

**Proposed Split:**
- `render_qti_to_html.py` - Main rendering logic
- `html_templates.py` - Template handling
- `render_utils.py` - File I/O and utilities

---

## Priority 3: Files 500-800 Lines

| File | Lines | Quick Fix |
|------|-------|-----------|
| `question_validator.py` | 787 | Split by validation type |
| `prompt_builder.py` | 685 | Group by domain |
| `ai_content_analyzer.py` | 584 | Separate LLM integration |
| `choice_diagrams.py` | 542 | Split detection/processing |
| `chunk_segmenter.py` | 534 | Split strategies |
| `pdf_utils.py` | 532 | Group by purpose |
| `tagger.py` | 509 | Extract strategies |
| `migrate_s3_images_by_test.py` | 504 | Extract S3 utilities |
| `qti_configs.py` | 502 | Use YAML/JSON for configs |

---

## Execution Checklist

### Phase 1: qti_transformer.py ✅ COMPLETE
- [x] Read full file and understand dependencies
- [x] Create `qti_encoding.py` (187 lines)
- [x] Create `qti_answer_utils.py` (112 lines)
- [x] Create `qti_response_parsers.py` (148 lines)
- [x] Create `qti_xml_utils.py` (228 lines)
- [x] Create `qti_image_handler.py` (323 lines)
- [x] Refactor `qti_transformer.py` (345 lines)
- [x] Update `modules/__init__.py`
- [x] Verify no broken imports
- [x] Run linting
- [ ] Manual testing (pending user verification)

### Phase 2: main.py
- [ ] Analyze `process_single_question_pdf` stages
- [ ] Create `pipeline_steps/` directory
- [ ] Extract step modules
- [ ] Create `pipeline.py`
- [ ] Refactor `main.py`
- [ ] Verify no broken imports
- [ ] Run linting
- [ ] Manual testing

---

## Success Criteria

- [ ] All files under 500 lines
- [ ] No broken imports
- [ ] Same functionality (manual testing passes)
- [ ] Clean linting (`ruff check app/`)
- [ ] Functions under 40 lines (ideally 25-30)

---

## Current Progress

| File | Status | New Line Count |
|------|--------|----------------|
| `qti_transformer.py` | ✅ **DONE** | 1093 → **345** |
| `qti_encoding.py` | ✅ **NEW** | **187** (extracted) |
| `qti_answer_utils.py` | ✅ **NEW** | **112** (extracted) |
| `qti_response_parsers.py` | ✅ **NEW** | **148** (extracted) |
| `qti_xml_utils.py` | ✅ **NEW** | **228** (extracted) |
| `qti_image_handler.py` | ✅ **NEW** | **323** (extracted) |
| `main.py` | 🔴 Not Started | 1092 → ? |
| `pdf_processor.py` | 🔴 Not Started | 997 → ? |
| `prompts.py` | 🔴 Not Started | 862 → ? |

---

## Notes

- Maintain backward compatibility via re-exports
- Commit after each file refactor
- Update this document as we progress

---

*Last updated: 2026-02-02 (qti_transformer.py complete)*
