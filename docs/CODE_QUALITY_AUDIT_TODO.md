# Code Quality Audit - TODO List

> **Branch:** `refactor/code-quality-audit`  
> **Created:** 2026-02-02  
> **Goal:** Ensure codebase aligns with SOLID principles, file size limits, and code standards.

---

## Quick Reference: Standards

| Metric | Limit | Ideal |
|--------|-------|-------|
| File size | < 500 lines | 300-400 lines |
| Function size | < 40 lines | 25-30 lines |
| Line length | < 150 chars | ~100 chars |

---

## Phase 1: Critical - Files Over 500 Lines

These files exceed the hard limit and need immediate refactoring.

### Priority 1: Files > 1000 Lines (Critical)

- [x] **`app/pruebas/pdf-to-qti/modules/qti_transformer.py`** (1093 → 345 lines) ✅
  - [x] Analyze responsibilities and identify logical splits
  - [x] Extract helper modules:
    - `qti_encoding.py` (187 lines) - encoding detection/validation
    - `qti_answer_utils.py` (112 lines) - answer extraction/update
    - `qti_response_parsers.py` (148 lines) - LLM response parsing
    - `qti_xml_utils.py` (228 lines) - XML cleanup, S3 replacement
    - `qti_image_handler.py` (323 lines) - image upload, LLM prep
  - [x] Ensure no functionality loss after split (backward compatible imports)

- [x] **`app/pruebas/pdf-to-qti/main.py`** (1092 → 449 lines) ✅
  - [x] Extract orchestration logic vs processing logic
  - [x] Created 4 new modules for better separation of concerns:
    - `external_validation.py` (236 lines) - external service validation
    - `pipeline_cache.py` (225 lines) - cache/skip/regeneration logic
    - `pipeline_s3.py` (364 lines) - S3 mapping and image processing
    - `pipeline_helpers.py` (196 lines) - question ID, answer key, debug files
  - [x] Enhanced `utils/s3_uploader.py` (262 → 366 lines) with convert function
  - [x] All backward-compatible imports maintained

### Priority 2: Files 800-1000 Lines (High)

- [x] **`app/pruebas/pdf-to-qti/modules/pdf_processor.py`** (997 → 184 lines) ✅
  - [x] Extracted text processing module:
    - `pdf_text_processing.py` (261 lines) - text block extraction, choice splitting
  - [x] Extracted image utilities module:
    - `pdf_image_utils.py` (207 lines) - rendering, trimming, meaningfulness check
  - [x] Extracted table extraction:
    - `pdf_table_extraction.py` (89 lines) - PyMuPDF table detection, reconstruction
  - [x] Refactored visual content pipeline:
    - `pdf_visual_pipeline.py` (399 lines) - main extraction orchestration
    - `pdf_visual_separation.py` (283 lines) - prompt vs choice image separation
  - [x] Main entry `pdf_processor.py` (184 lines) with backward-compatible exports

- [x] **`app/atoms/prompts.py`** (862 → 28 lines) ✅
  - [x] Created `app/atoms/prompts/` package with focused modules:
    - `atom_guidelines.py` (120 lines) - Granularity guidelines constant
    - `atom_schema.py` (30 lines) - JSON schema example
    - `atom_rules.py` (415 lines) - Generation rules
    - `atom_final_instruction.py` (214 lines) - Final checklist instruction
    - `atom_generation.py` (115 lines) - Main prompt builder
  - [x] Backward-compatible re-exports in `prompts.py`

- [x] **`app/pruebas/pdf-to-qti/modules/image_processing/image_detection.py`** (826 → 33 lines) ✅
  - [x] Created 5 focused modules:
    - `image_detection_ai.py` (198 lines) - AI-powered detection
    - `image_detection_helpers.py` (119 lines) - Text extraction, categorization
    - `image_bbox_construction.py` (207 lines) - Bbox from gaps
    - `image_bbox_expansion.py` (202 lines) - Intelligent expansion
    - `image_adequacy.py` (232 lines) - Adequacy assessment
  - [x] Backward-compatible re-exports maintained

