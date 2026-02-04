# QTI Feedback System

Standalone feedback generation system for QTI 3.0 assessment items.
Uses LLM (GPT) to generate per-choice rationales and worked solutions.

## Structure

```
feedback_system/
├── generator.py       # Main feedback generator class
├── validator.py       # LLM-based feedback validation
├── prompts.py         # Prompt templates for generation/validation
├── utils/
│   ├── openai_retry.py    # OpenAI API wrapper with retry logic
│   └── qti_xml_utils.py   # QTI XML parsing utilities
├── example_usage.py   # Example of how to use the system
└── README.md
```

## Dependencies

```bash
pip install openai python-dotenv
```

## Environment Variables

```bash
OPENAI_API_KEY=sk-...
```

## Quick Start

```python
from feedback_system.generator import FeedbackGenerator
from feedback_system.validator import FeedbackValidator
from feedback_system.utils.qti_xml_utils import extract_question_info, extract_image_urls

# Initialize
generator = FeedbackGenerator()
validator = FeedbackValidator()

# Your QTI XML
qti_xml = """<qti-assessment-item ...>...</qti-assessment-item>"""

# Extract metadata
question_info = extract_question_info(qti_xml)
image_urls = extract_image_urls(qti_xml)

# Generate feedback
feedback_data = generator.generate_feedback(question_info, qti_xml, image_urls)

# Inject feedback into QTI XML
qti_xml_with_feedback = generator.inject_feedback_into_qti(qti_xml, feedback_data, question_info)

# Validate (optional but recommended)
validation_result = validator.validate_feedback(
    qti_xml, qti_xml_with_feedback, feedback_data, question_info, image_urls
)

if validation_result.get("validation_result") == "pass":
    print("Feedback validated successfully!")
    # Use qti_xml_with_feedback
```

## Feedback Types Generated

### For Multiple Choice (MCQ)
- `correct_response`: Array of correct choice identifiers
- `per_choice_feedback`: Rationale for each choice (why right/wrong)
- `worked_solution`: Step-by-step solution with title and steps

### For Free Response (FRQ/Extended Text)
- `rubric_criteria`: Array of scoring criteria
- `exemplar`: Outline showing how to structure a strong response

## Customization

To adapt for different subjects/grade levels:
1. Edit `prompts.py` - change grade level references and subject matter
2. Edit `generator.py` schemas if you need different output fields

## QTI Elements Generated

- `<qti-feedback-inline>` - Per-choice rationales inside choices
- `<qti-feedback-block>` - Worked solution shown after submit
- `<qti-correct-response>` - Correct answer declaration
- `<qti-rubric-block>` - Scoring criteria for FRQ (grader view)
