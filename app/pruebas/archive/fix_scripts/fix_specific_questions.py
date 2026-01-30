#!/usr/bin/env python3
"""
Script para corregir imágenes específicas de preguntas problemáticas.
Maneja casos especiales de Q34, Q57, Q61, Q63, Q64.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict

# Load environment variables
from dotenv import load_dotenv

script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent.parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)

# Add modules to path
import sys

import fitz  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.pdf_processor import render_image_area
from modules.utils.s3_uploader import upload_image_to_s3


def fix_q34(question_dir: Path, pdf_path: Path, test_name: str) -> Dict[str, Any]:
    """Q34: Imagen en body incluye texto - ajustar bbox para excluir texto."""
    print("\n🔧 Corrigiendo Q34: Excluir texto de la imagen")

    processed_file = question_dir / "processed_content.json"
    with open(processed_file, "r", encoding="utf-8") as f:
        processed_data = json.load(f)

    pages = processed_data.get("pages", [])
    if not pages:
        return {"success": False, "error": "No hay páginas"}

    page_data = pages[0]
    text_blocks = page_data.get("structured_text", {}).get("blocks", [])

    # Obtener imagen actual
    all_images = processed_data.get("all_images", [])
    if not all_images:
        return {"success": False, "error": "No hay imágenes"}

    img0 = all_images[0]
    original_bbox = img0.get("bbox", [])

    # Buscar bloques de texto que están dentro o arriba de la imagen
    original_bbox[1]
    img_y1 = original_bbox[3]

    # Encontrar el último bloque de texto que claramente es pregunta (no parte de la imagen del chat)
    # Buscar bloques que contengan texto del enunciado
    question_end_y = 0
    for block in text_blocks:
        if block.get("type") != 0:  # Solo texto
            continue
        block_bbox = block.get("bbox", [])
        if len(block_bbox) == 4:
            block_bbox[1]
            block_y1 = block_bbox[3]

            # Obtener texto para verificar si es parte del enunciado
            lines = block.get("lines", [])
            block_text = ""
            for line in lines:
                for span in line.get("spans", []):
                    block_text += span.get("text", "")

            # Si el bloque contiene texto del enunciado o pregunta, y está arriba de la imagen
            # o se solapa con el inicio, debe excluirse
            if block_text.strip() and ("Tomás" in block_text or "parque" in block_text or
                                       "Escribe" in block_text or "chat" in block_text.lower()):
                # Este bloque es parte del enunciado, tomar su final
                if block_y1 > question_end_y and block_y1 <= img_y1:
                    question_end_y = block_y1

    # Buscar el bloque de texto del enunciado completo
    # El enunciado parece estar en un bloque grande que va desde y~10 hasta y~379
    enunciado_end_y = 0
    for block in text_blocks:
        if block.get("type") != 0:
            continue
        block_bbox = block.get("bbox", [])
        if len(block_bbox) == 4:
            block_bbox[1]
            block_y1 = block_bbox[3]

            lines = block.get("lines", [])
            block_text = ""
            for line in lines:
                for span in line.get("spans", []):
                    block_text += span.get("text", "")

            # Si es el bloque grande del enunciado (contiene "Tomás", "parque", etc.)
            if "Tomás" in block_text or ("parque" in block_text and "diversiones" in block_text):
                if block_y1 > enunciado_end_y:
                    enunciado_end_y = block_y1

    # Ajustar bbox para excluir texto arriba y abajo
    # Necesitamos:
    # - y0 más abajo para no cortar la parte superior de la imagen del chat
    # - y1 más arriba para excluir las opciones/pregunta de abajo

    # Ajustar ambos extremos para capturar solo la imagen del chat
    # Basado en análisis:
    # - Hay una imagen raster de 502x462px embebida
    # - Opciones empiezan en y~383.5
    # - El texto descriptivo va desde y~10 hasta y~100-120
    # - La imagen del chat debe estar en el medio, probablemente y~200-350
    # - Necesitamos valores más conservadores para no cortar ni incluir texto

    # Encontrar el área visual del chat
    # El chat es una imagen raster embebida, necesitamos capturar solo esa área
    # Si sigue cortada arriba: necesitamos y0 más pequeño (empezar más arriba)
    # Si muestra pregunta abajo: necesitamos y1 más pequeño (terminar más arriba)
    # Probando un rango más estrecho centrado en el área del chat

    # Ajustar para capturar solo el área del chat sin texto ni pregunta
    # Abajo ya está bien (no muestra pregunta), pero arriba sigue un poco cortada
    # Necesitamos empezar un poco más arriba aún para capturar toda la parte superior del chat
    new_y0 = 105.0  # Empezar en y=105 (un poco más arriba para capturar completamente la parte superior)
    new_y1 = 320.0  # Terminar en y=320 (mantener este valor ya que abajo está bien)

    adjusted_bbox = [
        original_bbox[0],
        new_y0,
        original_bbox[2],
        new_y1
    ]
    altura = new_y1 - new_y0
    print(f"   📏 Ajustando bbox: y0 de {original_bbox[1]:.1f} a {new_y0:.1f}, y1 de {original_bbox[3]:.1f} a {new_y1:.1f}")
    print(f"      Altura: {original_bbox[3] - original_bbox[1]:.1f}px -> {altura:.1f}px")

    # Renderizar y subir
    doc = fitz.open(pdf_path)
    page = doc[0]

    rendered = render_image_area(
        page=page,
        final_bbox=adjusted_bbox,
        original_bbox=original_bbox,
        idx=0,
        mask_areas=None,
    )

    if not rendered or not rendered.get("image_base64"):
        return {"success": False, "error": "Error al renderizar"}

    image_base64 = rendered["image_base64"]
    if not image_base64.startswith("data:"):
        image_base64 = f"data:image/png;base64,{image_base64}"

    s3_url = upload_image_to_s3(
        image_base64=image_base64,
        question_id="Q34_fixed",
        test_name=test_name,
    )

    if not s3_url:
        return {"success": False, "error": "Error al subir a S3"}

    # Actualizar XML
    xml_file = question_dir / "question.xml"
    with open(xml_file, "r", encoding="utf-8") as f:
        xml_content = f.read()

    # Reemplazar URL de imagen
    pattern = r'(<img[^>]*src=")([^"]*Q34[^"]*\.png)("[^>]*/>)'
    xml_content = re.sub(pattern, rf'\1{s3_url}\3', xml_content)

    with open(xml_file, "w", encoding="utf-8") as f:
        f.write(xml_content)

    print(f"✅ Q34 corregida: {s3_url}")
    return {"success": True, "s3_url": s3_url}


def fix_q57(question_dir: Path, pdf_path: Path, test_name: str) -> Dict[str, Any]:
    """Q57: Ajustar bbox para excluir texto del enunciado de la imagen."""
    print("\n🔧 Corrigiendo Q57: Excluir texto del enunciado de la imagen")

    processed_file = question_dir / "processed_content.json"
    with open(processed_file, "r", encoding="utf-8") as f:
        processed_data = json.load(f)

    pages = processed_data.get("pages", [])
    if not pages:
        return {"success": False, "error": "No hay páginas"}

    page_data = pages[0]
    page_bbox = page_data.get("structured_text", {})
    page_width = page_bbox.get("width", 600)
    page_height = page_bbox.get("height", 800)

    # El diagrama está formado por dibujos (drawings), no es una imagen raster
    # Buscar la posición de los dibujos en el PDF
    doc = fitz.open(pdf_path)
    page = doc[0]

    drawings = page.get_drawings()
    if not drawings:
        doc.close()
        return {"success": False, "error": "No se encontraron dibujos para el diagrama"}

    # Encontrar el rango vertical de los dibujos (el diagrama)
    drawing_ys = []
    drawing_xs = []
    for d in drawings:
        rect = d.get("rect", fitz.Rect())
        if rect and not rect.is_empty:
            drawing_ys.append((rect.y0, rect.y1))
            drawing_xs.append((rect.x0, rect.x1))

    if not drawing_ys:
        doc.close()
        return {"success": False, "error": "No se encontraron coordenadas de dibujos"}

    # Calcular el bbox del diagrama basado en los dibujos
    min_y = min(y[0] for y in drawing_ys)
    max_y = max(y[1] for y in drawing_ys)
    min_x = min(x[0] for x in drawing_xs) if drawing_xs else 10
    max_x = max(x[1] for x in drawing_xs) if drawing_xs else page_width - 10

    # Añadir un margen sutil alrededor del diagrama
    # Margen más generoso a la derecha para no cortar contenido
    margin_y = 10
    margin_x_left = 10
    margin_x_right = 80  # Margen aún más grande a la derecha para capturar todo el diagrama

    new_y0 = max(0, min_y - margin_y)
    new_y1 = min(page_height, max_y + margin_y)
    new_x0 = max(0, min_x - margin_x_left)
    new_x1 = min(page_width, max_x + margin_x_right)  # Margen generoso a la derecha

    bbox = [new_x0, new_y0, new_x1, new_y1]

    print(f"   📏 Diagrama encontrado: dibujos en y={min_y:.1f}-{max_y:.1f}")
    print(f"   📏 Bbox ajustado: y0={new_y0:.1f}, y1={new_y1:.1f}, altura={new_y1 - new_y0:.1f}px")

    doc.close()

    print(f"   📏 Ajustando bbox: y0={new_y0:.1f}, y1={new_y1:.1f} (excluye texto en y~0-237, opciones en y~415+)")

    doc = fitz.open(pdf_path)
    page = doc[0]

    rendered = render_image_area(
        page=page,
        final_bbox=bbox,
        original_bbox=bbox,
        idx=0,
        mask_areas=None,
    )

    if not rendered or not rendered.get("image_base64"):
        return {"success": False, "error": "Error al renderizar"}

    image_base64 = rendered["image_base64"]
    if not image_base64.startswith("data:"):
        image_base64 = f"data:image/png;base64,{image_base64}"

    s3_url = upload_image_to_s3(
        image_base64=image_base64,
        question_id="Q57_fixed",
        test_name=test_name,
    )

    if not s3_url:
        return {"success": False, "error": "Error al subir a S3"}

    # Actualizar XML
    xml_file = question_dir / "question.xml"
    with open(xml_file, "r", encoding="utf-8") as f:
        xml_content = f.read()

    # Reemplazar URL de imagen
    pattern = r'(<img[^>]*src=")([^"]*Q57[^"]*\.png)("[^>]*/>)'
    xml_content = re.sub(pattern, rf'\1{s3_url}\3', xml_content)

    with open(xml_file, "w", encoding="utf-8") as f:
        f.write(xml_content)

    print(f"✅ Q57 corregida: {s3_url}")
    return {"success": True, "s3_url": s3_url}


def fix_q61(question_dir: Path, pdf_path: Path, test_name: str) -> Dict[str, Any]:
    """Q61: Primera imagen incompleta arriba e incluye pregunta abajo."""
    print("\n🔧 Corrigiendo Q61: Capturar más arriba y excluir pregunta abajo")

    processed_file = question_dir / "processed_content.json"
    with open(processed_file, "r", encoding="utf-8") as f:
        processed_data = json.load(f)

    pages = processed_data.get("pages", [])
    if not pages:
        return {"success": False, "error": "No hay páginas"}

    page_data = pages[0]
    text_blocks = page_data.get("structured_text", {}).get("blocks", [])

    all_images = processed_data.get("all_images", [])
    if len(all_images) < 1:
        return {"success": False, "error": "No hay imágenes"}

    # Usar la primera imagen
    img0 = all_images[0]
    original_bbox = img0.get("bbox", [])

    # Buscar dónde empieza la pregunta para excluirla
    pregunta_start_y = 9999
    for block in text_blocks:
        if block.get("type") != 0:
            continue
        block_bbox = block.get("bbox", [])
        if len(block_bbox) == 4:
            lines = block.get("lines", [])
            block_text = ""
            for line in lines:
                for span in line.get("spans", []):
                    block_text += span.get("text", "")

            # Si es la pregunta (contiene "¿Por cuál")
            if "¿Por cuál" in block_text or "hay que multiplicar" in block_text:
                block_y0 = block_bbox[1]
                if block_y0 < pregunta_start_y and block_y0 > original_bbox[1]:
                    pregunta_start_y = block_y0

    # Ajustar bbox:
    # - Empezar más arriba para capturar todo el contenido (y0 menor)
    # - Terminar antes de la pregunta (y1 menor)
    # Basado en análisis: pregunta empieza en y~211.9, imagen actual termina en y~201.9
    # Necesitamos empezar aún más arriba y terminar antes de la pregunta
    new_y0 = original_bbox[1] - 45  # Empezar 45px más arriba (de 97.2 a ~52.2) para capturar más contenido arriba
    # Terminar antes de la pregunta - usar valor más conservador
    # La pregunta empieza en y~211.9, terminamos en y~200 para excluirla completamente
    new_y1 = 200.0

    expanded_bbox = [
        original_bbox[0],
        new_y0,
        original_bbox[2],
        new_y1
    ]

    print(f"   📏 Ajustando bbox: y0 de {original_bbox[1]:.1f} a {new_y0:.1f}, y1 de {original_bbox[3]:.1f} a {new_y1:.1f}")
    print(f"      Altura: {original_bbox[3] - original_bbox[1]:.1f}px -> {new_y1 - new_y0:.1f}px")

    doc = fitz.open(pdf_path)
    page = doc[0]

    rendered = render_image_area(
        page=page,
        final_bbox=expanded_bbox,
        original_bbox=original_bbox,
        idx=0,
        mask_areas=None,
    )

    if not rendered or not rendered.get("image_base64"):
        return {"success": False, "error": "Error al renderizar"}

    image_base64 = rendered["image_base64"]
    if not image_base64.startswith("data:"):
        image_base64 = f"data:image/png;base64,{image_base64}"

    s3_url = upload_image_to_s3(
        image_base64=image_base64,
        question_id="Q61_img0_fixed",
        test_name=test_name,
    )

    if not s3_url:
        return {"success": False, "error": "Error al subir a S3"}

    # Actualizar XML: reemplazar primera imagen, eliminar segunda
    xml_file = question_dir / "question.xml"
    with open(xml_file, "r", encoding="utf-8") as f:
        xml_content = f.read()

    # Reemplazar primera imagen
    pattern1 = r'(<img[^>]*src=")([^"]*Q61[^"]*restored_0[^"]*\.png)("[^>]*/>)'
    xml_content = re.sub(pattern1, rf'\1{s3_url}\3', xml_content)

    # Eliminar segunda imagen
    pattern2 = r'<p>\s*<img[^>]*src="[^"]*Q61[^"]*restored_1[^"]*\.png"[^>]*/>\s*</p>\s*'
    xml_content = re.sub(pattern2, '', xml_content)

    with open(xml_file, "w", encoding="utf-8") as f:
        f.write(xml_content)

    print(f"✅ Q61 corregida: {s3_url}")
    return {"success": True, "s3_url": s3_url}


def fix_q63(question_dir: Path, pdf_path: Path, test_name: str) -> Dict[str, Any]:
    """Q63: Reorganizar imágenes.

    Según el usuario:
    - La imagen del enunciado está en A (debe ir al body)
    - La de A está en B
    - La de B está en C
    - En D están C y D

    Imágenes disponibles (ordenadas por posición y):
    - img0: y=10.0 (más arriba, probablemente enunciado)
    - img4: y=10.0 (también arriba, altura 54.0)
    - img1: y=208.4
    - img2: y=318.2
    - img3: y=428.5

    El enunciado debería ser la imagen más pequeña arriba (img4, altura 54).
    Las opciones deberían ser img0, img1, img2, img3 en orden.
    """
    print("\n🔧 Corrigiendo Q63: Reorganizar imágenes")

    # Leer extracted_content.json que tiene las imágenes insertadas reales
    extracted_file = question_dir / "extracted_content.json"
    if not extracted_file.exists():
        processed_file = question_dir / "processed_content.json"
        with open(processed_file, "r", encoding="utf-8") as f:
            processed_data = json.load(f)
        all_images = processed_data.get("all_images", [])
    else:
        with open(extracted_file, "r", encoding="utf-8") as f:
            extracted_data = json.load(f)
        pages_data = extracted_data.get("pages", [])
        if not pages_data:
            return {"success": False, "error": "No hay páginas en extracted_content"}

        # Extraer imágenes insertadas (tipo 1) del extracted_content
        blocks = pages_data[0].get("structured_text", {}).get("blocks", [])
        image_blocks = [b for b in blocks if b.get("type") == 1]

        if len(image_blocks) < 5:
            return {"success": False, "error": f"Se esperaban 5 imágenes insertadas, hay {len(image_blocks)}"}

        # Convertir a formato similar a all_images
        all_images = []
        for i, block in enumerate(image_blocks):
            all_images.append({"bbox": block.get("bbox", [])})

    doc = fitz.open(pdf_path)
    page = doc[0]

    # Usar las imágenes insertadas reales del extracted_content.json:
    # - Imagen 1 (enunciado): bbox=[204.05, 38.43, 448.95, 135.38]
    # - Imagen 4 (opción A): bbox=[117.7, 204.38, 360.35, 302.08]
    # - Imagen 6 (opción B): bbox=[120.5, 316.58, 360.35, 410.98]
    # - Imagen 8 (opción C): bbox=[118.65, 425.53, 364.05, 522.78]
    # - Imagen 10 (opción D): bbox=[120.5, 537.33, 365.95, 635.93]

    # El enunciado es la primera imagen insertada (índice 0 en image_blocks, que corresponde a all_images[0])
    # Incluye el texto "63. Considera..." (y~10-154.2) y la pregunta (y~154.6-181.8)
    # El dibujo visual está entre estos textos. Ajustar bbox para capturar solo el dibujo
    img0 = all_images[0]
    img0_bbox = img0.get("bbox", [])

    # Usar el bbox de la imagen insertada real del enunciado
    # bbox=[204.05, 38.43, 448.95, 135.38] - esta ya es solo la imagen, sin textos
    # Pero puede tener texto alrededor, usar mask para estar seguro
    img0_bbox_adjusted = img0_bbox  # Usar bbox de la imagen insertada

    # Definir áreas a enmascarar: bordes que puedan tener texto
    mask_areas_body = [
        {"bbox": [60.0, 10.0, 205.0, 40.0]},  # Texto "63." arriba a la izquierda
        {"bbox": [95.0, 135.0, 560.0, 155.0]},  # Borde inferior que puede tener texto
    ]

    rendered0 = render_image_area(
        page=page,
        final_bbox=img0_bbox_adjusted,
        original_bbox=img0_bbox,
        idx=0,
        mask_areas=mask_areas_body,
    )

    if not rendered0 or not rendered0.get("image_base64"):
        return {"success": False, "error": "Error al renderizar img0 (enunciado)"}

    img0_base64 = rendered0["image_base64"]
    if not img0_base64.startswith("data:"):
        img0_base64 = f"data:image/png;base64,{img0_base64}"

    s3_url_body = upload_image_to_s3(
        image_base64=img0_base64,
        question_id="Q63_body",
        test_name=test_name,
    )

    # Opciones: img1 -> A, img2 -> B, img3 parte superior -> C, img3 parte inferior -> D
    # Pero img3 es muy grande (y=428.5-644.9, altura 216.4px), probablemente incluye C y D juntas
    # Necesitamos dividir img3 en dos partes
    option_images = []

    # A y B son directas
    mapping_direct = [
        (1, "A"),  # img1 -> A
        (2, "B"),  # img2 -> B
    ]

    # Para C y D, dividir img3 en dos partes
    img3 = all_images[3]
    img3_bbox = img3.get("bbox", [])
    img3_y0 = img3_bbox[1]
    img3_y1 = img3_bbox[3]
    img3_height = img3_y1 - img3_y0

    # Dividir img3 en dos partes, excluyendo completamente las letras "C)" y "D)"
    # C) está en x=101.5-117.6, y=428.5-455.7
    # D) está en x=101.5-117.6, y=539.9-567.1
    # Dividir aproximadamente en el medio (y~536.7), pero ajustando para excluir las letras
    split_point = img3_y0 + (img3_height / 2)  # Aproximadamente y~536.7
    # C: empezar después de "C)" (y~455.7) y excluir área izquierda
    # C: empezar un poco antes para que no se corte arriba, pero mask "C)" que está en y~428.5-455.7
    # Empezar en y~455 para capturar un poco más arriba, pero mask "C)"
    [125.0, 455.0, img3_bbox[2], split_point - 5]  # Parte superior (C), empezar un poco antes
    # D: empezar antes del split para capturar más arriba, pero mask "D)" que está en y~539.9-567.1
    [125.0, max(split_point - 5, 530.0), img3_bbox[2], img3_y1]  # Parte inferior (D), empezar más arriba

    # Renderizar A y B
    # Ajustar bboxes para excluir las letras de alternativas
    # A) está en y=208.4-235.5, empezar después de y=235.5
    # B) está en y=318.2-345.4, empezar después de y=345.4
    for img_idx, choice_letter in mapping_direct:
        img = all_images[img_idx]
        img_bbox = img.get("bbox", [])

        # Usar mask_areas para excluir las letras de alternativas
        mask_areas = []
        if choice_letter == "A":
            # "A)" está en x=101.5-116.9, y=208.4-235.5
            # La imagen real empieza en x=117.7, así que ya está bien, pero mask por seguridad
            mask_areas = [{"bbox": [95.0, 203.0, 120.0, 240.0]}]  # Área a la izquierda con "A)"
        elif choice_letter == "B":
            # "B)" está en x=101.5-116.9, y=318.2-345.4
            # La imagen real empieza en x=120.5, así que ya está bien, pero mask por seguridad
            mask_areas = [{"bbox": [95.0, 315.0, 123.0, 350.0]}]  # Área a la izquierda con "B)"
        elif choice_letter == "C":
            # "C)" está en x=101.5-117.6, y=428.5-455.7
            # La imagen real empieza en x=118.65, así que ya está bien, pero mask por seguridad
            mask_areas = [{"bbox": [95.0, 425.0, 122.0, 460.0]}]  # Área a la izquierda con "C)"
        elif choice_letter == "D":
            # "D)" está en x=101.5-117.6, y=539.9-567.1
            # La imagen real empieza en x=120.5, así que ya está bien, pero mask por seguridad
            mask_areas = [{"bbox": [95.0, 535.0, 123.0, 572.0]}]  # Área a la izquierda con "D)"

        rendered = render_image_area(
            page=page,
            final_bbox=img_bbox,
            original_bbox=img_bbox,
            idx=img_idx,
            mask_areas=mask_areas if mask_areas else None,
        )

        if rendered and rendered.get("image_base64"):
            img_base64 = rendered["image_base64"]
            if not img_base64.startswith("data:"):
                img_base64 = f"data:image/png;base64,{img_base64}"

            s3_url = upload_image_to_s3(
                image_base64=img_base64,
                question_id=f"Q63_choice_{choice_letter}",
                test_name=test_name,
            )

            if s3_url:
                option_images.append({
                    "choice": choice_letter,
                    "url": s3_url
                })

    # Renderizar C y D también
    # Ajustar bboxes para empezar un poco más arriba y evitar cortes
    for img_idx, choice_letter in [(3, "C"), (4, "D")]:
        img = all_images[img_idx]
        img_bbox = img.get("bbox", [])

        # Ajustar bbox para empezar más arriba y evitar cortes
        if choice_letter == "C":
            # Imagen original: y=425.53-522.78, empezar más arriba aún
            img_bbox_adjusted = [img_bbox[0], 415.0, img_bbox[2], img_bbox[3]]  # Empezar 10px más arriba
            mask_areas = [{"bbox": [95.0, 425.0, 122.0, 460.0]}]  # Área a la izquierda con "C)"
        elif choice_letter == "D":
            # Imagen original: y=537.33-635.93, empezar más arriba aún
            img_bbox_adjusted = [img_bbox[0], 527.0, img_bbox[2], img_bbox[3]]  # Empezar 10px más arriba
            mask_areas = [{"bbox": [95.0, 535.0, 123.0, 572.0]}]  # Área a la izquierda con "D)"
        else:
            img_bbox_adjusted = img_bbox
            mask_areas = []

        rendered = render_image_area(
            page=page,
            final_bbox=img_bbox_adjusted,
            original_bbox=img_bbox,
            idx=img_idx,
            mask_areas=mask_areas if mask_areas else None,
        )

        if rendered and rendered.get("image_base64"):
            img_base64 = rendered["image_base64"]
            if not img_base64.startswith("data:"):
                img_base64 = f"data:image/png;base64,{img_base64}"

            s3_url = upload_image_to_s3(
                image_base64=img_base64,
                question_id=f"Q63_choice_{choice_letter}",
                test_name=test_name,
            )

            if s3_url:
                option_images.append({
                    "choice": choice_letter,
                    "url": s3_url
                })

    if not s3_url_body or len(option_images) != 4:
        return {"success": False, "error": "Error al procesar imágenes"}

    # Actualizar XML
    xml_file = question_dir / "question.xml"
    with open(xml_file, "r", encoding="utf-8") as f:
        xml_content = f.read()

    # Eliminar todas las imágenes duplicadas del body primero
    body_img_pattern = r'<p><img src="[^"]*Q63[^"]*body[^"]*\.png"[^>]*/>\s*</p>\s*'
    xml_content = re.sub(body_img_pattern, '', xml_content)

    # Añadir imagen al body (solo una, antes del qti-choice-interaction)
    if "<qti-choice-interaction" in xml_content:
        # Buscar el párrafo del enunciado y añadir la imagen después
        body_img_pattern = r'(<p>Considera el siguiente dibujo de un velero en el agua\.</p>\s*)'
        replacement = rf'\1<p><img src="{s3_url_body}" alt="Dibujo del velero"/></p>\n    '
        xml_content = re.sub(body_img_pattern, replacement, xml_content)

    # Actualizar imágenes en opciones
    for opt_img in option_images:
        choice_id = f"Choice{opt_img['choice']}"
        choice_pattern = rf'<qti-simple-choice[^>]*identifier="{choice_id}"[^>]*>.*?</qti-simple-choice>'

        def replace_choice(match):
            full_match = match.group(0)
            # Extraer tag de apertura
            open_match = re.search(rf'(<qti-simple-choice[^>]*identifier="{choice_id}"[^>]*>)', full_match)
            if not open_match:
                return full_match
            open_tag = open_match.group(1)
            # Reemplazar contenido con solo la imagen
            return f'{open_tag}<p><img src="{opt_img["url"]}" alt="Opción {opt_img["choice"]}"/></p></qti-simple-choice>'

        xml_content = re.sub(choice_pattern, replace_choice, xml_content, flags=re.DOTALL)

    with open(xml_file, "w", encoding="utf-8") as f:
        f.write(xml_content)

    print("✅ Q63 corregida")
    return {"success": True}


def fix_q64(question_dir: Path, pdf_path: Path, test_name: str) -> Dict[str, Any]:
    """Q64: Corregir 2 imágenes del enunciado - deben estar separadas por texto intermedio."""
    print("\n🔧 Corrigiendo Q64: Corregir 2 imágenes del enunciado")

    processed_file = question_dir / "processed_content.json"
    with open(processed_file, "r", encoding="utf-8") as f:
        processed_data = json.load(f)

    pages = processed_data.get("pages", [])
    if not pages:
        return {"success": False, "error": "No hay páginas"}

    page_data = pages[0]
    page_bbox = page_data.get("structured_text", {})
    page_width = page_bbox.get("width", 600)
    page_height = page_bbox.get("height", 800)

    doc = fitz.open(pdf_path)
    page = doc[0]

    # Buscar dibujos que formen los tableros
    drawings = page.get_drawings()

    # Buscar dónde está el texto intermedio para separar los dos tableros
    text_blocks = page_data.get("structured_text", {}).get("blocks", [])

    # El texto intermedio es "El rey puede moverse... por ejemplo, a la flecha ↗ le corresponde..."

    for block in text_blocks:
        if block.get("type") != 0:
            continue
        block_bbox = block.get("bbox", [])
        if len(block_bbox) == 4:
            lines = block.get("lines", [])
            block_text = ""
            for line in lines:
                for span in line.get("spans", []):
                    block_text += span.get("text", "")

            # Texto intermedio que separa los dos tableros
            if "El rey puede moverse" in block_text or "ejemplo" in block_text.lower():
                block_bbox[1]
                block_bbox[3]
                break

    # Basado en análisis: texto intermedio en y~223-485, dibujos en y~265-641
    # Primer tablero: antes del texto intermedio (y~250-300 aproximadamente)
    # Segundo tablero: después del texto intermedio (y~500-650 aproximadamente)

    # Usar valores basados en el análisis del PDF
    # El texto intermedio "El rey puede moverse..." termina alrededor de y~485
    # Los dibujos del primer tablero están antes, los del segundo después

    # Agrupar dibujos por posición vertical
    drawing_regions = []
    for d in drawings:
        rect = d.get("rect", fitz.Rect())
        if rect and not rect.is_empty:
            drawing_regions.append((rect.y0, rect.y1, rect.x0, rect.x1))

    if not drawing_regions:
        doc.close()
        return {"success": False, "error": "No se encontraron dibujos"}

    # Basado en análisis del PDF:
    # - Texto intermedio "El rey puede moverse..." está en y~223-485
    # - Dibujos están en y~265-641
    # - Primer tablero: dibujos antes de y~450 (y~265-400)
    # - Segundo tablero: dibujos después de y~485 (y~500-650)

    # Dividir dibujos: primer tablero antes de y~450, segundo tablero después de y~485
    first_tablero_drawings = [r for r in drawing_regions if r[1] < 450]
    second_tablero_drawings = [r for r in drawing_regions if r[0] > 485]

    if first_tablero_drawings and second_tablero_drawings:
        # Calcular bboxes para cada tablero
        first_min_y = min(r[0] for r in first_tablero_drawings)
        first_max_y = max(r[1] for r in first_tablero_drawings)
        first_min_x = min(r[2] for r in first_tablero_drawings)
        first_max_x = max(r[3] for r in first_tablero_drawings)

        second_min_y = min(r[0] for r in second_tablero_drawings)
        second_max_y = max(r[1] for r in second_tablero_drawings)
        second_min_x = min(r[2] for r in second_tablero_drawings)
        second_max_x = max(r[3] for r in second_tablero_drawings)

        margin = 15
        bbox1 = [
            max(0, first_min_x - margin),
            max(0, first_min_y - margin),
            min(page_width, first_max_x + margin),
            min(page_height, first_max_y + margin)
        ]
        bbox2 = [
            max(0, second_min_x - margin),
            max(0, second_min_y - margin),
            min(page_width, second_max_x + margin),
            min(page_height, second_max_y + margin)
        ]
    else:
        # Fallback: usar valores fijos basados en análisis
        # Primer tablero: y~265-400 (antes del texto intermedio)
        # Segundo tablero: y~500-650 (después del texto intermedio)
        bbox1 = [10, 265.0, page_width - 10, 400.0]  # Primer tablero
        bbox2 = [10, 500.0, page_width - 10, 650.0]  # Segundo tablero

    print(f"   📏 Primer tablero: y={bbox1[1]:.1f}-{bbox1[3]:.1f}")
    print(f"   📏 Segundo tablero: y={bbox2[1]:.1f}-{bbox2[3]:.1f}")

    # Renderizar ambas imágenes
    body_images = []
    for i, bbox in enumerate([bbox1, bbox2]):
        rendered = render_image_area(
            page=page,
            final_bbox=bbox,
            original_bbox=bbox,
            idx=i,
            mask_areas=None,
        )

        if rendered and rendered.get("image_base64"):
            img_base64 = rendered["image_base64"]
            if not img_base64.startswith("data:"):
                img_base64 = f"data:image/png;base64,{img_base64}"

            s3_url = upload_image_to_s3(
                image_base64=img_base64,
                question_id=f"Q64_body_{i}",
                test_name=test_name,
            )

            if s3_url:
                body_images.append(s3_url)

    doc.close()

    if len(body_images) != 2:
        return {"success": False, "error": "Error al procesar las 2 imágenes"}

    # Actualizar XML
    xml_file = question_dir / "question.xml"
    with open(xml_file, "r", encoding="utf-8") as f:
        xml_content = f.read()

    # Reemplazar las dos imágenes existentes con las nuevas
    # Buscar todas las imágenes Q64 y reemplazarlas
    img_pattern = r'<p><img src="[^"]*Q64[^"]*\.png"[^>]*/>'
    matches = list(re.finditer(img_pattern, xml_content))

    if len(matches) >= 2:
        # Reemplazar primera imagen
        xml_content = (
            xml_content[:matches[0].start()] +
            f'<p><img src="{body_images[0]}" alt="Primer tablero de ajedrez con rey en e2"/></p>' +
            xml_content[matches[0].end():]
        )
        # Buscar de nuevo para la segunda (índices cambiaron)
        matches = list(re.finditer(img_pattern, xml_content))
        if matches:
            xml_content = (
                xml_content[:matches[0].start()] +
                f'<p><img src="{body_images[1]}" alt="Segundo tablero de ajedrez con ejemplo de movimiento"/></p>' +
                xml_content[matches[0].end():]
            )
    else:
        # Si solo hay una imagen o ninguna, añadir ambas
        # Buscar dónde insertar (después del primer párrafo)
        first_para_pattern = r'(<p>En el siguiente tablero de ajedrez[^<]*</p>\s*)'
        replacement = rf'\1<p><img src="{body_images[0]}" alt="Primer tablero de ajedrez con rey en e2"/></p>\n    <p><img src="{body_images[1]}" alt="Segundo tablero de ajedrez con ejemplo de movimiento"/></p>\n    '
        xml_content = re.sub(first_para_pattern, replacement, xml_content)

    with open(xml_file, "w", encoding="utf-8") as f:
        f.write(xml_content)

    print("✅ Q64 corregida: 2 imágenes separadas")
    return {"success": True}


def main():
    """Función principal."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Corregir imágenes específicas de preguntas"
    )
    parser.add_argument(
        "--questions-dir",
        default="../../data/pruebas/procesadas/seleccion-regular-2025/qti",
        help="Directorio base con preguntas"
    )
    parser.add_argument(
        "--pdfs-dir",
        default="../../data/pruebas/procesadas/seleccion-regular-2025/pdf",
        help="Directorio con PDFs originales"
    )
    parser.add_argument(
        "--test-name",
        default="seleccion-regular-2025",
        help="Nombre del test para S3"
    )
    parser.add_argument(
        "--questions",
        nargs="+",
        default=["Q34", "Q57", "Q61", "Q63", "Q64"],
        help="IDs de preguntas a corregir",
    )

    args = parser.parse_args()

    questions_dir = Path(args.questions_dir)
    pdfs_dir = Path(args.pdfs_dir)

    fixers = {
        "Q34": fix_q34,
        "Q57": fix_q57,
        "Q61": fix_q61,
        "Q63": fix_q63,
        "Q64": fix_q64,
    }

    print("=" * 60)
    print("🔧 CORRECCIÓN DE IMÁGENES ESPECÍFICAS")
    print("=" * 60)

    results = []
    for q_id in args.questions:
        if q_id not in fixers:
            print(f"\n❌ {q_id}: No hay fixer disponible")
            results.append({"question": q_id, "success": False, "error": "No fixer"})
            continue

        q_dir = questions_dir / q_id
        pdf_path = pdfs_dir / f"{q_id}.pdf"

        if not q_dir.exists() or not pdf_path.exists():
            print(f"\n❌ {q_id}: Archivos no encontrados")
            results.append({"question": q_id, "success": False, "error": "Archivos no encontrados"})
            continue

        fixer = fixers[q_id]
        result = fixer(q_dir, pdf_path, args.test_name)
        result["question"] = q_id
        results.append(result)

    print("\n" + "=" * 60)
    print("📊 RESUMEN")
    print("=" * 60)
    successful = sum(1 for r in results if r.get("success"))
    print(f"✅ Exitosas: {successful}/{len(results)}")
    print("=" * 60)

    return results


if __name__ == "__main__":
    main()
