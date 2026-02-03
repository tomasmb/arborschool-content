# arborschool-content

PAES M1 knowledge graph tooling: temarios, standards, atoms, question processing, and database sync.

## Overview

This repository contains the content pipeline for PAES M1 (Matemática 1) educational content:

- **Knowledge Graph**: Standards → Atoms → Questions hierarchy
- **Question Processing**: PDF → QTI 3.0 XML conversion pipeline
- **Variant Generation**: AI-powered question variant creation
- **Content Sync**: Push finalized content to student app database

## Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

## Quick Start

```bash
# Clone the repository
git clone https://github.com/tomasmb/arborschool-content.git
cd arborschool-content

# Install dependencies
uv sync

# Or with pip
pip install -e .

# Set up environment variables
cp .env.example .env  # Then edit with your API keys
```

## Project Structure

```
arborschool-content/
├── app/                    # Python code and data
│   ├── gemini_client.py    # Gemini API wrapper
│   ├── temarios/           # DEMRE temario PDF parsing
│   ├── standards/          # Standards generation pipeline
│   ├── atoms/              # Learning atom definitions
│   ├── question_variants/  # AI variant generation
│   ├── tagging/            # Question-atom tagging
│   ├── sync/               # Database sync
│   ├── pruebas/            # Question processing pipelines
│   │   ├── pdf-splitter/   # Split multi-question PDFs
│   │   └── pdf-to-qti/     # Convert PDFs to QTI XML
│   ├── utils/              # Shared utilities
│   └── data/               # All data files
│       ├── temarios/       # Temario PDFs and JSON
│       ├── standards/      # Canonical standards
│       ├── atoms/          # Atom definitions
│       ├── pruebas/        # Test questions (raw, processed, finalized)
│       └── diagnostico/    # Diagnostic test variants
├── docs/                   # Documentation
│   ├── specifications/     # Normative specs (data models, guidelines)
│   ├── research/           # Exploratory research
│   └── analysis/           # Content coverage analysis
├── tests/                  # Test fixtures and data
└── pyproject.toml          # Project configuration
```

## Key Modules

| Module | Purpose |
|--------|---------|
| `app/temarios/` | Parse DEMRE temario PDFs into structured JSON |
| `app/standards/` | Generate canonical learning standards from temarios |
| `app/atoms/` | Define fine-grained learning atoms with prerequisites |
| `app/question_variants/` | Generate question variants using AI |
| `app/pruebas/pdf-to-qti/` | Convert question PDFs to QTI 3.0 XML |
| `app/sync/` | Sync content to student app PostgreSQL database |

## Documentation

- [Repository Structure](docs/specifications/repo-structure-and-modules.md)
- [Code Standards](docs/specifications/CODE_STANDARDS.md)
- [Python Best Practices](docs/specifications/python-best-practices.md)
- [Data Model Specification](docs/specifications/data-model-specification.md)
- [Gemini Prompt Engineering](docs/specifications/gemini-prompt-engineering-best-practices.md)

See [docs/README.md](docs/README.md) for the complete documentation index.

## Environment Variables

Create a `.env` file at the project root:

```bash
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key  # Optional, for fallback
```

## Development

```bash
# Install dev dependencies
uv sync --group dev

# Run linter
uv run ruff check app/

# Format code
uv run ruff format app/
```

## License

Private repository - Arbor School
