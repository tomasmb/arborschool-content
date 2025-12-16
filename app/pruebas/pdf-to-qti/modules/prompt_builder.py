"""
Prompt Builder

This module handles the creation of sophisticated prompts for:
- Question type detection
- QTI XML transformation
- Error correction and feedback

Similar to the HTML transformer's prompt creation logic
"""

from typing import Dict, Any, Optional
from .content_processing.content_processor import create_content_summary
import fitz # type: ignore # For Rect operations


def _get_text_from_block(block: Dict[str, Any]) -> str:
    """Extracts all text from spans within lines of a block."""
    block_text = []
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            block_text.append(span.get("text", ""))
    return " ".join(block_text).strip()


def _find_nearby_text_for_image(
    image_bbox_coords: list[float],
    image_page_num: int,
    all_document_blocks: list[Dict[str, Any]],
    max_vertical_gap: int = 50,  # Increased from 30 to capture more context
    min_horizontal_overlap_percentage: float = 0.1  # Reduced from 0.2 to be more inclusive
) -> str:
    """Finds text blocks near an image bbox and returns semantic context for placement."""
    context_texts = []
    img_rect = fitz.Rect(image_bbox_coords)

    # Collect text blocks with their relative positions
    text_blocks = []
    for block in all_document_blocks:
        if block.get("page_number") != image_page_num or block.get("type") != 0:
            continue

        text_bbox_coords = block.get("bbox")
        if not text_bbox_coords:
            continue
        
        text_rect = fitz.Rect(text_bbox_coords)
        text_content = _get_text_from_block(block)
        if not text_content.strip():
            continue

        # Check for horizontal overlap (more lenient)
        overlap_x0 = max(img_rect.x0, text_rect.x0)
        overlap_x1 = min(img_rect.x1, text_rect.x1)
        horizontal_overlap_width = overlap_x1 - overlap_x0
        min_width_for_overlap = min(img_rect.width, text_rect.width) * min_horizontal_overlap_percentage

        # Also include text that's horizontally close (not just overlapping)
        horizontal_distance = min(
            abs(text_rect.x1 - img_rect.x0),  # Text left of image
            abs(img_rect.x1 - text_rect.x0),  # Text right of image
            0 if horizontal_overlap_width >= min_width_for_overlap else float('inf')
        )

        if horizontal_overlap_width >= min_width_for_overlap or horizontal_distance < 100:
            # Calculate vertical relationship
            vertical_distance = min(
                abs(text_rect.y1 - img_rect.y0),  # Text above image
                abs(img_rect.y1 - text_rect.y0),  # Text below image
                0 if (text_rect.y0 <= img_rect.y1 and text_rect.y1 >= img_rect.y0) else float('inf')  # Overlapping
            )

            if vertical_distance <= max_vertical_gap:
                # Determine relationship
                relationship = "overlapping"
                if text_rect.y1 <= img_rect.y0:
                    relationship = "above"
                elif text_rect.y0 >= img_rect.y1:
                    relationship = "below"
                elif text_rect.x1 <= img_rect.x0:
                    relationship = "left"
                elif text_rect.x0 >= img_rect.x1:
                    relationship = "right"

                text_blocks.append({
                    'content': text_content.strip(),
                    'relationship': relationship,
                    'distance': vertical_distance,
                    'y_pos': text_rect.y0
                })

    # Sort by distance (closest first) and create semantic description
    text_blocks.sort(key=lambda x: x['distance'])
    
    if text_blocks:
        # Group by relationship
        above_texts = [t['content'] for t in text_blocks if t['relationship'] == 'above']
        below_texts = [t['content'] for t in text_blocks if t['relationship'] == 'below']
        side_texts = [t['content'] for t in text_blocks if t['relationship'] in ['left', 'right']]
        
        # Create semantic description
        context_parts = []
        
        if above_texts:
            above_combined = " ".join(above_texts[:2])  # Take up to 2 closest text blocks
            context_parts.append(f"Text above: '{above_combined}'")
            
        if below_texts:
            below_combined = " ".join(below_texts[:2])
            context_parts.append(f"Text below: '{below_combined}'")
            
        if side_texts:
            side_combined = " ".join(side_texts[:1])
            context_parts.append(f"Adjacent text: '{side_combined}'")
        
        # Analyze semantic meaning for placement hints
        all_text = " ".join([t['content'] for t in text_blocks[:3]]).lower()
        placement_hints = []
        
        if any(word in all_text for word in ['question', 'which', 'what', 'how', 'why', 'when', 'where']):
            placement_hints.append("appears to be part of question stem")
        if any(word in all_text for word in ['a)', 'b)', 'c)', 'd)', 'choice', 'option']):
            placement_hints.append("near answer choices")
        if any(word in all_text for word in ['diagram', 'figure', 'image', 'picture', 'shows', 'illustration']):
            placement_hints.append("referenced by text")
        if any(word in all_text for word in ['instruction', 'direction', 'note', 'consider']):
            placement_hints.append("part of instructions")
            
        result = " | ".join(context_parts)
        if placement_hints:
            result += f" | Context suggests: {', '.join(placement_hints)}"
            
        return result
    
    return "No nearby text context found"


