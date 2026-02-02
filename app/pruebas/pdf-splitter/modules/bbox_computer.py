"""
Bounding Box Computer Module

This module contains functionality for computing bounding boxes by expanding
from start blocks to include all blocks to the right and bottom until hitting
another segment boundary.
"""

from typing import Dict, List

import fitz  # type: ignore

from .block_matcher import find_start_block_index, parse_start_marker


def expand_blocks_from_start(page, start_block_idx, other_segment_blocks):
    """
    Expand from the start block to include all blocks to the right and bottom,
    stopping when hitting another segment's blocks.

    Args:
        page: PyMuPDF page object
        start_block_idx: Index of the starting block
        other_segment_blocks: Set of block indices that belong to other segments

    Returns:
        List of bbox coordinates [x1, y1, x2, y2] for all blocks in this segment
    """
    blocks = page.get_text("dict", sort=True).get("blocks", [])

    if start_block_idx >= len(blocks) or blocks[start_block_idx].get("type") != 0:
        print(f"❌ Invalid start block index {start_block_idx} or not a text block")
        return []

    start_block = blocks[start_block_idx]
    start_bbox = start_block.get("bbox", [0, 0, 0, 0])

    print(f"🎯 Starting expansion from block {start_block_idx} at bbox {start_bbox}")
    print(f"🚫 Boundary blocks to avoid: {other_segment_blocks}")

    # Set to track which blocks we've included
    included_blocks = set()
    blocks_to_check = [start_block_idx]
    selected_bboxes = []

    # Tolerance for considering blocks as "aligned" (in points)
    alignment_tolerance = 10.0  # Increased tolerance for better alignment detection
    max_distance = 100.0  # Maximum distance to look for adjacent blocks

    iteration = 0
    max_iterations = len(blocks) * 2  # Prevent infinite loops

    while blocks_to_check and iteration < max_iterations:
        iteration += 1
        current_idx = blocks_to_check.pop(0)

        # Skip if already included or blocked by boundaries
        if current_idx in included_blocks:
            continue

        if current_idx in other_segment_blocks:
            print(f"🚫 Stopped expansion at boundary block {current_idx}")
            continue

        if current_idx >= len(blocks) or blocks[current_idx].get("type") != 0:
            continue

        current_block = blocks[current_idx]
        current_bbox = current_block.get("bbox", [0, 0, 0, 0])

        # Include this block
        included_blocks.add(current_idx)
        selected_bboxes.append(current_bbox)
        print(f"✅ Included block {current_idx} at bbox {current_bbox}")

        # Find adjacent blocks to the right and bottom
        candidates_added = 0
        for candidate_idx, candidate_block in enumerate(blocks):
            if (candidate_idx in included_blocks or
                candidate_idx in blocks_to_check or
                candidate_idx in other_segment_blocks or
                candidate_block.get("type") != 0):
                continue

            candidate_bbox = candidate_block.get("bbox", [0, 0, 0, 0])

            # Calculate distances
            horizontal_distance = candidate_bbox[0] - current_bbox[2]  # Left edge of candidate - right edge of current
            vertical_distance = candidate_bbox[1] - current_bbox[3]    # Top edge of candidate - bottom edge of current

            # Check if candidate is to the right (same row, roughly)
            is_to_right = (
                horizontal_distance >= -alignment_tolerance and  # Not too far left
                horizontal_distance <= max_distance and          # Not too far right
                abs(candidate_bbox[1] - current_bbox[1]) <= alignment_tolerance  # Similar top y-coordinate
            )

            # Check if candidate is below (similar or overlapping x-range)
            is_below = (
                vertical_distance >= -alignment_tolerance and   # Not too far up
                vertical_distance <= max_distance and           # Not too far down
                not (candidate_bbox[2] <= current_bbox[0] - alignment_tolerance or
                     candidate_bbox[0] >= current_bbox[2] + alignment_tolerance)  # X-ranges overlap with tolerance
            )

            # Check if candidate is diagonally below-right (within reasonable distance)
            is_diagonal = (
                horizontal_distance >= -alignment_tolerance and
                horizontal_distance <= max_distance // 2 and    # Stricter distance for diagonal
                vertical_distance >= -alignment_tolerance and
                vertical_distance <= max_distance // 2
            )

            if is_to_right or is_below or is_diagonal:
                blocks_to_check.append(candidate_idx)
                candidates_added += 1
                direction = "right" if is_to_right else ("below" if is_below else "diagonal")
                print(f"📍 Added candidate block {candidate_idx} ({direction}) to check queue")

        if candidates_added == 0:
            print(f"🔍 No more candidates found from block {current_idx}")

    if iteration >= max_iterations:
        print(f"⚠️  Expansion stopped due to iteration limit ({max_iterations})")

    print(f"🎉 Expansion complete: {len(selected_bboxes)} blocks included, {len(other_segment_blocks)} boundaries respected")
    return selected_bboxes

