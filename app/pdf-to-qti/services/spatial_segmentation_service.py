"""Line-based segmentation service.

Uses chunk.content (correct reading order) with simple line
numbering for reliable question boundary detection.
"""

import re
import logging
from typing import Dict, Any, List

# Import from parent package
try:
    from models import (
        SegmentationResult, SharedContext, QuestionChunk, 
        QuestionBoundary, ParsedPdf
    )
    from prompts.content_order_segmentation import create_content_order_segmentation_prompt
except ImportError:
    from ..models import (
        SegmentationResult, SharedContext, QuestionChunk, 
        QuestionBoundary, ParsedPdf
    )
    from ..prompts.content_order_segmentation import create_content_order_segmentation_prompt

from .ai_client_factory import AIClient
from .content_order_extractor import ContentOrderExtractor

logger = logging.getLogger(__name__)


class SpatialSegmentationService:
    """
    Segments text using line-based extraction.
    
    Simple, reliable approach:
    1. Extract text with line numbers [L1], [L2], [L3]...
    2. LLM identifies question boundaries by line number
    3. Extract content by line range
    """

    def __init__(self, ai_client: AIClient):
        """Initialize with AI client."""
        self.client = ai_client
        self.text_extractor = ContentOrderExtractor()

    def segment(
        self, 
        parsed_pdf: ParsedPdf,
        raw_parsed_pdf_data: Dict[str, Any] = None
    ) -> SegmentationResult:
        """Segment document into questions using line-based extraction."""
        logger.info("Extracting text with line numbers...")
        numbered_text, extraction_metadata = self.text_extractor.extract(
            parsed_pdf, raw_parsed_pdf_data=raw_parsed_pdf_data
        )
        
        line_index = extraction_metadata.get("line_index", {})
        total_lines = extraction_metadata.get("total_lines", 0)
        
        logger.info(
            f"Extracted {len(numbered_text)} chars, "
            f"{total_lines} lines across {extraction_metadata.get('total_chunks', 0)} pages"
        )
        
        if total_lines == 0:
            raise ValueError("No content extracted from document")
        
        condensed_text = self._create_condensed_text(numbered_text)
        prompt = create_content_order_segmentation_prompt(condensed_text, total_lines)
        
        logger.info(f"Prompt size: {len(prompt)} chars, max line: L{total_lines}")

        try:
            response_data = self.client.generate_json(
                prompt, thinking_level="high", max_tokens=65536
            )
            
            result = self._parse_response(response_data, line_index, total_lines)
            self._validate_boundaries(result.questions, line_index)
            
            return result
            
        except ValueError as e:
            raise ValueError(f"Segmentation failed - invalid response: {e}")
        except Exception as e:
            raise Exception(f"Segmentation failed - API error: {e}")

    def _create_condensed_text(self, text: str) -> str:
        """Create condensed text while preserving line markers."""
        lines = text.split('\n')
        condensed = []
        
        for line in lines:
            stripped = line.strip()
            
            if not stripped:
                continue
            
            if '[PAGE:' in line:
                condensed.append(line)
                continue
            
            if re.match(r'\[L\d+\]', stripped):
                if len(stripped) > 200:
                    marker_end = stripped.find(']') + 1
                    marker = stripped[:marker_end]
                    content = stripped[marker_end:].strip()
                    content = re.sub(r'\]\(https?://[^\)]+\)', '](IMG)', content)
                    if len(content) > 150:
                        content = content[:150] + "..."
                    condensed.append(f"{marker} {content}")
                else:
                    shortened = re.sub(r'\]\(https?://[^\)]+\)', '](IMG)', stripped)
                    condensed.append(shortened)
                continue
            
            if len(stripped) <= 150:
                condensed.append(line)
            else:
                condensed.append(stripped[:150] + "...")
        
        return '\n'.join(condensed)

    def _parse_response(
        self, data: Dict[str, Any], line_index: Dict[int, str], max_line: int
    ) -> SegmentationResult:
        """Parse LLM response and extract content using line numbers."""
        if "questions" not in data:
            raise ValueError("Missing 'questions' field in response")

        if not data["questions"]:
            raise ValueError("Empty questions array")

        questions_data = data["questions"]
        self._adjust_boundaries(questions_data, line_index, max_line)

        shared_contexts = []
        for ctx in data.get("shared_contexts", []):
            start = ctx.get("start_line")
            end = ctx.get("end_line")
            
            if start and end:
                try:
                    content = self.text_extractor.extract_by_line_range(
                        line_index, start, end
                    )
                    shared_contexts.append(SharedContext(
                        id=ctx.get("id", f"C{len(shared_contexts)+1}"),
                        content=content
                    ))
                except ValueError as e:
                    logger.warning(f"Failed to extract shared context: {e}")

        questions = []
        
        for q_data in questions_data:
            question_id = q_data.get("id", f"Q{len(questions)+1}")
            start = q_data.get("start_line")
            end = q_data.get("end_line")
            
            boundary = None
            if start and end:
                boundary = QuestionBoundary(
                    start_block_id=f"L{start}",
                    end_block_id=f"L{end}"
                )
            
            content = ""
            if start and end:
                try:
                    content = self.text_extractor.extract_by_line_range(
                        line_index, start, end
                    )
                    logger.info(f"Extracted {question_id}: L{start} → L{end} ({len(content)} chars)")
                except ValueError as e:
                    logger.error(f"Line extraction failed for {question_id}: {e}")
                    content = f"[Extraction failed: {e}]"
            else:
                content = f"[Missing line numbers for {question_id}]"
                logger.error(f"Missing line numbers for {question_id}")
            
            questions.append(QuestionChunk(
                id=question_id,
                content=content,
                shared_context_id=q_data.get("shared_context_id"),
                boundary=boundary
            ))

        return SegmentationResult(shared_contexts=shared_contexts, questions=questions)

    def _adjust_boundaries(
        self, questions_data: List[Dict[str, Any]], line_index: Dict[int, str], max_line: int
    ) -> None:
        """Adjust boundaries to fix common issues."""
        for q_data in questions_data:
            start = q_data.get("start_line")
            end = q_data.get("end_line")
            
            if start and start < 1:
                q_data["start_line"] = 1
            if end and end > max_line:
                q_data["end_line"] = max_line
            if start and start not in line_index:
                valid_lines = sorted(line_index.keys())
                for vl in valid_lines:
                    if vl >= start:
                        q_data["start_line"] = vl
                        break
            if end and end not in line_index:
                valid_lines = sorted(line_index.keys(), reverse=True)
                for vl in valid_lines:
                    if vl <= end:
                        q_data["end_line"] = vl
                        break

        for i in range(len(questions_data) - 1):
            current = questions_data[i]
            nxt = questions_data[i + 1]
            
            current_end = current.get("end_line")
            next_start = nxt.get("start_line")
            
            if current_end and next_start and current_end >= next_start:
                new_end = next_start - 1
                if new_end >= current.get("start_line", 1):
                    logger.info(
                        f"Fixed overlap: {current.get('id')} end L{current_end} → L{new_end}"
                    )
                    current["end_line"] = new_end

    def _validate_boundaries(
        self, questions: List[QuestionChunk], line_index: Dict[int, str]
    ) -> None:
        """Validate question boundaries and log warnings."""
        for question in questions:
            content = question.content
            
            if content.startswith("["):
                logger.error(f"⚠️ EXTRACTION ISSUE: {question.id} - {content[:100]}")
                continue
            
            q_numbers = re.findall(r'(?:^|\n)\s*(\d+)\s+[A-Z]', content)
            unique_nums = set(int(n) for n in q_numbers if n.isdigit())
            if len(unique_nums) > 1:
                logger.warning(
                    f"⚠️ POSSIBLE MERGE: {question.id} contains "
                    f"question numbers {sorted(unique_nums)}"
                )
            
            has_choices = bool(re.search(r'[A-J][\.\)]\s+', content))
            has_question_mark = '?' in content
            
            if has_question_mark and not has_choices:
                logger.warning(
                    f"⚠️ MISSING CHOICES: {question.id} has question but no A/B/C/D"
                )

