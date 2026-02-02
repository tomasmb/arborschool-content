#!/usr/bin/env python3
"""
Create individual question PDFs from segmented.json using bounding boxes.
This allows us to process questions with the new code.

Usage:
    python create_question_pdfs_from_segmented.py --test-name prueba-invierno-2026
"""

import json
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("❌ PyMuPDF not installed. Install with: pip install PyMuPDF")
    sys.exit(1)

# scripts/ -> pdf-to-qti/ -> pruebas/ -> app/ -> repo root
project_root = Path(__file__).resolve().parents[4]


def create_question_pdf(original_pdf_path: str, question_data: dict, output_path: str, margin: int = 10) -> bool:
    """
    Create a PDF for a single question using bounding boxes.

    Args:
        original_pdf_path: Path to original PDF
        question_data: Question data from segmented.json with page_nums and bboxes
        output_path: Where to save the question PDF
        margin: Margin in pixels to add around bboxes

    Returns:
        True if successful, False otherwise
    """
    try:
        doc = fitz.open(original_pdf_path)
        new_doc = fitz.open()  # Create new PDF

        page_nums = question_data.get("page_nums", [])
        bboxes = question_data.get("bboxes", [])

        if not page_nums or not bboxes:
            print("   ⚠️  Missing page_nums or bboxes, skipping")
            return False

        # Add pages for this question
        for page_num, bbox in zip(page_nums, bboxes):
            page_idx = page_num - 1  # Convert to 0-based
            if 0 <= page_idx < doc.page_count:
                page = doc.load_page(page_idx)

                # bbox is [x1, y1, x2, y2]
                x1, y1, x2, y2 = bbox

                # Add margin
                x1 = max(0, x1 - margin)
                y1 = max(0, y1 - margin)
                x2 = min(page.rect.width, x2 + margin)
                y2 = min(page.rect.height, y2 + margin)

                rect = fitz.Rect(x1, y1, x2, y2)

                # Create new page with same size as original
                new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)

                # Copy the region
                new_page.show_pdf_page(new_page.rect, doc, page_idx, clip=rect)

        # Save the new PDF
        new_doc.save(output_path)
        new_doc.close()
        doc.close()

        return True

    except Exception as e:
        print(f"   ❌ Error creating PDF: {e}")
        return False


def get_default_paths(test_name: str) -> dict[str, Path]:
    """Get default paths from test name."""
    data_dir = project_root / "app" / "data" / "pruebas"
    return {
        "segmented_json": data_dir / "procesadas" / test_name / "segmented.json",
        "original_pdf": data_dir / "raw" / f"{test_name}.pdf",
        "output_dir": data_dir / "finalizadas" / test_name / "questions",
    }


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Create individual question PDFs from segmented.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_question_pdfs_from_segmented.py --test-name prueba-invierno-2026
        """,
    )
    parser.add_argument("--test-name", required=True, help="Name of the test (e.g., prueba-invierno-2026)")
    parser.add_argument("--segmented-json", type=Path, help="Override: Path to segmented.json")
    parser.add_argument("--original-pdf", type=Path, help="Override: Path to original PDF")
    parser.add_argument("--output-dir", type=Path, help="Override: Output directory for question PDFs")

    args = parser.parse_args()

    # Get default paths from test name
    defaults = get_default_paths(args.test_name)
    args.segmented_json = args.segmented_json or defaults["segmented_json"]
    args.original_pdf = args.original_pdf or defaults["original_pdf"]
    args.output_dir = args.output_dir or defaults["output_dir"]

    # Load segmented.json
    segmented_path = Path(args.segmented_json)
    if not segmented_path.exists():
        print(f"❌ segmented.json not found: {segmented_path}")
        return

    print(f"📖 Loading {segmented_path}...")
    with open(segmented_path, "r", encoding="utf-8") as f:
        segmented_data = json.load(f)

    # Get original PDF
    original_pdf = Path(args.original_pdf)
    if not original_pdf.exists():
        print(f"❌ Original PDF not found: {original_pdf}")
        return

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get questions
    questions = segmented_data.get("validated_questions", segmented_data.get("questions", []))

    print(f"📋 Found {len(questions)} questions")
    print(f"📁 Output directory: {output_dir}")
    print()

    successful = 0
    failed = 0

    # Create PDF for each question
    for i, question in enumerate(questions, 1):
        question_id = question.get("id", f"Q{i}")
        question_number = question.get("number", i)

        # Use question_number if available, otherwise use id
        if "Q" in str(question_id).upper():
            filename = f"{question_id}.pdf"
        else:
            filename = f"Q{question_number}.pdf"

        output_path = output_dir / filename

        print(f"[{i}/{len(questions)}] Creating {filename}...", end=" ")

        if create_question_pdf(original_pdf_path=str(original_pdf), question_data=question, output_path=str(output_path)):
            print("✅")
            successful += 1
        else:
            print("❌")
            failed += 1

    print()
    print("=" * 60)
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📁 PDFs saved to: {output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
