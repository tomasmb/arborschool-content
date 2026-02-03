# PDF Splitter

Intelligently splits multi-question PDFs into individual question files using AI-powered analysis.

## Quick Start

```bash
# Run with environment variables loaded
uv run python run_with_env.py path/to/multi-question.pdf output/
```

## Project Structure

```
app/pruebas/pdf-splitter/
├── main.py                # Core splitting logic
├── run_with_env.py        # Wrapper that loads .env
└── modules/
    ├── pdf_processor.py   # PDF extraction & parsing
    ├── pdf_utils.py       # PDF utilities
    ├── chunk_segmenter.py # Question segmentation
    ├── bbox_computer.py   # Bounding box calculations
    ├── block_matcher.py   # Content block matching
    ├── quality_validator.py # Split quality validation
    ├── part_validator.py  # Part validation
    └── split_decision.py  # Split decision logic
```

## How It Works

1. **Extract PDF content** - Parse text, images, and layout from multi-question PDFs
2. **Detect question boundaries** - AI identifies where each question starts and ends
3. **Segment intelligently** - Split PDF into individual question files
4. **Validate quality** - Ensure each split question is complete and valid
5. **Save output** - Store individual question PDFs

## Dependencies

Uses dependencies defined in the root `pyproject.toml`:

```bash
# Install pdf-to-qti dependencies (includes splitter deps)
uv sync --group pdf-to-qti
```

## Related Modules

- **[PDF-to-QTI](../pdf-to-qti/)** - Converts individual question PDFs to QTI format
