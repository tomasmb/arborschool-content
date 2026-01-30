"""
Image area detection and construction.

This module contains functions for detecting and constructing image areas
in PDF documents by analyzing text blocks and gaps.
"""

from typing import List, Optional

import fitz  # type: ignore


def construct_multiple_image_areas(
    page: fitz.Page,
    question_answer_blocks: List[List[float]],
    image_label_blocks: List[List[float]]
) -> List[List[float]]:
    """
    Constructs one or more image areas based on label clustering and the presence of
    separating text blocks.
    """
    if not image_label_blocks:
        return []

    # Sort labels by vertical position
    image_label_blocks.sort(key=lambda bbox: bbox[1])

    # Cluster labels based on vertical gaps
    clusters = []
    if image_label_blocks:
        current_cluster = [image_label_blocks[0]]
        for i in range(1, len(image_label_blocks)):
            prev_bbox = image_label_blocks[i-1]
            current_bbox = image_label_blocks[i]
            vertical_gap = current_bbox[1] - prev_bbox[3]

            # If gap is large, start a new cluster
            if vertical_gap > 20:  # Threshold for what constitutes a "big" gap
                clusters.append(current_cluster)
                current_cluster = [current_bbox]
            else:
                current_cluster.append(current_bbox)
        clusters.append(current_cluster)

    # If only one cluster, use the existing single-image logic
    if len(clusters) <= 1:
        single_bbox = construct_image_area_including_labels(page, question_answer_blocks, image_label_blocks)
        return [single_bbox] if single_bbox else []

    # Create separate image areas for each cluster
    final_bboxes = []
    print(f"🔍 Found {len(clusters)} image clusters, creating separate images for each.")
    for cluster in clusters:
        # For each cluster, construct its own image area
        cluster_bbox = construct_image_area_including_labels(page, question_answer_blocks, cluster)
        if cluster_bbox:
            final_bboxes.append(cluster_bbox)

    if not final_bboxes:
        return []

    # Deduplicate bounding boxes based on significant overlap (80%+)
    unique_bboxes = []

    for bbox in final_bboxes:
        is_duplicate = False
        bbox_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])

        for existing_bbox in unique_bboxes:
            # Calculate overlap area
            overlap_x1 = max(bbox[0], existing_bbox[0])
            overlap_y1 = max(bbox[1], existing_bbox[1])
            overlap_x2 = min(bbox[2], existing_bbox[2])
            overlap_y2 = min(bbox[3], existing_bbox[3])

            if overlap_x1 < overlap_x2 and overlap_y1 < overlap_y2:
                overlap_area = (overlap_x2 - overlap_x1) * (overlap_y2 - overlap_y1)
                overlap_percentage = overlap_area / bbox_area if bbox_area > 0 else 0

                if overlap_percentage > 0.8:  # 80% overlap = duplicate
                    is_duplicate = True
                    break

        if not is_duplicate:
            unique_bboxes.append(bbox)

    if len(unique_bboxes) < len(final_bboxes):
        print(f"🔍 ⚠️  Removed {len(final_bboxes) - len(unique_bboxes)} duplicate image areas with >80% overlap.")

    return unique_bboxes


