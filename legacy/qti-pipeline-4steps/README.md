# PDF to QTI Converter

A standalone tool for converting PDF test documents into validated QTI 3.0 XML files.

## Overview

This tool provides a complete pipeline for:

1. **PDF Parsing** (Step 1): Convert PDF to structured markdown using Extend.ai API
2. **Segmentation** (Step 2): Split markdown into individual questions using AI
3. **QTI Generation** (Step 3): Convert each question to valid QTI 3.0 XML
4. **Extraction Validation** (Step 4): AI-powered validation of extraction quality

## Features

- Database-agnostic: runs entirely locally with file-based I/O
- Multiple AI provider support: Gemini, GPT-5.1, Claude Opus 4.5
- Automatic question type detection
- XSD and semantic validation during generation
- AI-powered extraction quality validation
- Preserves images and complex formatting

---

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Environment Variables

Create a `.env` file or set environment variables:

```bash
# =============================================================================
# AI Providers (at least one required)
# =============================================================================

# Google Gemini (recommended - best for high-volume processing)
GEMINI_API_KEY=your-gemini-api-key

# OpenAI GPT-5.1
OPENAI_API_KEY=your-openai-api-key

# Anthropic Claude Opus 4.5 via AWS Bedrock
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1

# =============================================================================
# PDF Parsing (required for parse step)
# =============================================================================

EXTEND_API_KEY=your-extend-api-key

# =============================================================================
# Optional Settings
# =============================================================================

DEFAULT_PROVIDER=gemini    # Default AI provider
DEFAULT_OUTPUT_DIR=./output
```

---

## Usage

### Full Pipeline (PDF → Validated QTI)

```bash
python run.py input.pdf --output ./output --provider gemini
```

### Step-by-Step Processing

Running steps individually gives you more control and allows you to inspect intermediate outputs:

```bash
# Step 1: Parse PDF to markdown (requires Extend.ai)
python run.py input.pdf --step parse --output ./output

# Step 2: Segment markdown into questions
python run.py ./output/parsed.json --step segment --output ./output

# Step 3: Generate QTI from segments
python run.py ./output/segmented.json --step generate --output ./output

# Step 4: Validate QTI extraction quality
python run.py ./output/qti --step validate --output ./output
```

### Options

```
--output, -o        Output directory (default: ./output)
--provider, -p      AI provider: gemini, gpt, opus (default: gemini)
--step, -s          Pipeline step: parse, segment, generate, validate, all
--skip-validation   Skip XSD and semantic validation during generation
--verbose, -v       Enable verbose logging
```

---

## ⚠️ IMPORTANT: PDF Parsing Efficiency

**The Extend.ai PDF parser is deterministic.** Running it multiple times on the same PDF
will produce the exact same result. This means:

1. **Parse a PDF only ONCE** - Save API costs by reusing the `parsed.json` output
2. **Store `parsed.json` alongside your PDFs** - Treat it as a cached artifact
3. **Skip the parse step on reruns** - Use `--step segment` to start from cached data

### 💰 Credit Management

**Extend.ai has limited free credits.** The parser automatically prevents re-parsing:
- If `parsed.json` exists, it will be reused automatically (no API call)
- You'll see a clear warning if you try to re-parse
- **Always save your `parsed.json` files** - they're your cache!

See `ADVERTENCIA_EXTEND.md` for detailed best practices.

```bash
# First time: Parse the PDF
python run.py input.pdf --step parse --output ./output

# Subsequent runs: Reuse the parsed data
python run.py ./output/parsed.json --step all --output ./output
```

The tool will automatically warn you if `parsed.json` already exists and skip re-parsing.

---

## Output Structure

```
output/
├── parsed.json              # Extend.ai parsed PDF output (cache this!)
├── segmented.json           # Segmented questions
├── questions/               # Individual question markdown
│   ├── Q1.md
│   ├── Q2.md
│   └── ...
├── qti/                     # Generated QTI XML files
│   ├── Q1.xml
│   ├── Q2.xml
│   └── ...
├── generator_output.json    # Generator results with all QTI items
├── validation_output.json   # Full validation results
├── validation_summary.json  # Summary of validation results
└── report.json              # Pipeline execution report
```

---

## Project Structure