def create_detection_prompt(pdf_content: Dict[str, Any]) -> str:
    """
    Create a sophisticated prompt for question type detection.
    
    Args:
        pdf_content: Extracted PDF content
        
    Returns:
        Detection prompt string
    """
    content_summary = create_content_summary(pdf_content)
    
    # Get basic content info without hardcoded keyword analysis
    combined_text = pdf_content.get('combined_text', '')
    text_length = len(combined_text)
    
    # Check for visual content
    has_images = bool(pdf_content.get('image_base64') or 
                     any(page.get('image_base64') for page in pdf_content.get('pages', [])))
    
    prompt = f"""
You are an expert in educational assessment formats, particularly QTI (Question and Test Interoperability).

Your task is to analyze the PDF question content and determine the most appropriate QTI 3.0 interaction type.

## PDF Content Analysis

### Extracted Text:
{combined_text}

### Content Summary:
{content_summary}

### Basic Info:
- Text length: {text_length} characters
- Has visual content: {has_images}

## Question Types
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
- IMPORTANT: If you see a question that looks like gap-match but has table structure with gaps inside table cells, classify it as "match" instead of "gap-match" because QTI 3.0 doesn't support gaps inside table cells.
- For table-based matching exercises where items in one column need to be matched with items in another column, use "match" interaction type.
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
- This is called a "composite item" and is fully supported in QTI 3.0

## Instructions
1. Analyze both the image and the extracted text to understand the question type and interactivity requirements
2. Apply the special classification rules for gap-match vs match interactions with tables
3. For multi-part questions, identify the DOMINANT interaction type or return "composite" as the question type
4. If the question cannot be properly represented by any of these types, indicate it as unsupported
5. Return your analysis in a JSON format ONLY:

{{
  "can_represent": true/false,
  "question_type": "one of the supported types, 'composite' for multi-part questions, or null if unsupported",
  "confidence": 0.0-1.0,
  "reason": "brief explanation of your decision",
  "key_elements": ["list", "of", "key", "interactive", "elements", "identified"],
  "potential_issues": ["any", "concerns", "about", "representation"]
}}

Your response should ONLY contain this JSON.
"""
    
    return prompt


