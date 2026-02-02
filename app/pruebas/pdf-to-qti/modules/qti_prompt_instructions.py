"""QTI prompt instructions for each question type.

This module contains the prompt instruction strings used by qti_configs.py
to guide the LLM in generating QTI XML for each question type.
"""

from __future__ import annotations

CHOICE_INSTRUCTIONS = """
For choice interactions:
1. Determine if it's a single-choice (radio buttons) or multiple-choice (checkboxes) question
2. For single-choice, set max-choices="1" and cardinality="single"
3. For multiple-choice, set max-choices to the appropriate number (or omit for unlimited)
   and cardinality="multiple"
4. Use <qti-simple-choice> elements for each option with unique identifiers
   (e.g., "ChoiceA", "ChoiceB")
5. **CRITICAL: Remove choice labels from text** - Strip A., B., C., D. prefixes from
   choice text content
6. Include the correct answer(s) in <qti-correct-response> with appropriate
   <qti-value> elements
7. Use the standard match_correct.xml template for response processing
"""

MATCH_INSTRUCTIONS = """
For match interactions:
1. Create two <qti-simple-match-set> elements, one for each column
2. Use <qti-simple-associable-choice> elements with unique identifiers for each item
3. Set match-max attributes appropriately based on the matching requirements
   - If the question is a "many to many" match, set match-max to the number of items
     in the second column
   - If the question is a "one to many" match, set match-max to the number of items
     in the first column
   - If the question is a "one to one" match, set match-max to 1
   - If the question is "one to two" match, set match-max to 2
   - And so on...
4. Remember to set max-associations in qti-match-interaction to the total number of
   associations that can be made (max-match target items * max-match source items)
5. Response declaration should have cardinality="multiple" and base-type="directedPair"
6. <qti-correct-response> should contain <qti-value> elements with pairs of identifiers
   (e.g., "A B")
"""

TEXT_ENTRY_INSTRUCTIONS = """
For text entry interactions:
1. Use <qti-text-entry-interaction> element with response-identifier attribute
2. Response declaration should have cardinality="single" and base-type="string"
3. If correct answers are known, include them in <qti-correct-response>
4. For pattern matching, consider using <qti-mapping> with pattern map entries
5. Use proper integer values for expected-length (number of characters):
   - Short answers: expected-length="50"
   - Medium answers: expected-length="200"
   - Long answers: expected-length="500"
   - Do NOT use descriptive words like "large", "medium", "small"
6. IMPORTANT: The <qti-text-entry-interaction> MUST be wrapped in a block element
   (<p> or <div>). It CANNOT be a direct child of <qti-item-body>.

   CORRECT structure:
   <div>
     <qti-text-entry-interaction response-identifier="RESPONSE" expected-length="100"/>
   </div>

   INCORRECT structure (will fail XSD validation):
   <qti-item-body>
     <qti-text-entry-interaction response-identifier="RESPONSE" expected-length="100"/>
   </qti-item-body>
"""

COMPOSITE_INSTRUCTIONS = """
For composite interactions (multi-part questions):
1. Create a separate <qti-response-declaration> for EACH part of the question
   (e.g., RESPONSE_A, RESPONSE_B).
2. Use standard HTML tags like <p>, <strong>, or <div> to introduce each part
   (e.g., "<p><strong>Part A</strong></p>").
3. **CRITICAL: DO NOT use <qti-prompt>**. All instructional text, including the
   prompts for each interaction, MUST be inside standard block elements like <p>.
4. Place each interaction (<qti-choice-interaction>, <qti-extended-text-interaction>,
   etc.) directly after its corresponding instructional text.
5. Ensure each interaction element uses the correct `response-identifier` that links
   to its declaration.
6. A single <qti-response-processing> element is usually sufficient for the entire item.
"""

