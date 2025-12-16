"""
AI Content Analyzer

This module implements the two-step LLM approach from converter guidelines:
1. Analyze PDF content to determine QTI 3.0 compatibility  
2. Provide intelligent content categorization for image extraction

Follows guideline #13: Prefer LLM analysis over text matching or 'dumb' methods.
"""

import base64
import fitz  # type: ignore
from typing import Dict, Any, List, Optional, Tuple
from .llm_client import chat_completion


def analyze_pdf_content_with_ai(
    page: fitz.Page,
    structured_data: Dict[str, Any],
    openai_api_key: str
) -> Dict[str, Any]:
    """
    Complete AI-powered analysis of PDF content following converter guidelines.
    
    Two-step approach:
    1. Assess QTI 3.0 compatibility 
    2. Categorize content for intelligent extraction
    
    Args:
        page: PyMuPDF page object
        structured_data: PyMuPDF structured text data
        openai_api_key: OpenAI API key
        
    Returns:
        Dictionary with compatibility assessment and content categorization
    """
    try:
        # Extract text blocks for analysis
        text_blocks = extract_text_blocks_for_analysis(structured_data)
        
        # Get page image for visual context
        page_image_bytes = get_page_image_for_ai(page)
        page_image_base64 = base64.b64encode(page_image_bytes).decode('utf-8')
        
        # Step 1: Analyze QTI compatibility and visual content needs
        compatibility_result = assess_qti_compatibility(
            text_blocks, page_image_base64, openai_api_key
        )
        
        # Step 2: If visual content is needed, categorize blocks intelligently
        categorization_result = {}
        if compatibility_result.get('visual_content_required', False):
            categorization_result = categorize_content_blocks(
                text_blocks, page_image_base64, openai_api_key
            )
        
        return {
            "success": True,
            "compatibility": compatibility_result,
            "categorization": categorization_result,
            "ai_categories": categorization_result.get("block_categories", {}),
            "has_visual_content": compatibility_result.get('visual_content_required', False)
        }
        
    except Exception as e:
        print(f"🧠 ⚠️ AI content analysis failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "compatibility": {},
            "categorization": {},
            "ai_categories": {},
            "has_visual_content": False
        }


def assess_qti_compatibility(
    text_blocks: List[Dict[str, Any]],
    page_image_base64: str,
    openai_api_key: str
) -> Dict[str, Any]:
    """
    Step 1: Use GPT-5.1 to assess if content can be represented in QTI 3.0.
    Following guideline #7: Two-step LLM approach.
    
    GPT-5.1 provides better spatial reasoning for document layout understanding.
    """
    
    # Prepare content summary for AI
    content_summary = prepare_content_summary(text_blocks)
    
    prompt = f"""Analyze this educational content to determine QTI 3.0 compatibility.

CONTENT SUMMARY:
{content_summary}

ASSESSMENT CRITERIA:
1. Can this be represented accurately in QTI 3.0 standard interaction types?
2. Does it contain any visual content (images, diagrams, maps)? If so, this visual content should be required. Tables are not considered visual content.
3. What interaction type would be most appropriate?
4. How complex is the content structure?

Supported QTI types: choice, match, text-entry, hotspot, extended-text, 
hot-text, gap-match, order, graphic-gap-match, inline-choice, select-point, media-interaction,
composite

Provide assessment with confidence score (0.0-1.0).

Respond with JSON in this format:
{{
    "can_represent": boolean,
    "visual_content_required": boolean,
    "question_type": "string or null",
    "confidence": number,
    "reasoning": "string explanation"
}}"""

    try:
        messages = [
            {
                "role": "system", 
                "content": "You are an expert in educational assessment and QTI 3.0 standards. Analyze content for QTI compatibility. Respond only with valid JSON."
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{page_image_base64}"}}
                ]
            }
        ]
        
        # Use unified LLM client (Gemini default, OpenAI fallback)
        response_text = chat_completion(
            messages=messages,
            api_key=openai_api_key,  # Will use GEMINI_API_KEY or OPENAI_API_KEY from env
            json_only=True,
            reasoning_effort="high",
        )
        
        # Parse structured JSON response
        analysis = parse_compatibility_response(response_text)
        
        print(f"🧠 QTI Compatibility: {analysis.get('can_represent', False)}")
        print(f"   Visual content required: {analysis.get('visual_content_required', False)}")
        
        return analysis
        
    except Exception as e:
        print(f"🧠 ⚠️ QTI compatibility assessment failed: {e}")
        return {"can_represent": False, "visual_content_required": False}