def construct_image_area_including_labels(
    page: fitz.Page,
    question_answer_blocks: List[List[float]],
    image_label_blocks: List[List[float]]
) -> Optional[List[float]]:
    """
    Construct image area that INCLUDES the image label blocks and finds the visual content around them.
    
    This is different from gap detection - instead of finding gaps between text,
    we find an area that encompasses the image labels and extends to capture the visual content.
    """
    print("🔍 🎯 CUSTOM IMAGE AREA DETECTION")
    print(f"🔍    Image labels to include: {len(image_label_blocks)}")
    print(f"🔍    Q&A blocks to avoid: {len(question_answer_blocks)}")

    if not image_label_blocks:
        print("🔍 ❌ No image label blocks to anchor the image area")
        return None

    page_width = page.rect.width
    page_height = page.rect.height
    margin = 10

    # Find the bounding box that encompasses all image labels
    min_x = min(bbox[0] for bbox in image_label_blocks)
    min_y = min(bbox[1] for bbox in image_label_blocks)
    max_x = max(bbox[2] for bbox in image_label_blocks)
    max_y = max(bbox[3] for bbox in image_label_blocks)

    print(f"🔍 📐 Image labels span: ({min_x:.1f}, {min_y:.1f}) to ({max_x:.1f}, {max_y:.1f})")

    # Expand this area to capture the visual content around the labels
    # The visual content (molecule diagrams) is likely ABOVE the labels

    # Find the nearest question/answer block above to determine top boundary
    top_boundary = margin  # Start from page top to find the closest Q&A block above
    for qa_bbox in question_answer_blocks:
        qa_bottom = qa_bbox[3]
        qa_top = qa_bbox[1]
        # If this Q&A block starts above our image labels, use it as boundary
        if qa_top < min_y and qa_bottom > top_boundary:
            top_boundary = qa_bottom + margin
            print(f"🔍 📐 Top boundary set by Q&A block ending at {qa_bottom:.1f}")

    # If no Q&A block was found above, default to just above the image labels
    if top_boundary == margin:
        top_boundary = min_y - 5
        print("🔍 📐 No Q&A block found above image labels, using conservative boundary")

    # Find the nearest question/answer block below to determine bottom boundary
    bottom_boundary = page_height - margin  # Default to page bottom
    for qa_bbox in question_answer_blocks:
        qa_top = qa_bbox[1]
        # If this Q&A block is below our image labels and closer than current boundary
        if qa_top > max_y and qa_top < bottom_boundary:
            bottom_boundary = qa_top - margin
            print(f"🔍 📐 Bottom boundary set by Q&A block starting at {qa_top:.1f}")

    # For horizontal boundaries, be generous but avoid Q&A blocks on the sides
    left_boundary = margin
    right_boundary = page_width - margin

    # Check for Q&A blocks that might constrain horizontal space
    for qa_bbox in question_answer_blocks:
        qa_left, qa_top, qa_right, qa_bottom = qa_bbox

        # If Q&A block overlaps vertically with our image area
        if not (qa_bottom <= top_boundary or qa_top >= bottom_boundary):
            # If Q&A block is to the right of our labels, constrain right boundary
            if qa_left > max_x and qa_left < right_boundary:
                right_boundary = qa_left - margin
                print(f"🔍 📐 Right boundary constrained by Q&A block at {qa_left:.1f}")
            # If Q&A block is to the left of our labels, constrain left boundary
            elif qa_right < min_x and qa_right > left_boundary:
                left_boundary = qa_right + margin
                print(f"🔍 📐 Left boundary constrained by Q&A block at {qa_right:.1f}")

    # Construct the final image area
    image_bbox = [left_boundary, top_boundary, right_boundary, bottom_boundary]

    # Validate the bbox
    width = right_boundary - left_boundary
    height = bottom_boundary - top_boundary

    if width <= 0 or height <= 0:
        print(f"🔍 ❌ Invalid image area: {width:.1f}x{height:.1f}")
        return None

    if width < 50 or height < 30:
        print(f"🔍 ⚠️ Image area very small: {width:.1f}x{height:.1f}, but proceeding")

    print("🔍 ✅ CONSTRUCTED image area:")
    print(f"🔍    Bbox: [{left_boundary:.1f}, {top_boundary:.1f}, {right_boundary:.1f}, {bottom_boundary:.1f}]")
    print(f"🔍    Size: {width:.1f} x {height:.1f} pixels")
    print(f"🔍    Area: {width * height:.0f} square pixels")
    print(f"🔍    Includes {len(image_label_blocks)} image label blocks")

    return image_bbox


