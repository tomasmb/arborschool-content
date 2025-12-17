#!/usr/bin/env python3
"""Regenerate QTI XML for specific questions.

This utility allows regenerating QTI XML for a subset of questions
after making manual corrections to segmented.json.

Usage:
    python -m app.qti_pipeline_4steps.pipeline.regenerate_qti_for_questions \
        --questions Q18 Q19 Q46 \
        --input segmented.json \
        --output ./output
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

try:
    from models import SegmenterOutput, QuestionChunk, SharedContext
    from pipeline import Generator
except ImportError:
    import sys
    from pathlib import Path
    # Updated path after folder rename
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from models import SegmenterOutput, QuestionChunk, SharedContext
    from pipeline import Generator

logger = logging.getLogger(__name__)


def regenerate_qti_for_questions(
    segmented_json_path: str,
    question_ids: list[str],
    output_dir: str,
    model_provider: str = "gemini",
    skip_validation: bool = False
) -> dict[str, Any]:
    """
    Regenerate QTI XML for specific questions.
    
    Args:
        segmented_json_path: Path to segmented.json
        question_ids: List of question IDs to regenerate (e.g., ["Q18", "Q19"])
        output_dir: Directory where QTI files will be saved
        model_provider: AI provider to use
        skip_validation: If True, skip XSD and semantic validation
        
    Returns:
        Dictionary with regeneration results
    """
    segmented_path = Path(segmented_json_path)
    if not segmented_path.exists():
        raise FileNotFoundError(f"File not found: {segmented_path}")
    
    # Load segmented data
    with open(segmented_path, 'r', encoding='utf-8') as f:
        segmented_data = json.load(f)
    
    segmenter_output = SegmenterOutput(**segmented_data)
    
    # Filter to only requested questions
    requested_questions = [
        q for q in segmenter_output.validated_questions
        if q.id in question_ids
    ]
    
    # Check for missing questions
    found_ids = {q.id for q in requested_questions}
    missing_ids = set(question_ids) - found_ids
    
    if missing_ids:
        logger.warning(
            f"Questions not found in segmented.json: {missing_ids}. "
            f"These may be in unvalidated_questions or not exist."
        )
        # Try to find in unvalidated questions
        for q in segmenter_output.unvalidated_questions:
            if q.id in missing_ids:
                requested_questions.append(q)
                found_ids.add(q.id)
        
        still_missing = set(question_ids) - found_ids
        if still_missing:
            raise ValueError(
                f"Questions not found: {still_missing}. "
                f"Available questions: {sorted([q.id for q in segmenter_output.validated_questions])}"
            )
    
    logger.info(
        f"Regenerating QTI for {len(requested_questions)} questions: "
        f"{sorted([q.id for q in requested_questions])}"
    )
    
    # Create a filtered SegmenterOutput with only requested questions
    filtered_output = SegmenterOutput(
        success=True,
        shared_contexts=segmenter_output.shared_contexts,
        validated_questions=requested_questions,
        unvalidated_questions=[],
        errors=[]
    )
    
    # Generate QTI
    generator = Generator(
        model_provider=model_provider,
        skip_validation=skip_validation
    )
    
    generator_output = generator.generate(
        filtered_output,
        output_dir=output_dir,
        source_format="markdown"
    )
    
    results = {
        "requested": question_ids,
        "generated": [item.question_id for item in generator_output.qti_items],
        "failed": generator_output.errors,
        "success": generator_output.success
    }
    
    return results


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Regenerate QTI XML for specific questions'
    )
    parser.add_argument(
        '--questions', '-q',
        nargs='+',
        required=True,
        help='Question IDs to regenerate (e.g., Q18 Q19 Q46)'
    )
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='Path to segmented.json'
    )
    parser.add_argument(
        '--output', '-o',
        required=True,
        help='Output directory for QTI files'
    )
    parser.add_argument(
        '--provider', '-p',
        choices=['gemini', 'gpt', 'opus'],
        default='gemini',
        help='AI provider (default: gemini)'
    )
    parser.add_argument(
        '--skip-validation',
        action='store_true',
        help='Skip XSD and semantic validation'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        results = regenerate_qti_for_questions(
            args.input,
            args.questions,
            args.output,
            model_provider=args.provider,
            skip_validation=args.skip_validation
        )
        
        print("\n" + "=" * 70)
        print("REGENERATION RESULTS")
        print("=" * 70)
        print(f"Requested: {len(results['requested'])} questions")
        print(f"Generated: {len(results['generated'])} QTI files")
        if results['failed']:
            print(f"Failed: {len(results['failed'])} questions")
            for error in results['failed']:
                print(f"  - {error}")
        print("=" * 70)
        
    except Exception as e:
        logger.exception(f"Failed to regenerate QTI: {e}")
        exit(1)
