"""
Chunk Segmenter Validation

Post-segmentation validation logic to detect common issues like missing questions,
oversized segments, and gaps in question numbering. Also includes statistics generation.
"""

from __future__ import annotations

import re
from typing import Any


def detect_test_type(pdf_path: str) -> tuple[str, int | None]:
    """
    Detect test type from PDF path/name.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Tuple of (test_type, expected_question_count)
        test_type is one of: "seleccion", "invierno", "unknown"
    """
    pdf_name_lower = pdf_path.lower()
    is_seleccion = 'seleccion' in pdf_name_lower
    is_invierno = 'invierno' in pdf_name_lower

    if is_seleccion:
        return "seleccion", 45
    elif is_invierno:
        return "invierno", 65
    else:
        return "unknown", None


def validate_question_count(
    questions: list[dict[str, Any]],
    expected_count: int | None,
    test_type: str
) -> None:
    """
    Validate and report on question count.

    Args:
        questions: List of question dictionaries
        expected_count: Expected number of questions (or None if unknown)
        test_type: Type of test ("seleccion", "invierno", "unknown")
    """
    total_questions = len(questions)

    if expected_count:
        if total_questions < expected_count * 0.7:  # Less than 70% expected
            print(
                f"\n⚠️  ADVERTENCIA: Solo se encontraron {total_questions} pregunta(s) "
                f"de {expected_count} esperadas para {test_type}"
            )
            print("   Esto es anormalmente bajo. Probablemente se perdieron preguntas en la segmentación.")
        elif total_questions < expected_count:
            print(
                f"\n⚠️  ADVERTENCIA: Se encontraron {total_questions} pregunta(s) "
                f"de {expected_count} esperadas para {test_type}"
            )
            print(f"   Faltan {expected_count - total_questions} pregunta(s).")
        elif total_questions == expected_count:
            print(f"\n✅ Correcto: Se encontraron {total_questions} pregunta(s) (esperado para {test_type})")
        else:
            print(
                f"\n⚠️  ADVERTENCIA: Se encontraron {total_questions} pregunta(s), "
                f"más de las {expected_count} esperadas para {test_type}"
            )
    elif total_questions < 10:
        print(f"\n⚠️  ADVERTENCIA: Solo se encontraron {total_questions} pregunta(s)")
        print("   Esto es anormalmente bajo. Probablemente se perdieron preguntas en la segmentación.")
        print("   Revisa el PDF - debería haber 45 (seleccion) o 65 (invierno) preguntas.")


def find_oversized_questions(questions: list[dict[str, Any]], max_pages: int = 5) -> list[dict[str, Any]]:
    """
    Find questions that span more pages than expected.

    Args:
        questions: List of question dictionaries
        max_pages: Maximum expected pages per question

    Returns:
        List of oversized question info dictionaries
    """
    oversized = []
    for q in questions:
        page_count = len(q.get('page_nums', []))
        if page_count > max_pages:
            oversized.append({
                'id': q.get('id', 'unknown'),
                'pages': page_count,
                'page_nums': q.get('page_nums', [])[:10]  # First 10 pages to show
            })
    return oversized


def report_oversized_questions(oversized_questions: list[dict[str, Any]]) -> None:
    """
    Print warnings about oversized questions.

    Args:
        oversized_questions: List of oversized question info dictionaries
    """
    if oversized_questions:
        print(f"\n⚠️  ADVERTENCIA: {len(oversized_questions)} pregunta(s) abarcan más de 5 páginas:")
        for q_info in oversized_questions:
            print(f"   - {q_info['id']}: {q_info['pages']} páginas (páginas {q_info['page_nums']}...)")
            print("     Esto sugiere que se combinaron múltiples preguntas. Busca números de pregunta intermedios.")


def extract_question_numbers(questions: list[dict[str, Any]]) -> list[int]:
    """
    Extract numeric question IDs from question list.

    Args:
        questions: List of question dictionaries

    Returns:
        Sorted list of question numbers
    """
    question_numbers = []
    for q in questions:
        q_id = q.get('id', '')
        match = re.match(r'Q(\d+)', q_id)
        if match:
            question_numbers.append(int(match.group(1)))
    question_numbers.sort()
    return question_numbers


def find_numbering_gaps(question_numbers: list[int]) -> list[int]:
    """
    Find gaps in sequential question numbering.

    Args:
        question_numbers: Sorted list of question numbers

    Returns:
        List of missing question numbers
    """
    gaps = []
    for i in range(len(question_numbers) - 1):
        current = question_numbers[i]
        next_num = question_numbers[i + 1]
        if next_num - current > 1:
            missing = list(range(current + 1, next_num))
            gaps.extend(missing)
    return gaps