def categorize_content_blocks(
    text_blocks: List[Dict[str, Any]],
    page_image_base64: str,
    openai_api_key: str
) -> Dict[str, Any]:
    """
    Step 2: Intelligently categorize text blocks for image extraction.
    Following guideline #3: Build image BBOX using surrounding blocks with AI.
    
    Uses GPT-5.1 for better spatial reasoning and layout understanding.
    """
    
    # Prepare block information for AI
    block_info = []
    for i, block in enumerate(text_blocks):
        block_info.append({
            "block_number": i + 1,
            "text": block["text"][:200],  # Limit text length for efficiency
            "bbox": block["bbox"],
            "area": block["area"]
        })
    
    prompt = f"""Categorize text blocks on this educational page for intelligent image extraction.

TEXT BLOCKS:
{block_info}

CATEGORIES:
- "question_text": Main question stems, instructions, introductory text
- "answer_choice": Multiple choice options (A, B, C, D, etc.)  
- "visual_content_title": Titles or captions for visual content
- "visual_content_label": Geographic labels, numbers, annotations on visual content
- "other_label": Source citations, compass directions, legends

GOAL: Identify which blocks are separate from visual content (question_text, answer_choice) 
vs. which are part of visual content (visual_content_title, visual_content_label, other_label).

Respond with JSON in this format:
{{
    "has_visual_content": boolean,
    "visual_description": "string",
    "block_categories": {{
        "1": "category_name",
        "2": "category_name"
    }}
}}"""

    try:
        import openai
        
        messages = [
            {
                "role": "system",
                "content": "You are an expert in educational content analysis. Categorize text blocks for intelligent image extraction. Respond only with valid JSON."
            },
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{page_image_base64}"}}
                ]
            }
        ]
        
        client = openai.OpenAI(api_key=openai_api_key)
        response = client.chat.completions.create(
            model="gpt-5.1",
            messages=messages,
            response_format={"type": "json_object"},
            reasoning_effort="high",
            seed=42,
        )
        
        # Parse categorization response
        response_text = response.choices[0].message.content
        categorization = parse_categorization_response(response_text, len(text_blocks))
        
        print(f"🧠 Content categorization: {len(categorization)} blocks categorized")
        
        return {
            "block_categories": categorization,
            "question_answer_blocks": [
                i for i, cat in categorization.items() 
                if cat in ["question_text", "answer_choice"]
            ],
            "image_related_blocks": [
                i for i, cat in categorization.items()
                if cat in ["visual_content_title", "visual_content_label", "other_label"]  
            ]
        }
        
    except Exception as e:
        print(f"🧠 ⚠️ Content categorization failed: {e}")
        return {"block_categories": {}, "question_answer_blocks": [], "image_related_blocks": []}


def extract_text_blocks_for_analysis(structured_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract and prepare text blocks for AI analysis."""
    blocks = structured_data.get("blocks", [])
    text_blocks = []
    
    for i, block in enumerate(blocks):
        if block.get("type") == 0:  # Text block
            bbox = block.get("bbox", [])
            if len(bbox) >= 4:
                # Extract text content
                block_text = ""
                for line in block.get('lines', []):
                    for span in line.get('spans', []):
                        block_text += span.get('text', '') + " "
                block_text = block_text.strip()
                
                if block_text:  # Only include blocks with actual text
                    text_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                    text_blocks.append({
                        "block_number": i + 1,
                        "text": block_text,
                        "bbox": bbox,
                        "area": text_area
                    })
    
    return text_blocks


def get_page_image_for_ai(page: fitz.Page, scale: float = 1.5) -> bytes:
    """Get page image optimized for AI analysis."""
    try:
        matrix = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        return pix.tobytes("png")
    except Exception as e:
        print(f"⚠️ Error getting page image: {e}")
        # Return minimal placeholder
        return b""


def prepare_content_summary(text_blocks: List[Dict[str, Any]]) -> str:
    """Prepare a concise summary of content for AI analysis."""
    if not text_blocks:
        return "No text content found."
    
    all_text = " ".join(block["text"] for block in text_blocks)
    
    # Limit text length for API efficiency
    if len(all_text) > 2000:
        all_text = all_text[:2000] + "..."
    
    return f"""Text content ({len(text_blocks)} blocks):
{all_text}

Block count: {len(text_blocks)}
Total text length: {len(all_text)} characters"""


def parse_compatibility_response(response_text: str) -> Dict[str, Any]:
    """Parse AI compatibility assessment response from structured JSON."""
    try:
        import json
        result = json.loads(response_text)
        
        # Validate and extract fields
        can_represent = result.get("can_represent", False)
        visual_required = result.get("visual_content_required", False)
        question_type = result.get("question_type")
        confidence = result.get("confidence", 0.8)
        reasoning = result.get("reasoning", "")
        
        # Validate question type
        valid_types = ["choice", "match", "text-entry", "hotspot", "extended-text", 
                      "hot-text", "gap-match", "order", "graphic-gap-match", 
                      "inline-choice", "select-point", "media-interaction", "composite"]
        
        if question_type and question_type not in valid_types:
            question_type = None
            can_represent = False
        
        return {
            "can_represent": can_represent,
            "visual_content_required": visual_required,
            "question_type": question_type,
            "confidence": confidence,
            "reasoning": reasoning
        }
        
    except json.JSONDecodeError as e:
        print(f"🧠 ⚠️ Failed to parse compatibility JSON: {e}")
        return {
            "can_represent": False,
            "visual_content_required": False,
            "question_type": None,
            "confidence": 0.0,
            "reasoning": "Failed to parse AI response"
        }


def parse_categorization_response(response_text: str, num_blocks: int) -> Dict[int, str]:
    """Parse AI categorization response from structured JSON."""
    try:
        import json
        result = json.loads(response_text)
        
        block_categories = result.get("block_categories", {})
        categorization = {}
        
        # Convert string keys to integers and validate categories
        valid_categories = ["question_text", "answer_choice", "visual_content_title", "visual_content_label", "other_label"]
        
        for block_str, category in block_categories.items():
            try:
                block_num = int(block_str)
                if 1 <= block_num <= num_blocks and category in valid_categories:
                    categorization[block_num] = category
            except (ValueError, TypeError):
                continue
        
        # Fill in any missing blocks with default category
        for i in range(1, num_blocks + 1):
            if i not in categorization:
                categorization[i] = "other_label"
        
        return categorization
        
    except json.JSONDecodeError as e:
        print(f"🧠 ⚠️ Failed to parse categorization JSON: {e}")
        # Fallback to default categorization
        return {i: "other_label" for i in range(1, num_blocks + 1)} 