def construct_image_area_from_gaps_flexible(
    page: fitz.Page,
    question_answer_blocks: List[List[float]],
    all_text_bboxes: List[List[float]]
) -> Optional[List[float]]:
    """
    Flexible gap detection for images without labels.
    Uses more relaxed thresholds and smarter gap analysis.
    """
    print("🔍 🎯 FLEXIBLE GAP DETECTION (for unlabeled images)")

    if not question_answer_blocks:
        print("🔍 ❌ No question/answer blocks to define gaps around")
        return None

    page_width = page.rect.width
    page_height = page.rect.height
    margin = 10

    # Sort Q&A blocks by vertical position
    qa_blocks_sorted = sorted(question_answer_blocks, key=lambda bbox: bbox[1])

    print(f"🔍 📋 Analyzing {len(qa_blocks_sorted)} Q&A blocks for gaps:")
    for i, bbox in enumerate(qa_blocks_sorted):
        print(f"🔍   Block {i+1}: y={bbox[1]:.1f} to {bbox[3]:.1f} (height: {bbox[3]-bbox[1]:.1f})")

    # Collect potential gaps with more flexible thresholds
    potential_gaps = []

    # Gap from top of page to first block
    if qa_blocks_sorted[0][1] > margin:
        gap_size = qa_blocks_sorted[0][1] - margin
        potential_gaps.append({
            "size": gap_size,
            "start": margin,
            "end": qa_blocks_sorted[0][1] - margin,
            "type": "top",
            "priority": 2
        })
        print(f"🔍 📐 Top gap: {gap_size:.1f}px")

    # Gaps between consecutive blocks
    for i in range(len(qa_blocks_sorted) - 1):
        current_bottom = qa_blocks_sorted[i][3]
        next_top = qa_blocks_sorted[i + 1][1]
        gap_size = next_top - current_bottom

        if gap_size > 0:  # Any positive gap
            potential_gaps.append({
                "size": gap_size,
                "start": current_bottom + margin,
                "end": next_top - margin,
                "type": "between",
                "priority": 3
            })
            print(f"🔍 📐 Between gap {i+1}: {gap_size:.1f}px")

    # Gap from last block to page bottom (conservative)
    effective_page_bottom = page_height - margin

    # Avoid footer text by checking for text blocks below the last Q&A block
    last_qa_bottom = qa_blocks_sorted[-1][3]
    for text_bbox in all_text_bboxes:
        if text_bbox[1] > last_qa_bottom + (margin / 2):
            potential_bottom = text_bbox[1] - margin
            if potential_bottom < effective_page_bottom:
                effective_page_bottom = potential_bottom
                print(f"🔍 📐 Bottom constrained by text at y={text_bbox[1]:.1f}")

    if qa_blocks_sorted[-1][3] < effective_page_bottom:
        gap_size = effective_page_bottom - qa_blocks_sorted[-1][3] - margin
        if gap_size > 0:
            potential_gaps.append({
                "size": gap_size,
                "start": qa_blocks_sorted[-1][3] + margin,
                "end": effective_page_bottom,
                "type": "bottom",
                "priority": 1
            })
            print(f"🔍 📐 Bottom gap: {gap_size:.1f}px")

    # Use flexible thresholds based on context
    min_gap_size = 30  # Much smaller than the original 100px

    # If we have reasonable-sized gaps, prefer them
    large_gaps = [gap for gap in potential_gaps if gap["size"] >= 60]
    if large_gaps:
        valid_gaps = large_gaps
        print(f"🔍 ✅ Found {len(large_gaps)} large gaps (≥60px)")
    else:
        # Fall back to smaller gaps
        valid_gaps = [gap for gap in potential_gaps if gap["size"] >= min_gap_size]
        print(f"🔍 ⚠️ Using smaller gaps (≥{min_gap_size}px): {len(valid_gaps)} found")

    if not valid_gaps:
        print(f"🔍 ❌ No gaps ≥{min_gap_size}px found")
        return None

    # Sort by priority, then by size
    valid_gaps.sort(key=lambda g: (-g["priority"], -g["size"]))
    best_gap = valid_gaps[0]

    print(f"🔍 ✅ Selected {best_gap['type']} gap: {best_gap['size']:.1f}px")

    # Construct the image bbox
    left_bound = margin
    right_bound = page_width - margin

    # Adjust horizontal bounds if Q&A blocks interfere
    for bbox in qa_blocks_sorted:
        if not (bbox[3] <= best_gap["start"] or bbox[1] >= best_gap["end"]):
            # This Q&A block overlaps with our gap vertically
            if bbox[0] > page_width / 2:  # Block is on the right side
                right_bound = min(right_bound, bbox[0] - margin)
            else:  # Block is on the left side
                left_bound = max(left_bound, bbox[2] + margin)

    if right_bound <= left_bound:
        print("🔍 ❌ No valid horizontal space for image")
        return None

    image_bbox = [left_bound, best_gap["start"], right_bound, best_gap["end"]]
    width = right_bound - left_bound
    height = best_gap["end"] - best_gap["start"]

    print("🔍 ✅ CONSTRUCTED flexible gap image:")
    print(f"🔍    Bbox: [{left_bound:.1f}, {best_gap['start']:.1f}, {right_bound:.1f}, {best_gap['end']:.1f}]")
    print(f"🔍    Size: {width:.1f} x {height:.1f} pixels")
    print(f"🔍    Area: {width * height:.0f} square pixels")

    return image_bbox