def create_transformation_prompt(
    pdf_content: Dict[str, Any], 
    question_type: str, 
    question_config: Dict[str, str],
    validation_feedback: Optional[str] = None
) -> str:
    """
    Create a sophisticated prompt for QTI XML transformation.
    
    Uses the exact same proven structure from the HTML transformer.
    
    Args:
        pdf_content: Extracted PDF content (contains all images, including small ones, and page structure)
        question_type: Detected question type
        question_config: Configuration for the question type
        validation_feedback: Optional validation feedback for corrections
        
    Returns:
        Transformation prompt string
    """
    content_summary = create_content_summary(pdf_content)
    
    # Prepare all document blocks for nearby text search, adding page_number to top-level blocks if not already there
    # This assumes pdf_content["pages"][page_num]["structured_text"]["blocks"] is the source of truth
    all_doc_blocks_with_page_info = []
    for i, page_data in enumerate(pdf_content.get("pages", [])):
        page_blocks = page_data.get("structured_text", {}).get("blocks", [])
        for block in page_blocks:
            block_copy = block.copy()
            block_copy["page_number"] = i # Ensure page_number is at block level
            all_doc_blocks_with_page_info.append(block_copy)

    large_images_for_prompt = []
    if pdf_content.get('all_images'): # 'all_images' comes from extract_pdf_content, has page_number
        for img_data in pdf_content['all_images']:
            width = int(img_data.get('width', 0))
            height = int(img_data.get('height', 0))
            
            # Using a slightly more relaxed area filter for prompt inclusion, 
            # as even moderately sized images might be contextually important for LLM
            # Include choice images regardless of size
            if width * height > 5000 or img_data.get('is_choice_diagram'): # Example: 50x100 or 70x70. Original was 10000.
                placeholder = img_data.get('image_base64') 
                if placeholder and placeholder.startswith("CONTENT_PLACEHOLDER_"):
                    img_page_num = img_data.get('page_number', 0)
                    page_dims = pdf_content.get("pages", [])[img_page_num] if img_page_num < len(pdf_content.get("pages", [])) else {}
                    page_w = page_dims.get("width", 612) # Default to standard PDF width
                    page_h = page_dims.get("height", 792) # Default to standard PDF height

                    nearby_text = _find_nearby_text_for_image(
                        img_data.get('bbox', [0,0,0,0]),
                        img_page_num,
                        all_doc_blocks_with_page_info, # Pass all blocks from all pages
                    )
                    
                    # Determine image type and description
                    alt_suggestion = f"Image {len(large_images_for_prompt) + 1} (size {width}x{height})"
                    
                    large_images_for_prompt.append({
                        'placeholder': placeholder,
                        'width': width,
                        'height': height,
                        'bbox': img_data.get('bbox', [0,0,0,0]),
                        'page_number': img_page_num,
                        'alt_suggestion': alt_suggestion,
                        'nearby_text': nearby_text
                    })

    image_info = ""
    if large_images_for_prompt:
        image_info = "\n## Relevant Extracted Images (Diagrams/Figures)\n"
        
        # The incoming images are already sorted by reading order. Do not re-sort.
        images_in_order = large_images_for_prompt
        
        image_info += f"Found {len(images_in_order)} image(s) in logical reading order:\n"
        for i, img_details in enumerate(images_in_order):
            bbox_coords = img_details['bbox']
            page_num = img_details['page_number']
            width = img_details['width']
            height = img_details['height']
            nearby_text_info = img_details.get('nearby_text', 'No nearby text context found.')
            
            # Determine position description for better placement
            y_pos = bbox_coords[1]
            page_height = 792  # Standard PDF height, could be improved with actual page dimensions
            position_desc = "middle"
            if y_pos < page_height * 0.3:
                position_desc = "top"
            elif y_pos > page_height * 0.7:
                position_desc = "bottom"
            
            image_info += (f"  Image {i+1}: Use placeholder '{img_details['placeholder']}'. "
                           f"Location: Page {page_num+1}, Position: {position_desc} of page, Size: {width}x{height}. "
                           f"Contextual Text: {nearby_text_info}. "
                           f"Alt text: '{img_details['alt_suggestion']}'.\n")
        
        image_info += ("\n## Image Placement Guidelines:\n"
                       "- **READING ORDER**: Place images in the SAME ORDER as listed above (Image 1 first, then Image 2, etc.) Try to infer the logical flow of the question.\\n"
                       "- **CONTEXTUAL PLACEMENT**: Use the 'Contextual Text' and your understanding of the question to determine WHERE each image belongs. Look for explicit references like 'see Figure 1', 'the diagram shows', or implicit needs for an image to understand a part of the text.\\n"
                       "  * If an image is referenced (e.g., 'As shown in the diagram...'), place it immediately after the sentence or paragraph containing that reference.\\n"
                       "  * If contextual text is part of the general question stem → place image generally AFTER the main question text but BEFORE answer choices, unless a more specific reference exists.\\n"
                       "  * If contextual text is clearly related to a specific answer choice → consider if the image should be near that choice (though typically images are part of the stem or general context).\\n"
                       "  * If contextual text consists of instructions that refer to the image → place image appropriately to make those instructions clear.\\n"
                       "- **SEMANTIC LOGIC**: Images should appear where they make the most sense for a student reading and answering the question. The flow should be natural.\\n"
                       "- **MULTIPLE IMAGES**: If multiple images exist, maintain their relative order (Image 1 before Image 2) but place each in its most logical semantic location within the question body.\\n"
                       "- **DEFAULT PLACEMENT**: If absolutely unclear, place images immediately after the main question prompt/text but before any answer choices or interaction elements.\\n")
    elif pdf_content.get('has_extracted_images'):
        image_info = "\n## Visual Content\n"
        image_info += "The PDF contains extracted images. If they are part of the question, include them using descriptive placeholder filenames like 'image1.png'.\n"
    else:
        image_info = "\n## Visual Content\n"
        image_info += "No significant visual content detected or provided for transformation.\n"
    
    retry_context = ""
    if validation_feedback:
        retry_context = f"\n\n## RETRY ATTEMPT CONTEXT\nThis is correction attempt. Previous attempt failed validation. Please:\n"
        retry_context += "- Pay extra attention to the specific validation errors listed below\n"
        retry_context += "- Be more conservative in your changes - make only the minimal fixes needed\n"
        retry_context += "- Double-check that all QTI 3.0 namespace and element requirements are met\n"
        retry_context += "- Ensure all attributes are properly quoted and elements properly closed\n"
        retry_context += "- THIS IS THE FINAL ATTEMPT - be extra careful and thorough\n"

    image_context_instructions = ""
    if "img" in pdf_content.get('combined_text', '').lower() or "__IMAGE_PLACEHOLDER_" in pdf_content.get('combined_text', ''):
        image_context_instructions = "\n\n## Image Handling:\n"
        image_context_instructions += "- Preserve all <img> tags and their structure exactly as they appear\n"
        image_context_instructions += "- Do NOT modify image src attributes or placeholders\n"
        image_context_instructions += "- Keep multiple images separate if they exist\n"

    # Check if we have visual choices
    has_choice_images = pdf_content.get('is_choice_diagram', False) or any(
        img.get('is_choice_diagram', False) for img in pdf_content.get('all_images', [])
    )
    
    visual_choice_instructions = ""
    if has_choice_images:
        visual_choice_instructions = """
## CRITICAL: Visual Choice Handling
**This question has CHOICE IMAGES (visual answer options):**
- Each choice should contain ONLY an image, NO text content
- Use format: `<qti-simple-choice identifier="ChoiceA"><img src="choice_image_placeholder" alt="Descriptive alt text for choice A"/></qti-simple-choice>`
- Alt text should describe what the choice shows (e.g., "Graph showing linear relationship between mass and kinetic energy")
- Do NOT mix text and images in choices - choices should be image-only
"""

    prompt = f"""You are an expert at converting educational content into QTI 3.0 XML format.

## Task
Convert the provided question content into valid QTI 3.0 XML format using the "{question_type}" interaction type.

## CRITICAL: Character Encoding and Special Characters
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

## Shared Context Handling
**IMPORTANT**: The provided content may include introductory text, figures, or tables that are shared across multiple questions.
- You MUST include all such shared context in the QTI XML for this question.
- Do NOT omit any information you think might be from a shared context block.
- If you see a passage or figure, and then a question that refers to it, both the passage/figure and the question must be in the output.

## Avoid adding cross question text
If there is text at the beggining that references other questions, do not add it to the QTI XML.
Example: "Use the information below to answer the three following questions". Avoid adding this to the QTI XML.

## Avoid Repetition
**DO NOT duplicate or repeat any text content**. Each piece of text should appear exactly once in the QTI XML.
Specifically, the main question text should not be present in both a `<qti-prompt>` and also within a `<p>` tag in the item body.

{retry_context}

## Content to Convert
{content_summary}

NOTE: Exclude page headers/footers, question numbers, test instructions or directions, fragments from other questions, and navigation elements.
IMPORTANT: Include any question-specific formatting or response instructions (e.g., "use complete sentences", "no bulleted lists").
IMPORTANT: If instructions refer to physical answering methods (e.g., "fill in the circles on the answer grid"), adapt or remove them to match the digital QTI interaction, as the physical answering elements have likely been removed.

{image_info}

## Question Type: {question_type}
{question_config.get('promptInstructions', '')}{visual_choice_instructions}

## CRITICAL: Choice Label Handling
For choice interactions (A, B, C, D, etc.):
- **Remove choice labels from choice text**: If the original content contains "A. This is the answer", the QTI choice text should only contain "This is the answer"
- **Do NOT include** the letter labels (A., B., C., D.) or numbers (1., 2., 3., 4.) in the <qti-simple-choice> text content
- **Preserve choice order**: Keep choices in their original sequence, but remove the prefixed labels
- **Use semantic identifiers**: Use identifiers like "ChoiceA", "ChoiceB", "ChoiceC", "ChoiceD" in the identifier attributes
- **Example**: Original "A. The sky is blue" becomes `<qti-simple-choice identifier="ChoiceA">The sky is blue</qti-simple-choice>`

## CRITICAL: Table Handling
If the content includes structured table data (marked with HTML table tags), you MUST:
- **Preserve table structure** in the QTI XML using proper HTML table elements
- **Do NOT convert tables to images** - use the provided HTML table content directly
- **Wrap tables in appropriate elements** like `<div>` or within question text
- **Ensure table accessibility** with proper `<thead>`, `<tbody>`, `<th>`, and `<td>` elements
- **Maintain table relationships** - if the question asks about table data, ensure the table is placed logically in relation to the question text
- If a table is represented as a structured HTML table, do NOT also include it as an image.

## CRITICAL: Text in Images
- If text is part of an essential image (e.g., labels on a diagram), that text should NOT be repeated in the `<qti-item-body>` as text. The image's alt text should describe the image including its text.
- Conversely, if a piece of text is rendered in the body, it should have been removed from any accompanying image. The goal is to avoid information duplication.

## Requirements for Description Field (only description field, not the QTI XML)
The "description" field must be extremely detailed and comprehensive - someone should be able to recreate the a semantically equivalent question from the description alone without seeing the original content.

Example of a detailed description:
"Multiple choice question about genetic variation in animals. Shows a photograph of six different bulldog puppies sitting together, demonstrating visible differences in coat color, size, and facial features despite being from the same litter. The question asks why puppies from the same parents don't look identical, with four answer choices: A) they were produced by asexual cloning, B) some puppies have genetic material from only one parent, C) each puppy has a different combination of genetic material from sexual reproduction, D) all puppies developed from the same fertilized egg."

## CRITICAL: For Images in QTI XML
- If images are listed above, you MUST use their exact placeholder strings in <img src="..."> tags
- Do NOT use generic filenames like "image1.png" 
- Use the EXACT placeholder strings provided (e.g., "CONTENT_PLACEHOLDER_P0")
- Each placeholder corresponds to a specific extracted image that will be restored later
- **IMPORTANT**: Use simple <img> tags within <p> or <div> elements, NOT <qti-figure> elements
- Images should be wrapped in block elements like: <p><img src="placeholder" alt="description"/></p>

## CRITICAL: QTI XML Structure Rules
- **DO NOT use <qti-figure>** - use <img> tags within <p> or <div> instead
- Images must be inside block elements (p, div) not standalone
- All content must be within the <qti-item-body> section
- Interaction elements go after content, before </qti-item-body>

## XML Validation Checklist (verify before finalizing)
- [ ] Root element <qti-assessment-item> is properly opened and closed
- [ ] All nested elements have matching closing tags
- [ ] No <qti-figure> elements used (use <img> in <p> or <div> instead)
- [ ] All images listed in 'Relevant Extracted Images' (if any) are included using their EXACT placeholders (e.g., CONTENT_PLACEHOLDER_P0) if they are part of the question
- [ ] All images are wrapped in block elements like <p> or <div> (e.g., <p><img src="placeholder" alt="description"/></p>)
- [ ] Meaningful alt text is provided for all images (use or adapt the 'alt_suggestion')
- [ ] Images are placed in the logical reading order and at semantically appropriate locations based on the guidelines
- [ ] <qti-response-processing> is self-closed with /> syntax (e.g., <qti-response-processing template="..."/>)
- [ ] All attributes (e.g., src, alt, identifier, title) are properly quoted
- [ ] Interaction elements (e.g., <qti-choice-interaction>) are correctly placed within <qti-item-body> and after relevant content

## Question Content and Fidelity Checklist (verify semantic accuracy)
- [ ] All question text (stem, prompts, context, instructions) from the original content is accurately and completely included in the <qti-item-body>.
- [ ] No text is repeated between <p>, <div>, and <qti-prompt> elements. Each sentence or phrase appears only once in the QTI XML.
- [ ] All answer choices, options, or interactive elements described in the original content are present and accurately transcribed within the appropriate QTI interaction structure.
- [ ] The question's core meaning, intent, and level of difficulty are preserved from the original PDF content.
- [ ] No extraneous or irrelevant information (e.g., page numbers, headers/footers from the PDF, content from unrelated questions) has been included in the <qti-item-body>.
- [ ] The 'description' field in your JSON response is detailed, comprehensive, and accurately summarizes the question, its components, and any included imagery as per the requirements.

## Response Format
You must respond with valid JSON containing:
- title: Clear, descriptive title
- description: Extremely detailed description (as specified above)
- qti_xml: Complete, valid QTI 3.0 XML
- key_features: Array of key QTI features implemented
- notes: Any important implementation details

{image_context_instructions}

Example QTI XML for reference:
{question_config.get('exampleXml', '')}

Ensure your QTI XML follows QTI 3.0 standards exactly and includes proper namespaces, identifiers, and response processing."""
    
    return prompt


