"""
PDF Question Segmentation using Gemini or OpenAI
Uses Gemini Preview 3 by default (with PDF converted to images),
with fallback to OpenAI's direct PDF upload if Gemini unavailable.
"""

import os
import json
import base64
import re
from typing import List, Dict, Any, Optional

# Try to import Gemini SDK
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None
    types = None

# Try to import OpenAI SDK
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None

# Try to import PyMuPDF for PDF to image conversion
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    fitz = None

# Clients will be initialized lazily
gemini_client = None
openai_client = None

def get_gemini_client():
    """Get or initialize Gemini client with API key from environment."""
    global gemini_client
    if gemini_client is None:
        if not GEMINI_AVAILABLE:
            raise ImportError("Gemini SDK not available. Install with: pip install google-genai")
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        gemini_client = genai.Client(api_key=api_key)
    return gemini_client

def get_openai_client():
    """Get or initialize OpenAI client with API key from environment."""
    global openai_client
    if openai_client is None:
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI SDK not available. Install with: pip install openai")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        openai_client = OpenAI(api_key=api_key)
    return openai_client

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

IMPORTANT: The first 2-3 pages of the PDF typically contain cover pages, general instructions, and scoring information. These should be classified as UNRELATED CONTENT, not questions. Questions typically start after these initial pages.

## Segment Types

**QUESTIONS**: Complete test questions including all parts (A, B, C), answer choices, answer spaces, and any reference material used ONLY by this question. Questions usually start with a number (1., 2., 3., etc.) followed by the question text.

**MULTI-QUESTION REFERENCES**: Content shared by multiple questions (tables, figures, passages, citations that appear before multiple questions).

**UNRELATED CONTENT**: Cover pages, general test instructions, section introductions unrelated to specific questions. This includes the first pages with test information, instructions, and scoring details.

## Core Rules

1. **Complete Coverage**: Every part of the PDF must belong to exactly one segment
2. **Self-Contained Questions**: Each question must include all content needed to answer it
3. **Reference Sharing**: If content is used by multiple questions, make it a multi-question reference
4. **Sequential Pages**: Use PDF page order (1, 2, 3...) not printed page numbers
5. **Start Markers**: Use the very first words that appear in each segment

## Question Identification - CRITICAL INSTRUCTIONS

**MOST IMPORTANT**: Each numbered question (1., 2., 3., 4., ... 65.) is a SEPARATE question segment. You MUST create a separate segment for EACH numbered question you find.

**Question Numbering Pattern**:
- Questions start with a number followed by a period: "1.", "2.", "3.", etc.
- Each number represents a distinct question
- Multiple questions can appear on the same page
- A single question can span multiple pages
- **IMPORTANT - Test Types**:
  - **Invierno tests**: Always have 65 questions (Q1 through Q65, all present)
  - **Regular/Seleccion tests**: Always have 45 questions, but numbers are NOT sequential!
    - In selecciones, questions keep their original numbers from the full test
    - Example: A seleccion might have Q2, Q3, Q4, Q6, Q19, Q23, Q45, etc.
    - Gaps in numbering are NORMAL and EXPECTED in selecciones
    - You should find exactly 45 questions, but their numbers may skip (Q1, Q2, Q5, Q10, etc.)
- **A question NEVER spans more than 5 pages** - if a segment would span more, you've missed intermediate question numbers!

**How to Identify Question Boundaries**:
1. **Systematically scan EVERY page** from page 3 onwards for question numbers
2. Look for question numbers: "1.", "2.", "3.", "4.", "5.", etc. - search for patterns like "^\d+\." or standalone numbers followed by periods
3. Each question includes:
   - The question text/prompt
   - Answer choices (typically A), B), C), D))
   - Any images, tables, or diagrams specific to that question
4. **A question ALWAYS ends when the next question number appears** - if you see "7." and then later "8.", everything between them belongs to question 7
5. If a question references content above it (like a table or passage), include that content in the question segment UNLESS it's used by multiple questions

