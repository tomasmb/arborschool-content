"""
Block Matching and LLM Fallback Module

This module contains functionality for finding and matching blocks in PDF pages,
including LLM-based fallback when deterministic matching fails.
"""

import json

from .chunk_segmenter import get_openai_client

# JSON Schema for LLM block matching
BLOCK_MATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "matched_block_index": {
            "type": ["integer", "null"],
            "description": "Index of the block that contains the start marker (0-based), or null if no match found",
        },
        "confidence": {"type": "string", "enum": ["high", "medium", "low"], "description": "Confidence level of the match"},
        "reasoning": {"type": "string", "description": "Brief explanation of why this block was chosen or why no match was found"},
    },
    "required": ["matched_block_index", "confidence", "reasoning"],
    "additionalProperties": False,
}


def find_block_with_llm_fallback(page, segment_data, page_num):
    """
    Use LLM to find which block contains the start marker when deterministic matching fails.

    Args:
        page: PyMuPDF page object
        segment_data: Dict with segment info (id, start_marker, text, etc.)
        page_num: Page number for context

    Returns:
        Block index (0-based) or None if no match found
    """
    try:
        # Extract blocks from the page
        blocks = page.get_text("dict", sort=True).get("blocks", [])
        text_blocks = []

        for i, block in enumerate(blocks):
            if block.get("type") == 0:  # Text block
                block_text = " ".join(span.get("text", "") for line in block.get("lines", []) for span in line.get("spans", [])).strip()

                if block_text:  # Only include non-empty blocks
                    text_blocks.append({"index": i, "text": block_text, "bbox": block.get("bbox", [0, 0, 0, 0])})

        if not text_blocks:
            print(f"❌ No text blocks found on page {page_num} for segment {segment_data.get('id', 'unknown')}")
            return None

        # Prepare LLM prompt: prioritize start_marker over text for matching
        start_marker = segment_data.get("start_marker", "")
        preview = segment_data.get("text", "")

        # Use start_marker if available, otherwise fall back to first 10 words of text
        if start_marker and not ("," in start_marker and start_marker.replace(",", "").replace(".", "").replace("-", "").isdigit()):
            # Start marker is text (not coordinates), use it for matching
            pass
        else:
            # Fall back to first 10 words of text content
            preview_words = preview.strip().split()[:10]
            " ".join(preview_words)

        # Let LLM handle all matching with full context

        system_prompt = """Find the starting block of the given segment using the start marker and content preview.
Once you identify the segment content, choose the block that represents the top-left start of that specific segment.

Example you have a identify 2 blocks that are part of the segment, both at same
y-coordinate, one to the left that has "1." and another block to the right that has
"In this question, you must...", then the starting block is the one that has "1.".

Output a JSON object with:
matched_block_index (integer or null)
confidence (high, medium, low)
reasoning (brief explanation)"""

        user_prompt = f"""Find which block this segment starts in:

**Segment ID:** {segment_data.get("id", "unknown")}
**Start Marker:** "{start_marker}"
**Segment Preview:** "{preview}"
**Page:** {page_num}

**Blocks on Page {page_num}:**
"""

        for block in text_blocks:
            user_prompt += f'\nBlock {block["index"]}: "{block["text"]}"\n'

        user_prompt += "\n**Instructions:** Identify which blocks belong to this segment, then choose the top-left block of that segment."

        # Get OpenAI client
        openai_client = get_openai_client()

        # Make LLM call
        completion = openai_client.chat.completions.create(
            model="gpt-5.1",  # Using gpt-5.1 for precision matching
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            response_format={"type": "json_schema", "json_schema": {"name": "block_match_result", "schema": BLOCK_MATCH_SCHEMA, "strict": True}},
            temperature=0.0,  # Low temperature for consistent results
            seed=42,  # Deterministic output
        )

        # Parse response
        response_content = completion.choices[0].message.content
        result = json.loads(response_content)

        matched_index = result.get("matched_block_index")
        confidence = result.get("confidence", "unknown")
        reasoning = result.get("reasoning", "No reasoning provided")

        if matched_index is not None:
            print(f"🤖 LLM found match for segment {segment_data.get('id', 'unknown')}: Block {matched_index} (confidence: {confidence})")
            print(f"   Reasoning: {reasoning}")
            return matched_index
        else:
            print(f"🤖 LLM found no match for segment {segment_data.get('id', 'unknown')} (confidence: {confidence})")
            print(f"   Reasoning: {reasoning}")
            return None

    except Exception as e:
        print(f"❌ LLM fallback failed for segment {segment_data.get('id', 'unknown')}: {str(e)}")
        return None