```
pdf-to-qti/
├── run.py                   # Main entry point
├── config.py                # Configuration handling
├── models.py                # Pydantic data models
├── requirements.txt         # Dependencies
├── pipeline/
│   ├── pdf_parser.py        # PDF → parsed JSON
│   ├── segmenter.py         # JSON → segmented questions
│   ├── generator.py         # Questions → QTI XML
│   └── validator.py         # QTI XML → Validated QTI
├── services/
│   ├── ai_client_factory.py # AI provider factory
│   ├── base_ai_client.py    # Base client with retry logic
│   ├── gemini_client.py     # Google Gemini client
│   ├── openai_client.py     # OpenAI GPT client
│   ├── anthropic_client.py  # Anthropic Claude via Bedrock
│   ├── qti_service.py       # QTI XML generation
│   ├── qti_validator_service.py  # Extraction validation
│   ├── xsd_validator.py     # XSD validation
│   ├── semantic_validator.py
│   ├── question_type_detector.py
│   ├── spatial_segmentation_service.py
│   ├── split_validator.py
│   └── content_order_extractor.py
└── prompts/
    ├── qti_generation.py
    ├── qti_validation.py    # Extraction validation prompts
    ├── qti_configs.py
    ├── question_type_detection.py
    ├── semantic_validation.py
    ├── content_order_segmentation.py
    └── split_validation.py
```

---

## Supported Question Types

- **choice**: Single/multiple choice
- **match**: Matching items
- **text-entry**: Short text input
- **extended-text**: Essay responses
- **composite**: Multi-part questions
- **hotspot**: Image region selection
- **gap-match**: Drag-and-drop text
- **order**: Ordering/ranking
- **inline-choice**: Dropdown selections
- **select-point**: Image point selection
- **hot-text**: Text span selection
- **graphic-gap-match**: Image-based matching
- **media-interaction**: Audio/video

---

## Validation

### Step 3: Generation Validation (XSD + Semantic)

During the generate step, each QTI file is validated for:
- **XSD Compliance**: Valid QTI 3.0 XML structure
- **Semantic Fidelity**: Content matches the source question

Use `--skip-validation` to bypass these checks for faster generation.

### Step 4: Extraction Validation (AI-Powered)

The validate step uses AI to check extraction quality:

#### ✅ What It Validates

1. **Content Completeness** - Was all content extracted?
   - Question stem/prompt is present and readable
   - All interactive elements populated (choices, match items, etc.)
   - MathML/equations properly formed

2. **Structure Validity** - Is the QTI structure correct?
   - Has `qti-item-body` with content
   - Correct interaction element for question type

3. **Parse Quality** - Is the content clean?
   - No encoding artifacts (â€™, Ã©, Â, etc.)
   - No placeholder text (`[IMAGE]`, `[TODO]`)
   - No contamination from adjacent questions

4. **Media Integrity** - Are images correct?
   - Images are accessible (URLs return 200)
   - Images match question context (AI vision check)

#### ❌ What It Does NOT Validate

- `responseDeclaration` / `correctResponse` (answer keys)
- Feedback elements
- Distractor quality
- Rubrics or scoring guidance
- Pedagogical soundness

---

## AI Providers

### Gemini (default)
- Model: `gemini-3-pro-preview`
- Best for: High-volume processing
- Rate limit: 25 requests/minute

### GPT-5.1
- Model: `gpt-5.1` with high reasoning
- Best for: Complex questions requiring more reasoning
- Rate limit: 450 requests/minute

### Claude Opus 4.5
- Model: `claude-opus-4-5` via AWS Bedrock
- Best for: Complex validation tasks
- Low hallucination rates

---

## Scoring (Validation)

Each validation category receives a score from 0-100:

| Score     | Meaning                                              |
|-----------|------------------------------------------------------|
| 100       | Perfect extraction                                   |
| 90-99     | Minor cosmetic issues (extra whitespace, formatting) |
| 70-89     | Noticeable issues but question is still usable       |
| 50-69     | Significant issues (missing choice text, garbled math)|
| 0-49      | Critical failures (missing stem, empty elements)     |

A question is marked as **valid** if:
- All category checks pass (score >= 90)
- Overall weighted score >= 90

---

## Example Workflow

```bash
# 1. Set up environment
export GEMINI_API_KEY="your-key"
export EXTEND_API_KEY="your-key"

# 2. Parse PDF (do this ONCE!)
python run.py test.pdf --step parse --output ./my-test

# 3. Review parsed.json, then segment
python run.py ./my-test/parsed.json --step segment --output ./my-test

# 4. Review segmented questions, then generate QTI
python run.py ./my-test/segmented.json --step generate --output ./my-test

# 5. Validate extraction quality
python run.py ./my-test/qti --step validate --output ./my-test

# 6. Review validation_summary.json for any issues
cat ./my-test/validation_summary.json
```

---

## License

MIT