**CRITICAL - Do NOT**:
- Combine multiple numbered questions into one segment - THIS IS THE MOST COMMON ERROR
- Skip question numbers - if you find "2.", "3.", "4.", "6." you MUST look harder for "5."
- Include unrelated content (cover pages, general instructions) as questions
- Stop after finding just a few questions - you MUST scan the ENTIRE document page by page
- Allow any single question to span more than 5 pages - if it does, you've missed question numbers in between

**Example**: If you see:
  "1. What is 2+2? A) 3 B) 4 C) 5 D) 6
   2. What is 3+3? A) 5 B) 6 C) 7 D) 8"
  
  You must create TWO separate question segments: Q1 and Q2.

## Multi-Question Reference Rules

- Only create if used by 2+ questions
- Group consecutive references with no questions between them
- Associate each reference with all questions that use it
- Don't duplicate reference content in question segments

## Process - Step by Step

1. **Initial Scan**: 
   - Skip the first 2-3 pages (cover/instructions)
   - Find the FIRST question number (usually "1." or "1)")
   - This marks where questions begin

2. **Question Extraction**:
   - For EACH question number you find (1., 2., 3., ... up to 65.):
     - Create a separate question segment
     - Include the question text
     - Include all answer choices (A), B), C), D))
     - Include any images, tables, or diagrams that belong ONLY to this question
     - Continue until you reach the next question number or end of document
   
3. **Boundaries**: 
   - Each question segment starts at its question number
   - Each question segment ends at the start of the next question number (or end of document)
   - No gaps, no overlaps

4. **References**: 
   - If content is used by multiple questions, make it a multi-question reference
   - Link questions to their references

5. **Validation**: 
   - Count your questions:
     - **Invierno tests**: You MUST find exactly 65 questions (Q1 through Q65, all present, sequential)
     - **Regular/Seleccion tests**: You MUST find exactly 45 questions (numbers may skip, gaps are normal)
   - **If you find fewer than expected, you have DEFINITELY missed some - scan again!**
   - **For Invierno only**: Check for gaps - if you have Q2, Q3, Q4, Q6 but no Q5, you missed Q5
   - **For Selecciones**: Gaps are EXPECTED - Q2, Q3, Q4, Q6 is valid (Q5 is not in this seleccion)
   - Ensure every question is self-contained

## IDs and Markers

- Questions: Q1, Q2, Q3, Q4, ... Q65 (one per question number found)
- References: R1, R2, R3... (only if shared by multiple questions)
- Unrelated: UC1, UC2, UC3... (cover pages, general instructions)
- Start markers: First words of each segment - for questions, use the question number and first few words

**CRITICAL REMINDER**: 
- You must find and segment EVERY numbered question in the document
- Do not stop after finding just a few questions
- Scan the ENTIRE document systematically, page by page
- **Expected counts**: 
  - If this is an "invierno" test, you MUST find exactly 65 questions (Q1 through Q65, all sequential)
  - If this is a "seleccion" or "regular" test, you MUST find exactly 45 questions (numbers may skip)
