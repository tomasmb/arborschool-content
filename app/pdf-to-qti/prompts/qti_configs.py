"""QTI 3.0 Configuration for all question types."""

from __future__ import annotations

from collections.abc import Callable
import re
import base64


class QuestionConfig:
    """Configuration for a QTI question type."""

    def __init__(
        self,
        type: str,
        example_xml: str,
        prompt_instructions: str,
        post_process: Optional[Callable[[str], str]] = None,
    ):
        self.type = type
        self.example_xml = example_xml
        self.prompt_instructions = prompt_instructions
        self.post_process = post_process


def hotspot_post_process(xml: str) -> str:
    """Post-process function for hotspot interactions."""
    if "<qti-hotspot-interaction" not in xml or "<svg" not in xml:
        return xml

    pattern = (
        r"(<qti-hotspot-interaction[^>]*>)([\s\S]*?)(<svg[\s\S]*?</svg>)"
        r"([\s\S]*?)(</qti-hotspot-interaction>)"
    )

    def replace_svg(match):
        interaction_start, before_svg, svg, after_svg, interaction_end = match.groups()
        width_match = re.search(r'width="(\d+)"', svg)
        height_match = re.search(r'height="(\d+)"', svg)
        width = width_match.group(1) if width_match else "254"
        height = height_match.group(1) if height_match else "252"
        base64_svg = base64.b64encode(svg.encode()).decode()
        img_src = f"data:image/svg+xml;base64,{base64_svg}"
        img = f'<img src="{img_src}" width="{width}" height="{height}" alt="Interactive hotspot area"/>'
        return f"{interaction_start}{img}{after_svg}{interaction_end}"

    return re.sub(pattern, replace_svg, xml)


def select_point_post_process(xml: str) -> str:
    """Post-process function for select-point interactions."""
    if "<qti-select-point-interaction" not in xml:
        return xml

    pattern = (
        r"(<qti-select-point-interaction[^>]*>)([\s\S]*?)(<svg[\s\S]*?</svg>)"
        r"([\s\S]*?)(</qti-select-point-interaction>)"
    )

    def replace_svg(match):
        start, before_svg, svg, after_svg, end = match.groups()
        width_match = re.search(r'width="(\d+)"', svg)
        height_match = re.search(r'height="(\d+)"', svg)
        width = width_match.group(1) if width_match else "400"
        height = height_match.group(1) if height_match else "400"
        base64_svg = base64.b64encode(svg.encode()).decode()
        img_src = f"data:image/svg+xml;base64,{base64_svg}"
        img = f'<img src="{img_src}" width="{width}" height="{height}" alt="Interactive graph"/>'
        if "<qti-prompt>" in before_svg:
            prompt_end = before_svg.rfind("</qti-prompt>") + len("</qti-prompt>")
            before_prompt = before_svg[:prompt_end]
            after_prompt = before_svg[prompt_end:]
            return f"{start}{before_prompt}{img}{after_prompt}{after_svg}{end}"
        else:
            return f"{start}{img}{before_svg}{after_svg}{end}"

    return re.sub(pattern, replace_svg, xml)


# Configuration for choice questions
choice_config = QuestionConfig(
    type="choice",
    example_xml='''<qti-assessment-item xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0" identifier="choice-example" title="Choice Example" adaptive="false" time-dependent="false">
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
</qti-assessment-item>''',
    prompt_instructions="""
For choice interactions:
1. Determine if it's single-choice (max-choices="1", cardinality="single") or multiple-choice
2. Use <qti-simple-choice> elements with unique identifiers
3. Remove choice labels from text but use them in identifiers
4. ONLY include <qti-correct-response> if answer key is EXPLICITLY in source markdown
5. VISUAL CHOICES: If choices are shown in an image, keep the image and use the labels as choice text
""",
)