def construct_image_bbox_from_gaps(
    page: fitz.Page,
    question_answer_blocks: List[List[float]],
    image_label_blocks: List[List[float]],
    all_page_text_bboxes: List[List[float]]
) -> Optional[List[float]]:
    """Construct image bbox by finding gaps between question/answer text blocks."""
    if not question_answer_blocks:
        return None

    qa_blocks_sorted = sorted(question_answer_blocks, key=lambda bbox: bbox[1])
    page_width = page.rect.width
    page_height = page.rect.height
    margin = 10

    # Collect all potential gaps with metadata
    potential_gaps = []

    # Check gap from top of page to first block
    if qa_blocks_sorted[0][1] > margin:
        gap_size = qa_blocks_sorted[0][1] - margin
        potential_gaps.append({
            "size": gap_size,
            "start": margin,
            "end": qa_blocks_sorted[0][1] - margin,
            "type": "top",
            "priority": 2
        })

    # Check gaps between consecutive blocks
    for i in range(len(qa_blocks_sorted) - 1):
        current_bottom = qa_blocks_sorted[i][3]
        next_top = qa_blocks_sorted[i + 1][1]
        gap_size = next_top - current_bottom
        potential_gaps.append({
            "size": gap_size,
            "start": current_bottom + margin,
            "end": next_top - margin,
            "type": "between",
            "priority": 3
        })

    # Determine effective page bottom considering all text blocks to avoid footer overlap
    effective_page_bottom_for_image = page_height - margin
    # qa_blocks_sorted is guaranteed to be non-empty here due to the early return.
    last_qa_block_bottom = qa_blocks_sorted[-1][3]
    for text_bbox in all_page_text_bboxes:
        # Consider text blocks that are strictly below the last QA block
        # Use a small buffer (margin / 2) to ensure clear separation before considering a block as "below"
        if text_bbox[1] > last_qa_block_bottom + (margin / 2):
            potential_new_image_bottom = text_bbox[1] - margin # Image should end above this block
            if potential_new_image_bottom < effective_page_bottom_for_image:
                effective_page_bottom_for_image = potential_new_image_bottom

    # Check gap from last block to determined effective bottom
    if qa_blocks_sorted[-1][3] < effective_page_bottom_for_image: # Check if there's any space left
        gap_start_y = qa_blocks_sorted[-1][3] + margin
        gap_end_y = effective_page_bottom_for_image

        if gap_end_y > gap_start_y:  # Ensure there's a valid positive-sized gap
            gap_size = gap_end_y - gap_start_y
            potential_gaps.append({
                "size": gap_size,
                "start": gap_start_y,
                "end": gap_end_y,
                "type": "bottom",
                "priority": 1
            })

    # Filter gaps that are large enough
    valid_gaps = [gap for gap in potential_gaps if gap["size"] >= 100]

    if not valid_gaps:
        print("🧠 ⚠️ No gaps larger than 100px found")
        return None

    # Sort by priority first, then by size (descending)
    # This ensures we prefer "between" gaps over "bottom" gaps even if bottom is larger
    valid_gaps.sort(key=lambda g: (-g["priority"], -g["size"]))

    best_gap = valid_gaps[0]
    print(f"🧠 ✅ Selected {best_gap['type']} gap: {best_gap['size']:.0f}px "
          f"(priority {best_gap['priority']})")

    left_bound = margin
    right_bound = page_width - margin

    # Adjust for overlapping blocks
    for bbox in qa_blocks_sorted:
        if not (bbox[3] <= best_gap["start"] or bbox[1] >= best_gap["end"]):
            if bbox[0] > page_width / 2:
                right_bound = min(right_bound, bbox[0] - margin)
            else:
                left_bound = max(left_bound, bbox[2] + margin)

    if right_bound <= left_bound:
        print("🧠 ⚠️ No valid horizontal space for image")
        return None

    image_bbox = [left_bound, best_gap["start"], right_bound, best_gap["end"]]
    width = right_bound - left_bound
    height = best_gap["end"] - best_gap["start"]

    print(f"🧠 ✅ Constructed image bbox: {image_bbox}, size: {width:.0f}x{height:.0f}")
    return image_bbox
