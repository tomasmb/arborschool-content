#!/usr/bin/env python3
"""
Script para renderizar QTI XML a HTML visual.
Permite ver las preguntas de forma atractiva para verificar que se plasmó correctamente del PDF.
"""

from __future__ import annotations

import html
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Import from refactored modules
from html_renderers import (
    extract_text_from_element,
    get_tag_name,
    render_element_with_math,
    render_equation_system,
    render_image_to_html,
    render_list_to_html,
    render_mathml_to_html,
    render_table_to_html,
)
from html_template import create_html_page

# MathML namespace
MATH_NS = 'http://www.w3.org/1998/Math/MathML'


def _find_qti_element(root, tag: str):
    """Busca un elemento QTI por sufijo del tag."""
    for elem in root.iter():
        if elem.tag.endswith(tag):
            return elem
    return None


def _get_correct_response(root) -> str | None:
    """Extrae la respuesta correcta del QTI."""
    correct_response = _find_qti_element(root, 'correct-response')
    if correct_response is not None:
        for child in correct_response.iter():
            if child.tag.endswith('value') and child.text:
                return child.text
    return None


def _render_prompt(prompt, math_ns: str) -> str:
    """Renderiza el prompt de un choice-interaction."""
    prompt_html = '<div class="question-prompt">'

    # Procesar hijos del prompt (puede incluir párrafos, listas, MathML)
    for child in prompt:
        child_tag_lower = get_tag_name(child).lower()

        if 'p' in child_tag_lower:
            p_content = render_element_with_math(child, math_ns)
            prompt_html += f'<p>{p_content}</p>'
        elif 'ul' in child_tag_lower or 'ol' in child_tag_lower:
            prompt_html += render_list_to_html(child, math_ns)
        elif 'math' in child_tag_lower:
            prompt_html += render_mathml_to_html(child)
        else:
            content = render_element_with_math(child, math_ns)
            if content.strip():
                prompt_html += f'<p>{content}</p>'

    # Si no hay hijos, procesar texto directo
    if not any(True for _ in prompt):
        if prompt.text:
            prompt_html += f'<p>{html.escape(prompt.text)}</p>'

    prompt_html += '</div>'
    return prompt_html


def _render_choices(elem, correct_value: str | None, math_ns: str) -> list[str]:
    """Renderiza las alternativas de un choice-interaction."""
    html_parts = ['<div class="choices-list">']

    # Buscar choices dentro del choice-interaction
    choices = [c for c in elem.iter() if 'simple-choice' in c.tag.lower()]

    for choice in choices:
        choice_id = choice.get('identifier', '')
        choice_text = extract_text_from_element(choice)

        # Buscar MathML en la alternativa
        math_elems = choice.findall(f'.//{{{math_ns}}}math') or choice.findall('.//math')
        for math in math_elems:
            math_html = render_mathml_to_html(math)
            math_text = extract_text_from_element(math)
            choice_text = choice_text.replace(math_text, math_html)

        # Buscar imágenes en la alternativa
        img_elems = choice.findall('.//img') or [e for e in choice.iter() if 'img' in e.tag.lower()]
        for img in img_elems:
            choice_text += render_image_to_html(img)

        is_correct = (choice_id == correct_value)
        correct_class = 'correct-choice' if is_correct else ''
        checked = 'checked' if is_correct else ''

        html_parts.append(f'<div class="choice-item {correct_class}">')
        html_parts.append(
            f'  <input type="radio" name="response" id="{choice_id}" '
            f'value="{choice_id}" {checked} />'
        )
        html_parts.append(
            f'  <label for="{choice_id}"><strong>{choice_id}:</strong> {choice_text}</label>'
        )
        html_parts.append('</div>')

    html_parts.append('</div>')
    return html_parts


def _render_choice_interaction(elem, correct_value: str | None, math_ns: str) -> list[str]:
    """Renderiza un choice-interaction completo."""
    html_parts = ['<div class="choices-container">']

    # Buscar prompt
    prompt = None
    for p in elem.iter():
        if 'prompt' in p.tag.lower():
            prompt = p
            break

    if prompt is not None:
        html_parts.append(_render_prompt(prompt, math_ns))

    html_parts.extend(_render_choices(elem, correct_value, math_ns))
    html_parts.append('</div>')
    return html_parts


def _collect_math_and_content(elem) -> list[tuple[str, any]]:
    """Recolecta contenido separando math display=block del resto."""
    math_children = []
    other_content = []

    if elem.text:
        other_content.append(('text', elem.text))

    for child in elem:
        child_tag_lower = get_tag_name(child).lower()

        if 'math' in child_tag_lower and child.get('display') == 'block':
            math_children.append(child)
        else:
            if math_children:
                other_content.append(('system', math_children))
                math_children = []
            other_content.append(('child', child))

        if child.tail and not math_children:
            other_content.append(('text', child.tail))

    # Si quedan math al final, agruparlos
    if math_children:
        other_content.append(('system', math_children))

    return other_content


