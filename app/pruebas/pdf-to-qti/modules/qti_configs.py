"""qti_configs.py
----------------
Contains the configuration snippets that the transformer uses for each
supported QTI 3.0 interaction. Updated to match the comprehensive
configurations from the JavaScript SDK implementation.

* No line exceeds 150 characters.
* Complete example XML for all question types.
* Detailed prompt instructions with specific requirements.
* The module stays under 500 lines to respect workspace guidelines.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Callable
import os
import re
import base64

# NOTE: Do **not** import heavy dependencies here – this file must stay
# lightweight so it can be imported very early without side-effects.

# Type definition for question config
class QuestionConfig:
    def __init__(self, 
                 type: str, 
                 example_xml: str, 
                 prompt_instructions: str,
                 post_process: Optional[Callable[[str], str]] = None):
        self.type = type
        self.example_xml = example_xml
        self.prompt_instructions = prompt_instructions
        self.post_process = post_process

def extract_example_xml(examples_xml: str, type: str, index: int = 0) -> str:
    """Extract example XML from the examples file"""
    # Default examples if extraction fails
    default_examples = {
        'choice': '''<qti-assessment-item xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.imsglobal.org/xsd/imsqtiasi_v3p0 https://purl.imsglobal.org/spec/qti/v3p0/schema/xsd/imsqti_asiv3p0_v1p0.xsd" identifier="choice-example" title="Choice Example" adaptive="false" time-dependent="false">
      <qti-response-declaration identifier="RESPONSE" cardinality="single" base-type="identifier">
        <qti-correct-response><qti-value>ChoiceA</qti-value></qti-correct-response>
      </qti-response-declaration>
      <qti-outcome-declaration identifier="SCORE" cardinality="single" base-type="float">
        <qti-default-value><qti-value>0</qti-value></qti-default-value>
      </qti-outcome-declaration>
      <qti-item-body>
        <p>Example question text</p>
        <qti-choice-interaction max-choices="1" response-identifier="RESPONSE">
          <qti-prompt>What is the correct answer?</qti-prompt>
          <qti-simple-choice identifier="ChoiceA">Option A</qti-simple-choice>
          <qti-simple-choice identifier="ChoiceB">Option B</qti-simple-choice>
          <qti-simple-choice identifier="ChoiceC">Option C</qti-simple-choice>
        </qti-choice-interaction>
      </qti-item-body>
      <qti-response-processing template="https://purl.imsglobal.org/spec/qti/v3p0/rptemplates/match_correct.xml"/>
    </qti-assessment-item>'''
    }
    
    # Return default example if examples file couldn't be read
    if not examples_xml:
        return default_examples.get(type, default_examples['choice'])
    
    # Try to find the comment marking the start of the example
    type_markers = {
        'choice': ['<!-- Choice Interaction', '<!-- Multiple Choice'],
        'match': ['<!-- Match -->'],
        'text-entry': ['<!-- Text Entry -->'],
        'hotspot': ['<!-- Hotspot Single', '<!-- Hotspot Multiple'],
        'extended-text': ['<!-- Extended Text Input -->'],
        'hot-text': ['<!-- HotText Single', '<!-- HotText Multiple'],
        'gap-match': ['<!-- Gap Match -->'],
        'order': ['<!-- Order -->'],
        'graphic-gap-match': ['<!-- Graphic Gap Match -->'],
        'inline-choice': ['<!-- Inline Choice', '<!-- Inline Choice Multiple'],
        'select-point': ['<!-- Select Point -->'],
        'media-interaction': ['<!-- Media Interaction Video', '<!-- Media Interaction Audio']
    }
    
    markers = type_markers.get(type, [])
    marker_to_use = markers[min(index, len(markers) - 1)] if markers else markers[0] if markers else None
    
    if not marker_to_use:
        return default_examples.get(type, default_examples['choice'])
    
    # Find the start of the example
    start_index = examples_xml.find(marker_to_use)
    if start_index == -1:
        return default_examples.get(type, default_examples['choice'])
    
    # Find the next comment which would mark the end
    end_index = examples_xml.find('<!--', start_index + len(marker_to_use))
    if end_index == -1:
        # If no next comment, extract to the end of the file
        return examples_xml[start_index:].strip()
    
    # Extract the XML between the markers
    extracted_xml = examples_xml[start_index:end_index].strip()
    
    # Try to isolate just the qti-assessment-item tag
    item_match = re.search(r'<qti-assessment-item[\s\S]*?</qti-assessment-item>', extracted_xml)
    if item_match:
        return item_match.group(0)
    
    return extracted_xml

# Try to read the QTI examples XML file
examples_xml_path = os.path.join(os.path.dirname(__file__), '..', 'EXAMPLES_QTI3_XML.xml')
examples_xml = ''
try:
    if os.path.exists(examples_xml_path):
        with open(examples_xml_path, 'r', encoding='utf-8') as f:
            examples_xml = f.read()
except Exception as error:
    print(f'Error reading QTI examples XML file: {error}')

def hotspot_post_process(xml: str) -> str:
    """
    Post-process function for hotspot interactions.
    
    NOTE: This function NO LONGER converts SVG to base64.
    Base64 encoding is NOT ALLOWED - all images must use S3 URLs.
    The LLM should generate QTI with proper img tags using S3 URLs.
    """
    # Post-processing removed - base64 encoding is not allowed
    # If SVG needs conversion, it should be done before this step
    # and uploaded to S3 first
    return xml

def select_point_post_process(xml: str) -> str:
    """
    Post-process function for select-point interactions.
    
    NOTE: This function NO LONGER converts SVG to base64.
    Base64 encoding is NOT ALLOWED - all images must use S3 URLs.
    The LLM should generate QTI with proper img tags using S3 URLs.
    """
    # Post-processing removed - base64 encoding is not allowed
    # If SVG needs conversion, it should be done before this step
    # and uploaded to S3 first
    return xml

# Configuration for choice questions (single or multiple)
choice_config = QuestionConfig(
    type='choice',
    example_xml=extract_example_xml(examples_xml, 'choice', 0),
    prompt_instructions="""