HOTSPOT_INSTRUCTIONS = """
For hotspot interactions:
1. Use <qti-hotspot-interaction> with:
   - response-identifier="RESPONSE"
   - max-choices="0" for unlimited selections or specific number for limited choices
2. Place the image as the FIRST child of qti-hotspot-interaction:
   <img src="..." width="..." height="..." alt="..."/>
3. After the image, add <qti-hotspot-choice> elements with:
   - identifier (e.g., "A", "B", "C")
   - shape (e.g., "circle", "rect")
   - coords (format depends on shape:
     * circle: "x,y,radius"
     * rect: "x1,y1,x2,y2")
4. Response declaration must have:
   - identifier="RESPONSE"
   - cardinality="multiple" for multiple selections
   - base-type="identifier"
5. Include correct answers in qti-correct-response using qti-value elements

For div-based layouts:
1. Convert the div structure into an SVG with proper dimensions
2. Convert the SVG to a PNG image and upload to S3 (NEVER use base64)
3. Place the image FIRST in the interaction using the S3 URL
4. Calculate hotspot coordinates based on the original div positions

Example structure:
<qti-hotspot-interaction response-identifier="RESPONSE" max-choices="0">
  <img src="..." width="..." height="..." alt="..."/>
  <qti-hotspot-choice identifier="A" shape="rect" coords="0,0,100,50"/>
  <qti-hotspot-choice identifier="B" shape="rect" coords="0,50,100,100"/>
</qti-hotspot-interaction>
"""

EXTENDED_TEXT_INSTRUCTIONS = """
For extended text interactions:
1. Use <qti-extended-text-interaction> with response-identifier attribute
2. Include <qti-prompt> to provide instructions
3. Response declaration should have cardinality="single" and base-type="string"
4. No correct response is typically provided as these are usually essay questions
5. Use proper integer values for expected-length (number of characters):
   - Short responses: expected-length="200"
   - Medium responses: expected-length="500"
   - Long essays: expected-length="2000"
   - Do NOT use descriptive words like "large", "medium", "small"
"""

HOT_TEXT_INSTRUCTIONS = """
For hot text interactions:
1. Use <qti-hottext-interaction> with response-identifier and max-choices attributes
2. Wrap selectable text in <qti-hottext> elements with unique identifiers
3. Response declaration cardinality depends on how many text elements can be selected
4. Include correct answer(s) in <qti-correct-response>
"""

GAP_MATCH_INSTRUCTIONS = """
For gap match interactions:
1. Use <qti-gap-match-interaction> with response-identifier and max-associations
2. Create <qti-gap-text> elements for the draggable text options
   - Each <qti-gap-text> MUST include a match-max attribute (e.g., match-max="1")
   - The match-max attribute specifies how many times this text can be used
3. Place <qti-gap> elements where the gaps should appear
4. Response declaration should have cardinality="multiple" and base-type="directedPair"
5. <qti-correct-response> should contain pairs of gap text ID to gap ID
6. IMPORTANT: The <qti-gap> elements are NOT allowed inside table cells.
"""

ORDER_INSTRUCTIONS = """
For order interactions:
1. Use <qti-order-interaction> with response-identifier attribute
2. Create <qti-simple-choice> elements for each item to be ordered
3. Response declaration should have cardinality="ordered" and base-type="identifier"
4. <qti-correct-response> should list identifiers in the correct order
"""

GRAPHIC_GAP_MATCH_INSTRUCTIONS = """
For graphic gap match interactions:
1. Use <qti-graphic-gap-match-interaction> with:
   - response-identifier
   - max-associations
2. Add the background image using <img> directly.
   - Valid elements: <img>, <object> (deprecated), or <picture>
   - Do NOT wrap the image in <div> or other elements.
3. For draggable options, choose one format based on content:
   a. If you have an image → use <qti-gap-img>:
      - Must contain a valid <img> (or <object>/<picture>)
      - Must include match-max (e.g., match-max="1")
      - Example:
        <qti-gap-img identifier="lamb" match-max="1">
          <img src="..." alt="Lamb"/>
        </qti-gap-img>
   b. If you only have text → use <qti-gap-text> (NEW supported option):
      - Must include match-max (e.g., match-max="1")
      - Example:
        <qti-gap-text identifier="lamb" match-max="1">Lamb</qti-gap-text>
4. Define one or more <qti-associable-hotspot> elements as drop zones.
   - Must include: shape, coords, and match-max
5. In <qti-response-declaration>:
   - cardinality = "multiple"
   - base-type = "directedPair"
   - Example value: <qti-value>lamb hotspot1</qti-value>
"""

