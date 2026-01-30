"""
PDF manipulation utilities.

This module contains functions for reading, manipulating, and writing PDFs.
"""

import base64
import json
import os
import shutil
import tempfile
from json import JSONEncoder

import fitz  # type: ignore # PyMuPDF
import openai

from .quality_validator import validate_question_quality


# Custom JSON encoder to handle bytes and other non-serializable types
class CustomJSONEncoder(JSONEncoder):
    """Custom JSON encoder that can handle bytes objects."""
    def default(self, obj):
        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode('utf-8')  # Convert bytes to base64 string
        # Let the base class default method handle other types
        return JSONEncoder.default(self, obj)


def get_page_structured_text(page: fitz.Page) -> str:
    """
    Extracts structured text from a PyMuPDF page object.
    Uses the "dict" output and serializes it to a JSON string for the LLM.

    Args:
        page: The fitz.Page object to extract text from.

    Returns:
        A JSON string containing the structured text.
    """
    structured_output = page.get_text("dict", sort=True)
    return json.dumps(structured_output, cls=CustomJSONEncoder)


def get_optimized_page_content(page: fitz.Page, max_length: int = 8000) -> str:
    """
    Creates an optimized representation of page content that prioritizes
    important elements while keeping the output size manageable.

    Args:
        page: The fitz.Page object to process
        max_length: Target maximum length for the optimized content

    Returns:
        A string containing the optimized representation of the page content
    """
    import re
    # First, extract structured information using different methods
    blocks_data = page.get_text("dict", sort=True)

    # Create a prioritized summary
    summary = {
        "page_size": {"width": page.rect.width, "height": page.rect.height},
        "blocks_count": len(blocks_data.get("blocks", [])),
        "page_description": "PDF page with the following elements:"
    }

    # Extract and prioritize content:
    # 1. Headers and question identifiers (likely short, high value)
    # 2. First text block of each section (often contains important context)
    # 3. Sample of other text content

    blocks = blocks_data.get("blocks", [])

    # Extract text blocks and sort by position (top to bottom)
    text_blocks = [b for b in blocks if b.get("type") == 0]  # Type 0 is text
    text_blocks.sort(key=lambda b: b.get("bbox", [0, 0, 0, 0])[1])  # Sort by y0 (top)

    important_texts = []
    question_markers = []

    # First pass: identify question markers and headers
    for block in text_blocks:
        text = ""
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                span_text = span.get("text", "").strip()
                text += span_text + " "

        text = text.strip()
        if not text:
            continue

        # Check if this looks like a question marker or header
        if re.search(r'question\s+\d+|^\d+\.\s+', text.lower()) or text.upper() == text:
            question_markers.append({
                "text": text,
                "bbox": block.get("bbox"),
                "type": "question_marker"
            })
        elif len(text) < 100:  # Short blocks are likely headers or important
            important_texts.append({
                "text": text,
                "bbox": block.get("bbox"),
                "type": "header"
            })

    # Second pass: get a representative sample of content
    remaining_length = max_length - len(json.dumps(summary)) - len(json.dumps(question_markers)) - len(json.dumps(important_texts))

    content_samples = []
    if remaining_length > 1000:
        # Add a sample of content blocks
        current_length = 0
        for block in text_blocks:
            if current_length > remaining_length:
                break

            text = ""
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text += span.get("text", "").strip() + " "

            text = text.strip()
            if not text or any(text == item["text"] for item in question_markers + important_texts):
                continue

            block_summary = {
                "text": text[:min(len(text), 200)],  # Limit individual block length
                "bbox": block.get("bbox"),
                "type": "content"
            }

            content_samples.append(block_summary)
            current_length += len(json.dumps(block_summary))

    # Combine everything into a final optimized representation
    summary["question_markers"] = question_markers
    summary["important_texts"] = important_texts
    summary["content_samples"] = content_samples
    summary["original_block_count"] = len(blocks)

    return json.dumps(summary, cls=CustomJSONEncoder)


