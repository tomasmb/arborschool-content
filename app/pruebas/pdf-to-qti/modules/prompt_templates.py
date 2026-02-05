"""
Prompt templates and guidelines for QTI transformation.

This module contains the static template parts, guidelines, and instructions
used by the prompt builder for QTI XML generation.
"""

from __future__ import annotations

# Character encoding instructions
CHARACTER_ENCODING_INSTRUCTIONS = """## CRITICAL: Character Encoding and Special Characters
**IMPORTANT**: You MUST preserve all special characters exactly as they appear in the source content:
- Spanish accents (á, é, í, ó, ú) must be preserved correctly - write them as actual characters, NOT as "e1", "f3", "e9", "ed", "fa"
- The letter "ñ" must be preserved correctly - write it as "ñ", NOT as "f1" or "n"
- Question marks (¿, ?) and exclamation marks (¡, !) must be preserved correctly - write "¿" NOT "bf" or "bfCue"
- All mathematical symbols and special characters must be preserved
- **DO NOT** replace special characters with numeric codes, ASCII approximations, or hexadecimal representations
- **DO NOT** use patterns like "e1", "f3", "e9", "ed", "fa", "f1", "bf", "d7" to represent special characters
- The QTI XML must use UTF-8 encoding and include all characters as-is
- Examples of CORRECT encoding: "ácido", "átomos", "año", "¿Cuál", "reflexión", "traslación", "vértice", "isométricas"
- Examples of INCORRECT encoding (DO NOT USE): "e1cido", "e1tomos", "af1o", "bfCue1l", "reflexif3n", "traslacif3n", "ve9rtice", "isome9tricas"
- If you see text with patterns like "e1", "f3", "e9" in the source, these are encoding errors - you must correct them to proper Spanish characters

**MathML Number Formatting**: Large numbers must use a SINGLE `<mn>` tag with `&#x202F;` (narrow no-break space) as thousands separator:
- CORRECT: `<mn>160&#x202F;934</mn>` (one number, one tag)
- INCORRECT: `<mn>160</mn><mspace width="0.25em"/><mn>934</mn>` (splits number into two tags)

**Plain Text Number Formatting**: Large numbers in plain text (answer choices, feedback, solutions)
must also use `&#x202F;` as thousands separator for consistency with MathML:
- CORRECT: `32&#x202F;186&#x202F;800&#x202F;000 kilómetros`
- INCORRECT: `32186800000 kilómetros` (no separator)
- INCORRECT: `32 186 800 000 kilómetros` (regular space - inconsistent with MathML)"""

# Shared context handling instructions
SHARED_CONTEXT_INSTRUCTIONS = """## Shared Context Handling
**IMPORTANT**: The provided content may include introductory text, figures, or tables that are shared across multiple questions.
- You MUST include all such shared context in the QTI XML for this question.
- Do NOT omit any information you think might be from a shared context block.
- If you see a passage or figure, and then a question that refers to it, both the passage/figure and the question must be in the output.

## Avoid adding cross question text
If there is text at the beggining that references other questions, do not add it to the QTI XML.
Example: "Use the information below to answer the three following questions". Avoid adding this to the QTI XML.

## Avoid Repetition
**DO NOT duplicate or repeat any text content**. Each piece of text should appear exactly once in the QTI XML.
Specifically, the main question text should not be present in both a `<qti-prompt>` and also within a `<p>` tag in the item body."""

# Choice label handling instructions
CHOICE_LABEL_INSTRUCTIONS = """## CRITICAL: Choice Label Handling
For choice interactions (A, B, C, D, etc.):
- **Remove choice labels from choice text**: If the original content contains
  "A. This is the answer", the QTI choice text should only contain "This is the answer"
- **Do NOT include** the letter labels (A., B., C., D.) or numbers (1., 2., 3., 4.)
  in the <qti-simple-choice> text content
- **Preserve choice order**: Keep choices in their original sequence, but remove the prefixed labels
- **Use semantic identifiers**: Use identifiers like "ChoiceA", "ChoiceB", "ChoiceC", "ChoiceD" in the identifier attributes
- **Example**: Original "A. The sky is blue" becomes `<qti-simple-choice identifier="ChoiceA">The sky is blue</qti-simple-choice>`"""

# Table handling instructions
TABLE_HANDLING_INSTRUCTIONS = """## CRITICAL: Table Handling
If the content includes structured table data (marked with HTML table tags), you MUST:
- **Preserve table structure** in the QTI XML using proper HTML table elements
- **Do NOT convert tables to images** - use the provided HTML table content directly
- **Wrap tables in appropriate elements** like `<div>` or within question text
- **Ensure table accessibility** with proper `<thead>`, `<tbody>`, `<th>`, and `<td>` elements
- **Maintain table relationships** - if the question asks about table data, ensure the table is placed logically in relation to the question text
- If a table is represented as a structured HTML table, do NOT also include it as an image."""