INLINE_CHOICE_INSTRUCTIONS = """
For inline choice interactions:
1. Use <qti-inline-choice-interaction> with response-identifier attribute
2. Create <qti-inline-choice> elements for each option with unique identifiers
3. Place the interaction inline within text where the dropdown should appear
4. Response declaration should have cardinality="single" and base-type="identifier"
5. Include the correct answer in <qti-correct-response>
6. IMPORTANT: For response processing, only use valid QTI 3.0 elements such as
   <qti-response-condition>, <qti-set-outcome-value>, <qti-response-processing-fragment>,
   <qti-exit-response>, and <qti-lookup-outcome-value>. Do NOT use <qti-match> or any
   other elements not allowed by the QTI 3.0 schema for response processing.
7. IMPORTANT: Only one <qti-match> (or equivalent condition) is allowed per
   <qti-response-if> block. Do NOT use multiple <qti-match> elements inside a
   single <qti-response-if>.
8. IMPORTANT: <qti-response-then> is NOT a valid child of <qti-response-if> in
   QTI 3.0. Use <qti-response-if> directly for the 'then' block, and only use
   <qti-response-else-if> or <qti-response-else> as siblings.
"""

SELECT_POINT_INSTRUCTIONS = """
For select point interactions:
1. Use <qti-select-point-interaction> with response-identifier and max-choices
2. Include the image with src and alt attributes as a DIRECT CHILD of the
   qti-select-point-interaction element
3. IMPORTANT: The image tag MUST be placed directly inside the interaction element
   after the qti-prompt (if any)
4. Response declaration should have cardinality="single" or "multiple" depending
   on how many points can be selected
5. Base-type should be "point"
6. <qti-correct-response> should contain the coordinates of the correct point(s)

## CRITICAL FOR SELECT-POINT INTERACTIONS
For select-point interactions, you MUST place the image or SVG as a DIRECT CHILD of
the <qti-select-point-interaction> element.
The correct structure is:
<qti-select-point-interaction max-choices="1" response-identifier="RESPONSE">
  <qti-prompt>...</qti-prompt>  <!-- prompt comes first if present -->
  <img src="..." /> <!-- or <svg>...</svg> content -->
</qti-select-point-interaction>

INCORRECT positioning of the image will cause the interaction to fail! The image
must be a direct child of the interaction element.

EXAMPLE STRUCTURE:
<qti-select-point-interaction max-choices="1" response-identifier="RESPONSE">
  <qti-prompt>
    <p>Mark the correct location on the image.</p>
  </qti-prompt>
  <img alt="Image description" width="400" height="300" src="image.png"/>
</qti-select-point-interaction>
"""

MEDIA_INTERACTION_INSTRUCTIONS = """
For media interactions:
1. Use <qti-media-interaction> with response-identifier attribute
2. Set appropriate attributes like autostart, loop, min-plays, and max-plays
3. Include either <audio> or <video> element with appropriate sources
4. For video, include appropriate tracks if available
5. Response declaration typically has cardinality="single" and base-type="integer"
   for tracking interaction
"""

GENERIC_INSTRUCTIONS = """
Analyze the HTML content carefully to identify what kind of interaction this
question requires. Choose the most appropriate QTI 3.0 interaction type to
represent the question. Ensure all content is preserved in the transformation.
"""
