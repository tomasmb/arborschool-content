#!/usr/bin/env python3
"""
Script para extraer respuestas correctas de un PDF con claves de respuestas.

Usage:
    python scripts/extract_answer_key.py \
        --pdf-path ../../data/pruebas/raw/respuestas-prueba-invierno-2026.pdf \
        --output ../../data/pruebas/procesadas/prueba-invierno-2026/respuestas_correctas.json \
        --test-name prueba-invierno-2026
"""

from __future__ import annotations

import os
import sys
import argparse
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional

# Load environment variables
from dotenv import load_dotenv
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent.parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)

# Add modules to path
sys.path.insert(0, str(script_dir.parent))

try:
    import fitz  # type: ignore  # PyMuPDF
except ImportError:
    # Try importing from parent directory's modules
    sys.path.insert(0, str(script_dir.parent.parent))
    import fitz  # type: ignore

from modules.ai_processing.llm_client import chat_completion


def extract_text_from_pdf(pdf_path: Path) -> Dict[str, Any]:
    """Extract text content from PDF."""
    doc = fitz.open(str(pdf_path))
    
    total_pages = len(doc)  # Save before closing
    
    pages_text = []
    for page_num in range(total_pages):
        page = doc.load_page(page_num)
        text = page.get_text()
        pages_text.append({
            "page_number": page_num + 1,
            "text": text
        })
    
    doc.close()
    
    return {
        "total_pages": total_pages,
        "pages": pages_text
    }


def extract_answer_key_with_ai(
    pdf_content: Dict[str, Any], 
    api_key: str,
    focus_page: Optional[int] = None
) -> Dict[str, str]:
    """
    Use AI to extract answer key from PDF content.
    
    Args:
        pdf_content: Dictionary with pages and text
        api_key: API key for AI
        focus_page: Optional page number to focus on (1-indexed). If provided, only that page will be analyzed.
    
    Returns a dictionary mapping question numbers to correct answers (e.g., {"1": "A", "2": "C", ...})
    """
    
    # Combine all page text, or focus on specific page if requested
    if focus_page:
        # Filter to only the specified page (focus_page is 1-indexed, pages are 0-indexed in list)
        pages_to_use = [p for p in pdf_content["pages"] if p['page_number'] == focus_page]
        if not pages_to_use:
            print(f"⚠️  Page {focus_page} not found in PDF. Using all pages instead.")
            pages_to_use = pdf_content["pages"]
    else:
        pages_to_use = pdf_content["pages"]
    
    all_text = "\n\n".join([f"=== Page {p['page_number']} ===\n{p['text']}" for p in pages_to_use])
    
    prompt = f"""You are an expert at extracting answer keys from educational test documents.

Your task is to extract the correct answers for each question from the provided PDF content.

The document likely contains:
- Question numbers (1, 2, 3, etc. or Q1, Q2, Q3, etc.)
- Correct answer letters (A, B, C, D, etc.) or identifiers
- Possibly formatted as a table, list, or inline text

Extract ALL question-answer pairs you can find and return them as a JSON object where:
- Keys are question numbers (as strings, e.g., "1", "2", "3")
- Values are the correct answer identifiers (e.g., "A", "B", "C", "D" or "ChoiceA", "ChoiceB", etc.)

Examples:
- If question 1 has answer A: {{"1": "A"}}
- If question 2 has answer C: {{"2": "C"}}
- If it says Q3: D: {{"3": "D"}}

Return ONLY valid JSON, no other text. If a question number is ambiguous, use the most likely interpretation.
If you cannot find answers for some questions, omit them from the result.

PDF Content:
{all_text}

Return the answer key as JSON:"""
    
    try:
        response = chat_completion(
            [
                {
                    "role": "system",
                    "content": "You are an expert at extracting structured data from educational documents. Always return valid JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            api_key=api_key,
            json_only=True,
        )
        
        # Parse JSON response
        answer_key = json.loads(response.strip())
        
        # Normalize keys and values
        normalized = {}
        for q_num, answer in answer_key.items():
            # Normalize question number (remove "Q" prefix, ensure it's a string)
            q_num_clean = str(q_num).upper().replace("Q", "").strip()
            if q_num_clean:
                # Normalize answer (ensure it's A, B, C, D format, or ChoiceA, ChoiceB, etc.)
                answer_clean = str(answer).strip().upper()
                # Convert "A" to "ChoiceA" format for consistency with QTI
                if answer_clean in ["A", "B", "C", "D", "E"]:
                    normalized[q_num_clean] = f"Choice{answer_clean}"
                elif answer_clean.startswith("CHOICE"):
                    normalized[q_num_clean] = answer_clean
                else:
                    # Try to extract letter
                    match = re.search(r'[A-E]', answer_clean)
                    if match:
                        normalized[q_num_clean] = f"Choice{match.group()}"
        
        return normalized
        
    except Exception as e:
        print(f"❌ Error extracting answer key with AI: {e}")
        return {}


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract answer key from PDF"
    )
    parser.add_argument(
        "--pdf-path",
        required=True,
        help="Path to PDF with answer key (e.g., ../../data/pruebas/raw/prueba-invierno-2026/respuestas.pdf)"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output JSON file path for answer key"
    )
    parser.add_argument(
        "--test-name",
        help="Test name (for documentation in output file)"
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="API key (uses GEMINI_API_KEY from env if not provided)"
    )
    parser.add_argument(
        "--focus-page",
        type=int,
        default=None,
        help="Focus extraction on a specific page number (1-indexed). Useful if answers are on a specific page."
    )
    
    args = parser.parse_args()
    
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        sys.exit(1)
    
    # Get API key
    api_key = args.api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ No API key provided. Set GEMINI_API_KEY or OPENAI_API_KEY in environment, or pass --api-key")
        sys.exit(1)
    
    print(f"📄 Extracting text from PDF: {pdf_path}")
    pdf_content = extract_text_from_pdf(pdf_path)
    print(f"   Found {pdf_content['total_pages']} page(s)")
    
    if args.focus_page:
        print(f"🎯 Focusing extraction on page {args.focus_page}")
    
    print(f"🤖 Extracting answer key using AI...")
    answer_key = extract_answer_key_with_ai(pdf_content, api_key, focus_page=args.focus_page)
    
    if not answer_key:
        print("❌ Failed to extract answer key")
        sys.exit(1)
    
    print(f"✅ Extracted {len(answer_key)} answer(s)")
    
    # Create output structure
    output_data = {
        "test_name": args.test_name or pdf_path.stem,
        "source_pdf": str(pdf_path),
        "total_questions": len(answer_key),
        "answers": answer_key,
        "metadata": {
            "extraction_method": "AI (Gemini/OpenAI)",
            "question_numbers": sorted(answer_key.keys(), key=lambda x: int(x) if x.isdigit() else 999)
        }
    }
    
    # Save output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Answer key saved to: {output_path}")
    print(f"\n📊 Summary:")
    print(f"   Total questions: {len(answer_key)}")
    print(f"   Question range: {min(answer_key.keys(), key=lambda x: int(x) if x.isdigit() else 999)} - {max(answer_key.keys(), key=lambda x: int(x) if x.isdigit() else 999)}")
    print(f"\n💡 Next step: Use this answer key when processing QTI questions")


if __name__ == "__main__":
    main()