- If you only find 5-10 questions, you have DEFINITELY missed many more - keep searching!
- Question numbers may appear as "1.", "2.", "3." or "1)", "2)", "3)" or just "1", "2", "3" followed by text
- A single question typically spans 1-3 pages MAX - if a segment spans 10+ pages, you've combined multiple questions

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
    
    # Detectar tipo de prueba desde el nombre del archivo/ruta
    pdf_name_lower = pdf_path.lower()
    is_seleccion = 'seleccion' in pdf_name_lower
    is_invierno = 'invierno' in pdf_name_lower
    expected_count = 45 if is_seleccion else (65 if is_invierno else None)
    test_type = "seleccion" if is_seleccion else ("invierno" if is_invierno else "unknown")
    
    # VALIDACIÓN POST-SEGMENTACIÓN: Detectar problemas comunes
    questions = results.get('questions', [])
    total_questions = len(questions)
    
    # Verificar cantidad de preguntas según el tipo de prueba
    if expected_count:
        if total_questions < expected_count * 0.7:  # Menos del 70% esperado
            print(f"\n⚠️  ADVERTENCIA: Solo se encontraron {total_questions} pregunta(s) de {expected_count} esperadas para {test_type}")
            print(f"   Esto es anormalmente bajo. Probablemente se perdieron preguntas en la segmentación.")
        elif total_questions < expected_count:
            print(f"\n⚠️  ADVERTENCIA: Se encontraron {total_questions} pregunta(s) de {expected_count} esperadas para {test_type}")
            print(f"   Faltan {expected_count - total_questions} pregunta(s).")
        elif total_questions == expected_count:
            print(f"\n✅ Correcto: Se encontraron {total_questions} pregunta(s) (esperado para {test_type})")
        else:
            print(f"\n⚠️  ADVERTENCIA: Se encontraron {total_questions} pregunta(s), más de las {expected_count} esperadas para {test_type}")
    elif total_questions < 10:
        print(f"\n⚠️  ADVERTENCIA: Solo se encontraron {total_questions} pregunta(s)")
        print(f"   Esto es anormalmente bajo. Probablemente se perdieron preguntas en la segmentación.")
        print(f"   Revisa el PDF - debería haber 45 (seleccion) o 65 (invierno) preguntas.")
    
    # Verificar si alguna pregunta abarca demasiadas páginas (indicador de que se combinaron múltiples)
    oversized_questions = []
    for q in questions:
        page_count = len(q.get('page_nums', []))
        if page_count > 5:
            oversized_questions.append({
                'id': q.get('id', 'unknown'),
                'pages': page_count,
                'page_nums': q.get('page_nums', [])[:10]  # Primeras 10 páginas para mostrar
            })
    
    if oversized_questions:
        print(f"\n⚠️  ADVERTENCIA: {len(oversized_questions)} pregunta(s) abarcan más de 5 páginas:")
        for q_info in oversized_questions:
            print(f"   - {q_info['id']}: {q_info['pages']} páginas (páginas {q_info['page_nums']}...)")
            print(f"     Esto sugiere que se combinaron múltiples preguntas. Busca números de pregunta intermedios.")
    
    # Verificar gaps en la numeración SOLO para pruebas Invierno (en selecciones, gaps son normales)
    if is_invierno and not is_seleccion:
        question_numbers = []
        for q in questions:
            q_id = q.get('id', '')
            # Extraer número de Q1, Q2, etc.
            match = re.match(r'Q(\d+)', q_id)
            if match:
                question_numbers.append(int(match.group(1)))
        
        if question_numbers:
            question_numbers.sort()
            gaps = []
            for i in range(len(question_numbers) - 1):
                current = question_numbers[i]
                next_num = question_numbers[i + 1]
                if next_num - current > 1:
                    missing = list(range(current + 1, next_num))
                    gaps.extend(missing)
            
            if gaps:
                print(f"\n⚠️  ADVERTENCIA (Invierno): Se detectaron gaps en la numeración de preguntas:")
                print(f"   Preguntas encontradas: {question_numbers[:10]}{'...' if len(question_numbers) > 10 else ''}")
                print(f"   Números faltantes detectados: {gaps[:10]}{'...' if len(gaps) > 10 else ''}")
                print(f"   En pruebas Invierno, TODAS las preguntas Q1-Q65 deben estar presentes.")
    elif is_seleccion:
        # Para selecciones, los gaps son normales - solo informar
        question_numbers = []
        for q in questions:
            q_id = q.get('id', '')
            match = re.match(r'Q(\d+)', q_id)
            if match:
                question_numbers.append(int(match.group(1)))
        
        if question_numbers:
            question_numbers.sort()
            min_q = min(question_numbers)
            max_q = max(question_numbers)
            print(f"\nℹ️  Selección detectada: Preguntas encontradas van de Q{min_q} a Q{max_q} (gaps son normales)")
    
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