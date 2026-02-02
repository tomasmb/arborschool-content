"""
Chunk Segmenter Prompts and Schema

Contains the JSON schema for structured output and the chain-of-thought
system prompt for reliable PDF segmentation.
"""

from __future__ import annotations

# JSON Schema for structured output
SEGMENT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Unique identifier for the question"},
                    "text": {"type": "string", "description": "Full text of the question"},
                    "start_marker": {
                        "type": "string",
                        "description": ("Start marker - the first 10 words of the segment text or coordinates in format 'x,y' (in PDF points)"),
                    },
                    "page_nums": {"type": "array", "items": {"type": "integer", "minimum": 1}, "description": "1-based pages where question appears"},
                    "type": {"type": "string", "enum": ["question", "sub_question"], "description": "Question type"},
                    "multi_page": {"type": "boolean", "description": "Whether question spans multiple pages"},
                    "multi_question_references": {
                        "type": "array",
                        "items": {"type": "string", "description": "ID of a multi-question reference used by this question"},
                        "description": "IDs of multi-question references used by this question",
                    },
                },
                "required": ["id", "text", "start_marker", "page_nums", "type", "multi_page", "multi_question_references"],
                "additionalProperties": False,
            },
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
                    "page_nums": {
                        "type": "array",
                        "items": {"type": "integer", "minimum": 1},
                        "description": "1-based pages where reference appears",
                    },
                    "question_ids": {
                        "type": "array",
                        "items": {"type": "string", "description": "ID of a question that uses this reference"},
                        "description": "IDs of questions that use this multi-question reference",
                    },
                },
                "required": ["id", "type", "text", "start_marker", "page_nums", "question_ids"],
                "additionalProperties": False,
            },
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
                    "page_nums": {
                        "type": "array",
                        "items": {"type": "integer", "minimum": 1},
                        "description": "1-based pages where unrelated content appears",
                    },
                },
                "required": ["id", "type", "text", "start_marker", "page_nums"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["questions", "multi_question_references", "unrelated_content_segments"],
    "additionalProperties": False,
}

# Chain-of-Thought system prompt for reliable segmentation
SEGMENT_PROMPT = r"""
You are an expert at segmenting educational test PDFs. Return only validated JSON without explanation.

CRITICAL: When returning the `text` field for any segment, include ONLY the first 50 words (or full text if shorter).

IMPORTANT: The first 2-3 pages of the PDF typically contain cover pages, general
instructions, and scoring information. These should be classified as UNRELATED
CONTENT, not questions. Questions typically start after these initial pages.

## Segment Types

**QUESTIONS**: Complete test questions including all parts (A, B, C), answer choices,
answer spaces, and any reference material used ONLY by this question. Questions
usually start with a number (1., 2., 3., etc.) followed by the question text.

**MULTI-QUESTION REFERENCES**: Content shared by multiple questions (tables, figures, passages, citations that appear before multiple questions).

**UNRELATED CONTENT**: Cover pages, general test instructions, section introductions
unrelated to specific questions. This includes the first pages with test information,
instructions, and scoring details.

## Core Rules

1. **Complete Coverage**: Every part of the PDF must belong to exactly one segment
2. **Self-Contained Questions**: Each question must include all content needed to answer it
3. **Reference Sharing**: If content is used by multiple questions, make it a multi-question reference
4. **Sequential Pages**: Use PDF page order (1, 2, 3...) not printed page numbers
5. **Start Markers**: Use the very first words that appear in each segment

## Question Identification - CRITICAL INSTRUCTIONS

**MOST IMPORTANT**: Each numbered question (1., 2., 3., 4., ... 65.) is a SEPARATE
question segment. You MUST create a separate segment for EACH numbered question
you find.

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
4. **A question ALWAYS ends when the next question number appears** - if you see
   "7." and then later "8.", everything between them belongs to question 7
5. If a question references content above it (like a table or passage), include
   that content in the question segment UNLESS it's used by multiple questions

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
