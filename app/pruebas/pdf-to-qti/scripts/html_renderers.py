"""
HTML element renderers for QTI to HTML conversion.

This module contains utility functions for converting XML elements
(MathML, images, tables, lists) to HTML format.
"""

from __future__ import annotations

import html


def extract_text_from_element(elem) -> str:
    """Extrae texto de un elemento XML, incluyendo texto directo."""
    text_parts = []
    if elem.text:
        text_parts.append(elem.text.strip())
    for child in elem:
        text_parts.append(extract_text_from_element(child))
        if child.tail:
            text_parts.append(child.tail.strip())
    return " ".join(text_parts)


def build_mathml_xml(elem) -> str:
    """Construye el XML del MathML recursivamente sin incluir tail."""
    tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
    # Remover prefijo ns0: si existe
    if tag.startswith("ns0:"):
        tag = tag[4:]

    xml = f"<{tag}"
    # Agregar atributos
    for key, value in elem.attrib.items():
        if "}" in key:
            attr_name = key.split("}")[-1]
        else:
            attr_name = key
        # Limpiar namespace de atributos
        if attr_name.startswith("ns0:"):
            attr_name = attr_name[4:]
        xml += f' {attr_name}="{value}"'

    # Asegurar namespace para MathML
    if tag == "math" and "xmlns=" not in xml:
        xml = xml.replace("<math", '<math xmlns="http://www.w3.org/1998/Math/MathML"')

    xml += ">"

    # Agregar texto del elemento
    if elem.text:
        xml += elem.text

    # Agregar hijos recursivamente
    for child in elem:
        xml += build_mathml_xml(child)
        if child.tail:
            xml += child.tail

    xml += f"</{tag}>"
    return xml


def render_mathml_to_html(math_elem) -> str:
    """Convierte MathML a HTML con MathJax.

    Nota: Esta función solo renderiza el elemento MathML, no incluye su tail.
    El tail debe ser procesado por separado por el código que llama a esta función.
    """
    math_str = build_mathml_xml(math_elem)

    # Limpiar namespaces y prefijos para que MathJax lo procese correctamente
    math_str = math_str.replace('xmlns:ns0="http://www.w3.org/1998/Math/MathML"', "")
    math_str = math_str.replace("ns0:", "")

    return f'<span class="math-container">{math_str}</span>'


def render_image_to_html(img_elem) -> str:
    """Renderiza una imagen desde base64 o URL."""
    src = img_elem.get("src", "")
    alt = img_elem.get("alt", "Imagen de la pregunta")

    # All image types (base64, URL, other) use the same format
    return f'<img src="{src}" alt="{alt}" class="question-image" />'


def render_element_with_math(elem, math_ns: str) -> str:
    """Renderiza un elemento XML preservando MathML y otros elementos inline."""
    result = []

    # Texto inicial del elemento
    if elem.text:
        result.append(html.escape(elem.text))

    # Procesar hijos
    for child in elem:
        child_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        child_tag_lower = child_tag.lower()

        if "math" in child_tag_lower:
            result.append(render_mathml_to_html(child))
        elif "img" in child_tag_lower:
            result.append(render_image_to_html(child))
        else:
            # Recursivamente procesar otros elementos
            result.append(render_element_with_math(child, math_ns))

        # Tail del hijo
        if child.tail:
            result.append(html.escape(child.tail))

    return "".join(result)


def render_list_to_html(list_elem, math_ns: str) -> str:
    """Renderiza una lista (ul/ol) preservando MathML en los items."""
    tag_name = list_elem.tag.split("}")[-1] if "}" in list_elem.tag else list_elem.tag
    list_type = "ul" if "ul" in tag_name.lower() else "ol"

    html_parts = [f"<{list_type}>"]

    for li in list_elem:
        li_tag = li.tag.split("}")[-1] if "}" in li.tag else li.tag
        if "li" in li_tag.lower():
            li_content = render_element_with_math(li, math_ns)
            html_parts.append(f"<li>{li_content}</li>")

    html_parts.append(f"</{list_type}>")
    return "".join(html_parts)


def render_table_to_html(table_elem, math_ns: str) -> str:
    """Renderiza una tabla a HTML preservando MathML."""
    html_parts = ['<table class="question-table">']

    # Buscar thead - iterar por todos los elementos para evitar problemas de namespace
    thead = _find_element_by_tag(table_elem, "thead")

    if thead is not None:
        html_parts.append("<thead>")
        _render_table_rows(thead, html_parts, math_ns, cell_tag="th")
        html_parts.append("</thead>")

    # Buscar tbody
    tbody = _find_element_by_tag(table_elem, "tbody")

    if tbody is not None:
        html_parts.append("<tbody>")
        _render_table_rows(tbody, html_parts, math_ns, cell_tag="td")
        html_parts.append("</tbody>")

    # Si no hay thead/tbody, buscar tr directamente
    if thead is None and tbody is None:
        _render_direct_table_rows(table_elem, html_parts, math_ns)

    html_parts.append("</table>")
    return "\n".join(html_parts)


def _find_element_by_tag(parent, tag_substr: str):
    """Busca un elemento hijo por substring del tag (ignora namespace)."""
    for elem in parent.iter():
        tag_name = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag_substr in tag_name.lower():
            return elem
    return None


def _render_table_rows(container, html_parts: list, math_ns: str, cell_tag: str = "td"):
    """Renderiza filas de una tabla (thead o tbody)."""
    for child in container:
        tag_name = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if "tr" in tag_name.lower():
            html_parts.append("<tr>")
            for grandchild in child:
                gc_tag = grandchild.tag.split("}")[-1] if "}" in grandchild.tag else grandchild.tag
                if cell_tag in gc_tag.lower():
                    cell_content = render_element_with_math(grandchild, math_ns)
                    html_parts.append(f"<{cell_tag}>{cell_content}</{cell_tag}>")
            html_parts.append("</tr>")


def _render_direct_table_rows(table_elem, html_parts: list, math_ns: str):
    """Renderiza filas directamente dentro de table (sin thead/tbody)."""
    found_tr = False
    for child in table_elem:
        tag_name = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if "tr" in tag_name.lower():
            if not found_tr:
                found_tr = True
                html_parts.append("<tbody>")

            html_parts.append("<tr>")
            for grandchild in child:
                gc_tag = grandchild.tag.split("}")[-1] if "}" in grandchild.tag else grandchild.tag
                if "th" in gc_tag.lower():
                    cell_content = render_element_with_math(grandchild, math_ns)
                    html_parts.append(f"<th>{cell_content}</th>")
                elif "td" in gc_tag.lower():
                    cell_content = render_element_with_math(grandchild, math_ns)
                    html_parts.append(f"<td>{cell_content}</td>")
            html_parts.append("</tr>")

    if found_tr:
        html_parts.append("</tbody>")


def render_equation_system(math_elements: list) -> str:
    """Renderiza un sistema de ecuaciones (múltiples math display=block)."""
    html_parts = ['<div class="equation-system">']
    for math in math_elements:
        html_parts.append(render_mathml_to_html(math))
    html_parts.append("</div>")
    return "\n".join(html_parts)


def get_tag_name(elem) -> str:
    """Extrae el nombre del tag sin namespace."""
    return elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