def get_page_image(page: fitz.Page, scale: float = 2.0) -> bytes:
    """
    Renders a page as an image with fallback strategies for complex pages.

    Args:
        page: The fitz.Page to render
        scale: Scale factor for resolution (higher = better quality but larger size)

    Returns:
        PNG image data as bytes
    """
    # Strategy 1: Try normal rendering
    try:
        matrix = fitz.Matrix(scale, scale)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        return pixmap.tobytes("png")
    except RuntimeError as e:
        if "Private data too large" in str(e):
            print("⚠️  Complex page detected, trying fallback strategies...")
        else:
            raise e

    # Strategy 2: Reduce scale factor
    fallback_scales = [1.5, 1.0, 0.75, 0.5]
    for fallback_scale in fallback_scales:
        try:
            print(f"🔄 Trying reduced scale: {fallback_scale}")
            matrix = fitz.Matrix(fallback_scale, fallback_scale)
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            return pixmap.tobytes("png")
        except RuntimeError as e:
            if "Private data too large" not in str(e):
                raise e
            continue

    # Strategy 3: Try without display list (direct rendering)
    try:
        print("🔄 Trying direct rendering without display list...")
        matrix = fitz.Matrix(1.0, 1.0)
        # Use a smaller colorspace and different rendering approach
        pixmap = page.get_pixmap(matrix=matrix, alpha=False, annots=False)
        return pixmap.tobytes("png")
    except RuntimeError as e:
        if "Private data too large" not in str(e):
            raise e

    # Strategy 4: Create a minimal placeholder image
    print("⚠️  All rendering strategies failed, creating placeholder image")
    try:
        # Create a simple white image with text indicating the issue
        import io

        from PIL import Image, ImageDraw, ImageFont  # type: ignore

        # Create a white image
        img = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(img)

        # Add text explaining the issue
        try:
            # Try to use a default font
            font = ImageFont.load_default()
        except Exception:
            font = None

        text = f"Page {page.number + 1}\nContent too complex to render\nText extraction available"
        draw.text((50, 250), text, fill='black', font=font)

        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        return img_bytes.getvalue()

    except Exception as fallback_error:
        print(f"❌ Even placeholder creation failed: {fallback_error}")
        # Return a minimal 1x1 white pixel as absolute fallback
        return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x12IDATx\x9cc```bPPP\x00\x02\xac\xea\x05\x1b\x00\x00\x00\x00IEND\xaeB`\x82'


def create_pdf_from_region(source_page: fitz.Page, rect: fitz.Rect, output_path: str):
    """
    Creates a new PDF file containing only the specified region of a source page.

    Args:
        source_page: The fitz.Page object to extract the region from.
        rect: A fitz.Rect defining the bounding box of the region to extract.
        output_path: Path to save the new PDF.
    """
    new_doc = fitz.open()  # Create a new empty PDF
    new_page = new_doc.new_page(width=rect.width, height=rect.height) # Page size of the rect

    # Add the content from the source page's rect to the new page
    # The target rectangle on the new page will be (0, 0, rect.width, rect.height)
    target_rect = fitz.Rect(0, 0, rect.width, rect.height)
    new_page.show_pdf_page(target_rect, source_page.parent, source_page.number, clip=rect)

    try:
        new_doc.save(output_path)
        print(f"Saved PDF region to: {output_path}")
    except Exception as e:
        print(f"Error saving PDF region {output_path}: {e}")
    finally:
        new_doc.close()


def save_pdf_pages(doc: fitz.Document, page_numbers: list[int], output_path: str):
    """
    Saves specified pages from a document to a new PDF file.
    Args:
        doc: The source fitz.Document.
        page_numbers: A list of 0-indexed page numbers to include.
        output_path: Path to save the new PDF.
    """
    new_doc = fitz.open()  # Create a new empty PDF
    for page_num in page_numbers:
        if 0 <= page_num < doc.page_count:
            new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
    if len(new_doc) > 0:
        new_doc.save(output_path)
        print(f"Saved PDF: {output_path} with pages: {[p + 1 for p in page_numbers]}")
    else:
        print(f"Warning: No pages selected for PDF: {output_path}")
    new_doc.close()


def merge_pdfs(pdf_paths: list[str], output_path: str):
    """
    Merges multiple PDF files into a single PDF file.
    Args:
        pdf_paths: List of paths to PDF files to merge.
        output_path: Path to save the merged PDF.
    """
    merged_doc = fitz.open()
    for pdf_path in pdf_paths:
        if os.path.exists(pdf_path):
            try:
                src_doc = fitz.open(pdf_path)
                merged_doc.insert_pdf(src_doc)
                src_doc.close()
            except Exception as e:
                print(f"Error merging {pdf_path}: {e}")
        else:
            print(f"Warning: PDF not found for merging: {pdf_path}")

    if len(merged_doc) > 0:
        merged_doc.save(output_path)
        print(f"Saved merged PDF: {output_path}")
    else:
        print(f"Warning: No documents to merge for: {output_path}")
    merged_doc.close()