# Configuration for match questions
match_config = QuestionConfig(
    type="match",
    example_xml='''<qti-assessment-item xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0" identifier="match-example" title="Match Example" adaptive="false" time-dependent="false">
  <qti-response-declaration identifier="RESPONSE" cardinality="multiple" base-type="directedPair">
    <qti-correct-response>
      <qti-value>A B</qti-value>
      <qti-value>C D</qti-value>
    </qti-correct-response>
  </qti-response-declaration>
  <qti-item-body>
    <p>Match the items:</p>
    <qti-match-interaction response-identifier="RESPONSE" max-associations="2">
      <qti-simple-match-set>
        <qti-simple-associable-choice identifier="A" match-max="1">Item 1</qti-simple-associable-choice>
        <qti-simple-associable-choice identifier="C" match-max="1">Item 2</qti-simple-associable-choice>
      </qti-simple-match-set>
      <qti-simple-match-set>
        <qti-simple-associable-choice identifier="B" match-max="1">Match 1</qti-simple-associable-choice>
        <qti-simple-associable-choice identifier="D" match-max="1">Match 2</qti-simple-associable-choice>
      </qti-simple-match-set>
    </qti-match-interaction>
  </qti-item-body>
  <qti-response-processing template="https://purl.imsglobal.org/spec/qti/v3p0/rptemplates/match_correct.xml"/>
</qti-assessment-item>''',
    prompt_instructions="""
For match interactions:
1. Create two <qti-simple-match-set> elements, one for each column
2. Use <qti-simple-associable-choice> elements with unique identifiers for each item
3. Set match-max attributes appropriately based on the matching requirements
4. Remember to set max-associations in qti-match-interaction
5. Response declaration should have cardinality="multiple" and base-type="directedPair"
6. **ANSWER KEY**: ONLY include <qti-correct-response> if the answer key is EXPLICITLY in the source markdown
""",
)

# Configuration for text entry questions
text_entry_config = QuestionConfig(
    type="text-entry",
    example_xml='''<qti-assessment-item xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0" identifier="text-entry-example" title="Text Entry Example" adaptive="false" time-dependent="false">
  <qti-response-declaration identifier="RESPONSE" cardinality="single" base-type="string">
    <qti-correct-response><qti-value>answer</qti-value></qti-correct-response>
  </qti-response-declaration>
  <qti-item-body>
    <p>Enter your answer:</p>
    <div>
      <qti-text-entry-interaction response-identifier="RESPONSE" expected-length="50"/>
    </div>
  </qti-item-body>
  <qti-response-processing template="https://purl.imsglobal.org/spec/qti/v3p0/rptemplates/match_correct.xml"/>
</qti-assessment-item>''',
    prompt_instructions="""
For text entry interactions:
1. Use <qti-text-entry-interaction> element with response-identifier attribute
2. Response declaration should have cardinality="single" and base-type="string"
3. ONLY include <qti-correct-response> if the answer is EXPLICITLY in the source markdown
4. IMPORTANT: The <qti-text-entry-interaction> MUST be wrapped in a block element (<p> or <div>)
""",
)

# Configuration for extended text questions
extended_text_config = QuestionConfig(
    type="extended-text",
    example_xml='''<qti-assessment-item xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0" identifier="extended-text-example" title="Extended Text Example" adaptive="false" time-dependent="false">
  <qti-response-declaration identifier="RESPONSE" cardinality="single" base-type="string"/>
  <qti-item-body>
    <p>Write your response:</p>
    <qti-extended-text-interaction response-identifier="RESPONSE" expected-length="500"/>
  </qti-item-body>
  <qti-response-processing template="https://purl.imsglobal.org/spec/qti/v3p0/rptemplates/match_correct.xml"/>
</qti-assessment-item>''',
    prompt_instructions="""
For extended text interactions:
1. Use <qti-extended-text-interaction> with response-identifier attribute
2. Include <qti-prompt> to provide instructions
3. Response declaration should have cardinality="single" and base-type="string"
4. No correct response is typically provided as these are usually essay questions
""",
)

# Configuration for composite questions
composite_config = QuestionConfig(
    type="composite",
    example_xml='''<qti-assessment-item xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0" identifier="composite-example" title="Multi-part Question Example" time-dependent="false">
  <qti-response-declaration identifier="RESPONSE_A" cardinality="single" base-type="identifier">
    <qti-correct-response><qti-value>ChoiceB</qti-value></qti-correct-response>
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
</qti-assessment-item>''',
    prompt_instructions="""
For composite interactions (multi-part questions):
1. **CRITICAL: There is NO <qti-composite-interaction> element in QTI 3.0. NEVER use it.**
2. Combine multiple standard interactions within a single qti-item-body
3. Create a separate <qti-response-declaration> for EACH part of the question
4. Use standard HTML tags like <p>, <strong>, or <div> to introduce each part
5. **DO NOT use <qti-prompt>**. All instructional text MUST be inside standard block elements like <p>
""",
)

