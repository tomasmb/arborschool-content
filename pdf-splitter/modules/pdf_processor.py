"""
PDF Processor for Lambda Deployment

This module provides the bridge between our working PDF segmentation pipeline
and AWS Lambda with S3 upload functionality.
"""

import os
import json
import tempfile
import requests
import base64
from typing import List, Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError
import fitz  # PyMuPDF

# Import our working modules
from .chunk_segmenter import segment_pdf_with_llm, get_question_statistics
from .pdf_utils import create_pdf_from_region, merge_pdfs, split_pdf_by_ai
from .split_decision import should_split_pdf, SPLIT_PAGE_THRESHOLD

# Import main functions - need to handle different import contexts
try:
    # When running as Lambda
    from main import compute_bboxes_for_segments, create_question_pdfs
except ImportError:
    # When running locally 
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from main import compute_bboxes_for_segments, create_question_pdfs


def download_pdf_from_url(url: str, temp_path: str) -> None:
    """Download PDF from URL to temporary file."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    
    with open(temp_path, 'wb') as f:
        f.write(response.content)


def save_base64_pdf(base64_data: str, temp_path: str) -> None:
    """Save base64 encoded PDF data to temporary file."""
    pdf_data = base64.b64decode(base64_data)
    
    with open(temp_path, 'wb') as f:
        f.write(pdf_data)


def upload_file_to_s3(file_path: str, session: boto3.Session, bucket_name: str, s3_key: str) -> str:
    """
    Upload file to S3 and return the public URL.
    
    Args:
        file_path: Local path to file to upload
        session: Boto3 session with AWS credentials
        bucket_name: S3 bucket name
        s3_key: S3 object key
        
    Returns:
        Public S3 URL
    """
    s3_client = session.client('s3')
    
    try:
        # Upload file
        s3_client.upload_file(file_path, bucket_name, s3_key)
        
        # Generate public URL
        s3_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"
        return s3_url
        
    except ClientError as e:
        raise Exception(f"Failed to upload {s3_key} to S3: {str(e)}")


def process_pdf_to_s3(
    pdf_source: str,
    is_base64: bool,
    session: boto3.Session,
    bucket_name: str,
    path_prefix: str,
    test_id: str,
    initial_chunk_size: Optional[int] = 20
) -> List[str]:
    """
    Process PDF and upload question PDFs to S3.
    
    Args:
        pdf_source: URL or base64 encoded PDF data
        is_base64: True if pdf_source is base64 data, False if URL
        session: Boto3 session with AWS credentials
        bucket_name: S3 bucket name
        path_prefix: S3 path prefix for uploaded files
        test_id: Unique identifier for this test
        initial_chunk_size: Optional chunk size parameter
        
    Returns:
        List of S3 URLs for generated question PDFs
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        # Step 1: Get PDF file
        input_pdf_path = os.path.join(temp_dir, "input.pdf")
        
        if is_base64:
            save_base64_pdf(pdf_source, input_pdf_path)
        else:
            download_pdf_from_url(pdf_source, input_pdf_path)
        
        # Step 2: Process PDF using our working pipeline
        print(f"🚀 Processing PDF with OpenAI's direct upload: {input_pdf_path}")
        
        # Create local output directory
        output_dir = os.path.join(temp_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # Decide if we need to split: only for large PDFs (>40 pages)
        doc = fitz.open(input_pdf_path)
        total_pages = doc.page_count
        doc.close()
        
        if should_split_pdf(total_pages):
            print(
                f"🔀 PDF has {total_pages} pages (>" \
                f"{SPLIT_PAGE_THRESHOLD}). Using AI to split into logical parts..."
            )
            chunks = split_pdf_by_ai(input_pdf_path, output_dir)
        else:
            # Treat the whole PDF as a single chunk
            chunks = [(input_pdf_path, 1)]

        if len(chunks) > 1:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            all_urls: List[str] = []
            
            def process_chunk(idx: int, chunk_path: str) -> List[str]:
                for attempt in range(1, 3):
                    try:
                        print(f"📦 Processing chunk {idx}/{len(chunks)}: {chunk_path}")
                        chunk_output_dir = os.path.join(output_dir, f"part_{idx}")
                        os.makedirs(chunk_output_dir, exist_ok=True)
                        results = segment_pdf_with_llm(
                            pdf_path=chunk_path,
                            output_file=os.path.join(chunk_output_dir, "segmentation_results.json")
                        )
                        results = compute_bboxes_for_segments(results, chunk_path)
                        create_question_pdfs(results, chunk_path, chunk_output_dir, fail_on_validation_error=False)
                        failed_log = os.path.join(chunk_output_dir, "failed_questions_log.json")
                        if os.path.exists(failed_log):
                            with open(failed_log, 'r') as f:
                                failed = json.load(f)
                            raise Exception(f"Quality validation failed for chunk {idx}: {len(failed)} questions failed")
                        urls: List[str] = []
                        questions_dir = os.path.join(chunk_output_dir, "questions")
                        if os.path.exists(questions_dir):
                            for filename in sorted(os.listdir(questions_dir)):
                                if filename.endswith('.pdf'):
                                    local_path = os.path.join(questions_dir, filename)
                                    s3_key = f"{path_prefix}{test_id}/part_{idx}/{filename}"
                                    url = upload_file_to_s3(local_path, session, bucket_name, s3_key)
                                    urls.append(url)
                        return urls
                    except Exception as e:
                        if attempt < 2:
                            print(f"🔄 Retry {attempt} for chunk {idx}: {e}")
                        else:
                            raise Exception(f"Chunk {idx} failed after {attempt} attempts: {e}")

            # Run chunk processing in parallel, abort on first chunk failure
            with ThreadPoolExecutor(max_workers=len(chunks)) as executor:
                future_to_idx = {
                    executor.submit(process_chunk, idx, chunk_path): idx
                    for idx, (chunk_path, _) in enumerate(chunks, start=1)
                }
                
                # Collect results in a dictionary to allow for reordering
                chunk_results = {}
                for future in as_completed(future_to_idx):
                    idx = future_to_idx[future]
                    try:
                        chunk_results[idx] = future.result()
                    except Exception as e:
                        # On first failure, cancel all other pending tasks and abort
                        print(f"❌ Chunk {idx} failed. Cancelling remaining tasks.")
                        for f in future_to_idx:
                            if not f.done():
                                f.cancel()
                        raise
                
                # After all chunks succeeded, assemble the results in correct order
                for i in range(1, len(chunks) + 1):
                    all_urls.extend(chunk_results.get(i, []))

            return all_urls

        try:
            # Use our working segmentation pipeline
            print("🔮 Using OpenAI's native PDF processing...")
            results = segment_pdf_with_llm(
                pdf_path=input_pdf_path,
                output_file=os.path.join(output_dir, "segmentation_results.json")
            )
            
            # Compute bounding boxes using PyMuPDF
            results = compute_bboxes_for_segments(results, input_pdf_path)
            
            # Generate statistics
            stats = get_question_statistics(results)
            
            print(f"📊 Processing Results:")
            print(f"   📝 Questions found: {stats['total_questions']}")
            print(f"   📚 Multi-question references found: {stats['total_multi_question_references']}")
            
            # Create question PDFs
            # For single-chunk processing in Lambda, fail immediately on validation errors
            create_question_pdfs(results, input_pdf_path, output_dir, fail_on_validation_error=True)
            
            # Step 3: Upload question PDFs to S3
            question_urls = []
            questions_dir = os.path.join(output_dir, "questions")
            
            if os.path.exists(questions_dir):
                # Upload each question PDF
                for filename in sorted(os.listdir(questions_dir)):
                    if filename.endswith('.pdf'):
                        local_path = os.path.join(questions_dir, filename)
                        s3_key = f"{path_prefix}{test_id}/{filename}"
                        
                        try:
                            s3_url = upload_file_to_s3(local_path, session, bucket_name, s3_key)
                            question_urls.append(s3_url)
                            print(f"✅ Uploaded: {filename} -> {s3_url}")
                        except Exception as e:
                            print(f"❌ Failed to upload {filename}: {str(e)}")
                            raise
                
                # Also upload metadata files
                metadata_files = [
                    "segmentation_results.json",
                    "processing_statistics.json", 
                    "questions_list.json",
                    "question_references.json"
                ]
                
                for metadata_file in metadata_files:
                    metadata_path = os.path.join(output_dir, metadata_file)
                    if os.path.exists(metadata_path):
                        s3_key = f"{path_prefix}{test_id}/metadata/{metadata_file}"
                        try:
                            upload_file_to_s3(metadata_path, session, bucket_name, s3_key)
                            print(f"✅ Uploaded metadata: {metadata_file}")
                        except Exception as e:
                            print(f"⚠️  Failed to upload metadata {metadata_file}: {str(e)}")
                            # Don't fail the whole process for metadata upload failures
            
            print(f"🎉 Successfully processed PDF and uploaded {len(question_urls)} question PDFs")
            return question_urls
            
        except Exception as e:
            print(f"❌ Error processing PDF: {str(e)}")
            raise Exception(f"PDF processing failed: {str(e)}") 