- [ ] **`app/pruebas/pdf-to-qti/scripts/render_qti_to_html.py`** (806 lines)
  - [ ] Split rendering logic from file I/O
  - [ ] Extract template handling

### Priority 3: Files 500-800 Lines (Medium)

- [ ] **`app/pruebas/pdf-to-qti/modules/validation/question_validator.py`** (787 lines)
  - [ ] Split validation rules into separate modules
  - [ ] Consider one file per validation type

- [ ] **`app/pruebas/pdf-to-qti/modules/prompt_builder.py`** (685 lines)
  - [ ] Group prompts by domain
  - [ ] Extract prompt templates to separate file

- [ ] **`app/pruebas/pdf-to-qti/modules/ai_processing/ai_content_analyzer.py`** (584 lines)
  - [ ] Separate analysis logic from LLM integration
  - [ ] Extract content-specific analyzers

- [ ] **`app/pruebas/pdf-to-qti/modules/image_processing/choice_diagrams.py`** (542 lines)
  - [ ] Extract diagram detection vs processing

- [ ] **`app/pruebas/pdf-splitter/modules/chunk_segmenter.py`** (534 lines)
  - [ ] Split segmentation strategies

- [ ] **`app/pruebas/pdf-splitter/modules/pdf_utils.py`** (532 lines)
  - [ ] Group utilities by purpose

- [ ] **`app/tagging/tagger.py`** (509 lines)
  - [ ] Extract tagging strategies
  - [ ] Separate I/O from core logic

- [ ] **`app/pruebas/pdf-to-qti/scripts/migrate_s3_images_by_test.py`** (504 lines)
  - [ ] Extract S3 utilities
  - [ ] Separate migration logic from CLI

- [ ] **`app/pruebas/pdf-to-qti/modules/qti_configs.py`** (502 lines)
  - [ ] Split configs by QTI version or type
  - [ ] Consider YAML/JSON for static configs

---

## Phase 2: Line Length Violations (> 150 chars)

Files with lines exceeding the 150-character limit.

### High Priority (> 10 violations)

- [ ] **`app/pruebas/pdf-to-qti/modules/prompt_builder.py`** (26 long lines)
  - [ ] Break long strings using parentheses or multi-line
  - [ ] Use variables for repeated long expressions

### Medium Priority (5-10 violations)

- [ ] **`app/pruebas/pdf-splitter/modules/quality_validator.py`** (9 violations)
- [ ] **`app/pruebas/pdf-to-qti/modules/image_processing/llm_analyzer.py`** (10 violations)
- [ ] **`app/pruebas/pdf-splitter/modules/chunk_segmenter.py`** (9 violations)
- [ ] **`app/atoms/validation/validation.py`** (8 violations)
- [ ] **`app/tagging/tagger.py`** (7 violations)
- [ ] **`app/pruebas/pdf-to-qti/modules/qti_configs.py`** (7 violations)

### Lower Priority (< 5 violations)

- [ ] `app/standards/prompts.py` (2 violations)
- [ ] `app/tagging/tag_habilidades.py` (3 violations)
- [ ] `app/question_variants/variant_generator.py` (2 violations)
- [ ] `app/pruebas/pdf-splitter/modules/pdf_utils.py` (3 violations)
- [ ] `app/pruebas/pdf-to-qti/scripts/force_upload_images.py` (2 violations)
- [ ] `app/pruebas/pdf-splitter/modules/bbox_computer.py` (2 violations)
- [ ] And others with 1 violation each...

---

## Phase 3: SOLID Principles Audit

### S - Single Responsibility

For each module, verify it has ONE clear purpose.

- [ ] **`app/pruebas/pdf-to-qti/main.py`**
  - Does it mix: CLI handling, orchestration, processing, error handling?
  - Recommendation: Split into `cli.py`, `pipeline.py`, `orchestrator.py`