def compute_bboxes_for_segments(results: dict, pdf_path: str, start_page_in_original: int = 1) -> dict:
    """
    Compute bounding boxes for each segment by slicing pages vertically between start markers.
    Each segment on a page spans from its start marker's y-coordinate down to the next segment's start or page bottom.
    Multi-page segments get a box on each page: first page from marker to next start, subsequent pages from top to next start.
    """
    doc = fitz.open(pdf_path)
    page_width = None

    # Determine actual start page and block for each segment, register boundaries
    boundaries: Dict[int, List] = {}
    segment_types = ["questions", "multi_question_references", "unrelated_content_segments"]
    for seg_type in segment_types:
        for segment in results.get(seg_type, []):
            page_nums = segment.get("page_nums", [])
            if not page_nums:
                continue
            original_page = page_nums[0]
            page = doc.load_page(original_page - 1)
            if page_width is None:
                page_width = page.rect.width
            parsed_marker = parse_start_marker(segment["start_marker"])
            try:
                res = find_start_block_index(page, {"marker": parsed_marker, "id": segment.get("id", "")}, segment, original_page, doc)
            except ValueError as e:
                # Segment not found - log and skip instead of aborting
                print(f"⚠️  WARNING: {str(e)} - Skipping this segment")
                segment["_bbox_compute_failed"] = True
                segment["_bbox_failure_reason"] = str(e)
                continue  # Skip this segment but continue with others

            # Handle tuple results to move page
            if isinstance(res, tuple) and res[0] in ("previous_page", "previous_previous_page", "next_page", "next_next_page"):
                _, block_idx, actual_page = res
                # Update page spans based on the actual start page
                original_pages = segment.get("page_nums", [])
                if len(original_pages) == 1:
                    # Single page segment - just move to actual page
                    segment["page_nums"] = [actual_page]
                else:
                    # Multi-page segment - shift the entire span
                    page_shift = actual_page - original_page
                    segment["page_nums"] = [p + page_shift for p in original_pages]
                print(f"🔄 Updated Q{segment.get('id', 'unknown')} pages from {original_pages} to {segment['page_nums']}")
                start_page = actual_page
                start_block_idx = block_idx
            elif isinstance(res, int):
                start_page = original_page
                start_block_idx = res
            else:
                # If block finding fails (res is None), log and skip
                print(f"⚠️  WARNING: Could not find start block for segment '{segment.get('id', '')}' - Skipping")
                segment["_bbox_compute_failed"] = True
                segment["_bbox_failure_reason"] = "find_start_block_index returned None"
                continue  # Skip this segment but continue with others

            # Register boundary for this segment on start_page
            blocks = doc.load_page(start_page - 1).get_text("dict", sort=True)["blocks"]
            if start_block_idx is not None and start_block_idx < len(blocks):
                y_start = blocks[start_block_idx].get("bbox", [0, 0, 0, 0])[1]
            else:
                y_start = 0.0
            boundaries.setdefault(start_page, []).append((segment, seg_type, y_start))
            print(f"📍 Registered boundary for {segment.get('id')} on page {start_page} at y={y_start}")

    # Pure principle: Each segment spans from its start until next segment starts
    # Collect all segment starts sorted by position
    all_segment_starts = []
    for seg_type in segment_types:
        for segment in results.get(seg_type, []):
            # Find the actual start position we found, not segmentation guess
            for page_num, boundary_list in boundaries.items():
                for seg, _, y_pos in boundary_list:
                    if seg.get("id") == segment.get("id"):
                        all_segment_starts.append((page_num, y_pos, segment, seg_type))
                        break

    # Sort by page, then by y position
    all_segment_starts.sort(key=lambda x: (x[0], x[1]))
    print(f"📋 Found {len(all_segment_starts)} segment starts, sorted by position")

    # Assign each segment its span: from start until next segment starts
    for i, (start_page, start_y, segment, seg_type) in enumerate(all_segment_starts):
        if i + 1 < len(all_segment_starts):
            next_start_page, next_start_y, _, _ = all_segment_starts[i + 1]
        else:
            # Last segment goes to end of document
            next_start_page = doc.page_count + 1

        # Compute page span: all pages from start until next segment starts
        if next_start_page > doc.page_count:
            # Last segment
            actual_pages = list(range(start_page, doc.page_count + 1))
        else:
            # Normal case: span from start_page to next_start_page (inclusive if on different pages)
            actual_pages = list(range(start_page, next_start_page))
            # Include next_start_page if next segment starts partway through it
            if next_start_page <= doc.page_count:
                actual_pages.append(next_start_page)

        segment["page_nums"] = actual_pages
        print(f"📐 Pure principle: {segment.get('id')} spans pages {actual_pages} (from page {start_page} until page {next_start_page})")

    # Sort boundaries on each page
    for page_num, bnds in boundaries.items():
        bnds.sort(key=lambda x: x[2])

    # Compute bboxes per segment
    for seg_type in segment_types:
        for segment in results.get(seg_type, []):
            page_nums = segment.get("page_nums", [])
            bboxes = []
            for page_num in page_nums:
                page = doc.load_page(page_num - 1)
                page_rect = page.rect
                # Get boundaries on this page (clean boundaries only)
                bnds = boundaries.get(page_num, [])

                # Find where this segment starts and ends on this page
                segment_start_y = None

                # Find this segment's start position on this page
                for seg, _, y in bnds:
                    if seg.get("id") == segment.get("id"):
                        segment_start_y = y
                        break

                # Find the next segment's start position on this page (if any)
                next_segment_starts = []
                for seg, _, y in bnds:
                    if seg.get("id") != segment.get("id"):
                        next_segment_starts.append((y, seg.get("id")))

                if segment_start_y is not None:
                    # This segment starts on this page
                    y_start = segment_start_y
                    # Find the next segment that starts after this one
                    next_starts_after = [(y, seg_id) for y, seg_id in next_segment_starts if y > segment_start_y]
                    if next_starts_after:
                        y_end, next_seg_id = min(next_starts_after)
                        print(f"📐 Segment {segment.get('id')} on page {page_num} spans y={y_start:.1f} to y={y_end:.1f} (until {next_seg_id})")
                    else:
                        y_end = page_rect.height
                        print(f"📐 Segment {segment.get('id')} on page {page_num} spans y={y_start:.1f} to end of page")
                else:
                    # This segment continues from previous page
                    y_start = 0.0
                    # Find the first segment that starts on this page
                    if next_segment_starts:
                        y_end, next_seg_id = min(next_segment_starts)
                        print(f"📐 Segment {segment.get('id')} on page {page_num} spans top to y={y_end:.1f} (until {next_seg_id})")
                    else:
                        y_end = page_rect.height
                        print(f"📐 Segment {segment.get('id')} on page {page_num} spans entire page")
                # Select all blocks in this vertical slice
                blocks = page.get_text("dict", sort=True)["blocks"]
                selected = []
                for block in blocks:
                    # Include all block types
                    bbox = block.get("bbox", [0, 0, 0, 0])
                    # Include blocks whose bounding box intersects the vertical slice [y_start, y_end)
                    if bbox[3] > y_start and bbox[1] < y_end:
                        selected.append(bbox)
                if selected:
                    # Original logic was too restrictive. For vertical layouts, we take the full width
                    # and the full vertical slice defined by the start of the next segment.
                    x_min = 0.0
                    x_max = page_rect.width
                    y1 = y_start
                    y2 = y_end  # Extend all the way to the next segment's start

                    bboxes.append([x_min, y1, x_max, y2])
                    print(
                        f"📦 Final bbox for {segment.get('id')} on page {page_num}: "
                        f"[{x_min:.1f}, {y1:.1f}, {x_max:.1f}, {y2:.1f}] "
                        f"(y_start={y_start:.1f}, y_end={y_end:.1f})"
                    )
                else:
                    # No blocks: minimal region
                    bboxes.append([0.0, y_start, page_rect.width, y_end])
                    print(
                        f"📦 Final bbox for {segment.get('id')} on page {page_num}: "
                        f"[0.0, {y_start:.1f}, {page_rect.width:.1f}, {y_end:.1f}] "
                        f"(no blocks found)"
                    )
            segment["bboxes"] = bboxes
    doc.close()
    return results
