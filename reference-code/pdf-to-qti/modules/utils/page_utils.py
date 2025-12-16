"""page_utils.py
---------------
Page rendering and image creation utilities extracted from pdf_processor.py.
Handles page-to-image conversion, placeholder creation, and multi-page
combination.
"""

from __future__ import annotations

import base64
import fitz  # type: ignore
from typing import Dict, Any, List

__all__ = [
    "get_page_image",
    "create_placeholder_image", 
    "create_combined_image",
    "combine_structured_data",
]


def get_page_image(page: fitz.Page, scale: float = 2.0) -> bytes:
    """Render a page as a high-quality PNG image."""
    try:
        matrix = fitz.Matrix(scale, scale)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        return pixmap.tobytes("png")
    except RuntimeError as e:
        if "Private data too large" in str(e):
            print(f"⚠️  Complex page detected, reducing scale...")
            for fallback_scale in [1.5, 1.0, 0.75]:
                try:
                    matrix = fitz.Matrix(fallback_scale, fallback_scale)
                    pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                    return pixmap.tobytes("png")
                except RuntimeError:
                    continue
        
        print("⚠️  Creating placeholder image due to rendering issues")
        return create_placeholder_image(page)


def create_placeholder_image(page: fitz.Page) -> bytes:
    """Create a placeholder image when rendering fails."""
    try:
        from PIL import Image, ImageDraw, ImageFont  # type: ignore
        
        img = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.load_default()
        except:
            font = None
            
        text = f"Page {page.number + 1}\nContent too complex to render\nText extraction available"
        draw.text((50, 250), text, fill='black', font=font)
        
        import io
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        return img_bytes.getvalue()
        
    except Exception:
        # Return minimal 1x1 white pixel as absolute fallback
        return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x12IDATx\x9cc```bPPP\x00\x02\xac\xea\x05\x1b\x00\x00\x00\x00IEND\xaeB`\x82'


def create_combined_image(doc: fitz.Document) -> str:
    """Create a combined image from multiple pages."""
    try:
        from PIL import Image  # type: ignore
        import io
        
        images = []
        max_width = 0
        total_height = 0
        
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            page_image_bytes = get_page_image(page, scale=1.5)
            
            img = Image.open(io.BytesIO(page_image_bytes))
            images.append(img)
            max_width = max(max_width, img.width)
            total_height += img.height
        
        combined = Image.new('RGB', (max_width, total_height), color='white')
        
        y_offset = 0
        for img in images:
            combined.paste(img, (0, y_offset))
            y_offset += img.height
        
        img_bytes = io.BytesIO()
        combined.save(img_bytes, format='PNG')
        return base64.b64encode(img_bytes.getvalue()).decode('utf-8')
        
    except Exception as e:
        print(f"Error creating combined image: {e}")
        page = doc.load_page(0)
        page_image = get_page_image(page)
        return base64.b64encode(page_image).decode('utf-8')


def combine_structured_data(pages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Combine structured data from multiple pages."""
    if not pages:
        return {}
    
    if len(pages) == 1:
        return pages[0]["structured_text"]
    
    combined = {
        "width": max(page["width"] for page in pages),
        "height": sum(page["height"] for page in pages),
        "blocks": []
    }
    
    y_offset = 0
    for page in pages:
        page_blocks = page["structured_text"].get("blocks", [])
        
        for block in page_blocks:
            if "bbox" in block:
                bbox = block["bbox"]
                block["bbox"] = [bbox[0], bbox[1] + y_offset, bbox[2], bbox[3] + y_offset]
            
            combined["blocks"].append(block)
        
        y_offset += page["height"]
    
    return combined 