For choice interactions:
1. Determine if it's a single-choice (radio buttons) or multiple-choice (checkboxes) question
2. For single-choice, set max-choices="1" and cardinality="single"
3. For multiple-choice, set max-choices to the appropriate number (or omit for unlimited) and cardinality="multiple"
4. Use <qti-simple-choice> elements for each option with unique identifiers (e.g., "ChoiceA", "ChoiceB")
5. **CRITICAL: Remove choice labels from text** - Strip A., B., C., D. prefixes from choice text content
6. Include the correct answer(s) in <qti-correct-response> with appropriate <qti-value> elements
7. Use the standard match_correct.xml template for response processing
"""
)

# Configuration for match questions
match_config = QuestionConfig(
    type='match',
    example_xml=extract_example_xml(examples_xml, 'match', 0),
    prompt_instructions="""
For match interactions:
1. Create two <qti-simple-match-set> elements, one for each column
2. Use <qti-simple-associable-choice> elements with unique identifiers for each item
3. Set match-max attributes appropriately based on the matching requirements
   - If the question is a "many to many" match, set match-max to the number of items in the second column
   - If the question is a "one to many" match, set match-max to the number of items in the first column
   - If the question is a "one to one" match, set match-max to 1
   - If the question is "one to two" match, set match-max to 2
   - And so on...
4. Remember to set max-associations in qti-match-interaction to the total number of associations that can be made (max-match target items * max-match source items)
5. Response declaration should have cardinality="multiple" and base-type="directedPair"
6. <qti-correct-response> should contain <qti-value> elements with pairs of identifiers (e.g., "A B")
"""
)

# Configuration for text entry questions
text_entry_config = QuestionConfig(
    type='text-entry',
    example_xml=extract_example_xml(examples_xml, 'text-entry', 0),
    prompt_instructions="""
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
6. IMPORTANT: The <qti-text-entry-interaction> MUST be wrapped in a block element (<p> or <div>).
   It CANNOT be a direct child of <qti-item-body>.
   
   CORRECT structure:
   <div>
     <qti-text-entry-interaction response-identifier="RESPONSE" expected-length="100"/>
   </div>
   
   INCORRECT structure (will fail XSD validation):
   <qti-item-body>
     <qti-text-entry-interaction response-identifier="RESPONSE" expected-length="100"/>
   </qti-item-body>
"""
)

# Configuration for composite questions
composite_config = QuestionConfig(
    type='composite',
    example_xml="""<qti-assessment-item xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.imsglobal.org/xsd/imsqtiasi_v3p0 https://purl.imsglobal.org/spec/qti/v3p0/schema/xsd/imsqti_asiv3p0_v1p0.xsd" identifier="composite-example" title="Multi-part Question Example" time-dependent="false">
      <qti-response-declaration identifier="RESPONSE_A" cardinality="single" base-type="identifier">
        <qti-correct-response>
          <qti-value>ChoiceB</qti-value>
        </qti-correct-response>
      </qti-response-declaration>
      <qti-response-declaration identifier="RESPONSE_B" cardinality="single" base-type="string"/>
      <qti-item-body>
        <p>This is a two-part question. Answer both parts.</p>
        <p><strong>Part A</strong></p>
        <p>What is the capital of France?</p>
        <qti-choice-interaction response-identifier="RESPONSE_A" max-choices="1">
          <qti-simple-choice identifier="ChoiceA">London</qti-simple-choice>
          <qti-simple-choice identifier="ChoiceB">Paris</qti-simple-choice>
          <qti-simple-choice identifier="ChoiceC">Berlin</qti-simple-choice>
        </qti-choice-interaction>
        <hr/>
        <p><strong>Part B</strong></p>
        <p>Explain why it is the capital.</p>
        <qti-extended-text-interaction response-identifier="RESPONSE_B" expected-lines="5"/>
      </qti-item-body>
      <qti-response-processing template="https://purl.imsglobal.org/spec/qti/v3p0/rptemplates/match_correct.xml"/>
    </qti-assessment-item>""",
    prompt_instructions="""
