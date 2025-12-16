#!/usr/bin/env python3
"""Apply MathCorrector rules to segmented.json.

This script applies the same mathematical notation corrections
that MathCorrector uses on parsed.json, but applies them directly
to segmented.json (the output of step 2).

This allows us to:
1. Correct parsed.json using MathCorrector
2. Apply the same corrections to segmented.json without re-running step 2
3. Maintain consistency between step 1 and step 2 outputs
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .math_corrector import MathCorrector

logger = logging.getLogger(__name__)


def apply_corrections_to_segmented(
    segmented_json_path: str,
    output_path: str | None = None,
    backup: bool = True
) -> dict[str, Any]:
    """
    Apply MathCorrector corrections to segmented.json.
    
    Args:
        segmented_json_path: Path to segmented.json file
        output_path: Optional output path (default: overwrite original)
        backup: If True, create a backup before modifying
        
    Returns:
        Corrected segmented data
    """
    segmented_path = Path(segmented_json_path)
    if not segmented_path.exists():
        raise FileNotFoundError(f"File not found: {segmented_path}")
    
    # Create backup if requested
    if backup:
        backup_path = segmented_path.with_suffix('.json.backup')
        import shutil
        shutil.copy(segmented_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
    
    # Load segmented data
    with open(segmented_path, 'r', encoding='utf-8') as f:
        segmented_data = json.load(f)
    
    # Initialize corrector
    corrector = MathCorrector()
    
    # Apply corrections to each question's content
    corrected_count = 0
    total_questions = 0
    
    # Correct validated questions
    for question in segmented_data.get('validated_questions', []):
        total_questions += 1
        original_content = question.get('content', '')
        if original_content:
            corrected_content = corrector.correct_content(original_content)
            if corrected_content != original_content:
                question['content'] = corrected_content
                corrected_count += 1
                logger.debug(
                    f"Corrected question {question.get('id', 'unknown')}: "
                    f"{len(original_content)} → {len(corrected_content)} chars"
                )
    
    # Correct unvalidated questions (if any)
    for question in segmented_data.get('unvalidated_questions', []):
        total_questions += 1
        original_content = question.get('content', '')
        if original_content:
            corrected_content = corrector.correct_content(original_content)
            if corrected_content != original_content:
                question['content'] = corrected_content
                corrected_count += 1
                logger.debug(
                    f"Corrected unvalidated question {question.get('id', 'unknown')}"
                )
    
    # Correct shared contexts (if any)
    for context in segmented_data.get('shared_contexts', []):
        original_content = context.get('content', '')
        if original_content:
            corrected_content = corrector.correct_content(original_content)
            if corrected_content != original_content:
                context['content'] = corrected_content
                logger.debug(f"Corrected shared context {context.get('id', 'unknown')}")
    
    logger.info(
        f"Applied corrections to {corrected_count}/{total_questions} questions"
    )
    
    # Save corrected data
    output_path_obj = Path(output_path) if output_path else segmented_path
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path_obj, 'w', encoding='utf-8') as f:
        json.dump(segmented_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved corrected segmented data to: {output_path_obj}")
    
    return segmented_data


if __name__ == '__main__':
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Apply MathCorrector corrections to segmented.json'
    )
    parser.add_argument(
        'input_file',
        help='Path to segmented.json file'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output path (default: overwrite input file)'
    )
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Do not create backup file'
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
        apply_corrections_to_segmented(
            args.input_file,
            output_path=args.output,
            backup=not args.no_backup
        )
        print("✓ Corrections applied successfully")
    except Exception as e:
        logger.exception(f"Failed to apply corrections: {e}")
        sys.exit(1)
