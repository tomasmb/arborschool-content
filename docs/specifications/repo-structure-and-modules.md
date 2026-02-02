## Repository Structure and Modules

This document explains how we organize this repo and how to add new
modules as the knowledge graph grows.

---

## 1. Top-level layout

- **`app/`**  
  All Python code and data that the application uses.

- **`docs/`**  
  Design docs, best-practices, learning-science guidelines, and
  domain explanations.

- **`tests/`**  
  Test fixtures and test data.

Other project-wide files live at the root (e.g. `pyproject.toml`,
configuration files).

---

## 2. Inside `app/` (current structure)

### Core modules

- `app/gemini_client.py`  
  Reusable Gemini client wrapper (using `gemini-3-pro-preview`).  
  Reads `GEMINI_API_KEY` from the project-level `.env` file.

- `app/temarios/`  
  - `parsing.py`: parses DEMRE temario PDFs and builds structured JSON.

- `app/standards/`  
  Python code that converts temarios into canonical standards.
  - `generation.py`, `validation.py`, `pipeline.py`
  - `models.py`, `prompts.py`

- `app/atoms/`  
  Atom definitions, prerequisite graphs, validation.
  - `generation.py`, `models.py`, `prompts.py`
  - `validation/`: atom validation logic
  - `scripts/`: generation and export scripts

- `app/question_variants/`  
  AI-powered generation of question variants.
  - `pipeline.py`, `variant_generator.py`, `variant_validator.py`

- `app/tagging/`  
  Tags questions with atoms and skills.
  - `tagger.py`, `batch_runner.py`

- `app/diagnostico/`  
  Diagnostic test engine and web UI.
  - `engine.py`, `scorer.py`
  - `config/`: skill tree and question mappings
  - `web/`: HTML/JS frontend
  - `scripts/`: utility scripts

- `app/sync/`  
  Syncs content repository to student app database.
  - `db_client.py`, `s3_client.py`, `transformers.py`

### Pipeline modules

- `app/pruebas/pdf-splitter/`  
  Splits multi-question PAES PDFs into individual question PDFs.
  - `main.py`, `lambda_handler.py`
  - `modules/`: processing logic

- `app/pruebas/pdf-to-qti/`  
  Converts question PDFs to QTI format.
  - `main.py`, `lambda_handler.py`
  - `modules/`: AI processing, image processing, validation
  - `scripts/`: processing and migration scripts

- `app/pruebas/archive/`  
  Archived one-time fix scripts (historical reference only).

### Data directories

- `app/data/temarios/`  
  - `pdf/`: official DEMRE temario PDFs (source inputs)
  - `json/`: structured JSON versions

- `app/data/standards/`  
  Canonical standards JSON files.

- `app/data/atoms/`  
  Atom definitions JSON.

- `app/data/pruebas/`  
  - `raw/`: original PAES test PDFs
  - `procesadas/`: processed questions (QTI, JSON, PDFs)
  - `alternativas/`: generated question variants
  - `finalizadas/`: finalized questions ready for production

- `app/data/diagnostico/`  
  Output data from diagnostic processing.

---

## 3. Documentation layout (`docs/`)

- `docs/specifications/`  
  Normative documentation (data models, standards, guidelines).

- `docs/research/`  
  Exploratory research and design options.

- `docs/analysis/`  
  Content analysis (coverage, gaps).

- `docs/archive/`  
  Historical documentation of completed work.

- `docs/HANDOVER.md`  
  Current state summary and immediate next steps.

- `docs/TECHNICAL_DEBT.md`  
  Files pending refactorization.

---

## 4. Adding a new module under `app/`

When you add new functionality, follow this pattern:

1. **Choose the right subfolder**
   - Temario parsing → `app/temarios/`
   - Standards generation → `app/standards/`
   - Atom definitions, prereqs → `app/atoms/`
   - Question processing → `app/pruebas/`
   - Question variants → `app/question_variants/`

2. **Create a focused module**
   - Prefer a single file with a clear purpose over many tiny files.
   - Keep the file below 500 lines and functions small.

3. **Expose clean entry points**
   - Standalone scripts live in `app/<area>/scripts/<name>.py`
   - Script entry points must be **thin wrappers** that call well-typed functions.

4. **Update docs if needed**
   - When you change a public contract, update the relevant doc in `docs/specifications/`.

---

## 5. Naming conventions

- **Folders**: lowercase with hyphens (e.g., `pdf-to-qti`, `prueba-invierno-2025`)
- **Python files**: lowercase with underscores (e.g., `gemini_client.py`)
- **Test IDs**: lowercase with hyphens (e.g., `prueba-invierno-2025`)