def create_question_pdfs(results: dict, original_pdf_path: str, output_dir: str, fail_on_validation_error: bool = False):
    """
    Create individual PDF files for each question using the segmentation results.

    Args:
        results: The segmentation results
        original_pdf_path: Path to the original PDF
        output_dir: Output directory for the results
        fail_on_validation_error: If True, raise exception immediately on validation failure
    """
    questions = results.get('questions', [])
    if not questions:
        print("❌ No questions found to create PDFs")
        return

    # Setup output directory
    questions_dir = os.path.join(output_dir, "questions")
    failed_dir = os.path.join(output_dir, "failed_questions")
    os.makedirs(questions_dir, exist_ok=True)
    os.makedirs(failed_dir, exist_ok=True)
    print(f"📁 Created questions directory: {questions_dir}")

    # Remove stale failed_questions_log.json from previous runs to avoid false positives
    log_path = os.path.join(output_dir, "failed_questions_log.json")
    if os.path.exists(log_path):
        os.remove(log_path)

    failed_questions_log = []

    doc = fitz.open(original_pdf_path)
    print("\n🔧 Creating self-contained question PDFs...")

    with tempfile.TemporaryDirectory() as tmpdir:
        for i, question in enumerate(questions, 1):
            ref_paths = []
            q_paths = []
            # First, crop shared multi-question references (can span multiple pages)
            for ref_id in question.get('multi_question_references', []):
                ref = next((r for r in results.get('multi_question_references', []) if r.get('id') == ref_id), None)
                if ref:
                    for rp, rb in zip(ref.get('page_nums', []), ref.get('bboxes', [])):
                        rp_idx = rp - 1
                        if 0 <= rp_idx < doc.page_count:
                            rpage = doc.load_page(rp_idx)
                            # rb is now [x1, y1, x2, y2] list, not a dict
                            rx1 = max(0, rb[0] - 10)
                            ry1 = max(0, rb[1] - 10)
                            rx2 = min(rpage.rect.width, rb[2] + 10)
                            ry2 = min(rpage.rect.height, rb[3] + 10)
                            rrect = fitz.Rect(rx1, ry1, rx2, ry2)
                            r_temp = os.path.join(tmpdir, f"r_{i}_{ref['id']}_p{rp}.pdf")
                            create_pdf_from_region(rpage, rrect, r_temp)
                            ref_paths.append(r_temp)
            # Then, crop question region across all pages with margin
            page_nums = question.get('page_nums', [])
            bboxes = question.get('bboxes', [])
            if not page_nums or not bboxes:
                print(f"⚠️  Question {i}: missing page_nums or bboxes, skipping.")
                continue
            for p, bbox in zip(page_nums, bboxes):
                page_idx = p - 1
                if 0 <= page_idx < doc.page_count:
                    page = doc.load_page(page_idx)
                    # bbox is now [x1, y1, x2, y2] list, not a dict
                    x1 = max(0, bbox[0] - 10)
                    y1 = max(0, bbox[1] - 10)
                    x2 = min(page.rect.width, bbox[2] + 10)
                    y2 = min(page.rect.height, bbox[3] + 10)
                    rect = fitz.Rect(x1, y1, x2, y2)
                    q_temp = os.path.join(tmpdir, f"q_{i}_p{p}.pdf")
                    create_pdf_from_region(page, rect, q_temp)
                    q_paths.append(q_temp)
            # Merge references first, then question pages
            final_paths = ref_paths + q_paths
            final_pdf_path = os.path.join(questions_dir, f"question_{i:03d}.pdf")
            merge_pdfs(final_paths, final_pdf_path)
            print(f"   ✅ Created PDF for Question {i}: {final_pdf_path}")

            # --- AI Quality Validation Step ---
            is_valid, reason = validate_question_quality(final_pdf_path)
            if not is_valid:
                # Move the failed PDF and log the reason
                failed_pdf_path = os.path.join(failed_dir, f"question_{i:03d}.pdf")
                shutil.move(final_pdf_path, failed_pdf_path)
                print(f"   🚚 Moved failed question to: {failed_pdf_path}")
                failed_questions_log.append({
                    "question_id": question.get("id", f"unknown_{i}"),
                    "pdf_name": os.path.basename(failed_pdf_path),
                    "reason": reason
                })

                # If fail_on_validation_error is True, fail immediately
                if fail_on_validation_error:
                    # Save the log immediately before failing
                    if failed_questions_log:
                        log_path = os.path.join(output_dir, "failed_questions_log.json")
                        with open(log_path, 'w', encoding='utf-8') as f:
                            json.dump(failed_questions_log, f, indent=2, ensure_ascii=False)
                        print(f"📓 Log of failed quality checks saved to: {log_path}")

                    doc.close()
                    raise Exception(f"Quality validation failed for question {i}: {reason}")

    doc.close()

    # Save the log of failed questions
    if failed_questions_log:
        log_path = os.path.join(output_dir, "failed_questions_log.json")
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(failed_questions_log, f, indent=2, ensure_ascii=False)
        print(f"📓 Log of failed quality checks saved to: {log_path}")

    print(f"🎉 Finished creating PDFs. See output in {questions_dir} and {failed_dir}")