def create_error_correction_prompt(
    qti_xml: str,
    validation_errors: str,
    question_type: str,
    retry_attempt: int = 1,
    max_attempts: int = 3
) -> str:
    """
    Create a prompt for correcting QTI XML validation errors.
    
    Args:
        qti_xml: Invalid QTI XML (potentially with base64 embedded images)
        validation_errors: Validation error messages
        question_type: Question type for context
        original_pdf_content: Original PDF content to give context about images if needed
        retry_attempt: Current attempt number (1-based)
        max_attempts: Maximum number of attempts
        
    Returns:
        Error correction prompt
    """
    image_context_instructions = ""
    # Since we're stripping base64 images and using simple placeholders,
    # we only need minimal instructions about preserving structure
    if "img" in qti_xml.lower() or "__IMAGE_PLACEHOLDER_" in qti_xml:
        image_context_instructions = "\n\n## EXTREMELY CRITICAL: Image Handling:\n"
        image_context_instructions += "- Preserve all <img> tags and their structure exactly as they appear\n"
        image_context_instructions += "- Do NOT modify image src attributes or placeholders\n"
        image_context_instructions += "- Keep multiple images separate if they exist\n"

    # Add retry context
    retry_context = ""
    if retry_attempt > 1:
        retry_context = f"\n\n## RETRY ATTEMPT CONTEXT\nThis is correction attempt {retry_attempt} of {max_attempts}. Previous attempt(s) failed validation. Please:\n"
        retry_context += "- Pay extra attention to the specific validation errors listed below\n"
        retry_context += "- Be more conservative in your changes - make only the minimal fixes needed\n"
        retry_context += "- Double-check that all QTI 3.0 namespace and element requirements are met\n"
        retry_context += "- Ensure all attributes are properly quoted and elements properly closed\n"
        if retry_attempt == max_attempts:
            retry_context += "- THIS IS THE FINAL ATTEMPT - be extra careful and thorough\n"

    prompt = f"""
You are an expert in QTI 3.0 XML. You will be given an invalid QTI XML document and a list of validation error messages.

Your task is to fix the XML to make it valid according to the QTI 3.0 schema while preserving all content and functionality.

## Question Type Context
This is a "{question_type}" type question.
{retry_context}
## Invalid QTI XML
```xml
{qti_xml}
```

## Validation Errors
{validation_errors}
{image_context_instructions}
## Instructions
1. Carefully analyze the validation errors and the XML structure.
2. **CRITICAL XML STRUCTURE FIXES**:
   - If the error mentions "qti-assessment-item must be terminated", check that the root element is properly closed with </qti-assessment-item> at the very end
   - Ensure ALL opening tags have matching closing tags
   - The <qti-response-processing> element should be self-closed with /> (e.g., <qti-response-processing template="..."/>)
   - Check for any missing or malformed closing tags
   - Verify proper XML hierarchy and nesting
3. PRESERVE image placeholders (like __IMAGE_PLACEHOLDER_N__) exactly as they appear.
4. Correct ONLY the specific validation errors reported. Do NOT restructure or simplify other parts of the XML (like image tags or their content) unless an error forces you to.
5. Ensure all original text, choices, image data (if any), and interactive elements are preserved EXACTLY as they were, unless the error is directly related to them.
6. The goal is minimal valid changes. If multiple images were present, keep them separate.
7. **XML VALIDATION CHECKLIST** - Before finalizing, verify:
   - [ ] Root element <qti-assessment-item> is properly opened and closed
   - [ ] All nested elements are properly closed (e.g., <p>...</p>, <qti-simple-choice>...</qti-simple-choice>)
   - [ ] Self-closing elements use /> syntax correctly (e.g., <qti-response-processing .../>, <img .../> if not including alt text as content)
   - [ ] No unclosed tags remain
   - [ ] All attributes are properly quoted
   - [ ] Image placeholders (e.g., __IMAGE_PLACEHOLDER_N__ or CONTENT_PLACEHOLDER_P0) in <img> src attributes remain unchanged from the input XML
   - [ ] Changes made directly address the listed validation errors and minimize unrelated modifications
8. **SPECIFIC FIX FOR "must be terminated" ERRORS**:
   - Count opening and closing tags to ensure they match for all elements, especially the root <qti-assessment-item>
   - Look for any truncated or incomplete XML at the end
   - Ensure the very last characters of your XML are ></qti-assessment-item>
   - Check for any hidden characters or formatting issues
9. Return a JSON object containing the corrected QTI XML:

{{
  "qti_xml": "The corrected and valid QTI 3.0 XML as a string"
}}

Make sure your response ONLY contains this JSON.
"""
    
    return prompt


def create_visual_comparison_prompt() -> str:
    """
    Create a prompt for visual comparison between original PDF and rendered QTI.
    
    Returns:
        Visual comparison prompt string
    """
    return """
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