For composite interactions (multi-part questions):
1. Create a separate <qti-response-declaration> for EACH part of the question (e.g., RESPONSE_A, RESPONSE_B).
2. Use standard HTML tags like <p>, <strong>, or <div> to introduce each part (e.g., "<p><strong>Part A</strong></p>").
3. **CRITICAL: DO NOT use <qti-prompt>**. All instructional text, including the prompts for each interaction, MUST be inside standard block elements like <p>.
4. Place each interaction (<qti-choice-interaction>, <qti-extended-text-interaction>, etc.) directly after its corresponding instructional text.
5. Ensure each interaction element uses the correct `response-identifier` that links to its declaration.
6. A single <qti-response-processing> element is usually sufficient for the entire item.
"""
)

# Configuration for hotspot questions
hotspot_config = QuestionConfig(
    type='hotspot',
    example_xml=extract_example_xml(examples_xml, 'hotspot', 0),
    prompt_instructions="""
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
""",
    post_process=hotspot_post_process
)

# Configuration for extended text questions
extended_text_config = QuestionConfig(
    type='extended-text',
    example_xml=extract_example_xml(examples_xml, 'extended-text', 0),
    prompt_instructions="""
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
)

# Configuration for hot text questions
hot_text_config = QuestionConfig(
    type='hot-text',
    example_xml=extract_example_xml(examples_xml, 'hot-text', 0),
    prompt_instructions="""
For hot text interactions:
1. Use <qti-hottext-interaction> with response-identifier and max-choices attributes
2. Wrap selectable text in <qti-hottext> elements with unique identifiers
3. Response declaration cardinality depends on how many text elements can be selected
4. Include correct answer(s) in <qti-correct-response>
"""
)

# Configuration for gap match questions
gap_match_config = QuestionConfig(
    type='gap-match',
    example_xml=extract_example_xml(examples_xml, 'gap-match', 0),
    prompt_instructions="""
For gap match interactions:
1. Use <qti-gap-match-interaction> with response-identifier and max-associations attributes
2. Create <qti-gap-text> elements for the draggable text options
   - Each <qti-gap-text> MUST include a match-max attribute (e.g., match-max="1")
   - The match-max attribute specifies how many times this text can be used
3. Place <qti-gap> elements where the gaps should appear
4. Response declaration should have cardinality="multiple" and base-type="directedPair"
5. <qti-correct-response> should contain pairs of gap text ID to gap ID
6. IMPORTANT: The <qti-gap> elements are NOT allowed inside table cells.
"""
)

# Configuration for order questions
order_config = QuestionConfig(
    type='order',
    example_xml=extract_example_xml(examples_xml, 'order', 0),
    prompt_instructions="""
For order interactions:
1. Use <qti-order-interaction> with response-identifier attribute
2. Create <qti-simple-choice> elements for each item to be ordered
3. Response declaration should have cardinality="ordered" and base-type="identifier"
4. <qti-correct-response> should list identifiers in the correct order
"""
)