# Configuration for hotspot questions
hotspot_config = QuestionConfig(
    type="hotspot",
    example_xml='''<qti-assessment-item xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0" identifier="hotspot-example" title="Hotspot Example" adaptive="false" time-dependent="false">
  <qti-response-declaration identifier="RESPONSE" cardinality="multiple" base-type="identifier">
    <qti-correct-response>
      <qti-value>A</qti-value>
      <qti-value>B</qti-value>
    </qti-correct-response>
  </qti-response-declaration>
  <qti-item-body>
    <qti-hotspot-interaction response-identifier="RESPONSE" max-choices="0">
      <img src="image.png" width="400" height="300" alt="Interactive image"/>
      <qti-hotspot-choice identifier="A" shape="rect" coords="0,0,100,50"/>
      <qti-hotspot-choice identifier="B" shape="rect" coords="0,50,100,100"/>
    </qti-hotspot-interaction>
  </qti-item-body>
  <qti-response-processing template="https://purl.imsglobal.org/spec/qti/v3p0/rptemplates/match_correct.xml"/>
</qti-assessment-item>''',
    prompt_instructions="""
For hotspot interactions:
1. Use <qti-hotspot-interaction> with response-identifier and max-choices attributes
2. Place the image as the FIRST child of qti-hotspot-interaction
3. After the image, add <qti-hotspot-choice> elements with identifier, shape, and coords
4. Response declaration must have cardinality="multiple" and base-type="identifier"
""",
    post_process=hotspot_post_process,
)

# Configuration for gap match questions
gap_match_config = QuestionConfig(
    type="gap-match",
    example_xml='''<qti-assessment-item xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0" identifier="gap-match-example" title="Gap Match Example" adaptive="false" time-dependent="false">
  <qti-response-declaration identifier="RESPONSE" cardinality="multiple" base-type="directedPair">
    <qti-correct-response>
      <qti-value>text1 gap1</qti-value>
      <qti-value>text2 gap2</qti-value>
    </qti-correct-response>
  </qti-response-declaration>
  <qti-item-body>
    <p>Fill in the gaps:</p>
    <qti-gap-match-interaction response-identifier="RESPONSE" max-associations="2">
      <qti-gap-text identifier="text1" match-max="1">Option 1</qti-gap-text>
      <qti-gap-text identifier="text2" match-max="1">Option 2</qti-gap-text>
      <p>The answer is <qti-gap identifier="gap1"/> and <qti-gap identifier="gap2"/>.</p>
    </qti-gap-match-interaction>
  </qti-item-body>
  <qti-response-processing template="https://purl.imsglobal.org/spec/qti/v3p0/rptemplates/match_correct.xml"/>
</qti-assessment-item>''',
    prompt_instructions="""
For gap match interactions:
1. Use <qti-gap-match-interaction> with response-identifier and max-associations attributes
2. Create <qti-gap-text> elements for the draggable text options
3. Place <qti-gap> elements where the gaps should appear
4. Response declaration should have cardinality="multiple" and base-type="directedPair"
5. IMPORTANT: The <qti-gap> elements are NOT allowed inside table cells
""",
)

# Configuration for order questions
order_config = QuestionConfig(
    type="order",
    example_xml='''<qti-assessment-item xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0" identifier="order-example" title="Order Example" adaptive="false" time-dependent="false">
  <qti-response-declaration identifier="RESPONSE" cardinality="ordered" base-type="identifier">
    <qti-correct-response>
      <qti-value>A</qti-value>
      <qti-value>B</qti-value>
      <qti-value>C</qti-value>
    </qti-correct-response>
  </qti-response-declaration>
  <qti-item-body>
    <p>Put these in order:</p>
    <qti-order-interaction response-identifier="RESPONSE">
      <qti-simple-choice identifier="A">First</qti-simple-choice>
      <qti-simple-choice identifier="B">Second</qti-simple-choice>
      <qti-simple-choice identifier="C">Third</qti-simple-choice>
    </qti-order-interaction>
  </qti-item-body>
  <qti-response-processing template="https://purl.imsglobal.org/spec/qti/v3p0/rptemplates/match_correct.xml"/>
</qti-assessment-item>''',
    prompt_instructions="""
For order interactions:
1. Use <qti-order-interaction> with response-identifier attribute
2. Create <qti-simple-choice> elements for each item to be ordered
3. Response declaration should have cardinality="ordered" and base-type="identifier"
""",
)

