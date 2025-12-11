"""Content-order extractor using parsed PDF chunk.content.

Uses chunk.content (correct multi-column reading order) with simple line 
numbering for reliable LLM-based segmentation.
"""

import logging
import re
from typing import Dict, List, Tuple, Any

# Import from parent package
try:
    from models import ParsedPdf, Chunk
except ImportError:
    from ..models import ParsedPdf, Chunk

logger = logging.getLogger(__name__)


class ContentOrderExtractor:
    """
    Extracts text using chunk.content with line numbering.
    
    Simple, reliable approach:
    - Uses chunk.content directly (correct reading order)
    - Numbers paragraphs sequentially: [L1], [L2], [L3]...
    - LLM references lines by number
    - Extraction is trivial: just slice by line number
    """

    def __init__(self):
        """Initialize extractor."""
        pass

    def extract(
        self,
        parsed_pdf: ParsedPdf,
        raw_parsed_pdf_data: Dict[str, Any] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Extract text with line numbers in correct reading order.
        
        Returns:
            Tuple of (numbered_text, metadata)
        """
        image_url_map = self._build_image_url_map(raw_parsed_pdf_data)
        
        output_parts = []
        line_index: Dict[int, str] = {}
        current_line = 1
        images_found = []
        tables_found = []
        
        for chunk in parsed_pdf.chunks:
            page_num = self._get_page_number(chunk)
            chunk_content = chunk.content or ""
            if not chunk_content.strip():
                continue
            
            chunk_content = self._inject_image_urls(chunk_content, chunk, image_url_map)
            paragraphs = self._split_into_paragraphs(chunk_content)
            
            page_parts = [f"[PAGE:{page_num}]"]
            
            for para in paragraphs:
                if not para.strip():
                    continue
                
                line_index[current_line] = para
                page_parts.append(f"[L{current_line}] {para}")
                
                if '![' in para and '](' in para:
                    images_found.append({
                        "line": current_line,
                        "page": page_num,
                        "content": para[:100]
                    })
                
                if '|' in para and para.count('|') >= 2:
                    tables_found.append({"line": current_line, "page": page_num})
                
                current_line += 1
            
            output_parts.append("\n\n".join(page_parts))
        
        full_text = "\n\n".join(output_parts)
        
        metadata = {
            "line_index": line_index,
            "total_lines": current_line - 1,
            "total_chunks": len(parsed_pdf.chunks),
            "images": images_found,
            "tables": tables_found
        }
        
        logger.info(
            f"Extracted {metadata['total_lines']} lines from "
            f"{metadata['total_chunks']} pages"
        )
        
        return full_text, metadata

    def _split_into_paragraphs(self, content: str) -> List[str]:
        """Split content into logical paragraphs."""
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        raw_blocks = re.split(r'\n\s*\n', content)
        
        paragraphs = []
        for block in raw_blocks:
            block = block.strip()
            if not block:
                continue
            
            if '|' in block and block.count('|') >= 4:
                paragraphs.append(block)
            else:
                lines = block.split('\n')
                if len(lines) <= 3:
                    paragraphs.append(block)
                else:
                    if self._is_answer_choices(block):
                        paragraphs.append(block)
                    else:
                        for line in lines:
                            line = line.strip()
                            if line:
                                paragraphs.append(line)
        
        return paragraphs

    def _is_answer_choices(self, text: str) -> bool:
        """Check if text block contains answer choices (A., B., C., D.)."""
        lines = text.strip().split('\n')
        choice_pattern = re.compile(r'^\s*[A-J][\.\)]\s+')
        choice_count = sum(1 for line in lines if choice_pattern.match(line))
        return choice_count >= 2

    def _get_page_number(self, chunk: Chunk) -> int:
        """Extract page number from chunk metadata."""
        page_range = chunk.metadata.pageRange if chunk.metadata else None
        return page_range.get('start', 0) if page_range else 0

    def _build_image_url_map(self, raw_parsed_pdf_data: Dict[str, Any]) -> Dict[str, str]:
        """Build map of block_id -> imageUrl from raw data."""
        if not raw_parsed_pdf_data:
            return {}

        url_map = {}
        for chunk_data in raw_parsed_pdf_data.get("chunks", []):
            for block in chunk_data.get("blocks", []):
                if block.get("type") == "figure":
                    block_id = block.get("id")
                    details = block.get("details", {})
                    image_url = details.get("imageUrl")
                    if block_id and image_url:
                        url_map[block_id] = image_url

        logger.info(f"Found {len(url_map)} figure blocks with image URLs")
        return url_map

    def _inject_image_urls(
        self, content: str, chunk: Chunk, image_url_map: Dict[str, str]
    ) -> str:
        """Inject image URLs into figure blocks in chunk content."""
        if not chunk.blocks or not image_url_map:
            return content
        
        figure_blocks = []
        for block in chunk.blocks:
            if block.type != "figure":
                continue
            block_id = block.id
            image_url = image_url_map.get(block_id)
            if image_url:
                figure_blocks.append({
                    'id': block_id,
                    'content': block.content,
                    'url': image_url,
                    'caption': self._extract_caption(block.content)
                })
        
        if not figure_blocks:
            return content
        
        for fig in figure_blocks:
            markdown_image = f"![{fig['caption']}]({fig['url']})"
            
            if fig['content'] in content:
                content = content.replace(fig['content'], markdown_image, 1)
                continue
            
            figure_pattern = re.compile(
                r'<figure[^>]*>.*?</figure>',
                re.DOTALL | re.IGNORECASE
            )
            
            if figure_pattern.search(content):
                content = figure_pattern.sub(markdown_image, content, count=1)
                continue
            
            content = self._inject_image_for_plain_figure(content, fig, markdown_image)
        
        return content

    def _inject_image_for_plain_figure(
        self, content: str, fig: Dict[str, str], markdown_image: str
    ) -> str:
        """Inject markdown image for a figure that appears as plain text."""
        inner = fig['content']
        inner = re.sub(r'<figure[^>]*>', '', inner, flags=re.IGNORECASE)
        inner = re.sub(r'</figure>', '', inner, flags=re.IGNORECASE)
        inner = re.sub(r'<caption>.*?</caption>', '', inner, flags=re.DOTALL | re.IGNORECASE)
        inner = inner.strip()
        
        if not inner:
            return content
        
        lines = inner.split('\n')
        anchor_lines = []
        for line in lines:
            line = line.strip()
            if line:
                anchor_lines.append(line)
                if len(anchor_lines) >= 2:
                    break
        
        if not anchor_lines:
            return content
        
        anchor_pattern = r'\s*'.join(re.escape(line) for line in anchor_lines)
        anchor_regex = re.compile(anchor_pattern)
        
        match = anchor_regex.search(content)
        if match:
            insert_pos = match.start()
            line_start = content.rfind('\n', 0, insert_pos)
            if line_start == -1:
                line_start = 0
            else:
                line_start += 1
            
            content = content[:line_start] + markdown_image + "\n\n" + content[line_start:]
        else:
            first_line = anchor_lines[0]
            if first_line in content:
                idx = content.find(first_line)
                line_start = content.rfind('\n', 0, idx)
                if line_start == -1:
                    line_start = 0
                else:
                    line_start += 1
                
                content = content[:line_start] + markdown_image + "\n\n" + content[line_start:]
        
        return content

    def _extract_caption(self, figure_content: str) -> str:
        """Extract caption from figure block content."""
        if not figure_content:
            return "Figure"
            
        caption_match = re.search(
            r'<caption>(.*?)</caption>', 
            figure_content, 
            re.DOTALL | re.IGNORECASE
        )
        if caption_match:
            caption = caption_match.group(1).strip()
            caption = re.sub(r'\s+', ' ', caption)
            if len(caption) > 100:
                caption = caption[:97] + "..."
            return caption if caption else "Figure"
        
        lines = figure_content.strip().split('\n')
        if lines and lines[0].strip():
            first_line = lines[0].strip()
            first_line = re.sub(r'<figure[^>]*>', '', first_line, flags=re.IGNORECASE)
            first_line = re.sub(r'</figure>', '', first_line, flags=re.IGNORECASE)
            return first_line[:80] if first_line else "Figure"
        
        return "Figure"

    def extract_by_line_range(
        self, line_index: Dict[int, str], start_line: int, end_line: int
    ) -> str:
        """Extract content from a range of lines (inclusive)."""
        if start_line not in line_index:
            raise ValueError(f"Start line not found: L{start_line}")
        if end_line not in line_index:
            raise ValueError(f"End line not found: L{end_line}")
        if start_line > end_line:
            raise ValueError(f"Start line L{start_line} is after end line L{end_line}")

        content_parts = []
        for line_num in range(start_line, end_line + 1):
            if line_num in line_index:
                content_parts.append(line_index[line_num])

        return "\n\n".join(content_parts)

    def get_total_lines(self, line_index: Dict[int, str]) -> int:
        """Get total number of lines."""
        return max(line_index.keys()) if line_index else 0