def validate_invierno_gaps(questions: list[dict[str, Any]]) -> None:
    """
    Check for gaps in Invierno test numbering (gaps are errors).

    Args:
        questions: List of question dictionaries
    """
    question_numbers = extract_question_numbers(questions)

    if question_numbers:
        gaps = find_numbering_gaps(question_numbers)

        if gaps:
            print("\n⚠️  ADVERTENCIA (Invierno): Se detectaron gaps en la numeración de preguntas:")
            nums_preview = question_numbers[:10]
            print(f"   Preguntas encontradas: {nums_preview}{'...' if len(question_numbers) > 10 else ''}")
            gaps_preview = gaps[:10]
            print(f"   Números faltantes detectados: {gaps_preview}{'...' if len(gaps) > 10 else ''}")
            print("   En pruebas Invierno, TODAS las preguntas Q1-Q65 deben estar presentes.")


def report_seleccion_range(questions: list[dict[str, Any]]) -> None:
    """
    Report question range for seleccion tests (gaps are normal).

    Args:
        questions: List of question dictionaries
    """
    question_numbers = extract_question_numbers(questions)

    if question_numbers:
        min_q = min(question_numbers)
        max_q = max(question_numbers)
        print(f"\nℹ️  Selección detectada: Preguntas encontradas van de Q{min_q} a Q{max_q} (gaps son normales)")


def validate_segmentation_results(results: dict[str, Any], pdf_path: str) -> None:
    """
    Run all post-segmentation validations.

    Args:
        results: Segmentation results dictionary
        pdf_path: Path to the PDF file
    """
    test_type, expected_count = detect_test_type(pdf_path)
    questions = results.get('questions', [])

    # Validate question count
    validate_question_count(questions, expected_count, test_type)

    # Check for oversized questions
    oversized = find_oversized_questions(questions)
    report_oversized_questions(oversized)

    # Check numbering gaps based on test type
    is_seleccion = test_type == "seleccion"
    is_invierno = test_type == "invierno"

    if is_invierno and not is_seleccion:
        validate_invierno_gaps(questions)
    elif is_seleccion:
        report_seleccion_range(questions)


def validate_coordinates(
    bbox: dict[str, float],
    page_width: float = 612,
    page_height: float = 792
) -> dict[str, float]:
    """
    Validate and clamp coordinates to page boundaries.

    Args:
        bbox: Bounding box coordinates with keys x1, y1, x2, y2
        page_width: Page width in points (default: 612 for US Letter)
        page_height: Page height in points (default: 792 for US Letter)

    Returns:
        Validated bounding box
    """
    return {
        'x1': max(0, min(bbox['x1'], page_width)),
        'y1': max(0, min(bbox['y1'], page_height)),
        'x2': max(0, min(bbox['x2'], page_width)),
        'y2': max(0, min(bbox['y2'], page_height))
    }


def get_question_statistics(results: dict[str, Any]) -> dict[str, Any]:
    """
    Generate statistics about the segmented questions.

    Args:
        results: Segmentation results dictionary

    Returns:
        Statistics dictionary with counts and breakdowns
    """
    questions = results.get('questions', [])
    multi_refs = results.get('multi_question_references', [])
    unrelated = results.get('unrelated_content_segments', [])

    stats: dict[str, Any] = {
        'total_questions': len(questions),
        'total_multi_question_references': len(multi_refs),
        'total_unrelated_content_segments': len(unrelated),
        'question_types': {},
        'reference_types': {},
        'unrelated_content_types': {},
        'pages_with_questions': set(),
        'multi_page_questions': 0
    }

    # Analyze questions
    for q in questions:
        q_type = q.get('type', 'unknown')
        stats['question_types'][q_type] = stats['question_types'].get(q_type, 0) + 1
        # Add all pages a question spans
        for p in q.get('page_nums', []):
            stats['pages_with_questions'].add(p)
        if q.get('multi_page', False):
            stats['multi_page_questions'] += 1

    # Analyze references
    for ref in multi_refs:
        ref_type = ref.get('type', 'unknown')
        stats['reference_types'][ref_type] = stats['reference_types'].get(ref_type, 0) + 1

    # Analyze unrelated content
    for unrel in unrelated:
        unrel_type = unrel.get('type', 'unknown')
        stats['unrelated_content_types'][unrel_type] = stats['unrelated_content_types'].get(unrel_type, 0) + 1

    stats['pages_with_questions'] = len(stats['pages_with_questions'])

    return stats
