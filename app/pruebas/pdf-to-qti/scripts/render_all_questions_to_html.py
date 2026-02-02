#!/usr/bin/env python3
"""
Script para renderizar todas las preguntas QTI a un único HTML.
Permite revisar toda la prueba en un solo archivo con navegación.
"""

import html
import sys
from pathlib import Path

# Importar funciones del script de renderizado individual
from render_qti_to_html import render_qti_to_html


def create_full_test_html(output_dir: Path, num_questions: int = 65) -> str:
    """Crea un HTML completo con todas las preguntas."""

    # Construir índice
    index_html = []
    index_html.append('<div class="test-index">')
    index_html.append("<h2>Índice de Preguntas</h2>")
    index_html.append('<div class="index-grid">')

    for i in range(1, num_questions + 1):
        question_num = f"{i:03d}"
        index_html.append(f'<a href="#question-{i}" class="index-item">Pregunta {i}</a>')

    index_html.append("</div>")
    index_html.append("</div>")

    # Construir contenido de todas las preguntas
    questions_html = []

    for i in range(1, num_questions + 1):
        question_num = f"{i:03d}"
        xml_path = output_dir / f"question_{question_num}" / "question.xml"

        if not xml_path.exists():
            questions_html.append(f'<div id="question-{i}" class="question-section">')
            questions_html.append('<div class="question-header">')
            questions_html.append(f'<h1 class="question-title">Pregunta {i}</h1>')
            questions_html.append(f'<p class="question-id">ID: question_{question_num}</p>')
            questions_html.append("</div>")
            questions_html.append('<div class="question-content">')
            questions_html.append('<p style="color: red;">❌ Pregunta no encontrada</p>')
            questions_html.append("</div>")
            questions_html.append("</div>")
            continue

        try:
            qti_html = render_qti_to_html(xml_path)

            # Agregar navegación
            nav_html = '<div class="question-navigation">'
            if i > 1:
                nav_html += f'<a href="#question-{i - 1}" class="nav-link">← Anterior</a>'
            nav_html += '<a href="#index" class="nav-link">↑ Índice</a>'
            if i < num_questions:
                nav_html += f'<a href="#question-{i + 1}" class="nav-link">Siguiente →</a>'
            nav_html += "</div>"

            questions_html.append(f'<div id="question-{i}" class="question-section">')
            questions_html.append(nav_html)
            questions_html.append(qti_html)
            questions_html.append("</div>")

        except Exception as e:
            questions_html.append(f'<div id="question-{i}" class="question-section">')
            questions_html.append('<div class="question-header">')
            questions_html.append(f'<h1 class="question-title">Pregunta {i}</h1>')
            questions_html.append("</div>")
            questions_html.append('<div class="question-content">')
            questions_html.append(f'<p style="color: red;">❌ Error al renderizar: {html.escape(str(e))}</p>')
            questions_html.append("</div>")
            questions_html.append("</div>")

    # Combinar todo
    full_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PAES Invierno 2026 - Visualización Completa</title>
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

        .test-container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}

        .test-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }}

        .test-header h1 {{
            font-size: 32px;
            font-weight: 600;
            margin-bottom: 10px;
        }}

        .test-header p {{
            font-size: 16px;
            opacity: 0.9;
        }}

        .test-index {{
            padding: 30px;
            background: #f8f9fa;
            border-bottom: 2px solid #e0e0e0;
        }}

        .test-index h2 {{
            font-size: 24px;
            margin-bottom: 20px;
            color: #333;
        }}

        .index-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
            gap: 10px;
        }}

        .index-item {{
            display: block;
            padding: 10px 15px;
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            text-decoration: none;
            color: #667eea;
            text-align: center;
            font-weight: 500;
            transition: all 0.3s ease;
        }}

        .index-item:hover {{
            border-color: #667eea;
            background: #f0f0ff;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}

        .question-section {{
            padding: 30px;
            border-bottom: 3px solid #e0e0e0;
        }}

        .question-section:last-child {{
            border-bottom: none;
        }}

        .question-navigation {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }}

        .nav-link {{
            padding: 8px 16px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 500;
            transition: background 0.3s;
        }}

        .nav-link:hover {{
            background: #5568d3;
        }}

        .question-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 20px;
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
            padding: 20px 0;
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

        .back-to-top {{
            position: fixed;
            bottom: 30px;
            right: 30px;
            padding: 15px 20px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 50px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            font-weight: 500;
            transition: all 0.3s;
        }}

        .back-to-top:hover {{
            background: #5568d3;
            transform: translateY(-3px);
            box-shadow: 0 6px 16px rgba(0,0,0,0.4);
        }}
    </style>
</head>
<body>
    <div class="test-container">
        <div class="test-header">
            <h1>PAES Invierno 2026 - M1</h1>
            <p>Visualización completa de todas las preguntas</p>
        </div>

        <div id="index">
            {"".join(index_html)}
        </div>

        {"".join(questions_html)}
    </div>

    <a href="#index" class="back-to-top">↑ Índice</a>
</body>
</html>"""

    return full_html


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Renderizar todas las preguntas QTI a un único HTML")
    parser.add_argument("--output-dir", default="./output/paes-invierno-2026-new", help="Directorio con los QTI generados")
    parser.add_argument("--output-html", default="./output/paes-invierno-2026-new/full_test_preview.html", help="Archivo HTML de salida")
    parser.add_argument("--num-questions", type=int, default=65, help="Número total de preguntas")

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    if not output_dir.exists():
        print(f"❌ No se encontró el directorio: {output_dir}")
        sys.exit(1)

    print(f"📄 Generando HTML completo con {args.num_questions} preguntas...")

    try:
        full_html = create_full_test_html(output_dir, args.num_questions)

        output_path = Path(args.output_html)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_html)

        print(f"✅ HTML generado: {output_path}")
        print("🌐 Abre el archivo en tu navegador para revisar todas las preguntas")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