def _render_paragraph(elem, math_ns: str) -> list[str]:
    """Renderiza un párrafo detectando sistemas de ecuaciones."""
    html_parts = []
    content = _collect_math_and_content(elem)

    # Solo sistema de ecuaciones
    if len(content) == 1 and content[0][0] == 'system':
        html_parts.append(render_equation_system(content[0][1]))
        return html_parts

    # Contenido mixto
    p_html = '<p>'
    for item_type, item_data in content:
        if item_type == 'text':
            p_html += html.escape(item_data)
        elif item_type == 'system':
            p_html += '</p>'
            html_parts.append(p_html)
            html_parts.append(render_equation_system(item_data))
            p_html = '<p>'
        elif item_type == 'child':
            child = item_data
            child_tag_lower = get_tag_name(child).lower()
            if 'math' in child_tag_lower:
                p_html += render_mathml_to_html(child)
            elif 'img' in child_tag_lower:
                p_html += render_image_to_html(child)
            else:
                p_html += render_element_with_math(child, math_ns)
    p_html += '</p>'
    html_parts.append(p_html)

    return html_parts


def _render_div(elem, math_ns: str) -> list[str]:
    """Renderiza un div detectando sistemas de ecuaciones y tablas."""
    html_parts = []
    math_children = []
    other_children = []

    for child in elem:
        child_tag_lower = get_tag_name(child).lower()

        if 'math' in child_tag_lower and child.get('display') == 'block':
            math_children.append(child)
        else:
            if math_children:
                html_parts.append(render_equation_system(math_children))
                math_children = []
            if 'table' in child_tag_lower:
                html_parts.append(render_table_to_html(child, math_ns))
            else:
                other_children.append(child)

    # Si quedan math al final
    if math_children:
        html_parts.append(render_equation_system(math_children))

    # Procesar otros hijos
    for child in other_children:
        child_tag_lower = get_tag_name(child).lower()
        if 'p' in child_tag_lower:
            p_content = render_element_with_math(child, math_ns)
            html_parts.append(f'<p>{p_content}</p>')
        else:
            content = render_element_with_math(child, math_ns)
            if content.strip():
                html_parts.append(f'<div>{content}</div>')

    return html_parts


def render_qti_to_html(xml_path: Path) -> str:
    """Convierte un QTI XML a HTML visual.

    Args:
        xml_path: Path to the QTI XML file

    Returns:
        HTML string of the rendered question
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Extraer información
    title = root.get('title', 'Sin título')
    identifier = root.get('identifier', 'unknown')
    correct_value = _get_correct_response(root)

    # Buscar item-body
    item_body = _find_qti_element(root, 'item-body')
    if item_body is None:
        return "<p>Error: No se encontró item-body</p>"

    # Construir HTML
    html_parts = []

    # Header
    html_parts.append('<div class="question-header">')
    html_parts.append(f'<h1 class="question-title">{html.escape(title)}</h1>')
    html_parts.append(f'<p class="question-id">ID: {html.escape(identifier)}</p>')
    if correct_value:
        html_parts.append(
            f'<p class="correct-answer">Respuesta correcta: '
            f'<strong>{html.escape(correct_value)}</strong></p>'
        )
    html_parts.append('</div>')

    # Contenido del item-body
    html_parts.append('<div class="question-content">')

    # Procesar todos los elementos
    for elem in item_body:
        tag_lower = get_tag_name(elem).lower()

        if 'choice-interaction' in tag_lower or 'choiceinteraction' in tag_lower:
            html_parts.extend(_render_choice_interaction(elem, correct_value, MATH_NS))
        elif 'p' in tag_lower or get_tag_name(elem) == 'p':
            html_parts.extend(_render_paragraph(elem, MATH_NS))
        elif 'img' in tag_lower:
            html_parts.append(render_image_to_html(elem))
        elif 'table' in tag_lower:
            html_parts.append(render_table_to_html(elem, MATH_NS))
        elif 'div' in tag_lower:
            html_parts.extend(_render_div(elem, MATH_NS))

    html_parts.append('</div>')

    return '\n'.join(html_parts)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Renderizar QTI XML a HTML visual"
    )
    parser.add_argument(
        "--question",
        type=int,
        default=7,
        help="Número de pregunta a renderizar"
    )
    parser.add_argument(
        "--output-dir",
        default="./output/paes-invierno-2026-new",
        help="Directorio con los QTI generados"
    )
    parser.add_argument(
        "--output-html",
        help="Archivo HTML de salida (opcional)"
    )

    args = parser.parse_args()

    question_num = f"{args.question:03d}"
    xml_path = Path(args.output_dir) / f"question_{question_num}" / "question.xml"

    if not xml_path.exists():
        print(f"❌ No se encontró: {xml_path}")
        sys.exit(1)

    print(f"📄 Renderizando pregunta {args.question}...")

    try:
        qti_html = render_qti_to_html(xml_path)
        full_html = create_html_page(qti_html, question_num)

        # Guardar HTML
        if args.output_html:
            output_path = Path(args.output_html)
        else:
            output_path = Path(args.output_dir) / f"question_{question_num}" / "preview.html"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_html)

        print(f"✅ HTML generado: {output_path}")
        print("🌐 Abre el archivo en tu navegador para ver la pregunta")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
