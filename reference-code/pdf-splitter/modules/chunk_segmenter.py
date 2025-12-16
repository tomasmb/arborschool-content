"""
PDF Question Segmentation using OpenAI's Direct PDF Upload
Leverages OpenAI's native PDF processing with vision and text extraction
"""

import os
import json
import base64
from typing import List, Dict, Any, Optional
from openai import OpenAI

# OpenAI client will be initialized lazily
client = None

def get_openai_client() -> OpenAI:
    """Get or initialize OpenAI client with API key from environment."""
    global client
    if client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        client = OpenAI(api_key=api_key)
    return client

# JSON Schema for structured output
SEGMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Unique identifier for the question"},
                    "text": {"type": "string", "description": "Full text of the question"},
                    "start_marker": {"type": "string", "description": "Start marker - the first 10 words of the segment text or coordinates in format 'x,y' (in PDF points)"},
                    "page_nums": {"type": "array", "items": {"type": "integer", "minimum": 1}, "description": "1-based pages where question appears"},
                    "type": {"type": "string", "enum": ["question", "sub_question"], "description": "Question type"},
                    "multi_page": {"type": "boolean", "description": "Whether question spans multiple pages"},
                    "multi_question_references": {
                        "type": "array",
                        "items": {"type": "string", "description": "ID of a multi-question reference used by this question"},
                        "description": "IDs of multi-question references used by this question"
                    }
                },
                "required": ["id", "text", "start_marker", "page_nums", "type", "multi_page", "multi_question_references"],
                "additionalProperties": False
            }
        },
        "multi_question_references": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Unique identifier for the reference"},
                    "type": {"type": "string", "enum": ["citation", "figure", "table", "footnote"], "description": "Reference type"},
                    "text": {"type": "string", "description": "Full text content of the reference"},
                    "start_marker": {"type": "string", "description": "Start marker for segment"},
                    "page_nums": {"type": "array", "items": {"type": "integer", "minimum": 1}, "description": "1-based pages where reference appears"},
                    "question_ids": {
                        "type": "array",
                        "items": {"type": "string", "description": "ID of a question that uses this reference"},
                        "description": "IDs of questions that use this multi-question reference"
                    }
                },
                "required": ["id", "type", "text", "start_marker", "page_nums", "question_ids"],
                "additionalProperties": False
            }
        },
        "unrelated_content_segments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Unique identifier for the unrelated content segment"},
                    "type": {"type": "string", "enum": ["cover_page", "general_instructions", "other"], "description": "Type of unrelated content"},
                    "text": {"type": "string", "description": "Full text content of the unrelated segment"},
                    "start_marker": {"type": "string", "description": "Start marker for segment"},
                    "page_nums": {"type": "array", "items": {"type": "integer", "minimum": 1}, "description": "1-based pages where unrelated content appears"}
                },
                "required": ["id", "type", "text", "start_marker", "page_nums"],
                "additionalProperties": False
            }
        }
    },
    "required": ["questions", "multi_question_references", "unrelated_content_segments"],
    "additionalProperties": False
}

# Chain-of-Thought system prompt for reliable segmentation
SEGMENT_PROMPT = """
You are an expert at segmenting educational test PDFs. Return only validated JSON without explanation.

CRITICAL: When returning the `text` field for any segment, include ONLY the first 50 words (or full text if shorter).

## Segment Types

**QUESTIONS**: Complete test questions including all parts (A, B, C), answer choices, answer spaces, and any reference material used ONLY by this question.

**MULTI-QUESTION REFERENCES**: Content shared by multiple questions (tables, figures, passages, citations that appear before multiple questions).

**UNRELATED CONTENT**: Cover pages, general test instructions, section introductions unrelated to specific questions.

## Core Rules

1. **Complete Coverage**: Every part of the PDF must belong to exactly one segment
2. **Self-Contained Questions**: Each question must include all content needed to answer it
3. **Reference Sharing**: If content is used by multiple questions, make it a multi-question reference
4. **Sequential Pages**: Use PDF page order (1, 2, 3...) not printed page numbers
5. **Start Markers**: Use the very first words that appear in each segment

## Question Identification

- Single questions can span multiple pages
- Multiple questions can appear on one page (create separate segments)
- Question parts (A, B, C) belong to the same question segment
- Include question-specific instructions and single-use references
- If a question references "the passage below" or "Figure 2", that content must be in the question segment UNLESS it's used by other questions
- **CRITICAL**: When reference material or question instructions appear before a question number, the start marker must be the beginning of that reference material or question instructions, not the question number. Always scan backwards from question numbers to find any preceding content.

## Multi-Question Reference Rules

- Only create if used by 2+ questions
- Group consecutive references with no questions between them
- Associate each reference with all questions that use it
- Don't duplicate reference content in question segments

## Process

1. **Scan**: Identify all questions, references, and unrelated content
2. **Boundaries**: Determine start/end of each segment (no gaps, no overlaps)
3. **Associations**: Link questions to their multi-question references
4. **Validation**: Ensure every question is self-contained

## IDs and Markers

- Questions: Q1, Q2, Q3... (or Q1.1, Q1.2 for subsections)
- References: R1, R2, R3...
- Unrelated: UC1, UC2, UC3...
- Start markers: First words of each segment - for questions with preceding references, content or instructions, use the reference intro, not the question number

Return the JSON with all segments properly identified and associated.
"""

