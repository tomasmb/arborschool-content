# PDF-to-QTI Converter

Converts PDF questions to QTI 3.0 XML format using AI-powered analysis.

## Quick Start

```bash
# Process a complete test
uv run python scripts/process_test.py --test-name prueba-invierno-2026

# Process specific questions
uv run python scripts/process_test.py --test-name prueba-invierno-2026 --questions 1 5 10
```

## Project Structure

```
app/pruebas/pdf-to-qti/
├── main.py                     # Core conversion logic
├── backup_manager.py           # QTI backup management
├── modules/
│   ├── pdf_processor.py        # PDF extraction & parsing
│   ├── question_detector.py    # AI-powered question type detection
│   ├── qti_transformer.py      # QTI XML generation
│   ├── question_evaluator.py   # Question validation
│   ├── prompt_builder.py       # AI prompt construction
│   ├── qti_configs.py          # QTI configurations
│   ├── ai_processing/          # AI content analysis
│   ├── content_processing/     # Content transformation
│   ├── image_processing/       # Image extraction & analysis
│   ├── utils/                  # Utility functions
│   └── validation/             # XML & visual validation
└── scripts/                    # Processing scripts
    ├── process_test.py         # Main test processing script
    ├── extract_answer_key.py   # Extract answers from PDF
    ├── render_qti_to_html.py   # Preview QTI as HTML
    └── ...                     # See scripts/README.md
```

## Common Commands

```bash
# Process a test (auto-derives paths from test name)
uv run python scripts/process_test.py --test-name prueba-invierno-2026

# Skip already processed questions
uv run python scripts/process_test.py --test-name prueba-invierno-2026 --skip-existing

# Extract answer key from PDF
uv run python scripts/extract_answer_key.py --pdf-path path/to/answers.pdf

# Preview generated QTI as HTML
uv run python scripts/render_all_questions_to_html.py --test-name prueba-invierno-2026

# Validate QTI output quality
uv run python scripts/validate_qti_output.py --output-dir path/to/qti
```

## How It Works

1. **Extract PDF content** - Parse text, images, and layout from question PDFs
2. **Detect question type** - AI identifies the question format (multiple choice, etc.)
3. **Transform to QTI** - Generate valid QTI 3.0 XML
4. **Validate** - Check XML validity and visual correctness
5. **Save results** - Store QTI XML and metadata

## Dependencies

Uses dependencies defined in the root `pyproject.toml`:

```bash
# Install pdf-to-qti dependencies
uv sync --group pdf-to-qti
```

## Documentation

- **[scripts/README.md](./scripts/README.md)** - Detailed scripts documentation

## Related Modules

- **[PDF Splitter](../pdf-splitter/)** - Splits multi-question PDFs into individual files
