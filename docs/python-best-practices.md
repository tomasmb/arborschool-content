## Python Best Practices for This Repo

This document summarizes how we write Python in this project.  
It blends modern Python ecosystem guidance (up to 2024) with classic
software-engineering ideas (SOLID, DRY) and your specific constraints.

---

## 1. Project philosophy

- **Readable over clever**
  - Prioritize clarity, domain naming and short functions.
  - Favour explicitness over “Python one-liners”.

- **Stable interfaces, evolving internals**
  - Public functions and modules in `app/` are the long–lived API.
  - Internals can be refactored as long as behaviour and tests remain
    consistent.

- **Small, composable pieces**
  - Prefer small pure functions and data classes.
  - Push I/O (file system, CLI) to thin wrappers at the edges.

---

## 2. Repository layout (Python view)

- **`app/`** is the code and data “source of truth”
  - `app/temarios/`: Python code to parse and work with temarios.
  - `app/data/temarios/`: DEMRE temario PDFs and the structured JSON generated from them.
  - Future modules:
    - `app/standards/`: canonical standards JSON and tooling.
    - `app/atoms/`: atom definitions, prereq graphs, KG utilities.
    - `app/graph/`: knowledge-graph assembly, queries, exports.

- **`docs/`**: explainer and design docs, not executable code.

- **`legacy/`**: previous experiments and artifacts.  
  Read-only from the point of view of new code.

Internally, we prefer **flat, feature-oriented modules** over deeply nested
packages until there is a strong reason to split further.

---

## 3. Code style and structure

- **Type hints**
  - All new public functions must be type annotated.
  - Use `from __future__ import annotations` in modules with hints.
  - Prefer standard types (`dict[str, str]`) over `typing.Dict`.

- **Functions**
  - Target **≤ 25–40 lines** per function.
  - Each function has **one clear responsibility**.
  - Avoid boolean flags that radically change behaviour; prefer two functions.

- **Modules**
  - Target **≤ 300–400 lines** per module (hard limit 500 as per repo rule).
  - Group by domain (e.g. `temarios`, `standards`, `atoms`), not by layer.

- **Imports**
  - Standard lib, then third-party, then local imports, separated by blank lines.
  - Absolute imports within `app` (e.g. `from app.temarios import parser`).

---

## 4. SOLID and DRY in this project

We apply these principles pragmatically and lightly.

- **Single Responsibility (S)**
  - A module should “do one thing well”: parsing temarios, building standards,
    generating atoms, etc.
  - Example: `app/temarios/parsing.py` only:
    - reads temario PDFs,
    - builds structured JSON,
    - writes it to disk.

- **Open/Closed (O)**
  - New temarios, standards or atoms should be addable **by adding modules or
    functions**, not by editing many existing call sites.
  - Use small, pluggable functions (e.g. a `parse_temario()` function that
    accepts a config object for each exam version).

- **Liskov Substitution (L)**
  - When introducing abstractions (e.g. protocol for data sources), make sure
    every implementation can be used wherever the base type is expected,
    without surprising behaviour.

- **Interface Segregation (I)**
  - Expose **narrow interfaces** tailored to each use case.
  - Avoid “god” classes or modules that mix parsing, modeling and exporting.

- **Dependency Inversion (D)**
  - High-level modules (`standards`, `atoms`, `graph`) depend on **abstract
    interfaces** (e.g. functions that return Python dicts), not on concrete
    file formats or CLI tools.

- **DRY (Don’t Repeat Yourself)**
  - Shared helpers for:
    - file I/O patterns,
    - common temario parsing utilities,
    - JSON load/save with consistent options.
  - If two modules share three or more lines of “structural” logic, extract a
    helper in `app/common/` (once that exists).

---

## 5. Error handling and logging

- Use **exceptions for exceptional situations**, not for control flow.
- In scripts:
  - Catch top-level exceptions and print a short, actionable message.
  - Exit with non-zero code on failure.
- For now we avoid heavy logging frameworks; when needed, use `logging` from
  the standard library with module-level loggers.

---

## 6. Testing and reproducibility

Even if tests are written later, code should be **testable by design**:

- Deterministic functions (given same inputs, same outputs).
- External dependencies (files, network) passed in as parameters or small
  wrapper functions, not hidden globals.
- Where randomness is needed, allow injection of a seed or RNG.

---

## 7. Style tools and linters

We use a modern, minimal toolchain:

- **Ruff** for linting (and optionally formatting) configured via `pyproject.toml`.
  - Enforce:
    - import order,
    - unused imports/variables,
    - simple style rules,
    - complexity limits where useful.
- Keep **line length < 150 chars** (project rule), but aim for ~100 chars for
  readability.

Tools are helpers, not goals. If a rule hurts clarity in a specific case, we
can selectively disable it with an inline comment **and document why**.

---

## 8. Practical checklist for new Python code

Before committing new Python:

1. File lives under `app/` and respects the current module layout.
2. Functions and public APIs are type-annotated.
3. No obvious duplication with existing helpers.
4. Lines are shorter than 150 characters.
5. Ruff (and formatter, if configured) runs clean on the changed files.