# Configuration for inline choice questions
inline_choice_config = QuestionConfig(
    type="inline-choice",
    example_xml='''<qti-assessment-item xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0" identifier="inline-choice-example" title="Inline Choice Example" adaptive="false" time-dependent="false">
  <qti-response-declaration identifier="RESPONSE" cardinality="single" base-type="identifier">
    <qti-correct-response><qti-value>ChoiceA</qti-value></qti-correct-response>
  </qti-response-declaration>
  <qti-item-body>
    <p>The capital of France is <qti-inline-choice-interaction response-identifier="RESPONSE">
      <qti-inline-choice identifier="ChoiceA">Paris</qti-inline-choice>
      <qti-inline-choice identifier="ChoiceB">London</qti-inline-choice>
      <qti-inline-choice identifier="ChoiceC">Berlin</qti-inline-choice>
    </qti-inline-choice-interaction>.</p>
  </qti-item-body>
  <qti-response-processing template="https://purl.imsglobal.org/spec/qti/v3p0/rptemplates/match_correct.xml"/>
</qti-assessment-item>''',
    prompt_instructions="""
For inline choice interactions:
1. Use <qti-inline-choice-interaction> with response-identifier attribute
2. Create <qti-inline-choice> elements for each option with unique identifiers
3. Place the interaction inline within text where the dropdown should appear
4. Response declaration should have cardinality="single" and base-type="identifier"
""",
)

# Configuration for select point questions
select_point_config = QuestionConfig(
    type="select-point",
    example_xml='''<qti-assessment-item xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0" identifier="select-point-example" title="Select Point Example" adaptive="false" time-dependent="false">
  <qti-response-declaration identifier="RESPONSE" cardinality="single" base-type="point">
    <qti-correct-response><qti-value>100 200</qti-value></qti-correct-response>
  </qti-response-declaration>
  <qti-item-body>
    <qti-select-point-interaction max-choices="1" response-identifier="RESPONSE">
      <qti-prompt><p>Mark the correct location on the image.</p></qti-prompt>
      <img alt="Image description" width="400" height="300" src="image.png"/>
    </qti-select-point-interaction>
  </qti-item-body>
  <qti-response-processing template="https://purl.imsglobal.org/spec/qti/v3p0/rptemplates/match_correct.xml"/>
</qti-assessment-item>''',
    prompt_instructions="""
For select point interactions:
1. Use <qti-select-point-interaction> with response-identifier and max-choices attributes
2. Include the image with src and alt attributes as a DIRECT CHILD of the interaction element
3. Response declaration should have cardinality="single" or "multiple"
4. Base-type should be "point"
""",
    post_process=select_point_post_process,
)

# Configuration for hot text questions
hot_text_config = QuestionConfig(
    type="hot-text",
    example_xml='''<qti-assessment-item xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0" identifier="hottext-example" title="Hot Text Example" adaptive="false" time-dependent="false">
  <qti-response-declaration identifier="RESPONSE" cardinality="single" base-type="identifier">
    <qti-correct-response><qti-value>word2</qti-value></qti-correct-response>
  </qti-response-declaration>
  <qti-item-body>
    <qti-hottext-interaction response-identifier="RESPONSE" max-choices="1">
      <qti-prompt>Select the word that best describes the main idea.</qti-prompt>
      <p>The <qti-hottext identifier="word1">quick</qti-hottext> brown fox <qti-hottext identifier="word2">jumped</qti-hottext> over the <qti-hottext identifier="word3">lazy</qti-hottext> dog.</p>
    </qti-hottext-interaction>
  </qti-item-body>
  <qti-response-processing template="https://purl.imsglobal.org/spec/qti/v3p0/rptemplates/match_correct.xml"/>
</qti-assessment-item>''',
    prompt_instructions="""
For hot text interactions:
1. Use <qti-hottext-interaction> with response-identifier and max-choices attributes
2. Wrap selectable text in <qti-hottext> elements with unique identifiers
3. Response declaration cardinality depends on how many text elements can be selected
""",
)

