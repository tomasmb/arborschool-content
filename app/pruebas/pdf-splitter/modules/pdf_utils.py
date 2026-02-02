"""
PDF manipulation utilities.

This module contains high-level functions for PDF processing workflows,
delegating low-level operations to specialized modules:
- pdf_rendering.py: Text/image extraction
- pdf_manipulation.py: PDF creation, saving, merging
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile

import fitz  # type: ignore # PyMuPDF
import openai

from .pdf_manipulation import (
    create_pdf_from_region,
    extract_page_region_with_margin,
    merge_pdfs,
    save_pdf_pages,
)
from .pdf_rendering import (
    CustomJSONEncoder,
    get_optimized_page_content,
    get_page_image,
    get_page_structured_text,
)
from .quality_validator import validate_question_quality


def create_question_pdfs(results: dict, original_pdf_path: str, output_dir: str, fail_on_validation_error: bool = False) -> None:
    """
    Create individual PDF files for each question using the segmentation results.

    Args:
        results: The segmentation results
        original_pdf_path: Path to the original PDF
        output_dir: Output directory for the results
        fail_on_validation_error: If True, raise exception immediately on validation failure
    """
    questions = results.get("questions", [])
    if not questions:
        print("❌ No questions found to create PDFs")
        return

    # Setup directories
    questions_dir = os.path.join(output_dir, "questions")
    failed_dir = os.path.join(output_dir, "failed_questions")
    os.makedirs(questions_dir, exist_ok=True)
    os.makedirs(failed_dir, exist_ok=True)
    print(f"📁 Created questions directory: {questions_dir}")

    # Remove stale failed_questions_log.json from previous runs
    log_path = os.path.join(output_dir, "failed_questions_log.json")
    if os.path.exists(log_path):
        os.remove(log_path)

    failed_questions_log: list[dict] = []

    doc = fitz.open(original_pdf_path)
    print("\n🔧 Creating self-contained question PDFs...")

    with tempfile.TemporaryDirectory() as tmpdir:
        for i, question in enumerate(questions, 1):
            final_pdf_path = _create_single_question_pdf(doc, results, question, i, questions_dir, tmpdir)

            if final_pdf_path is None:
                continue

            # AI Quality Validation Step
            is_valid, reason = validate_question_quality(final_pdf_path)
            if not is_valid:
                _handle_failed_question(
                    final_pdf_path, failed_dir, question, i, reason, failed_questions_log, output_dir, doc, fail_on_validation_error
                )

    doc.close()

    # Save the log of failed questions
    if failed_questions_log:
        log_path = os.path.join(output_dir, "failed_questions_log.json")
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(failed_questions_log, f, indent=2, ensure_ascii=False)
        print(f"📓 Log of failed quality checks saved to: {log_path}")

    print(f"🎉 Finished creating PDFs. See output in {questions_dir} and {failed_dir}")


def _create_single_question_pdf(doc: fitz.Document, results: dict, question: dict, question_num: int, questions_dir: str, tmpdir: str) -> str | None:
    """
    Create a PDF for a single question including its references.

    Returns:
        Path to the created PDF, or None if skipped
    """
    ref_paths = []
    q_paths = []

    # First, crop shared multi-question references
    for ref_id in question.get("multi_question_references", []):
        ref = next((r for r in results.get("multi_question_references", []) if r.get("id") == ref_id), None)
        if ref:
            for rp, rb in zip(ref.get("page_nums", []), ref.get("bboxes", [])):
                rp_idx = rp - 1
                if 0 <= rp_idx < doc.page_count:
                    rpage = doc.load_page(rp_idx)
                    rrect = extract_page_region_with_margin(rpage, rb)
                    r_temp = os.path.join(tmpdir, f"r_{question_num}_{ref['id']}_p{rp}.pdf")
                    create_pdf_from_region(rpage, rrect, r_temp)
                    ref_paths.append(r_temp)

    # Then, crop question region across all pages
    page_nums = question.get("page_nums", [])
    bboxes = question.get("bboxes", [])
    if not page_nums or not bboxes:
        print(f"⚠️  Question {question_num}: missing page_nums or bboxes, skipping.")
        return None

    for p, bbox in zip(page_nums, bboxes):
        page_idx = p - 1
        if 0 <= page_idx < doc.page_count:
            page = doc.load_page(page_idx)
            rect = extract_page_region_with_margin(page, bbox)
            q_temp = os.path.join(tmpdir, f"q_{question_num}_p{p}.pdf")
            create_pdf_from_region(page, rect, q_temp)
            q_paths.append(q_temp)

    # Merge references first, then question pages
    final_paths = ref_paths + q_paths
    final_pdf_path = os.path.join(questions_dir, f"question_{question_num:03d}.pdf")
    merge_pdfs(final_paths, final_pdf_path)
    print(f"   ✅ Created PDF for Question {question_num}: {final_pdf_path}")

    return final_pdf_path


def _handle_failed_question(
    final_pdf_path: str,
    failed_dir: str,
    question: dict,
    question_num: int,
    reason: str,
    failed_questions_log: list[dict],
    output_dir: str,
    doc: fitz.Document,
    fail_on_validation_error: bool,
) -> None:
    """Handle a question that failed quality validation."""
    failed_pdf_path = os.path.join(failed_dir, f"question_{question_num:03d}.pdf")
    shutil.move(final_pdf_path, failed_pdf_path)
    print(f"   🚚 Moved failed question to: {failed_pdf_path}")

    failed_questions_log.append(
        {"question_id": question.get("id", f"unknown_{question_num}"), "pdf_name": os.path.basename(failed_pdf_path), "reason": reason}
    )

    if fail_on_validation_error:
        # Save the log immediately before failing
        if failed_questions_log:
            log_path = os.path.join(output_dir, "failed_questions_log.json")
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(failed_questions_log, f, indent=2, ensure_ascii=False)
            print(f"📓 Log of failed quality checks saved to: {log_path}")

        doc.close()
        raise Exception(f"Quality validation failed for question {question_num}: {reason}")


def split_pdf_by_ai(input_pdf_path: str, output_dir: str | None = None, model: str = "gpt-5.1") -> list[tuple[str, int]]:
    """
    Use an LLM to suggest logical split points for a PDF, then split at those points.

    Returns:
        List of tuples: (chunk_path, chunk_start_page).
        If the PDF is already a single logical part, returns a list with the original path.
    """
    doc = fitz.open(input_pdf_path)
    total_pages = doc.page_count

    if total_pages <= 1:
        doc.close()
        return [(input_pdf_path, 1)]

    # Get LLM-suggested split points
    split_pages = _get_ai_split_points(doc, input_pdf_path, model)

    # Build and save chunks
    chunk_infos = _create_pdf_chunks(doc, split_pages, input_pdf_path, output_dir)

    doc.close()
    return chunk_infos


def _get_ai_split_points(doc: fitz.Document, input_pdf_path: str, model: str) -> list[int]:
    """Get AI-suggested split points for the PDF."""
    total_pages = doc.page_count

    # Extract page summaries
    page_summaries = []
    for i in range(total_pages):
        text = doc.load_page(i).get_text().strip()
        lines = [line for line in text.split("\n") if line.strip()]
        summary = " | ".join(lines[:3])[:200]
        page_summaries.append(f"Page {i + 1}: {summary}")

    # Prepare LLM prompt
    prompt = _build_split_prompt(page_summaries)

    # Define JSON schema
    split_schema = {
        "type": "object",
        "properties": {
            "split_pages": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Sorted list of split page numbers (first page of each part, 1-based)",
            }
        },
        "required": ["split_pages"],
        "additionalProperties": False,
    }

    # Call OpenAI LLM
    client = openai.Client()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": prompt}],
        response_format={"type": "json_schema", "json_schema": {"name": "logical_pdf_split", "schema": split_schema, "strict": True}},
        temperature=0,
        top_p=1,
        max_tokens=512,
        seed=42,
    )

    llm_json = response.choices[0].message.content
    return _parse_split_response(llm_json, total_pages, input_pdf_path)


def _build_split_prompt(page_summaries: list[str]) -> str:
    """Build the prompt for AI-based PDF splitting."""
    return (
        "You are an expert at splitting educational test PDFs into logical, self-contained parts.\n"
        "Here are the first 3 non-empty lines from each page of a test PDF.\n\n"
        "Your task:\n"
        "- Split this PDF at the start of every new section, item set, part, or other natural division.\n"
        "- Look for lines containing 'Section', 'Part', 'Item Set', 'Directions', or similar.\n"
        "- Never split in the middle of a section, item set, or reference block.\n"
        "- Each part must be self-contained: no question should reference material in another part.\n"
        "- Return ONLY a JSON object with 'split_pages' as a sorted list of split page numbers (1-based).\n\n"
        "Page summaries:\n" + "\n".join(page_summaries)
    )


def _parse_split_response(llm_json: str, total_pages: int, input_pdf_path: str) -> list[int]:
    """Parse the LLM response for split pages."""
    split_pages = [1]  # Always start with page 1

    try:
        data = json.loads(llm_json)
        if isinstance(data, dict) and "split_pages" in data and isinstance(data["split_pages"], list):
            for n in data["split_pages"]:
                if isinstance(n, int) and n not in split_pages and 1 <= n <= total_pages:
                    split_pages.append(n)
        else:
            raise ValueError(f"LLM returned invalid JSON structure: {llm_json}")
    except json.JSONDecodeError as e:
        _save_debug_response(llm_json, input_pdf_path, "debug_split_response.json")
        raise ValueError(f"LLM returned non-parsable JSON for PDF splitting: {e}")
    except Exception as e:
        raise ValueError(f"LLM PDF splitting failed: {e}")

    return sorted(set(split_pages))


def _save_debug_response(response: str, pdf_path: str, filename: str) -> None:
    """Save a failed LLM response for debugging."""
    debug_path = os.path.join(os.path.dirname(pdf_path), filename)
    try:
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(response)
        print(f"⚠️ Saved invalid LLM response to {debug_path}")
    except Exception as write_err:
        print(f"⚠️ Could not save debug response: {write_err}")


def _create_pdf_chunks(doc: fitz.Document, split_pages: list[int], input_pdf_path: str, output_dir: str | None) -> list[tuple[str, int]]:
    """Create PDF chunks from split points."""
    total_pages = doc.page_count

    # Build chunks from split points
    chunks = []
    for i in range(len(split_pages)):
        start = split_pages[i] - 1
        end = split_pages[i + 1] - 1 if i + 1 < len(split_pages) else total_pages
        chunks.append((start, end))

    # Write out each chunk
    chunk_infos = []
    for idx, (start, end) in enumerate(chunks):
        chunk_doc = fitz.open()
        for i in range(start, end):
            chunk_doc.insert_pdf(doc, from_page=i, to_page=i)

        # Determine output path
        if output_dir:
            base_name = os.path.splitext(os.path.basename(input_pdf_path))[0]
            chunks_dir = os.path.join(output_dir, "chunks")
            os.makedirs(chunks_dir, exist_ok=True)
            chunk_path = os.path.join(chunks_dir, f"{base_name}_ai_chunk_{idx + 1}.pdf")
        else:
            chunk_path = f"{os.path.splitext(input_pdf_path)[0]}_ai_chunk_{idx + 1}.pdf"

        chunk_doc.save(chunk_path)
        chunk_doc.close()
        chunk_infos.append((chunk_path, start + 1))

    return chunk_infos


# =============================================================================
# Backward-compatible exports
# =============================================================================

__all__ = [
    # From pdf_rendering
    "CustomJSONEncoder",
    "get_page_structured_text",
    "get_optimized_page_content",
    "get_page_image",
    # From pdf_manipulation
    "create_pdf_from_region",
    "save_pdf_pages",
    "merge_pdfs",
    # High-level functions
    "create_question_pdfs",
    "split_pdf_by_ai",
]
