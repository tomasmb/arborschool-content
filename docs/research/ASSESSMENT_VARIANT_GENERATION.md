# Assessment Variant Generation Pipeline

> **Comprehensive Guide to Generating High-Quality Alternate Versions of Assessment Questions**

This document provides a complete implementation guide for generating pedagogically-sound variant questions from source exemplars. The pipeline ensures each variant tests the **exact same concept** as the original while using different scenarios, contexts, and numbers.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Phase 1: Variant Planning](#phase-1-variant-planning)
4. [Phase 2: Image Enrichment](#phase-2-image-enrichment)
5. [Phase 3: QTI Generation](#phase-3-qti-generation)
6. [Phase 4: Validation](#phase-4-validation)
7. [Prompt Architecture & Design](#prompt-architecture--design)
8. [Image Strategy: Generation vs. Reuse](#image-strategy-generation-vs-reuse)
9. [Implementation Guide](#implementation-guide)
10. [Quality Considerations](#quality-considerations)

---

## Overview

### Problem Statement

Given a source "exemplar" question from a standardized test, generate 5-10 high-quality variant questions that:
- Test the **identical concept** as the source
- Maintain the **same difficulty level**
- Use **different scenarios, contexts, and numbers**
- Are **unique** from each other (not trivial rewordings)
- Include **feedback** for every answer choice
- Optionally include **images/diagrams** where pedagogically appropriate

### Why This Matters

1. **Test Security**: Students can't memorize specific questions
2. **Practice Volume**: More questions for learning/assessment
3. **Fairness**: Equivalent difficulty across variants
4. **Adaptive Learning**: Feed question pools for personalized paths

### Pipeline Summary

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   PHASE 1       │     │   PHASE 2       │     │   PHASE 3       │     │   PHASE 4       │
│   PLANNING      │ ──▶ │   IMAGE         │ ──▶ │   GENERATION    │ ──▶ │   VALIDATION    │
│                 │     │   ENRICHMENT    │     │                 │     │                 │
│ • Extract       │     │ • Decide if     │     │ • Generate QTI  │     │ • XSD Schema    │
│   concept       │     │   image needed  │     │   3.0 XML       │     │ • Concept       │
│ • Plan 5-10     │     │ • Generate or   │     │ • Match source  │     │   alignment     │
│   scenarios     │     │   find images   │     │   format        │     │ • Answer check  │
│ • Maintain      │     │ • Fall back to  │     │ • Add feedback  │     │ • Uniqueness    │
│   difficulty    │     │   text-only     │     │   for all       │     │ • Feedback      │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## Architecture

### Core Design Principles

1. **Single Responsibility**: Each phase has one job
2. **Parallel Execution**: ThreadPoolExecutor for throughput
3. **Structured LLM Output**: JSON schemas for reliable parsing
4. **Resume Support**: Phase outputs saved to disk for recovery
5. **Validation Gates**: Only valid variants proceed

### Data Flow

```
ExemplarQuestion
       │
       ▼
┌──────────────┐
│ VariantPlan  │  ← Phase 1 output (5-10 per exemplar)
│ • variant_id │
│ • source_id  │
│ • concept    │
│ • scenario   │
│ • difficulty │
└──────────────┘
       │
       ▼
┌──────────────────┐
│ EnrichedVariant  │  ← Phase 2 output (with image data)
│ Plan             │
│ • has_image      │
│ • image_url      │
│ • image_alt_text │
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ GeneratedVariant │  ← Phase 3 output (actual QTI XML)
│ • qti_xml        │
│ • title          │
│ • feedback       │
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ ValidatedVariant │  ← Phase 4 output (quality-checked)
│ • all checks ✓   │
└──────────────────┘
```

### File Structure

```
app/assessment/
├── __init__.py           # Module exports
├── models.py             # Data classes & JSON schemas
├── pipeline.py           # 4-phase orchestrator
├── prompts.py            # LLM prompt templates
├── variant_planner.py    # Phase 1: Planning
├── variant_generator.py  # Phase 3: Generation
└── variant_validator.py  # Phase 4: Validation
```

---

## Phase 1: Variant Planning

### Purpose

Analyze each exemplar question and create 5-10 variant plans that test the **exact same concept** with different scenarios.

### Input

```python
@dataclass
class ExemplarQuestion:
    question_id: str
    test_id: str
    title: str
    standard: str              # e.g., "3-PS2-1"
    difficulty: str            # "Easy", "Medium", "Hard"
    question_text: str
    answer_choices: list[dict] # [{id, text, is_correct}]
    correct_answer: str
    qti_xml: str               # Original QTI 3.0 XML
```

### Output

```python
@dataclass
class VariantPlan:
    variant_id: str           # e.g., "exemplar_123_v1"
    source_exemplar_id: str   # ALWAYS tracked for debugging
    source_concept: str       # Core concept being tested
    difficulty: str           # Same as source
    interaction_type: str     # choice, choice-n, match, etc.
    scenario_description: str # NEW scenario for this variant
    context: str              # Different context/numbers
    requires_image: bool      # Does this variant need an image?
    image_description: str    # What the image should show
```

### Prompt Architecture

The planning prompt follows **GPT-5.1 best practices**: static context FIRST (cached), dynamic input LAST.

#### Static Context (Cached by LLM)

```
<role>
You are an expert educational assessment developer creating variant 
questions from exemplars. Your task is to plan DIFFERENT questions 
that test the EXACT SAME concept as the source exemplar.
</role>

<planning_rules>
1. Every variant must test the IDENTICAL concept as the source exemplar
2. Variants must have the SAME difficulty level - no easier, no harder
3. Variants must use DIFFERENT scenarios, contexts, numbers, or situations
4. Variants must be answerable without the original exemplar
5. Each variant must be unique from all other variants
</planning_rules>

<uniqueness_criteria>
A variant is considered "unique enough" if it has ANY of these differences:
- Different correct answer (e.g., different numerical result)
- Different context/scenario (e.g., different real-world situation)
- Different numbers/values (e.g., different measurements, quantities)
</uniqueness_criteria>

<variant_diversity>
For each exemplar, create variants that span:
- Different real-world applications of the same concept
- Different measurement contexts (if applicable)
- Different student/scientist scenarios
- Different ways of asking about the same underlying knowledge
</variant_diversity>
```

#### Dynamic Content (Per-Exemplar)

```
<source_exemplar>
Question ID: {exemplar.question_id}
Standard: {exemplar.standard}
Difficulty: {exemplar.difficulty}

Question Text:
{exemplar.question_text}

Answer Choices:
[✓] A: {correct_choice}
[ ] B: {distractor_1}
[ ] C: {distractor_2}
[ ] D: {distractor_3}

Correct Answer: {exemplar.correct_answer}
</source_exemplar>

<unit_context>
Unit: {unit_name}
Related Atoms: {atom_titles}
</unit_context>

<task>
Create {num_variants} DIFFERENT variant questions that test the EXACT SAME concept.
Each variant must:
1. Test the same underlying knowledge
2. Maintain {exemplar.difficulty} difficulty level
3. Use a DIFFERENT scenario, context, or numbers
4. Be unique from the source and all other variants
</task>
```

### JSON Schema for Response

```python
VARIANT_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "variants": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "scenario_description": {
                        "type": "string",
                        "description": "A new scenario that tests the same concept"
                    },
                    "context": {
                        "type": "string",
                        "description": "The context/numbers used in this variant"
                    },
                    "requires_image": {
                        "type": "boolean",
                        "description": "Whether this variant needs an image"
                    },
                    "image_description": {
                        "type": ["string", "null"],
                        "description": "What the image should show (if requires_image)"
                    }
                },
                "required": ["scenario_description", "context", "requires_image", "image_description"]
            }
        },
        "source_concept": {
            "type": "string",
            "description": "The core concept being tested by the exemplar"
        }
    },
    "required": ["variants", "source_concept"]
}
```

### Key Design Decisions

1. **LLM extracts the concept**: Don't rely on metadata; let the LLM analyze what's actually being tested
2. **Difficulty is preserved**: The plan inherits difficulty from source—no reinterpretation
3. **Interaction type detected**: Parse the source QTI to determine question format
4. **Medium reasoning effort**: Balances quality with throughput

---

## Phase 2: Image Enrichment

### Purpose

Decide if each variant needs an image, and if so, generate or find an appropriate one.

### ⚠️ IMPORTANT: Image Strategy Decision

**Before committing to this pipeline, consider your image strategy carefully.**

There are three approaches:

| Approach | Pros | Cons |
|----------|------|------|
| **Generate New Images** | Tailored to variant scenarios | Cost, complexity, quality variance |
| **Reuse Original Images** | Consistent quality, simpler | May not match new scenario |
| **Text-Only Variants** | Simplest, fastest | Reduces question variety |

#### Option A: Generate New Images (Current Implementation)

Our pipeline supports multiple image generation methods:

1. **Coordinate Plane (SVG)**: Graphs, waves, X-Y plots
2. **Gemini Compositional**: Labeled diagrams (cells, anatomy, tools)
3. **Photorealistic**: Animals, plants, landscapes (via Imagen)
4. **Comparison Images**: Side-by-side before/after
5. **Image Bank Search**: Find existing images

#### Option B: Reuse Original Question Images

If the source exemplar has an image, you might **reuse it** for variants:

```python
# Simplified approach - copy original image to all variants
if source_exemplar.has_image:
    for variant in variants:
        variant.image_url = source_exemplar.image_url
        variant.image_alt_text = source_exemplar.image_alt_text
```

**When to consider this approach:**
- The image shows a general concept (e.g., a cell diagram)
- Multiple variants can reference the same visual
- You want consistent quality without generation complexity
- The original images are high-quality and rights-cleared

**When NOT to use this approach:**
- Variants have scenario-specific visuals (e.g., different graph values)
- The original image contains answer hints
- The variant scenario differs significantly from the original

#### Option C: Text-Only Variants

Skip images entirely and generate text-based variants:

```python
config = AssessmentPipelineConfig(
    enable_images=False,  # Skip Phase 2 entirely
    # ... other config
)
```

**When to consider:**
- Rapid prototyping
- Questions where images aren't pedagogically valuable
- Cost constraints

### Image Type Decision (LLM-Driven)

If generating images, a **single LLM call** decides:
1. Whether an image is needed
2. What TYPE of image would be best
3. Which generation method to use

#### Static Prompt (Cached)

```
<role>
You are an educational content expert deciding if a question needs an 
image and what type would work best.
</role>

<image_generation_capabilities>
We CAN generate these image types:
- coordinate_plane: SVG graphs: waves, distance-time, X-Y relationships
- gemini_compositional: Labeled diagrams: cells, anatomy, ecosystems, 
  plant structures, measurement tools, labeled equipment
- photo_realistic: Photorealistic images of animals, plants, landscapes
- comparison_image: Side-by-side or before/after comparison images

We CANNOT reliably generate these (would need to search image bank):
- force_diagram: Free-body diagrams with force arrows
- circuit_diagram: Electrical circuits
- vector_diagram: Velocity/acceleration vectors
</image_generation_capabilities>

<decision_rules>
1. ONLY recommend an image if it genuinely helps understanding
2. Consider what TYPE of image would best serve the educational goal
3. Choose the generation method that matches the content
4. CRITICAL - TABLES MUST NEVER BE GENERATED AS IMAGES
   Tables belong in QTI XML, NOT as generated images.
</decision_rules>
```

#### Decision Schema

```python
{
    "needs_image": bool,       # Does this question benefit from an image?
    "image_type": str,         # coordinate_plane | gemini_compositional | 
                               # photo_realistic | comparison_image | 
                               # image_bank | none
    "reason": str,             # Why this type was chosen
    "description_hint": str    # What the image should show
}
```

### Image Generation Flow

```
LLM Decision
     │
     ├─▶ coordinate_plane ──▶ SVG Generator ──▶ S3 Upload
     │
     ├─▶ gemini_compositional ──▶ Gemini API ──▶ S3 Upload
     │
     ├─▶ photo_realistic ──▶ Imagen API ──▶ S3 Upload
     │
     ├─▶ comparison_image ──▶ Dual Generation ──▶ S3 Upload
     │
     ├─▶ image_bank ──▶ API Search ──▶ Vision Validation
     │
     └─▶ none ──▶ Text-Only (adjust plan if needed)
```

### Fallback Strategy

If image generation fails:
1. Try image bank search as backup
2. If that fails, adjust plan to text-only
3. Optionally rewrite the question to remove visual references

---

## Phase 3: QTI Generation

### Purpose

Generate actual QTI 3.0 XML from enriched variant plans.

### Prompt Architecture

#### Static Context (Cached)

```
<role>
You are an expert QTI 3.0 XML developer creating variant assessment items.
Your task is to generate a VARIANT question that tests the EXACT SAME 
concept as the source exemplar.
</role>

<qti_rules>
1. Use namespace: xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0"
2. Root element: <qti-assessment-item>
3. Required attributes: identifier, title, adaptive="false", time-dependent="false"
4. Body: Use <qti-item-body> for content
5. Include <qti-response-declaration> with identifier="RESPONSE"
6. Include <qti-outcome-declaration> for SCORE and FEEDBACK
7. Identifier format: MUST start with letter (a-z, A-Z)
8. Attribute syntax is kebab-case: time-dependent, base-type, response-identifier
</qti_rules>

<xsd_constraints>
NEVER do these (XSD validation will fail):
- Start identifier with digit or hyphen
- Use camelCase attributes (timeDependent, baseType)
- Place <img> directly inside <qti-item-body> (wrap in <p>)
- Use single quotes for attributes

CHARACTER ENCODING:
- Use ONLY standard ASCII characters
- Use straight quotes (' and ") not curly/smart quotes
- Use plain hyphen (-) for ranges, not en-dash or em-dash
</xsd_constraints>

<feedback_requirements>
- Include feedback for EVERY choice option
- Correct answer feedback: "Correct! [Brief explanation why]"
- Incorrect answer feedback: "Incorrect. [Brief explanation why wrong + 
  what's correct]"
- Include a worked solution showing step-by-step reasoning
</feedback_requirements>

<output_format>
Return ONLY raw XML. No markdown blocks, no XML declaration.
Start directly with <qti-assessment-item>.
</output_format>
```

#### Type-Specific Instructions

For each interaction type (choice, match, order, etc.), we provide:
- Structural template (XSD-valid example)
- Feedback pattern example
- Type-specific rules

```
<type_instructions>
INTERACTION TYPE: CHOICE

Use <qti-choice-interaction> with max-choices="1" for single-select.
Each <qti-simple-choice> needs a unique identifier starting with "Choice".

FEEDBACK PATTERN:
<qti-modal-feedback outcome-identifier="FEEDBACK" identifier="feedback_A">
  <qti-content-body>
    <p>Correct! This is the right answer because...</p>
  </qti-content-body>
</qti-modal-feedback>
</type_instructions>

<example_structure>
{XSD-valid example XML for this question type}
</example_structure>
```

#### Dynamic Content

```
<source_exemplar>
This is the SOURCE exemplar. Use it for CONTENT reference (concept, difficulty).
For XML STRUCTURE, follow the example_structure above.

Question ID: {source_exemplar.question_id}
Standard: {source_exemplar.standard}
Difficulty: {source_exemplar.difficulty}

Question Text: {source_exemplar.question_text}

Answer Choices:
{formatted_choices}

Correct Answer: {source_exemplar.correct_answer}
</source_exemplar>

<concept_to_test>
{plan.source_concept}
</concept_to_test>

<variant_plan>
Variant ID: {plan.variant_id}
Difficulty Level: {plan.difficulty} (MUST match source exemplar)
Interaction Type: {plan.interaction_type}
Scenario: {plan.scenario_description}
Context: {plan.context}
</variant_plan>

<image_info>  <!-- If applicable -->
Image URL: {plan.image_url}
Alt Text: {plan.image_alt_text}
Include this image in the question body using: <p><img src="{url}" alt="{alt}" /></p>
</image_info>

<requirements>
Generate a variant question that:
1. Tests the EXACT SAME concept as the source exemplar
2. Uses the new scenario and context from the variant plan
3. Maintains the SAME difficulty level
4. Follows the XSD-valid structure from example_structure
5. Includes feedback for EVERY choice
</requirements>
```

### Generation Schema

```python
VARIANT_GENERATION_SCHEMA = {
    "type": "object",
    "properties": {
        "qti_xml": {
            "type": "string",
            "description": "The complete QTI 3.0 XML for the variant question"
        },
        "title": {
            "type": "string",
            "description": "Short title for the question"
        }
    },
    "required": ["qti_xml", "title"]
}
```

---

## Phase 4: Validation

### Purpose

Multi-step validation ensuring variants are:
1. **XSD-compliant** (valid QTI 3.0)
2. **Concept-aligned** (tests same thing as source)
3. **Quality-checked** (clear, grade-appropriate)
4. **Answer-verified** (correct answer is actually correct)
5. **Unique** (different from source and siblings)
6. **Feedback-complete** (all choices have feedback)

### Validation Flow

```
Raw Variants
     │
     ▼
┌────────────────┐
│ Step 4a: XSD   │ ← Fast, synchronous, runs first
│ Schema Check   │   Filters out malformed XML
└────────────────┘
     │ (passed only)
     ▼
┌────────────────┐
│ Step 4b-4f:    │ ← Single LLM call per variant
│ LLM Validation │   Parallel execution
│ • Concept      │
│ • Quality      │
│ • Answer       │
│ • Uniqueness   │
│ • Feedback     │
└────────────────┘
     │
     ▼
Valid Variants Only
```

### Validation Prompt

```
<role>
You are a curriculum alignment and quality expert validating variant 
assessment items. Your task is to ensure variants properly test the 
same concept as their source exemplar.
</role>

<validation_criteria>
1. CONCEPT ALIGNMENT: Does the variant test the EXACT same concept?
   - Same underlying knowledge or skill
   - Same cognitive level
   - Would correctly answering require the same understanding?

2. QUALITY CHECK: Is the variant well-written?
   - Clear and unambiguous stem
   - Grade-appropriate vocabulary (G3-5)
   - Distractors based on genuine misconceptions
   - Options homogeneous in length/style

3. ANSWER VERIFICATION: Is the answer key correct?
   - Solve the question step-by-step
   - Verify YOUR answer matches the marked correct answer
   - Check if any distractor could arguably be correct
   - NUMERICAL CONSISTENCY: Verify feedback uses EXACT same values
   - LANGUAGE CONSISTENCY: "all" vs "most" is a mismatch error

4. UNIQUENESS CHECK: Is the variant sufficiently different?
   - Different context/scenario from source exemplar
   - Different numbers/values OR different correct answer
   - Not a trivial rewording of the original

5. FEEDBACK VALIDATION: Is feedback complete?
   - Every choice has feedback
   - Feedback explains why correct/incorrect
   - Feedback is educational, not just "Wrong"
</validation_criteria>

<grading_rubric>
- "valid": Passes all checks, ready for use
- "minor_issues": Small issues but usable
- "reject": Fails critical checks (wrong answer, off-concept, duplicate)
</grading_rubric>
```

### Validation Schema

```python
VARIANT_VALIDATION_SCHEMA = {
    "type": "object",
    "properties": {
        "concept_alignment": {
            "type": "object",
            "properties": {
                "passes": {"type": "boolean"},
                "reason": {"type": "string"}
            }
        },
        "quality_check": {
            "type": "object",
            "properties": {
                "passes": {"type": "boolean"},
                "reason": {"type": "string"}
            }
        },
        "answer_verification": {
            "type": "object",
            "properties": {
                "passes": {"type": "boolean"},
                "reason": {"type": "string"},
                "your_answer": {"type": "string"},
                "marked_answer": {"type": "string"}
            }
        },
        "uniqueness_check": {
            "type": "object",
            "properties": {
                "passes": {"type": "boolean"},
                "reason": {"type": "string"},
                "is_different_enough": {"type": "boolean"}
            }
        },
        "feedback_validation": {
            "type": "object",
            "properties": {
                "passes": {"type": "boolean"},
                "reason": {"type": "string"},
                "all_choices_have_feedback": {"type": "boolean"}
            }
        },
        "overall_recommendation": {
            "type": "string",
            "enum": ["valid", "minor_issues", "reject"]
        }
    }
}
```

---

## Prompt Architecture & Design

### GPT-5.1 Best Practices

Our prompts follow these principles:

1. **Static Context First**: Unchanging instructions at the start maximize prompt cache hits
2. **Dynamic Content Last**: Per-request data at the end
3. **Structured Output**: JSON schemas ensure parseable responses
4. **Reasoning Effort Calibration**:
   - `medium` for planning and generation (balance speed/quality)
   - `high` for validation (accuracy matters)
   - `low` for simple decisions (image type)

### Prompt Structure Template

```
┌─────────────────────────────────────────┐
│ STATIC SECTION (Cached 24 hours)        │
│                                         │
│ <role>...</role>                        │
│ <rules>...</rules>                      │
│ <constraints>...</constraints>          │
│ <examples>...</examples>                │
│                                         │
│ <!-- Delimiter -->                      │
│ <!-- ======= DYNAMIC CONTENT ======= -->│
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│ DYNAMIC SECTION (Changes per request)   │
│                                         │
│ <input_data>...</input_data>            │
│ <task>...</task>                        │
└─────────────────────────────────────────┘
```

### Key Prompt Design Decisions

| Decision | Rationale |
|----------|-----------|
| **XML tags for structure** | Clearer than markdown for nested content |
| **Explicit rules** | Reduces hallucination and edge cases |
| **Worked examples** | Improves output quality significantly |
| **Negative examples** | "NEVER do X" prevents common errors |
| **Schema enforcement** | Guarantees parseable, structured output |

---

## Image Strategy: Generation vs. Reuse

### Decision Framework

Before building your pipeline, answer these questions:

#### 1. Do your source exemplars have images?

- **Yes → Consider reuse strategy**
- **No → Must generate or go text-only**

#### 2. Are the images scenario-specific or concept-general?

| Image Type | Example | Recommendation |
|------------|---------|----------------|
| **Concept-general** | Cell diagram, periodic table | ✅ Safe to reuse across variants |
| **Scenario-specific** | Graph with specific values | ❌ Need new images per variant |
| **Answer-revealing** | Image shows the correct choice | ❌ Must generate new images |

#### 3. What's your quality/cost tradeoff?

| Approach | Cost | Quality | Complexity |
|----------|------|---------|------------|
| Generate all | $$$ | Variable | High |
| Reuse original | $ | Consistent | Low |
| Text-only | $ | N/A | Lowest |
| Hybrid | $$ | Mixed | Medium |

### Recommended: Hybrid Approach

```python
def decide_image_strategy(source_exemplar, variant_plan):
    """Decide whether to generate, reuse, or skip image."""
    
    # If source has no image, check if variant needs one
    if not source_exemplar.has_image:
        if variant_plan.requires_image:
            return "generate"
        return "none"
    
    # Source has image - can we reuse it?
    if is_concept_general_image(source_exemplar.image_url):
        # Diagram of a cell, measurement tool, etc.
        return "reuse"
    
    if image_contains_answer_hint(source_exemplar):
        # Must generate to avoid giving away answer
        return "generate"
    
    if variant_scenario_differs_significantly(source_exemplar, variant_plan):
        # New scenario needs new image
        return "generate"
    
    # Default: reuse original image
    return "reuse"
```

### Implementing Image Reuse

```python
class SimpleImageStrategy:
    """Simplified image enrichment that reuses original images."""
    
    def enrich_plan(self, plan, source_exemplar):
        if source_exemplar.has_image:
            return EnrichedVariantPlan(
                **plan.__dict__,
                has_image=True,
                image_url=source_exemplar.image_url,
                image_alt_text=source_exemplar.image_alt_text,
            )
        return EnrichedVariantPlan.from_plan(plan)
```

---

## Implementation Guide

### Quick Start

```python
from assessment import AssessmentPipeline, AssessmentPipelineConfig

# Configure
config = AssessmentPipelineConfig(
    enable_images=True,           # Set False for text-only
    min_variants_per_exemplar=5,
    max_variants_per_exemplar=10,
    max_workers=15,               # Parallel execution
    model="gpt-5.1"
)

# Run
pipeline = AssessmentPipeline(config)
result = pipeline.run(
    grade="3",
    unit_sequence=5,
    unit_data=unit_data,  # Contains exemplar_mappings
    resume=False
)

print(f"Generated {result.variants_valid} valid variants")
```

### Required Environment

```bash
# Environment variables
OPENAI_API_KEY=sk-...          # Required
AWS_ACCESS_KEY_ID=...          # For S3 image upload (if generating)
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET_NAME=...

# Dependencies
pip install openai requests boto3
```

### Customization Points

1. **Swap image strategy**: Replace `ImageEnricher` with your own
2. **Add validation steps**: Extend `VariantValidator`
3. **Change prompts**: Modify `prompts.py`
4. **Adjust schemas**: Update `models.py`

---

## Quality Considerations

### Common Failure Modes

| Issue | Cause | Mitigation |
|-------|-------|------------|
| **Variants too similar** | LLM not diverse enough | Add diversity requirements to prompt |
| **Wrong answers** | LLM math errors | Answer verification in Phase 4 |
| **Off-concept** | LLM drifted from original | Concept alignment check |
| **XSD failures** | Malformed XML | Strict schema examples in prompt |
| **Missing feedback** | LLM forgot | Explicit feedback requirements |

### Monitoring Metrics

Track these to ensure quality:

```python
{
    "total_exemplars": 50,
    "total_variants_planned": 350,      # 7 per exemplar
    "xsd_pass_rate": 0.95,
    "concept_alignment_pass_rate": 0.92,
    "answer_verification_pass_rate": 0.88,
    "final_valid_rate": 0.85,           # Target: >80%
    "variants_per_exemplar_avg": 6.0,   # Target: 5-10
}
```

### Gap-Fill Repair

If some exemplars end up with fewer than minimum variants:

```python
result = pipeline.repair_gaps(
    grade="3",
    unit_sequence=5,
    unit_data=unit_data
)
# Generates additional variants only for under-threshold exemplars
```

---

## Appendix: Full Data Models

### VariantPlan

```python
@dataclass
class VariantPlan:
    variant_id: str           # "exemplar_123_v1"
    source_exemplar_id: str   # Original exemplar ID (ALWAYS tracked)
    source_concept: str       # Extracted concept being tested
    difficulty: str           # Same as source exemplar
    interaction_type: str     # choice, match, order, etc.
    scenario_description: str # New scenario for this variant
    context: str              # Different context/numbers
    requires_image: bool      # Image needed?
    image_description: str    # What image should show
```

### EnrichedVariantPlan

```python
@dataclass
class EnrichedVariantPlan:
    variant_id: str
    source_exemplar_id: str
    source_concept: str
    difficulty: str
    interaction_type: str
    scenario_description: str
    context: str
    has_image: bool
    image_url: str | None      # Validated image URL
    image_alt_text: str | None # Alt text for accessibility
```

### GeneratedVariant

```python
@dataclass
class GeneratedVariant:
    variant_id: str
    source_exemplar_id: str    # ALWAYS tracked
    qti_xml: str               # The actual QTI 3.0 XML
    title: str
    difficulty: str
    interaction_type: str
    context: str
    has_image: bool
    generation_timestamp: str
```

### AssessmentPipelineConfig

```python
@dataclass
class AssessmentPipelineConfig:
    enable_images: bool = True
    min_variants_per_exemplar: int = 5
    max_variants_per_exemplar: int = 10
    max_workers: int = 15
    model: str = "gpt-5.1"
```

---

## Conclusion

This pipeline provides a systematic approach to generating high-quality assessment variants. The key success factors are:

1. **Strong prompts** with explicit rules and examples
2. **Multi-stage validation** to catch errors
3. **Structured output** for reliable parsing
4. **Flexible image strategy** that fits your needs
5. **Resume/repair capabilities** for production robustness

Adapt the image strategy section based on your specific requirements—there's no one-size-fits-all answer, and the right choice depends on your source content and quality requirements.
