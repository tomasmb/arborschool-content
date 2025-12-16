#!/usr/bin/env python3
"""
Script para renderizar QTI XML a HTML visual.
Permite ver las preguntas de forma atractiva para verificar que se plasmó correctamente del PDF.
"""

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any
import html
import base64

def extract_text_from_element(elem) -> str:
    """Extrae texto de un elemento XML, incluyendo texto directo."""
    text_parts = []
    if elem.text:
        text_parts.append(elem.text.strip())
    for child in elem:
        text_parts.append(extract_text_from_element(child))
        if child.tail:
            text_parts.append(child.tail.strip())
    return ' '.join(text_parts)

def render_mathml_to_html(math_elem) -> str:
    """Convierte MathML a HTML con MathJax.
    
    Nota: Esta función solo renderiza el elemento MathML, no incluye su tail.
    El tail debe ser procesado por separado por el código que llama a esta función.
    """
    # Crear una copia del elemento para serializar solo el MathML sin el tail
    # Necesitamos serializar solo el elemento, no su tail
    # ET.tostring incluye el tail, así que necesitamos construir el XML manualmente
    # o usar un método que no incluya el tail
    
    # Opción 1: Construir manualmente el MathML
    def build_mathml_xml(elem):
        """Construye el XML del MathML recursivamente sin incluir tail."""
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        # Remover prefijo ns0: si existe
        if tag.startswith('ns0:'):
            tag = tag[4:]
        
        xml = f'<{tag}'
        # Agregar atributos
        for key, value in elem.attrib.items():
            if '}' in key:
                attr_name = key.split('}')[-1]
            else:
                attr_name = key
            # Limpiar namespace de atributos
            if attr_name.startswith('ns0:'):
                attr_name = attr_name[4:]
            xml += f' {attr_name}="{value}"'
        
        # Asegurar namespace para MathML
        if tag == 'math' and 'xmlns=' not in xml:
            xml = xml.replace('<math', '<math xmlns="http://www.w3.org/1998/Math/MathML"')
        
        xml += '>'
        
        # Agregar texto del elemento
        if elem.text:
            xml += elem.text
        
        # Agregar hijos recursivamente
        for child in elem:
            xml += build_mathml_xml(child)
            if child.tail:
                xml += child.tail
        
        xml += f'</{tag}>'
        return xml
    
    math_str = build_mathml_xml(math_elem)
    
    # Limpiar namespaces y prefijos para que MathJax lo procese correctamente
    math_str = math_str.replace('xmlns:ns0="http://www.w3.org/1998/Math/MathML"', '')
    math_str = math_str.replace('ns0:', '')
    
    return f'<span class="math-container">{math_str}</span>'

def render_image_to_html(img_elem) -> str:
    """Renderiza una imagen desde base64 o URL."""
    src = img_elem.get('src', '')
    alt = img_elem.get('alt', 'Imagen de la pregunta')
    
    if src.startswith('data:image'):
        # Ya está en base64
        return f'<img src="{src}" alt="{alt}" class="question-image" />'
    elif src.startswith('http'):
        # URL externa
        return f'<img src="{src}" alt="{alt}" class="question-image" />'
    else:
        return f'<img src="{src}" alt="{alt}" class="question-image" />'