def parse_start_marker(marker_str):
    """
    Parse start marker string format.

    Args:
        marker_str: Start marker string - either text or coordinates

    Returns:
        Dict with type and parsed data
    """
    if "," in marker_str and marker_str.replace(",", "").replace(".", "").replace("-", "").isdigit():
        # It's coordinates in "x,y" format
        x, y = map(float, marker_str.split(","))
        return {"type": "coordinate", "x": x, "y": y}
    else:
        # It's text
        return {"type": "text", "text": marker_str.strip()}


def find_start_block_index(page, marker_obj, segment_data=None, page_num=None, doc=None):
    """
    Find the block index that contains the start marker.

    Args:
        page: PyMuPDF page object
        marker_obj: Parsed marker object
        segment_data: Full segment data for LLM fallback
        page_num: Current page number
        doc: Full document for adjacent page checks

    Returns:
        Block index, tuple for adjacent page results, or None if not found
    """
    blocks = page.get_text("dict", sort=True).get("blocks", [])
    marker = marker_obj["marker"] if "marker" in marker_obj else marker_obj
    segment_id = marker_obj.get("id", "unknown")

    if marker["type"] == "text":
        # Always use LLM fallback for text segments
        print(f"⚠️  Trying LLM block matching for segment {segment_id} on page {page_num}...")
        matched = find_block_with_llm_fallback(page, segment_data, page_num)
        if isinstance(matched, int):
            return matched

        print(f"🔍 Segment {segment_id} not found on page {page_num}, searching adjacent pages...")

        # Try adjacent pages: previous, next, previous previous, next next
        # Previous page
        if doc and page_num > 1:
            print(f"🔍 Searching page {page_num - 1} for segment {segment_id}")
            matched = find_block_with_llm_fallback(doc.load_page(page_num - 2), segment_data, page_num - 1)
            if isinstance(matched, int):
                print(f"✅ Found segment {segment_id} on page {page_num - 1} (was expected on page {page_num})")
                return ("previous_page", matched, page_num - 1)
        # Next page
        if doc and page_num < doc.page_count:
            print(f"🔍 Searching page {page_num + 1} for segment {segment_id}")
            matched = find_block_with_llm_fallback(doc.load_page(page_num), segment_data, page_num + 1)
            if isinstance(matched, int):
                print(f"✅ Found segment {segment_id} on page {page_num + 1} (was expected on page {page_num})")
                return ("next_page", matched, page_num + 1)
        # Previous previous page
        if doc and page_num > 2:
            print(f"🔍 Searching page {page_num - 2} for segment {segment_id}")
            matched = find_block_with_llm_fallback(doc.load_page(page_num - 3), segment_data, page_num - 2)
            if isinstance(matched, int):
                print(f"✅ Found segment {segment_id} on page {page_num - 2} (was expected on page {page_num})")
                return ("previous_previous_page", matched, page_num - 2)
        # Next next page
        if doc and page_num < doc.page_count - 1:
            print(f"🔍 Searching page {page_num + 2} for segment {segment_id}")
            matched = find_block_with_llm_fallback(doc.load_page(page_num + 1), segment_data, page_num + 2)
            if isinstance(matched, int):
                print(f"✅ Found segment {segment_id} on page {page_num + 2} (was expected on page {page_num})")
                return ("next_next_page", matched, page_num + 2)
        # Not found anywhere
        raise ValueError(f"❌ CRITICAL: Could not find start block for segment '{segment_id}'")

    elif marker["type"] == "coordinate":
        x, y = marker.get("x", 0), marker.get("y", 0)
        for idx, block in enumerate(blocks):
            bbox = block.get("bbox", [0, 0, 0, 0])
            if bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]:
                print(f"✅ Coordinate match found for segment {segment_id}: block {idx}")
                return idx

        print(f"❌ No block found at coordinates for segment {segment_id}")
        return None

    return None
