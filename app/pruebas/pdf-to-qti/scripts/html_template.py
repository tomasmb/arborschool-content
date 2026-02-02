"""
HTML template and styles for QTI HTML preview.

This module contains the CSS styles and page template for rendering
QTI questions as visual HTML.
"""

from __future__ import annotations

# MathJax configuration script
MATHJAX_CONFIG = """
    <script>
        window.MathJax = {
            tex: {
                inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
                displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']]
            },
            options: {
                skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre']
            }
        };
    </script>"""

# CSS styles for QTI preview
HTML_STYLES = """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
                         'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }

        .question-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
        }

        .question-title {
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 10px;
        }

        .question-id {
            font-size: 14px;
            opacity: 0.9;
            margin-bottom: 5px;
        }

        .correct-answer {
            background: rgba(255,255,255,0.2);
            padding: 10px 15px;
            border-radius: 6px;
            margin-top: 15px;
            font-size: 14px;
        }

        .question-content {
            padding: 30px;
        }

        .question-prompt {
            font-size: 18px;
            margin-bottom: 25px;
            line-height: 1.6;
            color: #333;
        }

        .question-prompt ul,
        .question-prompt ol {
            margin: 15px 0;
            padding-left: 30px;
        }

        .question-prompt li {
            margin: 8px 0;
            line-height: 1.6;
        }

        .question-prompt p {
            margin: 10px 0;
        }

        .question-image {
            max-width: 100%;
            width: auto;
            height: auto;
            border-radius: 8px;
            margin: 10px 0;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            display: block;
            object-fit: contain;
        }

        p img.question-image {
            max-width: 100%;
            width: auto;
            height: auto;
            display: block;
            margin: 15px auto;
        }

        .choice-item .question-image {
            max-width: 100%;
            width: auto;
            min-width: 200px;
            height: auto;
            display: block;
            margin: 10px 0;
        }

        .question-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .question-table th,
        .question-table td {
            padding: 12px;
            text-align: left;
            border: 1px solid #e0e0e0;
        }

        .question-table th {
            background: #f5f5f5;
            font-weight: 600;
            color: #333;
        }

        .question-table tr:nth-child(even) {
            background: #fafafa;
        }

        .choices-container {
            margin-top: 30px;
        }

        .choices-list {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }

        .choice-item {
            display: flex;
            align-items: flex-start;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            background: #f9f9f9;
            transition: all 0.3s ease;
        }

        .choice-item:hover {
            border-color: #667eea;
            background: #f0f0ff;
            transform: translateX(5px);
        }

        .choice-item.correct-choice {
            border-color: #4caf50;
            background: #e8f5e9;
        }

        .choice-item input[type="radio"] {
            margin-right: 12px;
            margin-top: 3px;
            cursor: pointer;
            flex-shrink: 0;
        }

        .choice-item label {
            flex: 1;
            cursor: pointer;
            line-height: 1.5;
            font-size: 16px;
            display: block;
            min-width: 0;
        }

        .choice-item label img {
            max-width: 100%;
            width: auto;
            height: auto;
            display: block;
            margin: 10px 0;
        }

        .choice-item label strong {
            color: #667eea;
            margin-right: 8px;
        }

        .correct-choice label strong {
            color: #4caf50;
        }

        .math-container {
            display: inline-block;
            margin: 0 4px;
            vertical-align: middle;
        }

        .math-container math {
            display: inline-block;
        }

        .equation-system {
            margin: 20px 0;
            padding: 15px;
            background: #f9f9f9;
            border-left: 4px solid #667eea;
            border-radius: 4px;
        }

        .equation-system math {
            display: block;
            margin: 8px 0;
            text-align: center;
        }

        p {
            margin: 15px 0;
            line-height: 1.6;
            color: #444;
        }

        .back-link {
            display: inline-block;
            margin: 20px 30px;
            color: white;
            text-decoration: none;
            padding: 10px 20px;
            background: rgba(255,255,255,0.2);
            border-radius: 6px;
            transition: background 0.3s;
        }

        .back-link:hover {
            background: rgba(255,255,255,0.3);
        }"""


def create_html_page(qti_html: str, question_num: str) -> str:
    """Crea una página HTML completa con estilos.

    Args:
        qti_html: HTML content of the question
        question_num: Question number for the title

    Returns:
        Complete HTML page as string
    """
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pregunta {question_num} - Visualización QTI</title>
    <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
    <script id="MathJax-script" async
            src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
{MATHJAX_CONFIG}
    <style>
{HTML_STYLES}
    </style>
</head>
<body>
    <a href="#" class="back-link" onclick="window.close()">← Volver</a>
    <div class="container">
        {qti_html}
    </div>
</body>
</html>"""