def segment_pdf_document(pdf_path: str) -> Dict[str, Any]:
    """
    Segment PDF using OpenAI's direct PDF upload feature.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Dictionary containing questions and references with metadata
    """
    try:
        print(f"Processing PDF: {pdf_path}")
        
        # Get OpenAI client (lazy initialization)
        openai_client = get_openai_client()
        
        # Upload PDF file to OpenAI
        with open(pdf_path, 'rb') as pdf_file:
            file_response = openai_client.files.create(
                file=pdf_file,
                purpose="user_data"
            )
        
        print(f"PDF uploaded with ID: {file_response.id}")
        
        # Process PDF with direct file input and chain-of-thought
        completion = openai_client.chat.completions.create(
            model="o4-mini-2025-04-16",  # Use o4-mini with vision capability
            messages=[
                {"role": "system", "content": SEGMENT_PROMPT},
                {"role": "user", "content": [
                    {"type": "file", "file": {"file_id": file_response.id}},
                    {"type": "text", "text": "Please segment this PDF into question and reference segments as instructed."}
                ]}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "pdf_segmentation",
                    "schema": SEGMENT_SCHEMA,
                    "strict": True
                }
            },
            seed=42
        )
        
        # Parse response (contains precomputed bboxes from LLM)
        response_content = completion.choices[0].message.content

        # Ensure we received a structured JSON object from the API.
        if isinstance(response_content, dict):
            result = response_content
        else:
            # We received text instead of a dict. Attempt to parse.
            try:
                result = json.loads(response_content)
            except json.JSONDecodeError as e:
                # Persist raw response for debugging, then fail loud.
                debug_path = os.path.join(os.path.dirname(pdf_path), "debug_raw_response.json")
                try:
                    with open(debug_path, "w", encoding="utf-8") as f:
                        f.write(response_content)
                    print(f"⚠️  Saved invalid JSON to {debug_path}")
                except Exception as write_err:
                    print(f"⚠️  Could not save raw response for inspection: {write_err}")

                raise ValueError(
                    f"OpenAI returned non-parsable JSON (error: {e}). "
                    "Raw response has been written to debug_raw_response.json for inspection."
                )
        
        # Keep the segment order as returned by the LLM, preserving original PDF order
        
        # No manual normalization: LLM is required to supply 'text' field for all segment types
        
        # Add metadata
        result['metadata'] = {
            'pdf_path': pdf_path,
            'file_id': file_response.id,
            'processing_method': 'direct_pdf_upload',
            'model_used': 'o4-mini-2025-04-16',
            'total_questions': len(result.get('questions', [])),
            'total_multi_question_references': len(result.get('multi_question_references', [])),
            'total_unrelated_content_segments': len(result.get('unrelated_content_segments', []))
        }
        
        print(f"✅ Segmentation complete:")
        print(f"   Questions found: {result['metadata']['total_questions']}")
        print(f"   References found: {result['metadata']['total_multi_question_references']}")
        print(f"   Unrelated content segments found: {result['metadata']['total_unrelated_content_segments']}")
        
        # Clean up uploaded file
        try:
            openai_client.files.delete(file_response.id)
            print(f"✓ Cleaned up uploaded file: {file_response.id}")
        except Exception as e:
            print(f"⚠️  Could not delete uploaded file: {e}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error processing PDF: {str(e)}")
        raise

def segment_pdf_with_llm(pdf_path: str, output_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Main function to segment PDF and optionally save results.
    
    Args:
        pdf_path: Path to input PDF file
        output_file: Optional path to save JSON results
        
    Returns:
        Segmentation results dictionary
    """
    # Process the PDF
    results = segment_pdf_document(pdf_path)
    
    # Save results if output file specified
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"📄 Results saved to: {output_file}")
    
    return results

def validate_coordinates(bbox: Dict[str, float], page_width: float = 612, page_height: float = 792) -> Dict[str, float]:
    """
    Validate and clamp coordinates to page boundaries.
    
    Args:
        bbox: Bounding box coordinates
        page_width: Page width in points (default: 612 for US Letter)
        page_height: Page height in points (default: 792 for US Letter)
        
    Returns:
        Validated bounding box
    """
    return {
        'x1': max(0, min(bbox['x1'], page_width)),
        'y1': max(0, min(bbox['y1'], page_height)),
        'x2': max(0, min(bbox['x2'], page_width)),
        'y2': max(0, min(bbox['y2'], page_height))
    }

def get_question_statistics(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate statistics about the segmented questions.
    
    Args:
        results: Segmentation results
        
    Returns:
        Statistics dictionary
    """
    questions = results.get('questions', [])
    multi_refs = results.get('multi_question_references', [])
    unrelated = results.get('unrelated_content_segments', [])
    
    stats = {
        'total_questions': len(questions),
        'total_multi_question_references': len(multi_refs),
        'total_unrelated_content_segments': len(unrelated),
        'question_types': {},
        'reference_types': {},
        'unrelated_content_types': {},
        'pages_with_questions': set(),
        'multi_page_questions': 0
    }
    
    # Analyze questions
    for q in questions:
        q_type = q.get('type', 'unknown')
        stats['question_types'][q_type] = stats['question_types'].get(q_type, 0) + 1
        # Add all pages a question spans
        for p in q.get('page_nums', []):
            stats['pages_with_questions'].add(p)
        if q.get('multi_page', False):
            stats['multi_page_questions'] += 1
    
    # Analyze references
    for ref in multi_refs:
        ref_type = ref.get('type', 'unknown')
        stats['reference_types'][ref_type] = stats['reference_types'].get(ref_type, 0) + 1
    
    # Analyze unrelated content
    for unrel in unrelated:
        unrel_type = unrel.get('type', 'unknown')
        stats['unrelated_content_types'][unrel_type] = stats['unrelated_content_types'].get(unrel_type, 0) + 1
    
    stats['pages_with_questions'] = len(stats['pages_with_questions'])
    
    return stats 