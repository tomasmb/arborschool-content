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

- **`legacy/`**  
  Previous experiments and artifacts. Read-only for new work.

Other project-wide files live at the root (e.g. `README.md`,
`pyproject.toml`, configuration files).

---

## 2. Inside `app/`

Current structure:

- `app/temarios/`  
  - `parsing.py`: Python code to parse temarios and build structured JSON.

- `app/data/temarios/`  
  - `pdf/`: official DEMRE temario PDFs.  
  - `json/`: structured JSON versions of each temario.

Planned modules:

- `app/standards/`  
  Python code and JSON schemas that convert temarios into canonical
  standards (similar in richness to `standards-paes-m1-full-GPT.md`,
  but machine-friendly).

- `app/atoms/`  
  Atom definitions and prerequisite graphs, plus helpers to map
  standards to atoms and export the KG.

- `app/graph/`  
  Higher-level knowledge-graph assembly, queries and exports (for
  visualizations, downstream tools, etc.).

We will add these folders when we implement the first real code
for each responsibility, rather than creating empty placeholders.

---

## 3. Documentation layout (`docs/`)

- `docs/python-best-practices.md`  
  How we write Python in this repo (style, SOLID/DRY, tooling).

- `docs/repo-structure-and-modules.md` (this file)  
  How the repo is organized and how to extend it.

- `docs/learning-atom-granularity-guidelines.md`  
  Learning-science guidance for atom design (moved from legacy).

- `docs/standards-from-temarios.md`  
  How to go from DEMRE temarios to canonical standards JSON, using M1
  as running example.

We keep **technical repo docs** (tooling, structure) separate from
**learning-science docs** (granularity, pedagogy, KG methodology).

---

## 4. Legacy artifacts

The `legacy/` folder currently contains:

- `legacy/PAES-kg/`: previous markdown explorations of the PAES temario.
- `legacy/PAES-kg-demo/`: demo atoms, prereq graphs and methodology.

These are **reference material only**. New code in `app/` should not
depend on `legacy/` paths, but you can copy over ideas or text into
new docs or modules when needed.

---

## 5. Adding a new module under `app/`

When you add new functionality (e.g. mapping exemplar questions to
atoms), follow this pattern:

1. **Choose the right subfolder**
   - Temario parsing or variants → `app/temarios/`.
   - Standards generation or manipulation → `app/standards/`.
   - Atom definitions, prereqs, KG edges → `app/atoms/`.

2. **Create a focused module**
   - Prefer a single file with a clear purpose over many tiny files.
   - Keep the file below 500 lines and functions small.

3. **Expose clean entry points**
   - Standalone scripts live either as:
     - `app/<area>/scripts/<name>.py`, or
     - small `if __name__ == "__main__":` blocks in focused modules.

4. **Update docs if needed**
   - If a new pattern or process emerges (e.g. new way of building
     standards JSON), add or update a short section in `docs/`.

This keeps the repo simple while making it obvious where new
functionality should live.