- [ ] **`app/atoms/generation.py`**
  - [ ] Review: Does it only generate atoms, or also validate/persist?
  
- [ ] **`app/tagging/tagger.py`**
  - [ ] Review: Does it mix tagging logic with I/O operations?

- [ ] **`app/diagnostico/engine.py`**
  - [ ] Review: Single purpose or multiple responsibilities?

### O - Open/Closed Principle

Check if new features require modifying existing code or just adding new code.

- [ ] **Question type handling**
  - Can new question types be added without modifying core logic?
  - Consider strategy pattern for extensibility

- [ ] **Validation rules**
  - Can new validators be added via registration/configuration?

- [ ] **Prompt templates**
  - Are prompts configurable without code changes?

### L - Liskov Substitution

Review any inheritance or protocol usage.

- [ ] Scan for `class X(Y):` patterns
- [ ] Verify derived classes don't break parent contracts
- [ ] Check for proper use of abstract base classes

### I - Interface Segregation

Check for "god" modules or overly broad interfaces.

- [ ] **`app/pruebas/pdf-to-qti/modules/qti_transformer.py`**
  - Does it expose too many unrelated functions?
  - Split into focused interfaces

- [ ] **`app/utils/` modules**
  - Are utilities properly segregated by concern?

### D - Dependency Inversion

High-level modules should depend on abstractions.

- [ ] Check for hardcoded file paths in business logic
- [ ] Review direct I/O calls in processing modules
- [ ] Consider dependency injection for testability

---

## Phase 4: DRY Principle (Don't Repeat Yourself)

### Potential Duplications to Investigate

- [ ] **JSON load/save patterns**
  - Search for repeated `json.load()` / `json.dump()` with same options
  - Consider `app/common/io.py` helpers

- [ ] **File path handling**
  - Look for repeated path construction patterns
  - Centralize in `app/common/paths.py`

- [ ] **LLM client initialization**
  - Multiple modules likely initialize similar clients
  - Consider shared client factory

- [ ] **Error handling patterns**
  - Look for repeated try/except structures
  - Consider decorators for common error handling

- [ ] **Prompt construction**
  - Multiple files build prompts similarly
  - Centralize prompt utilities

---

## Phase 5: Type Hints Audit

### Check for Missing Type Annotations

- [ ] Run: `mypy app/ --ignore-missing-imports` (when available)
- [ ] Or manually review public functions for missing hints

### Priority Modules

- [ ] **`app/atoms/`** - Core domain, should be fully typed
- [ ] **`app/diagnostico/`** - User-facing, needs type safety
- [ ] **`app/tagging/`** - Integration module, benefits from types
- [ ] **`app/pruebas/pdf-to-qti/`** - Large module, prioritize public APIs

### Specific Checks

- [ ] Verify `from __future__ import annotations` in typed modules
- [ ] Use `dict[str, T]` not `Dict[str, T]`
- [ ] Use `list[T]` not `List[T]`

---

## Phase 6: Linting & Formatting

### Setup (if not already)

- [ ] Ensure `ruff` is installed: `pip install ruff`
- [ ] Run full check: `ruff check app/`
- [ ] Fix all errors before proceeding

### Specific Ruff Rules

- [ ] `E` - pycodestyle errors
- [ ] `F` - Pyflakes
- [ ] `W` - Warnings  
- [ ] `I` - Import sorting

### Optional Enhancements

- [ ] Consider enabling complexity rules (`C901`)
- [ ] Consider enabling docstring rules (`D`)

---

## Phase 7: Documentation Audit

### Missing Documentation

- [ ] Check all public functions have docstrings
- [ ] Verify docstrings describe "why" not just "what"
- [ ] Remove obsolete/outdated comments

### README Files

- [ ] **`app/pruebas/pdf-to-qti/README.md`** - Exists? Up to date?
- [ ] **`app/atoms/README.md`** - Describes generation pipeline?
- [ ] **`app/diagnostico/README.md`** - Documents engine behavior?

---

