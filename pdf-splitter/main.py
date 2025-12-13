#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF Splitter Main Module - Direct PDF Upload Processing

This is the main entry point for the PDF splitter application.
Uses OpenAI's revolutionary direct PDF upload feature for maximum accuracy.
"""

import os
import argparse
import json
import shutil
from modules.chunk_segmenter import segment_pdf_with_llm, get_question_statistics
from modules.bbox_computer import compute_bboxes_for_segments
from modules.pdf_utils import create_question_pdfs, split_pdf_by_ai
from modules.part_validator import validate_segmentation_results
from modules.split_decision import should_split_pdf, SPLIT_PAGE_THRESHOLD

def process_pdf(input_pdf_path: str, output_dir: str, start_page_in_original: int = 1, run_summary: list = None, only_part: int = None):
    """
    Revolutionary PDF processing using OpenAI's direct PDF upload.
    No preprocessing, no image conversion, no coordinate scaling - just pure intelligence.
    """
    if not os.path.exists(input_pdf_path):
        print(f"❌ Error: Input PDF not found at {input_pdf_path}")
        return
        
    # Create output directory 
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"📁 Created output directory: {output_dir}")

    # --- AI-based splitting for large PDFs ---
    import fitz
    doc = fitz.open(input_pdf_path)
    total_pages = doc.page_count
    doc.close()
    
    part_summary = {
        "part_name": os.path.basename(input_pdf_path),
        "status": "Skipped",
        "total_questions": 0,
        "reason": ""
    }

    if should_split_pdf(total_pages):
        print(
            f"🔀 PDF has {total_pages} pages (>" \
            f"{SPLIT_PAGE_THRESHOLD}). Using AI to split into logical parts..."
        )
        try:
            ai_chunks = split_pdf_by_ai(input_pdf_path, output_dir)
        except Exception as e:
            print(f"❌ Failed to split PDF with AI: {e}")
            # If splitting fails, treat the whole PDF as a single part
            ai_chunks = [(input_pdf_path, 1)]
        
        if len(ai_chunks) > 1:
            print(f"🧩 Split into {len(ai_chunks)} parts. Processing each part independently...")
            # This is where the main processing now happens, in the main() function loop
            return ai_chunks

    print(f"🚀 Processing PDF with OpenAI's direct upload: {input_pdf_path}")

    try:
        # Process PDF using OpenAI's native PDF upload
        print("\n🔮 Using OpenAI's native PDF processing...")
        results = segment_pdf_with_llm(
            pdf_path=input_pdf_path,
            output_file=os.path.join(output_dir, "segmentation_results.json")
        )

        # Compute bounding boxes using PyMuPDF and start_marker
        results = compute_bboxes_for_segments(results, input_pdf_path, start_page_in_original=start_page_in_original)
        
        # --- Per-part validation ---
        is_valid = validate_segmentation_results(results, output_dir)
        if not is_valid:
            part_summary["status"] = "Failed Validation"
            part_summary["reason"] = "One or more segments could not be located in the PDF."
            if run_summary is not None:
                run_summary.append(part_summary)
            # Early exit for this part, but don't raise error for the whole process
            return None

        # Generate statistics
        stats = get_question_statistics(results)
        
        print(f"\n📊 Processing Results:")
        print(f"   📝 Questions found: {stats['total_questions']}")
        print(f"   📚 Multi-question references found: {stats['total_multi_question_references']}")
        print(f"   🚫 Unrelated content segments found: {stats['total_unrelated_content_segments']}")
        print(f"   📄 Pages with questions: {stats['pages_with_questions']}")
        print(f"   📑 Multi-page questions: {stats['multi_page_questions']}")
        
        if stats['question_types']:
            print(f"   🔢 Question types: {dict(stats['question_types'])}")
        if stats['reference_types']:
            print(f"   📖 Reference types: {dict(stats['reference_types'])}")
        if stats['unrelated_content_types']:
            print(f"   🚫 Unrelated content types: {dict(stats['unrelated_content_types'])}")
        
        # Save detailed statistics
        stats_file = os.path.join(output_dir, "processing_statistics.json")
        # Convert set to list for JSON serialization
        stats_copy = stats.copy()
        stats_copy['pages_with_questions'] = stats['pages_with_questions']
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats_copy, f, indent=2, ensure_ascii=False, sort_keys=True)
        print(f"📈 Statistics saved to: {stats_file}")
        
        # Create simple question list for easy access
        questions_list = []
        for i, question in enumerate(results.get('questions', []), 1):
            questions_list.append({
                'number': i,
                'id': question.get('id', f'Q{i}'),
                'text': question.get('text', ''),
                'pages': question.get('page_nums', []),
                'type': question.get('type', 'question'),
                'multi_page': question.get('multi_page', False)
            })
        
        questions_file = os.path.join(output_dir, "questions_list.json")
        with open(questions_file, 'w', encoding='utf-8') as f:
            json.dump(questions_list, f, indent=2, ensure_ascii=False, sort_keys=True)
        print(f"📋 Questions list saved to: {questions_file}")
        
        # Save per-question shared references detail
        question_refs = []
        for i, question in enumerate(results.get('questions', []), 1):
            refs = []
            for rid in question.get('multi_question_references', []):
                ref_obj = next((r for r in results.get('multi_question_references', []) if r.get('id') == rid), None)
                if ref_obj:
                    refs.append(ref_obj)
            question_refs.append({'number': i, 'references': refs})
        refs_file = os.path.join(output_dir, 'question_references.json')
        with open(refs_file, 'w', encoding='utf-8') as f:
            json.dump(question_refs, f, indent=2, ensure_ascii=False, sort_keys=True)
        print(f"🗂 Question references saved to: {refs_file}")
        
        # Create self-contained question PDFs (questions + same-page references)
        # For single PDF processing (run_summary is None), fail immediately on validation errors
        fail_on_validation_error = (run_summary is None)
        create_question_pdfs(results, input_pdf_path, output_dir, fail_on_validation_error=fail_on_validation_error)
        
        print(f"🎯 Revolutionary approach used: Direct PDF Upload with o4-mini")

        # Check for failed questions after PDF creation (only for per-part processing)
        failed_log_path = os.path.join(output_dir, "failed_questions_log.json")
        failed_count = 0
        if os.path.exists(failed_log_path):
            with open(failed_log_path, 'r') as f:
                failed_questions = json.load(f)
                failed_count = len(failed_questions)

        part_summary["status"] = "Success"
        part_summary["total_questions"] = stats['total_questions']
        if run_summary is not None:
            # Per-part processing: update summary with pass/fail counts
            part_summary["questions_passed"] = stats['total_questions'] - failed_count
            part_summary["questions_failed"] = failed_count
            if failed_count > 0:
                part_summary["status"] = "Partial Success"
            run_summary.append(part_summary)
        else:
            # Single PDF processing: all questions passed if we reach here
            part_summary["questions_passed"] = stats['total_questions']
            part_summary["questions_failed"] = 0
        
        return results
    
    except Exception as e:
        print(f"❌ Error processing PDF: {str(e)}")
        part_summary["status"] = "Failed"
        part_summary["reason"] = str(e)
        if run_summary is not None:
            run_summary.append(part_summary)
        return None

def main():
    """Main entry point for the PDF splitter application."""
    parser = argparse.ArgumentParser(
        description="Segments a PDF into questions and references using document-wide processing."
    )
    parser.add_argument("input_pdf", help="Path to the input PDF file.")
    parser.add_argument("output_dir", help="Directory to save the output results.")
    parser.add_argument("--clean", action="store_true", 
                       help="Clean the output directory before processing.")
    parser.add_argument("--start-part", type=int, default=1,
                        help="Start processing from a specific part number.")
    parser.add_argument("--only-part", type=int, default=None,
                        help="Process only a single specific part.")

    args = parser.parse_args()
    
    # Smart cleaning logic
    if args.clean:
        if args.only_part is not None:
            # If only processing one part, just clean that part's directory
            part_dir_to_clean = os.path.join(args.output_dir, f"part_{args.only_part}")
            if os.path.exists(part_dir_to_clean):
                print(f"🧹 Cleaning specific part directory: {part_dir_to_clean}")
                shutil.rmtree(part_dir_to_clean)
        else:
            # Otherwise, clean the entire output directory
            if os.path.exists(args.output_dir):
                print(f"🧹 Cleaning entire output directory: {args.output_dir}")
                shutil.rmtree(args.output_dir)

    print("🚀 Starting PDF Segmentation with Direct PDF Upload Processing...")
    
    # This is now the main processing controller
    run_summary = []
    
    # First, get the chunks. This might return the original PDF path if it's small or splitting fails.
    chunks = process_pdf(args.input_pdf, args.output_dir)
    
    if isinstance(chunks, list) and len(chunks) > 1:
        # We have multiple parts from a large PDF
        for i, (chunk_path, chunk_start_page) in enumerate(chunks, 1):
            part_num = i
            
            # Handle --start-part and --only-part logic
            if args.only_part is not None:
                if part_num != args.only_part:
                    continue # Skip if not the specified part
            elif part_num < args.start_part:
                continue # Skip if before the start part

            part_output_dir = os.path.join(args.output_dir, f"part_{part_num}")
            print(f"\n🚀 Processing part {part_num}/{len(chunks)}: {chunk_path}")
            
            # Process this individual part
            process_pdf(chunk_path, part_output_dir, start_page_in_original=chunk_start_page, run_summary=run_summary, only_part=args.only_part)

            if args.only_part is not None and part_num == args.only_part:
                break # Stop after processing the specified part

    elif chunks is not None:
        # This was a small PDF, and it has already been processed.
        # The summary was already added inside the single process_pdf call.
        # We need to get the summary info if it's not already populated.
        if not run_summary:
            run_summary.append({
                "part_name": os.path.basename(args.input_pdf),
                "status": "Success", # Assume success if we reached here
                "total_questions": len(chunks.get("questions", [])),
                "reason": ""
            })

    print("\n🏁 PDF Segmentation Finished. Run Summary:")
    print("="*80)
    print(f"{'Part':<60} | {'Status':<15} | {'Passed':<10} | {'Failed':<10} | {'Reason'}")
    print("-"*120)
    total_passed = 0
    total_failed = 0
    for summary in run_summary:
        passed = summary.get('questions_passed', 0)
        failed = summary.get('questions_failed', 0)
        print(f"{summary.get('part_name', 'N/A'):<60} | {summary.get('status', 'Unknown'):<15} | {passed:<10} | {failed:<10} | {summary.get('reason', '')}")
        total_passed += passed
        total_failed += failed
    print("-"*120)
    print(f"Total questions passed validation: {total_passed}")
    print(f"Total questions failed validation: {total_failed}")

    # Cleanup temporary chunk PDFs
    chunks_dir = os.path.join(args.output_dir, "chunks")
    if os.path.exists(chunks_dir):
        print(f"🧹 Removing temporary chunk PDFs: {chunks_dir}")
        shutil.rmtree(chunks_dir)

if __name__ == "__main__":
    main() 