# Text in images instructions
TEXT_IN_IMAGES_INSTRUCTIONS = """## CRITICAL: Text in Images
- If text is part of an essential image (e.g., labels on a diagram), that text should
  NOT be repeated in the `<qti-item-body>` as text. The image's alt text should
  describe the image including its text.
- Conversely, if a piece of text is rendered in the body, it should have been removed
  from any accompanying image. The goal is to avoid information duplication."""

# Description field requirements
DESCRIPTION_REQUIREMENTS = """## Requirements for Description Field (only description field, not the QTI XML)
The "description" field must be extremely detailed and comprehensive - someone should
be able to recreate the a semantically equivalent question from the description alone
without seeing the original content.

Example of a detailed description:
"Multiple choice question about genetic variation in animals. Shows a photograph of
six different bulldog puppies sitting together, demonstrating visible differences in
coat color, size, and facial features despite being from the same litter. The question
asks why puppies from the same parents don't look identical, with four answer choices:
A) they were produced by asexual cloning, B) some puppies have genetic material from
only one parent, C) each puppy has a different combination of genetic material from
sexual reproduction, D) all puppies developed from the same fertilized egg."
"""

# Image handling in QTI instructions
IMAGE_QTI_INSTRUCTIONS = """## CRITICAL: For Images in QTI XML
- If images are listed above, you MUST use their exact placeholder strings in <img src="..."> tags
- Do NOT use generic filenames like "image1.png"
- Use the EXACT placeholder strings provided (e.g., "CONTENT_PLACEHOLDER_P0")
- Each placeholder corresponds to a specific extracted image that will be restored later
- **IMPORTANT**: Use simple <img> tags within <p> or <div> elements, NOT <qti-figure> elements
- Images should be wrapped in block elements like: <p><img src="placeholder" alt="description"/></p>

## CRITICAL: Image Source Requirements - NO BASE64 ALLOWED
**NEVER use base64 encoding for images in the QTI XML.**
- **DO NOT** use `data:image/png;base64,...` or any base64 data URIs
- **DO NOT** use `src="data:image/..."`
- **MUST** use placeholder strings like "image1.png", "CONTENT_PLACEHOLDER_P0", etc.
- Images will be replaced with S3 URLs automatically - you should only use placeholder names
- Base64 encoding will cause the transformation to FAIL"""

# QTI XML structure rules
QTI_STRUCTURE_RULES = """## CRITICAL: QTI XML Structure Rules
- **DO NOT use <qti-figure>** - use <img> tags within <p> or <div> instead
- Images must be inside block elements (p, div) not standalone
- All content must be within the <qti-item-body> section
- Interaction elements go after content, before </qti-item-body>"""

# XML validation checklist
XML_VALIDATION_CHECKLIST = """## XML Validation Checklist (verify before finalizing)
- [ ] Root element <qti-assessment-item> is properly opened and closed
- [ ] All nested elements have matching closing tags
- [ ] No <qti-figure> elements used (use <img> in <p> or <div> instead)
- [ ] All images listed in 'Relevant Extracted Images' (if any) are included using their
      EXACT placeholders (e.g., CONTENT_PLACEHOLDER_P0) if they are part of the question
- [ ] All images are wrapped in block elements like <p> or <div>
      (e.g., <p><img src="placeholder" alt="description"/></p>)
- [ ] Meaningful alt text is provided for all images (use or adapt the 'alt_suggestion')
- [ ] Images are placed in the logical reading order and at semantically appropriate
      locations based on the guidelines
- [ ] <qti-response-processing> is self-closed with /> syntax
      (e.g., <qti-response-processing template="..."/>)
- [ ] All attributes (e.g., src, alt, identifier, title) are properly quoted
- [ ] Interaction elements (e.g., <qti-choice-interaction>) are correctly placed
      within <qti-item-body> and after relevant content"""

# Content fidelity checklist
CONTENT_FIDELITY_CHECKLIST = """## Question Content and Fidelity Checklist (verify semantic accuracy)
- [ ] All question text (stem, prompts, context, instructions) from the original content
      is accurately and completely included in the <qti-item-body>.
- [ ] No text is repeated between <p>, <div>, and <qti-prompt> elements. Each sentence
      or phrase appears only once in the QTI XML.
- [ ] All answer choices, options, or interactive elements described in the original
      content are present and accurately transcribed within the appropriate QTI
      interaction structure.
- [ ] The question's core meaning, intent, and level of difficulty are preserved
      from the original PDF content.
- [ ] No extraneous or irrelevant information (e.g., page numbers, headers/footers
      from the PDF, content from unrelated questions) has been included in the
      <qti-item-body>.
- [ ] The 'description' field in your JSON response is detailed, comprehensive, and
      accurately summarizes the question, its components, and any included imagery
      as per the requirements."""

# Response format specification
RESPONSE_FORMAT_SPEC = """## Response Format
You must respond with valid JSON containing:
- title: Clear, descriptive title
- description: Extremely detailed description (as specified above)
- qti_xml: Complete, valid QTI 3.0 XML
- key_features: Array of key QTI features implemented
- notes: Any important implementation details"""