## Phase 8: Code Smells Checklist

Review each refactored file for these smells:

| Smell | Check | Fixed? |
|-------|-------|--------|
| Long Method | Functions > 40 lines | [ ] |
| Large Module | Files > 500 lines | [ ] |
| Duplicate Code | Same logic in 2+ places | [ ] |
| Feature Envy | Function uses other module's data excessively | [ ] |
| Magic Numbers | Hardcoded values without names | [ ] |
| Dead Code | Commented or unused code | [ ] |
| Long Parameter List | Functions with 5+ params | [ ] |

---

## Execution Order (Recommended)

1. **Phase 6: Linting** - Quick wins, establishes baseline
2. **Phase 2: Line Length** - Easy fixes, improves readability
3. **Phase 1: File Splitting** - Most impactful, enables other changes
4. **Phase 3: SOLID Audit** - Deep review during splitting
5. **Phase 4: DRY** - Extract common patterns found during splitting
6. **Phase 5: Type Hints** - Add as you touch files
7. **Phase 7: Documentation** - Update after structural changes
8. **Phase 8: Final Review** - Catch remaining smells

---

## Progress Tracking

### Summary

| Phase | Total Items | Completed | Progress |
|-------|-------------|-----------|----------|
| Phase 1 | 15 files | 5 | 33% |
| Phase 2 | ~20 files | 0 | 0% |
| Phase 3 | 5 principles | 0 | 0% |
| Phase 4 | 5 areas | 0 | 0% |
| Phase 5 | 4 modules | 0 | 0% |
| Phase 6 | 1 task | 0 | 0% |
| Phase 7 | 3 areas | 0 | 0% |
| Phase 8 | Final | 0 | 0% |

---

## Notes

- Reference: `docs/specifications/CODE_STANDARDS.md`
- Reference: `docs/specifications/python-best-practices.md`
- When splitting files, maintain backward compatibility with imports
- Test thoroughly after each major refactoring
- Commit frequently with descriptive messages

---

*Last updated: 2026-02-02*

---

## Changelog

### 2026-02-02 (Session 3)
- **image_detection.py** refactored: 826 → 33 lines (96% reduction)
  - Created 5 focused modules for AI detection, helpers, bbox construction,
    bbox expansion, and adequacy assessment
  - All backward-compatible imports maintained

- **atoms/prompts.py** refactored: 862 → 28 lines (97% reduction)
  - Created `app/atoms/prompts/` package with 5 focused modules
  - Separated guidelines, rules, schema, instructions, and generation logic
  - All backward-compatible imports maintained

- **pdf_processor.py** refactored: 997 → 184 lines (82% reduction)
  - Created 5 new modules for clean separation of concerns:
    - `pdf_text_processing.py` (261 lines) - text extraction, choice block splitting
    - `pdf_image_utils.py` (207 lines) - image rendering, trimming utilities
    - `pdf_table_extraction.py` (89 lines) - PyMuPDF table detection
    - `pdf_visual_pipeline.py` (399 lines) - main extraction orchestration
    - `pdf_visual_separation.py` (283 lines) - prompt/choice image separation
  - Broke 440-line "god function" into focused step functions
  - All backward-compatible imports maintained

### 2026-02-02 (Session 2)
- **main.py** refactored: 1092 → 449 lines (59% reduction)
  - Created 4 new pipeline modules:
    - `external_validation.py` (236 lines) - external validation service client
    - `pipeline_cache.py` (225 lines) - cache checking, skip logic, regeneration
    - `pipeline_s3.py` (364 lines) - S3 mapping, image post-processing
    - `pipeline_helpers.py` (196 lines) - question ID, answer key, debug files
  - Enhanced `utils/s3_uploader.py` with `convert_base64_to_s3_in_xml` function
  - All backward-compatible imports maintained

### 2026-02-02 (Session 1)
- **qti_transformer.py** refactored: 1093 → 345 lines
  - Created 5 new modules for better separation of concerns
  - All backward-compatible imports maintained