def render_table_to_html(table_elem) -> str:
    """Renderiza una tabla a HTML."""
    html_parts = ['<table class="question-table">']
    
    # Buscar thead - iterar por todos los elementos para evitar problemas de namespace
    thead = None
    for elem in table_elem.iter():
        tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        if 'thead' in tag_name.lower():
            thead = elem
            break
    
    if thead is not None:
        html_parts.append('<thead>')
        for child in thead:
            tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            if 'tr' in tag_name.lower():
                html_parts.append('<tr>')
                for grandchild in child:
                    gc_tag = grandchild.tag.split('}')[-1] if '}' in grandchild.tag else grandchild.tag
                    if 'th' in gc_tag.lower():
                        text = extract_text_from_element(grandchild)
                        html_parts.append(f'<th>{html.escape(text)}</th>')
                html_parts.append('</tr>')
        html_parts.append('</thead>')
    
    # Buscar tbody - iterar por todos los elementos para evitar problemas de namespace
    tbody = None
    for elem in table_elem.iter():
        tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        if 'tbody' in tag_name.lower():
            tbody = elem
            break
    
    if tbody is not None:
        html_parts.append('<tbody>')
        for child in tbody:
            tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            if 'tr' in tag_name.lower():
                html_parts.append('<tr>')
                for grandchild in child:
                    gc_tag = grandchild.tag.split('}')[-1] if '}' in grandchild.tag else grandchild.tag
                    if 'td' in gc_tag.lower():
                        text = extract_text_from_element(grandchild)
                        html_parts.append(f'<td>{html.escape(text)}</td>')
                html_parts.append('</tr>')
        html_parts.append('</tbody>')
    
    # Si no hay thead/tbody, buscar tr directamente
    if thead is None and tbody is None:
        found_tr = False
        for child in table_elem:
            tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            if 'tr' in tag_name.lower():
                if not found_tr:
                    found_tr = True
                    html_parts.append('<tbody>')
                
                html_parts.append('<tr>')
                for grandchild in child:
                    gc_tag = grandchild.tag.split('}')[-1] if '}' in grandchild.tag else grandchild.tag
                    if 'th' in gc_tag.lower():
                        text = extract_text_from_element(grandchild)
                        html_parts.append(f'<th>{html.escape(text)}</th>')
                    elif 'td' in gc_tag.lower():
                        text = extract_text_from_element(grandchild)
                        html_parts.append(f'<td>{html.escape(text)}</td>')
                html_parts.append('</tr>')
        
        if found_tr:
            html_parts.append('</tbody>')
    
    html_parts.append('</table>')
    return '\n'.join(html_parts)