# Configuration for graphic gap match questions
graphic_gap_match_config = QuestionConfig(
    type='graphic-gap-match',
    example_xml=extract_example_xml(examples_xml, 'graphic-gap-match', 0),
    prompt_instructions="""
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
)

# Configuration for inline choice questions
inline_choice_config = QuestionConfig(
    type='inline-choice',
    example_xml=extract_example_xml(examples_xml, 'inline-choice', 0),
    prompt_instructions="""
For inline choice interactions:
1. Use <qti-inline-choice-interaction> with response-identifier attribute
2. Create <qti-inline-choice> elements for each option with unique identifiers
3. Place the interaction inline within text where the dropdown should appear
4. Response declaration should have cardinality="single" and base-type="identifier"
5. Include the correct answer in <qti-correct-response>
6. IMPORTANT: For response processing, only use valid QTI 3.0 elements such as <qti-response-condition>, <qti-set-outcome-value>, <qti-response-processing-fragment>, <qti-exit-response>, and <qti-lookup-outcome-value>. Do NOT use <qti-match> or any other elements not allowed by the QTI 3.0 schema for response processing.
7. IMPORTANT: Only one <qti-match> (or equivalent condition) is allowed per <qti-response-if> block. Do NOT use multiple <qti-match> elements inside a single <qti-response-if>.
8. IMPORTANT: <qti-response-then> is NOT a valid child of <qti-response-if> in QTI 3.0. Use <qti-response-if> directly for the 'then' block, and only use <qti-response-else-if> or <qti-response-else> as siblings.
"""
)

# Configuration for select point questions
select_point_config = QuestionConfig(
    type='select-point',
    example_xml=extract_example_xml(examples_xml, 'select-point', 0),
    prompt_instructions="""
For select point interactions:
1. Use <qti-select-point-interaction> with response-identifier and max-choices attributes
2. Include the image with src and alt attributes as a DIRECT CHILD of the qti-select-point-interaction element
3. IMPORTANT: The image tag MUST be placed directly inside the interaction element after the qti-prompt (if any)
4. Response declaration should have cardinality="single" or "multiple" depending on how many points can be selected
5. Base-type should be "point"
6. <qti-correct-response> should contain the coordinates of the correct point(s)

## CRITICAL FOR SELECT-POINT INTERACTIONS
For select-point interactions, you MUST place the image or SVG as a DIRECT CHILD of the <qti-select-point-interaction> element.
The correct structure is:
<qti-select-point-interaction max-choices="1" response-identifier="RESPONSE">
  <qti-prompt>...</qti-prompt>  <!-- prompt comes first if present -->
  <img src="..." /> <!-- or <svg>...</svg> content -->
</qti-select-point-interaction>

INCORRECT positioning of the image will cause the interaction to fail! The image must be a direct child of the interaction element.

EXAMPLE STRUCTURE:
<qti-select-point-interaction max-choices="1" response-identifier="RESPONSE">
  <qti-prompt>
    <p>Mark the correct location on the image.</p>
  </qti-prompt>
  <img alt="Image description" width="400" height="300" src="image.png"/>
</qti-select-point-interaction>
""",
    post_process=select_point_post_process
)

# Configuration for media interaction questions
media_interaction_config = QuestionConfig(
    type='media-interaction',
    example_xml=extract_example_xml(examples_xml, 'media-interaction', 0),
    prompt_instructions="""
For media interactions:
1. Use <qti-media-interaction> with response-identifier attribute
2. Set appropriate attributes like autostart, loop, min-plays, and max-plays
3. Include either <audio> or <video> element with appropriate sources
4. For video, include appropriate tracks if available
5. Response declaration typically has cardinality="single" and base-type="integer" for tracking interaction
"""
)

# Generic instructions for unknown question types
generic_instructions = """
Analyze the HTML content carefully to identify what kind of interaction this question requires.
Choose the most appropriate QTI 3.0 interaction type to represent the question.
Ensure all content is preserved in the transformation.
"""

# Map of all question type configurations
question_configs: Dict[str, QuestionConfig] = {
    # Original types from the source code
    'choice': choice_config,
    'match': match_config,
    'text-entry': text_entry_config,
    'composite': composite_config,
    'hotspot': hotspot_config,
    'extended-text': extended_text_config,
    'hot-text': hot_text_config,
    'gap-match': gap_match_config,
    'order': order_config,
    'graphic-gap-match': graphic_gap_match_config,
    'inline-choice': inline_choice_config,
    'select-point': select_point_config,
    'media-interaction': media_interaction_config,
    
    # Default fallback for unknown types
    'unknown': QuestionConfig(
        type='unknown',
        prompt_instructions=generic_instructions,
        example_xml=extract_example_xml(examples_xml, 'choice', 0)
    )
}

def get_question_config(question_type: str) -> QuestionConfig:
    """Get the configuration for a specific question type
    
    Args:
        question_type: The question type to get configuration for
        
    Returns:
        The question type configuration or the unknown type config if not found
    """
    return question_configs.get(question_type, question_configs['unknown'])

def get_available_question_types() -> List[str]:
    """Get all available question types
    
    Returns:
        List of question type names
    """
    return [t for t in question_configs.keys() if t != 'unknown']

# Backward compatibility: Keep the old QTI_TYPE_CONFIGS format for existing code
QTI_TYPE_CONFIGS = {
    config.type: {
        "type": config.type,
        "promptInstructions": config.prompt_instructions.strip(),
        "exampleXml": config.example_xml
    }
    for config in question_configs.values()
    if config.type != 'unknown'
} 