# Configuration for graphic gap match questions
graphic_gap_match_config = QuestionConfig(
    type="graphic-gap-match",
    example_xml='''<qti-assessment-item xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0" identifier="graphic-gap-match-example" title="Graphic Gap Match Example" adaptive="false" time-dependent="false">
  <qti-response-declaration identifier="RESPONSE" cardinality="multiple" base-type="directedPair">
    <qti-correct-response>
      <qti-value>item1 hotspot1</qti-value>
      <qti-value>item2 hotspot2</qti-value>
    </qti-correct-response>
  </qti-response-declaration>
  <qti-item-body>
    <qti-graphic-gap-match-interaction response-identifier="RESPONSE" max-associations="2">
      <img src="background.png" width="400" height="300" alt="Background image"/>
      <qti-gap-img identifier="item1" match-max="1">
        <img src="drag1.png" alt="Draggable item 1"/>
      </qti-gap-img>
      <qti-gap-img identifier="item2" match-max="1">
        <img src="drag2.png" alt="Draggable item 2"/>
      </qti-gap-img>
      <qti-associable-hotspot identifier="hotspot1" shape="rect" coords="10,10,100,100" match-max="1"/>
      <qti-associable-hotspot identifier="hotspot2" shape="rect" coords="200,10,300,100" match-max="1"/>
    </qti-graphic-gap-match-interaction>
  </qti-item-body>
  <qti-response-processing template="https://purl.imsglobal.org/spec/qti/v3p0/rptemplates/match_correct.xml"/>
</qti-assessment-item>''',
    prompt_instructions="""
For graphic gap match interactions:
1. Use <qti-graphic-gap-match-interaction> with response-identifier and max-associations
2. Add the background image using <img> directly as first child
3. For draggable options, use <qti-gap-img> or <qti-gap-text>
4. Define <qti-associable-hotspot> elements as drop zones
""",
)

# Configuration for media interaction questions
media_interaction_config = QuestionConfig(
    type="media-interaction",
    example_xml='''<qti-assessment-item xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0" identifier="media-example" title="Media Interaction Example" adaptive="false" time-dependent="false">
  <qti-response-declaration identifier="RESPONSE" cardinality="single" base-type="integer"/>
  <qti-item-body>
    <qti-media-interaction response-identifier="RESPONSE" autostart="false" max-plays="0">
      <video width="640" height="480" controls="controls">
        <source src="video.mp4" type="video/mp4"/>
      </video>
    </qti-media-interaction>
    <p>After watching the video, answer the following question:</p>
    <qti-choice-interaction response-identifier="ANSWER" max-choices="1">
      <qti-simple-choice identifier="A">Option A</qti-simple-choice>
      <qti-simple-choice identifier="B">Option B</qti-simple-choice>
    </qti-choice-interaction>
  </qti-item-body>
  <qti-response-processing template="https://purl.imsglobal.org/spec/qti/v3p0/rptemplates/match_correct.xml"/>
</qti-assessment-item>''',
    prompt_instructions="""
For media interactions:
1. Use <qti-media-interaction> with response-identifier attribute
2. Set appropriate attributes like autostart, loop, min-plays, and max-plays
3. Include either <audio> or <video> element with appropriate sources
""",
)

# Map of all question type configurations
QTI_TYPE_CONFIGS: dict[str, QuestionConfig] = {
    "choice": choice_config,
    "match": match_config,
    "text-entry": text_entry_config,
    "extended-text": extended_text_config,
    "composite": composite_config,
    "hotspot": hotspot_config,
    "gap-match": gap_match_config,
    "order": order_config,
    "inline-choice": inline_choice_config,
    "select-point": select_point_config,
    "hot-text": hot_text_config,
    "graphic-gap-match": graphic_gap_match_config,
    "media-interaction": media_interaction_config,
}


def get_question_config(question_type: str) -> QuestionConfig:
    """Get the configuration for a specific question type."""
    return QTI_TYPE_CONFIGS.get(question_type, choice_config)


def get_available_question_types() -> list[str]:
    """Get all available question types."""
    return list(QTI_TYPE_CONFIGS.keys())