# Image placement guidelines
IMAGE_PLACEMENT_GUIDELINES = """
## Image Placement Guidelines:
- **READING ORDER**: Place images in the SAME ORDER as listed above (Image 1 first,
  then Image 2, etc.) Try to infer the logical flow of the question.
- **CONTEXTUAL PLACEMENT**: Use the 'Contextual Text' and your understanding of the
  question to determine WHERE each image belongs. Look for explicit references like
  'see Figure 1', 'the diagram shows', or implicit needs for an image to understand
  a part of the text.
  * If an image is referenced (e.g., 'As shown in the diagram...'), place it
    immediately after the sentence or paragraph containing that reference.
  * If contextual text is part of the general question stem → place image generally
    AFTER the main question text but BEFORE answer choices, unless a more specific
    reference exists.
  * If contextual text is clearly related to a specific answer choice → consider if
    the image should be near that choice (though typically images are part of the
    stem or general context).
  * If contextual text consists of instructions that refer to the image → place
    image appropriately to make those instructions clear.
- **SEMANTIC LOGIC**: Images should appear where they make the most sense for a
  student reading and answering the question. The flow should be natural.
- **MULTIPLE IMAGES**: If multiple images exist, maintain their relative order
  (Image 1 before Image 2) but place each in its most logical semantic location
  within the question body.
- **DEFAULT PLACEMENT**: If absolutely unclear, place images immediately after the
  main question prompt/text but before any answer choices or interaction elements."""

# Visual comparison prompt template
VISUAL_COMPARISON_PROMPT = """
You are comparing two images of the same educational question:

1. **Original PDF Image**: The first image shows the question as it appears in the original PDF
2. **Rendered QTI Image**: The second image shows the same question rendered from QTI 3.0 XML

## Your Task

Analyze both images and determine how well the QTI version represents the original question.

## Comparison Criteria

**Content Accuracy** (40%):
- Is all text content preserved correctly?
- Are all answer options present and correctly formatted?
- Are mathematical expressions rendered properly?
- Is the question structure maintained?

**Visual Layout** (30%):
- Does the overall layout match the original?
- Are images positioned correctly?
- Is the spacing and alignment reasonable?
- Are interactive elements properly placed?

**Functionality** (20%):
- Are interactive elements (buttons, dropdowns, etc.) present?
- Do the interaction types match the original intent?
- Are all selectable options available?

**Overall Usability** (10%):
- Is the question clear and understandable?
- Would a student be able to answer it properly?
- Are there any confusing or missing elements?

## Response Format

Respond with ONLY a JSON object:

```json
{
  "overall_match": true/false,
  "similarity_score": 0.0-1.0,
  "content_accuracy": 0.0-1.0,
  "visual_layout": 0.0-1.0,
  "functionality": 0.0-1.0,
  "usability": 0.0-1.0,
  "issues_found": ["list", "of", "specific", "issues"],
  "positive_aspects": ["list", "of", "things", "done", "well"],
  "recommendation": "accept/reject/needs_improvement",
  "notes": "brief explanation of your assessment"
}
```

Focus on whether the QTI version accurately represents the original question and would provide the same learning/assessment experience.
"""

# Detection prompt question types section
DETECTION_QUESTION_TYPES = """## Question Types
Only classify the question as one of these supported QTI interaction types:
- choice: Single or multiple-choice questions with radio buttons or checkboxes
- match: Questions where items from two sets need to be paired
- text-entry: Questions requiring short text input into a field
- hotspot: Questions requiring clicking on a specific area of an image (can be used for shading areas in some special cases)
- extended-text: Questions requiring longer text input/essay
- hot-text: Questions where specific text needs to be selected
- gap-match: Questions where text must be dragged to fill gaps
- order: Questions requiring ordering/ranking items
- graphic-gap-match: Questions matching items to locations on an image
- inline-choice: Questions with dropdown selections within text
- select-point: Questions requiring clicking specific points on an image
- media-interaction: Questions involving audio or video media

## Special Classification Rules
- IMPORTANT: If you see a question that looks like gap-match but has table structure
  with gaps inside table cells, classify it as "match" instead of "gap-match" because
  QTI 3.0 doesn't support gaps inside table cells.
- For table-based matching exercises where items in one column need to be matched
  with items in another column, use "match" interaction type.
- Gap-match should only be used for inline text with gaps, not for table-based layouts.

## Unsupported Types
- Dragging the top of a bar to a certain height
- Dividing a shape into sections
- Placing a shape into a coordinate grid
- Any question that requires a custom interaction that is not part of the QTI 3.0 standard
- Custom drawing or sketching interactions
- Complex mathematical input requiring special editors
- Interactive simulations or animations

## Multi-Part Question Support
QTI 3.0 supports COMPOSITE ITEMS with multiple interaction types in a single question:
- A question can have multiple parts (e.g., Part A, Part B, Part C)
- Each part can use different interaction types (e.g., Part A: choice, Part B: extended-text)
- Use separate response-identifier for each interaction (e.g., "RESPONSE_A", "RESPONSE_B")
- Each interaction needs its own qti-response-declaration
- This is called a "composite item" and is fully supported in QTI 3.0"""