def render_qti_to_html(xml_path: Path) -> str:
    """Convierte un QTI XML a HTML visual."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    # Namespace
    qti_ns = 'http://www.imsglobal.org/xsd/imsqtiasi_v3p0'
    math_ns = 'http://www.w3.org/1998/Math/MathML'
    
    # Helper para buscar elementos
    def find_qti(tag):
        for elem in root.iter():
            if elem.tag.endswith(tag):
                return elem
        return None
    
    def findall_qti(tag):
        results = []
        for elem in root.iter():
            if elem.tag.endswith(tag):
                results.append(elem)
        return results
    
    # Extraer información
    title = root.get('title', 'Sin título')
    identifier = root.get('identifier', 'unknown')
    
    # Buscar item-body
    item_body = find_qti('item-body')
    if item_body is None:
        return "<p>Error: No se encontró item-body</p>"
    
    # Buscar choice-interaction
    choice_interaction = find_qti('choice-interaction')
    
    # Buscar respuesta correcta
    correct_response = find_qti('correct-response')
    correct_value = None
    if correct_response is not None:
        for child in correct_response.iter():
            if child.tag.endswith('value') and child.text:
                correct_value = child.text
                break
    
    # Construir HTML
    html_parts = []
    
    # Header
    html_parts.append(f'<div class="question-header">')
    html_parts.append(f'<h1 class="question-title">{html.escape(title)}</h1>')
    html_parts.append(f'<p class="question-id">ID: {html.escape(identifier)}</p>')
    if correct_value:
        html_parts.append(f'<p class="correct-answer">Respuesta correcta: <strong>{html.escape(correct_value)}</strong></p>')
    html_parts.append('</div>')
    
    # Contenido del item-body
    html_parts.append('<div class="question-content">')
    
    # Procesar todos los elementos en una sola pasada
    for elem in item_body:
        # Obtener el nombre del tag sin namespace
        tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        tag_lower = tag_name.lower()
        
        if 'choice-interaction' in tag_lower or 'choiceinteraction' in tag_lower:
            # Choice interaction - procesar primero para capturar todo
            html_parts.append('<div class="choices-container">')
            
            # Prompt
            prompt = None
            for p in elem.iter():
                if 'prompt' in p.tag.lower():
                    prompt = p
                    break
            
            if prompt is not None:
                # Renderizar el prompt del choice-interaction preservando MathML
                prompt_html = '<p class="question-prompt"><strong>'
                if prompt.text:
                    prompt_html += html.escape(prompt.text)
                
                # Procesar hijos (puede incluir MathML)
                for child in prompt:
                    child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    child_tag_lower = child_tag.lower()
                    
                    if 'math' in child_tag_lower:
                        prompt_html += render_mathml_to_html(child)
                    else:
                        # Otros elementos
                        if child.text:
                            prompt_html += html.escape(child.text)
                        for grandchild in child:
                            gc_tag = grandchild.tag.split('}')[-1] if '}' in grandchild.tag else grandchild.tag
                            if 'math' in gc_tag.lower():
                                prompt_html += render_mathml_to_html(grandchild)
                            else:
                                if grandchild.text:
                                    prompt_html += html.escape(grandchild.text)
                        if child.tail:
                            prompt_html += html.escape(child.tail)
                    
                    if child.tail:
                        prompt_html += html.escape(child.tail)
                
                prompt_html += '</strong></p>'
                html_parts.append(prompt_html)
            
            # Choices - buscar dentro del choice-interaction
            choices = []
            for choice in elem.iter():
                if 'simple-choice' in choice.tag.lower():
                    choices.append(choice)
            
            html_parts.append('<div class="choices-list">')
            for choice in choices:
                choice_id = choice.get('identifier', '')
                choice_text = extract_text_from_element(choice)
                
                # Buscar MathML en la alternativa
                math_elems = choice.findall(f'.//{{{math_ns}}}math') or choice.findall('.//math')
                if math_elems:
                    for math in math_elems:
                        math_html = render_mathml_to_html(math)
                        math_text = extract_text_from_element(math)
                        choice_text = choice_text.replace(math_text, math_html)
                
                # Buscar imágenes en la alternativa
                img_elems = choice.findall('.//img') or [e for e in choice.iter() if 'img' in e.tag.lower()]
                for img in img_elems:
                    img_html = render_image_to_html(img)
                    choice_text += img_html
                
                is_correct = (choice_id == correct_value)
                correct_class = 'correct-choice' if is_correct else ''
                html_parts.append(f'<div class="choice-item {correct_class}">')
                html_parts.append(f'  <input type="radio" name="response" id="{choice_id}" value="{choice_id}" {"checked" if is_correct else ""} />')
                html_parts.append(f'  <label for="{choice_id}"><strong>{choice_id}:</strong> {choice_text}</label>')
                html_parts.append('</div>')
            
            html_parts.append('</div>')
            html_parts.append('</div>')
        
        elif 'p' in tag_lower or tag_name == 'p':
            # Párrafo - construir HTML preservando imágenes y MathML
            p_html = '<p>'
            if elem.text:
                p_html += html.escape(elem.text)
            
            # Procesar hijos (puede incluir MathML o imágenes)
            for child in elem:
                child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                child_tag_lower = child_tag.lower()
                
                if 'math' in child_tag_lower:
                    p_html += render_mathml_to_html(child)
                elif 'img' in child_tag_lower:
                    p_html += render_image_to_html(child)
                else:
                    # Otros elementos
                    if child.text:
                        p_html += html.escape(child.text)
                    for grandchild in child:
                        gc_tag = grandchild.tag.split('}')[-1] if '}' in grandchild.tag else grandchild.tag
                        if 'math' in gc_tag.lower():
                            p_html += render_mathml_to_html(grandchild)
                        elif 'img' in gc_tag.lower():
                            p_html += render_image_to_html(grandchild)
                    if child.tail:
                        p_html += html.escape(child.tail)
                
                if child.tail:
                    p_html += html.escape(child.tail)
            
            p_html += '</p>'
            html_parts.append(p_html)
        
        elif 'img' in tag_lower:
            # Imagen
            html_parts.append(render_image_to_html(elem))
        
        elif 'table' in tag_lower:
            # Tabla
            html_parts.append(render_table_to_html(elem))
        
        elif 'div' in tag_lower:
            # Div (puede contener tablas)
            for child in elem:
                child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                if 'table' in child_tag.lower():
                    html_parts.append(render_table_to_html(child))
    
    html_parts.append('</div>')
    
    return '\n'.join(html_parts)

def create_html_page(qti_html: str, question_num: str) -> str:
    """Crea una página HTML completa con estilos."""
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pregunta {question_num} - Visualización QTI</title>
    <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    <script>
        window.MathJax = {{
            tex: {{
                inlineMath: [['$', '$'], ['\\(', '\\)']],
                displayMath: [['$$', '$$'], ['\\[', '\\]']]
            }},
            options: {{
                skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre']
            }}
        }};
    </script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .question-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
        }}
        
        .question-title {{
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 10px;
        }}
        
        .question-id {{
            font-size: 14px;
            opacity: 0.9;
            margin-bottom: 5px;
        }}
        
        .correct-answer {{
            background: rgba(255,255,255,0.2);
            padding: 10px 15px;
            border-radius: 6px;
            margin-top: 15px;
            font-size: 14px;
        }}
        
        .question-content {{
            padding: 30px;
        }}
        
        .question-prompt {{
            font-size: 18px;
            margin-bottom: 25px;
            line-height: 1.6;
            color: #333;
        }}
        
        .question-image {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            margin: 20px 0;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        
        .question-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .question-table th,
        .question-table td {{
            padding: 12px;
            text-align: left;
            border: 1px solid #e0e0e0;
        }}
        
        .question-table th {{
            background: #f5f5f5;
            font-weight: 600;
            color: #333;
        }}
        
        .question-table tr:nth-child(even) {{
            background: #fafafa;
        }}
        
        .choices-container {{
            margin-top: 30px;
        }}
        
        .choices-list {{
            display: flex;
            flex-direction: column;
            gap: 15px;
        }}
        
        .choice-item {{
            display: flex;
            align-items: flex-start;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            background: #f9f9f9;
            transition: all 0.3s ease;
        }}
        
        .choice-item:hover {{
            border-color: #667eea;
            background: #f0f0ff;
            transform: translateX(5px);
        }}
        
        .choice-item.correct-choice {{
            border-color: #4caf50;
            background: #e8f5e9;
        }}
        
        .choice-item input[type="radio"] {{
            margin-right: 12px;
            margin-top: 3px;
            cursor: pointer;
        }}
        
        .choice-item label {{
            flex: 1;
            cursor: pointer;
            line-height: 1.5;
            font-size: 16px;
        }}
        
        .choice-item label strong {{
            color: #667eea;
            margin-right: 8px;
        }}
        
        .correct-choice label strong {{
            color: #4caf50;
        }}
        
        .math-container {{
            display: inline-block;
            margin: 0 4px;
        }}
        
        p {{
            margin: 15px 0;
            line-height: 1.6;
            color: #444;
        }}
        
        .back-link {{
            display: inline-block;
            margin: 20px 30px;
            color: white;
            text-decoration: none;
            padding: 10px 20px;
            background: rgba(255,255,255,0.2);
            border-radius: 6px;
            transition: background 0.3s;
        }}
        
        .back-link:hover {{
            background: rgba(255,255,255,0.3);
        }}
    </style>
</head>
<body>
    <a href="#" class="back-link" onclick="window.close()">← Volver</a>
    <div class="container">
        {qti_html}
    </div>
</body>
</html>"""

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
        print(f"🌐 Abre el archivo en tu navegador para ver la pregunta")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
