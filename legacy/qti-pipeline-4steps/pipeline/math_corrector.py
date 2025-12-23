"""Mathematical Notation Corrector - Post-processes parsed.json to fix common OCR errors.

This module corrects mathematical notation errors introduced by Extend.ai parsing.
It runs as a post-processing step after PDF parsing and before segmentation.
"""

from __future__ import annotations

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)


class MathCorrector:
    """Corrects common mathematical notation errors in parsed PDF content."""

    def __init__(self):
        """Initialize the math corrector."""
        self.patterns = self._build_correction_patterns()

    def _build_correction_patterns(self) -> list[tuple[re.Pattern, str]]:
        """Build regex patterns for mathematical notation corrections."""
        patterns = []

        # Pattern 1: V followed by 4+ digits where last digit is exponent → √(base²)
        # Examples: V2002 → √(200²), V1502 → √(150²)
        # The pattern: V + base (3+ digits) + exponent (1 digit) → √(base²)
        patterns.append((
            re.compile(r'\bV(\d{3,})(\d)\b'),
            r'√(\1²)'  # V2002 → √(200²), V1502 → √(150²)
        ))

        # Pattern 2: V followed by 2-3 digits where last digit might be exponent
        # Examples: V52 → could be √(5²) but also could be √52
        # We'll be conservative: V + 2 digits → √(first digit²) only if context suggests
        # For now, treat V + 2 digits as √(first digit²) if followed by operations
        patterns.append((
            re.compile(r'\bV(\d)(\d)\b(?=\s*[+\-*/·])'),  # Only if followed by operator
            r'√(\1²)'  # V52 - → √(5²) -
        ))

        # Pattern 3: Number followed by V and number → number√number
        # Examples: 4V5 → 4√5, 2V5 → 2√5
        patterns.append((
            re.compile(r'(\d+)\s*V(\d+)\b'),
            r'\1√\2'  # 4V5 → 4√5
        ))

        # Pattern 4: Lowercase v in mathematical context (after digits)
        # Examples: 4v10 → 4√10
        patterns.append((
            re.compile(r'(\d+)\s*v(\d+)\b'),
            r'\1√\2'  # 4v10 → 4√10
        ))

        # Pattern 5: V followed by simple numbers (1-2 digits) → √number
        # Examples: V5 → √5, V10 → √10
        # Only if not part of a larger pattern (avoid URLs)
        patterns.append((
            re.compile(r'\bV(\d{1,2})\b(?![\w/])'),
            r'√\1'  # V5 → √5
        ))

        # Pattern 6: Standalone numbers with exponent - ONLY in clear math context
        # We're very conservative here to avoid false positives
        # Only convert if there's clear mathematical context:
        # - In expressions with square roots (√ already present)
        # - In subtraction/addition with another number of same pattern
        # - After operators in math expressions
        
        # Pattern 6a: In expressions with square roots (√ indicates math context)
        # This will be handled in the correct_content method with a function
        # Skip for now, handle in Step 4
        
        # Pattern 6b: Pairs of 4-digit numbers in subtraction (both likely exponents)
        # Example: "2002 - 1502" → "200² - 150²" (only if both match pattern)
        patterns.append((
            re.compile(r'\b(\d{3})(2)\s*-\s*(\d{3})(2)\b'),
            r'\1² - \3²'  # 2002 - 1502 → 200² - 150²
        ))
        
        # Pattern 6c: After V expressions (already has square root context)
        # Example: "V2002 - 1502" after V conversion becomes "√(200²) - 1502"
        # This will be handled in Step 3

        return patterns

    def correct_content(self, content: str) -> str:
        """
        Correct mathematical notation in content.
        
        Args:
            content: Original content string
            
        Returns:
            Corrected content string
        """
        corrected = content

        # Step 1: Handle V patterns first (V2002 → √(200²))
        # Apply V patterns first
        for pattern, replacement in self.patterns[:3]:  # First 3 patterns are for V
            corrected = pattern.sub(replacement, corrected)

        # Step 2: Handle standalone number patterns (2002 → 200²)
        # But only if not already part of a square root
        for pattern, replacement in self.patterns[3:]:  # Remaining patterns
            corrected = pattern.sub(replacement, corrected)

        # Step 3: Handle numbers after square root expressions (very specific context)
        # "√(200²) - 1502" → "√(200²) - 150²"
        # Only convert if there's already a square root in the expression
        corrected = re.sub(
            r'(√\([^)]*²[^)]*\))\s*-\s*(\d{3})(2)\b',
            r'\1 - \2²',
            corrected
        )
        corrected = re.sub(
            r'(√\([^)]*²[^)]*\))\s*\+\s*(\d{3})(2)\b',
            r'\1 + \2²',
            corrected
        )

        # Additional context-aware corrections
        corrected = self._correct_power_notation(corrected)
        corrected = self._remove_square_root_markers(corrected)

        return corrected

    def _correct_power_notation(self, content: str) -> str:
        """
        Correct power notation errors.
        
        Common errors:
        - 215 → could be 2¹⁵ (context-dependent)
        - 2010 → could be 2¹⁰ (context-dependent)
        """
        # This is more complex and context-dependent
        # For now, we'll skip this and let it be handled manually
        # or by AI-based correction if needed
        return content

    def _remove_square_root_markers(self, content: str) -> str:
        """
        Remove [x] markers that were used to indicate square root.
        
        After converting V to √, [x] markers are no longer needed
        in most contexts. However, we need to be careful:
        - [x] after √ expressions → remove (was square root indicator)
        - [x] after regular text → might be correct answer marker (keep)
        """
        # Remove [x] that appears after mathematical expressions with √
        # Pattern: expression with √ followed by [x]
        pattern = re.compile(r'([√\d\s\(\)\+\-\*·]+)\s*\[x\]')
        
        def replace_if_math(match):
            expr = match.group(1)
            # Check if expression contains √ or looks mathematical
            if '√' in expr or any(c.isdigit() for c in expr):
                return expr  # Remove [x]
            return match.group(0)  # Keep [x] if not clearly mathematical
        
        corrected = pattern.sub(replace_if_math, content)
        
        # Also remove [x] at end of lines that look like math expressions
        lines = corrected.split('\n')
        corrected_lines = []
        for line in lines:
            # If line ends with [x] and contains √ or looks mathematical
            if line.strip().endswith('[x]') and ('√' in line or re.search(r'\d+\s*[·\*\+-]', line)):
                line = line.replace('[x]', '').strip()
            corrected_lines.append(line)
        
        return '\n'.join(corrected_lines)

    def correct_parsed_data(self, parsed_data: dict[str, Any]) -> dict[str, Any]:
        """
        Correct mathematical notation in parsed PDF data structure.
        
        Args:
            parsed_data: Parsed PDF data (same structure as Extend.ai output)
            
        Returns:
            Corrected parsed data with same structure
        """
        corrected_data = parsed_data.copy()
        chunks_corrected = 0

        if 'chunks' in corrected_data:
            for chunk in corrected_data['chunks']:
                original_content = chunk.get('content', '')
                if original_content:
                    corrected_content = self.correct_content(original_content)
                    if corrected_content != original_content:
                        chunk['content'] = corrected_content
                        chunks_corrected += 1
                    
                    # Also correct in blocks if present
                    if 'blocks' in chunk:
                        for block in chunk['blocks']:
                            if 'content' in block:
                                block['content'] = self.correct_content(block['content'])

        logger.info(f"Corrected mathematical notation in {chunks_corrected} chunks")
        return corrected_data


def correct_parsed_json(json_path: str, output_path: str | None = None) -> dict[str, Any]:
    """
    Load, correct, and optionally save parsed.json.
    
    Args:
        json_path: Path to parsed.json file
        output_path: Optional path to save corrected version (if None, overwrites)
        
    Returns:
        Corrected parsed data
    """
    import json
    
    with open(json_path, 'r', encoding='utf-8') as f:
        parsed_data = json.load(f)
    
    corrector = MathCorrector()
    corrected_data = corrector.correct_parsed_data(parsed_data)
    
    save_path = output_path or json_path
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(corrected_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved corrected parsed data to: {save_path}")
    return corrected_data