def split_pdf_by_ai(input_pdf_path: str, output_dir: str = None, model: str = "gpt-4o") -> list:
    """
    Use an LLM to suggest logical split points for a PDF, then split the PDF at those points.
    Returns a list of tuples: (chunk_path, chunk_start_page). If the PDF is already a single logical part, returns a list with the original path.
    """
    import json
    doc = fitz.open(input_pdf_path)
    total_pages = doc.page_count
    if total_pages <= 1:
        doc.close()
        return [(input_pdf_path, 1)]

    # Extract first 3 non-empty lines (joined with ' | '), up to 200 chars, from each page
    page_summaries = []
    for i in range(total_pages):
        text = doc.load_page(i).get_text().strip()
        lines = [line for line in text.split('\n') if line.strip()]
        summary = ' | '.join(lines[:3])[:200]
        page_summaries.append(f"Page {i+1}: {summary}")

    # Prepare LLM prompt
    prompt = (
        "You are an expert at splitting educational test PDFs into logical, self-contained parts.\n"
        "Here are the first 3 non-empty lines from each page of a test PDF.\n\n"
        "Your task:\n"
        "- Split this PDF at the start of every new section, item set, part, or other natural division.\n"
        "- In particular, look for lines containing 'Section', 'Part', 'Item Set', 'Directions', or similar as likely split points.\n"
        "- Never split in the middle of a section, item set, or reference block, even if it means a part is longer than 50 pages.\n"
        "- Each part must be self-contained: no question in a part should reference material (figures, instructions, passages, etc.) that only appears in another part.\n"
        "- Return ONLY a JSON object with a single key 'split_pages' whose value is a sorted list of split page numbers (the first page of each part, 1-based).\n\n"
        "Page summaries:\n" + "\n".join(page_summaries)
    )

    # Define the JSON schema for structured output
    split_schema = {
        "type": "object",
        "properties": {
            "split_pages": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Sorted list of split page numbers (the first page of each logical part, 1-based)"
            }
        },
        "required": ["split_pages"],
        "additionalProperties": False
    }

    # Call OpenAI LLM using structured output with schema
    client = openai.Client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "logical_pdf_split",
                "schema": split_schema,
                "strict": True
            }
        },
        temperature=0,
        top_p=1,
        max_tokens=512,
        seed=42  # Use a fixed seed for deterministic splitting
    )
    llm_json = response.choices[0].message.content
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
        # Save the failed response for debugging
        debug_path = os.path.join(os.path.dirname(input_pdf_path), "debug_split_response.json")
        try:
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(llm_json)
            print(f"⚠️ Saved invalid LLM response to {debug_path}")
        except Exception as write_err:
            print(f"⚠️ Could not save debug response: {write_err}")

        raise ValueError(f"LLM returned non-parsable JSON for PDF splitting: {e}")
    except Exception as e:
        raise ValueError(f"LLM PDF splitting failed: {e}")

    split_pages = sorted(set(split_pages))

    # Build chunks from split points
    chunks = []
    for i in range(len(split_pages)):
        start = split_pages[i] - 1
        end = split_pages[i+1] - 1 if i+1 < len(split_pages) else total_pages
        chunks.append((start, end))

    # Write out each chunk as a new PDF, and track the start page (1-based in original PDF)
    chunk_infos = []  # List of (chunk_path, chunk_start_page)
    for idx, (start, end) in enumerate(chunks):
        chunk_doc = fitz.open()
        for i in range(start, end):
            chunk_doc.insert_pdf(doc, from_page=i, to_page=i)
        # Determine output path for chunk PDF
        if output_dir:
            base_name = os.path.splitext(os.path.basename(input_pdf_path))[0]
            chunks_dir = os.path.join(output_dir, "chunks")
            os.makedirs(chunks_dir, exist_ok=True)
            chunk_path = os.path.join(chunks_dir, f"{base_name}_ai_chunk_{idx+1}.pdf")
        else:
            chunk_path = f"{os.path.splitext(input_pdf_path)[0]}_ai_chunk_{idx+1}.pdf"
        chunk_doc.save(chunk_path)
        chunk_doc.close()
        chunk_infos.append((chunk_path, start + 1))  # start+1 is the 1-based start page in original PDF
    doc.close()
    return chunk_infos
