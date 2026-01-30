#!/usr/bin/env python3
"""
Script para corregir imágenes sin llamar a la API.
Re-renderiza imágenes desde PDF con bboxes ajustados para excluir texto de pregunta.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

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


def find_question_text_blocks_in_image(
    image_bbox: List[float],
    text_blocks: List[Dict[str, Any]],
    margin: float = 30.0
) -> List[Dict[str, Any]]:
    """
    Encuentra bloques de texto que están dentro o muy cerca del área de la imagen.
    
    Args:
        image_bbox: Bbox de la imagen [x0, y0, x1, y1]
        text_blocks: Lista de bloques de texto
        margin: Margen adicional para considerar solapamiento
        
    Returns:
        Lista de bloques que están dentro del área de la imagen
    """
    if len(image_bbox) != 4:
        return []

    img_x0, img_y0, img_x1, img_y1 = image_bbox

    # Expandir área de imagen con margen (especialmente hacia arriba)
    check_y0 = img_y0 - margin
    check_y1 = img_y1

    overlapping_blocks = []
    for block in text_blocks:
        if block.get("type") != 0:  # Solo bloques de texto
            continue

        block_bbox = block.get("bbox", [])
        if len(block_bbox) != 4:
            continue

        block_x0, block_y0, block_x1, block_y1 = block_bbox

        # Verificar si el bloque está dentro del área expandida de la imagen
        # Especialmente en la parte superior (donde suele estar la pregunta)
        # También considerar bloques que empiezan antes pero terminan dentro
        if (block_y0 >= check_y0 and block_y1 <= img_y1 and
            block_x1 >= img_x0 and block_x0 <= img_x1):
            overlapping_blocks.append({
                "block": block,
                "bbox": block_bbox,
                "bottom": block_y1,
                "top": block_y0,
            })
        # También considerar bloques que empiezan antes de la imagen pero terminan dentro
        elif (block_y0 < img_y0 and block_y1 > img_y0 and block_y1 <= img_y1 and
              block_x1 >= img_x0 and block_x0 <= img_x1):
            overlapping_blocks.append({
                "block": block,
                "bbox": block_bbox,
                "bottom": block_y1,
                "top": block_y0,
            })

    return overlapping_blocks


def adjust_image_bbox_to_exclude_text(
    image_bbox: List[float],
    text_blocks: List[Dict[str, Any]],
    margin: float = 20.0,
    page_width: float = 600.0
) -> Tuple[List[float], bool]:
    """
    Ajusta el bbox de la imagen para excluir bloques de texto de pregunta.
    
    Args:
        image_bbox: Bbox original de la imagen
        text_blocks: Bloques de texto que están dentro de la imagen
        margin: Margen adicional después del último bloque de texto
        
    Returns:
        Tuple de (bbox_ajustado, fue_ajustado)
    """
    if len(image_bbox) != 4:
        return image_bbox, False

    if not text_blocks:
        return image_bbox, False

    img_top = image_bbox[1]
    img_bottom = image_bbox[3]
    img_width = image_bbox[2] - image_bbox[0]
    img_height = image_bbox[3] - image_bbox[1]

    # Si el bbox es pequeño (ancho < 70% de página), probablemente es un gráfico real
    # En ese caso, solo excluir texto que está claramente ARRIBA del gráfico, no dentro
    is_small_graphic = img_width < page_width * 0.7

    # Filtrar bloques: para gráficos pequeños, solo considerar bloques grandes arriba
    # Para bboxes grandes, considerar todos los bloques dentro
    filtered_blocks = []
    for block in text_blocks:
        block_width = block["bbox"][2] - block["bbox"][0]
        block_top = block.get("top", block["bottom"])

        if is_small_graphic:
            # Para gráficos pequeños, solo excluir bloques grandes que están arriba
            # Ignorar bloques pequeños dentro (pueden ser etiquetas del gráfico)
            if block_width > page_width * 0.3 and block_top < img_top + 10:
                filtered_blocks.append(block)
        else:
            # Para bboxes grandes, considerar todos los bloques dentro
            filtered_blocks.append(block)

    if not filtered_blocks:
        return image_bbox, False

    # Encontrar el bloque más bajo que está dentro de la imagen
    max_bottom = max(block["bottom"] for block in filtered_blocks)

    # También encontrar bloques que empiezan dentro de la imagen
    blocks_starting_inside = [
        block for block in filtered_blocks
        if block.get("top", block["bottom"]) >= img_top
    ]

    # Si hay bloques que empiezan dentro, necesitamos excluir todo desde donde empiezan
    if blocks_starting_inside:
        min_top = min(block.get("top", block["bottom"]) for block in blocks_starting_inside)
        # Si el bloque empieza muy arriba (cerca del inicio de la imagen), excluirlo completamente
        if min_top <= img_top + 20:
            # Encontrar el bloque más bajo que empieza en esa zona
            max_bottom = max(block["bottom"] for block in blocks_starting_inside)

    # Ajustar y0 para empezar después del último bloque de texto
    adjusted_bbox = image_bbox.copy()
    new_y0 = max_bottom + margin

    # Verificar que el nuevo bbox tiene sentido
    if new_y0 >= image_bbox[3]:  # Si y0 >= y1, el bbox no tiene sentido
        return image_bbox, False

    # Verificar que hay suficiente espacio para una imagen válida
    min_height = 50  # Altura mínima
    if (image_bbox[3] - new_y0) < min_height:
        # Si no hay suficiente espacio, intentar ajustar también y1
        # Pero solo si el ajuste es razonable
        return image_bbox, False

    adjusted_bbox[1] = new_y0

    print(f"   🔧 Ajuste: y0 {image_bbox[1]:.1f} → {new_y0:.1f} (excluyendo {len(text_blocks)} bloques de texto)")

    return adjusted_bbox, True


def fix_q64_special(
    question_dir: Path,
    pdf_path: Path,
    test_name: str,
) -> Dict[str, Any]:
    """Caso especial para Q64: renderizar 2 tableros de ajedrez separados."""
    print("\n🔧 Q64: Renderizando 2 tableros de ajedrez separados")

    doc = fitz.open(pdf_path)
    page = doc[0]

    # Las dos imágenes son tableros separados por el texto "El rey puede moverse..."
    # Estructura del PDF:
    # - Enunciado inicial: y~10-223 ("En el siguiente tablero...")
    # - PRIMER TABLERO (rey en e2): debe estar después del enunciado inicial pero antes del texto intermedio
    #   Basado en la imagen adjunta, es un tablero completo de 8x8. Los dibujos empiezan en y~265.
    #   El tablero completo probablemente está en y~265-350 (antes del texto intermedio que termina en y~278)
    # - Texto intermedio: y~223-278 ("El rey puede moverse...")
    # - SEGUNDO TABLERO: dibujos en y~535-607 (después del texto intermedio, antes de alternativas)
    # - Alternativas: y~533+ ("A)...", "B)...", etc.)

    # Ajustar para capturar correctamente cada tablero
    # Estructura del PDF:
    # - Enunciado inicial: y~10-223 ("En el siguiente tablero...")
    # - PRIMER TABLERO (rey en e2): debe estar entre y~223-278 (después del enunciado, antes del texto intermedio)
    # - Texto intermedio: y~223-278 ("El rey puede moverse...")
    # - SEGUNDO TABLERO (ejemplo): debe estar entre y~278-520 (después del texto intermedio, antes de la pregunta y alternativas)
    # - Pregunta y alternativas: y~533+

    # Ajustar basándose en feedback:
    # - Primera imagen actualmente captura el segundo tablero -> primer tablero está MÁS ARRIBA
    # - Segunda imagen actualmente captura alternativas -> segundo tablero está más arriba también

    # Primer tablero (rey en e2): debe estar más arriba, probablemente integrado en el enunciado inicial
    # El enunciado inicial es y~10-223, el tablero podría estar dentro de esta área o justo después
    # Falta un poquito por arriba, empezar más arriba aún (reducir y0 más)
    bbox1 = [10, 30.0, 600, 220.0]  # Primer tablero (rey en e2) - empezar más arriba para capturar todo
    # Segundo tablero: expandir un poco más hacia abajo para que no se corte
    # El texto intermedio termina en y~278, y las alternativas empiezan en y~533
    # Necesitamos un poco más abajo que 460, hasta y~470 aproximadamente
    bbox2 = [10, 280.0, 600, 470.0]  # Segundo tablero (ejemplo) - un poco más abajo

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
                print(f"   ✅ Imagen {i+1} subida: {s3_url}")

    doc.close()

    if len(body_images) != 2:
        return {"success": False, "error": f"Error al procesar imágenes: {len(body_images)}/2"}

    # Actualizar XML
    xml_file = question_dir / "question.xml"
    with open(xml_file, "r", encoding="utf-8") as f:
        xml_content = f.read()

    # Reemplazar las dos imágenes existentes con las nuevas
    # Buscar todas las imágenes Q64 en el XML
    img_pattern = r'<p><img src="[^"]*Q64[^"]*\.png"[^>]*/>\s*</p>?'
    matches = list(re.finditer(img_pattern, xml_content))

    if len(matches) >= 2:
        # Reemplazar en orden inverso para mantener los índices correctos
        # Primero reemplazar la segunda (más abajo)
        xml_content = (
            xml_content[:matches[1].start()] +
            f'<p><img src="{body_images[1]}" alt="Segundo tablero de ajedrez con ejemplo de movimiento"/></p>' +
            xml_content[matches[1].end():]
        )
        # Luego reemplazar la primera (más arriba)
        matches = list(re.finditer(img_pattern, xml_content))
        if matches:
            xml_content = (
                xml_content[:matches[0].start()] +
                f'<p><img src="{body_images[0]}" alt="Primer tablero de ajedrez con rey en e2"/></p>' +
                xml_content[matches[0].end():]
            )

    # Asegurar que las imágenes estén separadas por el texto intermedio
    # La estructura correcta debe ser:
    # 1. Párrafo inicial: "En el siguiente tablero..."
    # 2. PRIMERA IMAGEN (primer tablero)
    # 3. Texto intermedio: "El rey puede moverse..."
    # 4. SEGUNDA IMAGEN (segundo tablero)
    # 5. Pregunta y alternativas

    # Buscar el párrafo del texto intermedio
    texto_intermedio_pattern = r'(<p>El rey puede moverse[^<]*</p>)'
    texto_match = re.search(texto_intermedio_pattern, xml_content)

    if texto_match:
        # Separar: primera imagen ANTES del texto, segunda imagen DESPUÉS del texto
        primera_img_tag = f'<p><img src="{body_images[0]}" alt="Primer tablero de ajedrez con rey en e2"/></p>'
        segunda_img_tag = f'<p><img src="{body_images[1]}" alt="Segundo tablero de ajedrez con ejemplo de movimiento"/></p>'

        # Reemplazar todas las imágenes Q64 con estructura correcta
        # Primero, eliminar las imágenes existentes
        xml_content = re.sub(r'<p><img src="[^"]*Q64[^"]*\.png"[^>]*/>\s*</p>', '', xml_content)

        # Insertar primera imagen después del primer párrafo
        primer_parrafo_pattern = r'(<p>En el siguiente tablero[^<]*</p>\s*)'
        replacement1 = rf'\1{primera_img_tag}\n    '
        xml_content = re.sub(primer_parrafo_pattern, replacement1, xml_content)

        # Insertar segunda imagen después del texto intermedio
        replacement2 = rf'\1{segunda_img_tag}\n    '
        xml_content = re.sub(texto_intermedio_pattern, replacement2, xml_content)
    else:
        # Si no encontramos el texto intermedio, usar el método anterior
        img_pattern = r'<p><img src="[^"]*Q64[^"]*\.png"[^>]*/>\s*</p>?'
        matches = list(re.finditer(img_pattern, xml_content))

        if len(matches) >= 2:
            # Reemplazar en orden inverso para mantener los índices correctos
            xml_content = (
                xml_content[:matches[1].start()] +
                f'<p><img src="{body_images[1]}" alt="Segundo tablero de ajedrez con ejemplo de movimiento"/></p>' +
                xml_content[matches[1].end():]
            )
            matches = list(re.finditer(img_pattern, xml_content))
            if matches:
                xml_content = (
                    xml_content[:matches[0].start()] +
                    f'<p><img src="{body_images[0]}" alt="Primer tablero de ajedrez con rey en e2"/></p>' +
                    xml_content[matches[0].end():]
                )

    with open(xml_file, "w", encoding="utf-8") as f:
        f.write(xml_content)

    print("✅ Q64 corregida: 2 imágenes separadas por texto intermedio")
    return {"success": True}


def fix_image_for_question(
    question_id: str,
    question_dir: Path,
    pdf_path: Path,
    test_name: str = "seleccion-regular-2025",
) -> Dict[str, Any]:
    """
    Corrige la imagen de una pregunta re-renderizándola con bbox ajustado.
    
    Args:
        question_id: ID de la pregunta (ej: "Q2")
        question_dir: Directorio de la pregunta
        pdf_path: Ruta al PDF original
        test_name: Nombre del test para S3
        
    Returns:
        Resultado de la corrección
    """
    print(f"\n{'='*60}")
    print(f"🔧 Corrigiendo imagen para {question_id}")
    print(f"{'='*60}")

    # Caso especial para Q64: necesita 2 imágenes separadas en el body
    if question_id == "Q64":
        return fix_q64_special(question_dir, pdf_path, test_name)

    processed_file = question_dir / "processed_content.json"
    if not processed_file.exists():
        return {
            "success": False,
            "error": "processed_content.json no encontrado"
        }

    if not pdf_path.exists():
        return {
            "success": False,
            "error": f"PDF no encontrado: {pdf_path}"
        }

    # Cargar processed_content
    with open(processed_file, "r", encoding="utf-8") as f:
        processed_data = json.load(f)

    # Obtener páginas primero
    pages = processed_data.get("pages", [])
    if not pages:
        return {
            "success": False,
            "error": "No hay páginas en processed_content"
        }

    all_images = processed_data.get("all_images", [])
    if not all_images:
        return {
            "success": False,
            "error": "No hay imágenes en processed_content"
        }

    # Para preguntas con múltiples imágenes, identificar cuáles son imágenes de opciones
    # Primero verificar en el XML si las opciones realmente tienen imágenes
    xml_file = question_dir / "question.xml"
    options_have_images = False
    if xml_file.exists():
        with open(xml_file, "r", encoding="utf-8") as f:
            xml_content_check = f.read()
        # Verificar si hay imágenes dentro de qti-simple-choice
        if re.search(r'<qti-simple-choice[^>]*>.*?<img', xml_content_check, re.DOTALL):
            options_have_images = True

    # Solo buscar opciones en el texto si las opciones tienen imágenes en el XML
    option_labels = []
    if pages and options_have_images:
        blocks = pages[0].get("structured_text", {}).get("blocks", [])
        text_blocks = [b for b in blocks if b.get("type") == 0]
        for b in text_blocks:
            text = ""
            if b.get("lines"):
                spans = b["lines"][0].get("spans", [])
                if spans:
                    text = spans[0].get("text", "")
            if text.strip() in ["A)", "B)", "C)", "D)"]:
                option_labels.append((text.strip(), b.get("bbox", [])))

    # Si hay opciones con imágenes, preferir imágenes que estén cerca de las opciones
    images_to_process = []
    if option_labels and len(all_images) > 1 and options_have_images:
        # Calcular qué imágenes están cerca de las opciones
        for img_info in all_images:
            img_bbox = img_info.get("original_bbox") or img_info.get("bbox", [])
            if len(img_bbox) == 4:
                img_center_y = (img_bbox[1] + img_bbox[3]) / 2
                # Verificar si está cerca de alguna opción
                near_option = False
                for label, opt_bbox in option_labels:
                    if len(opt_bbox) == 4:
                        opt_center_y = (opt_bbox[1] + opt_bbox[3]) / 2
                        if abs(img_center_y - opt_center_y) < 100:
                            near_option = True
                            break
                if near_option:
                    images_to_process.append(img_info)

        # Si encontramos imágenes cerca de opciones, usar esas; si no, usar todas
        if images_to_process:
            print(f"📋 Encontradas {len(images_to_process)} imágenes cerca de opciones")
        else:
            images_to_process = all_images
            print(f"📋 Procesando todas las {len(all_images)} imágenes")
    else:
        # Si no hay opciones o solo hay una imagen, usar la primera
        images_to_process = [all_images[0]]
        print("📋 Procesando 1 imagen principal")

    # Usar la primera imagen de las seleccionadas
    image_info = images_to_process[0]

    # Preferir original_bbox si existe (bbox detectado inicialmente antes de expansiones)
    original_bbox = image_info.get("original_bbox") or image_info.get("bbox", [])
    current_bbox = image_info.get("bbox", [])

    if len(original_bbox) != 4:
        original_bbox = current_bbox
    if len(original_bbox) != 4:
        return {
            "success": False,
            "error": f"Bbox inválido: {original_bbox}"
        }

    print(f"📋 Bbox detectado original: {original_bbox}")
    if original_bbox != current_bbox:
        print(f"📋 Bbox actual (expandido): {current_bbox}")

    # Usar original_bbox como base para trabajar
    working_bbox = original_bbox.copy()

    # Obtener bloques de texto de la primera página (pages ya fue obtenido arriba)
    page_data = pages[0]
    blocks = page_data.get("structured_text", {}).get("blocks", [])
    text_blocks = [b for b in blocks if b.get("type") == 0]

    # Buscar bloques de imagen PyMuPDF (tipo 1) que pueden ser más precisos
    pymupdf_image_blocks = [b for b in blocks if b.get("type") == 1 and b.get("bbox")]
    using_pymupdf = False

    # Si hay bloques PyMuPDF, preferirlos si son más pequeños/precisos que el working_bbox
    if pymupdf_image_blocks:
        # Usar el bloque de imagen más grande (probablemente el principal)
        best_pymupdf = max(pymupdf_image_blocks, key=lambda b: (b["bbox"][2] - b["bbox"][0]) * (b["bbox"][3] - b["bbox"][1]))
        pymupdf_bbox = best_pymupdf["bbox"]

        # Verificar que este bbox es razonable (no es todo el ancho de la página como texto)
        page_width = page_data.get("structured_text", {}).get("width", 600)
        img_width = pymupdf_bbox[2] - pymupdf_bbox[0]
        img_height = pymupdf_bbox[3] - pymupdf_bbox[1]

        # Si el ancho del PyMuPDF es menor que 90% del ancho de página, probablemente es correcto
        if img_width < page_width * 0.9 and img_height > 20:
            print(f"📸 Usando bbox PyMuPDF más preciso: {[round(x, 1) for x in pymupdf_bbox]}")
            working_bbox = pymupdf_bbox
            original_bbox = pymupdf_bbox  # Actualizar también original_bbox
            using_pymupdf = True

    # Encontrar bloques de texto dentro de la imagen
    overlapping_blocks = find_question_text_blocks_in_image(working_bbox, text_blocks)

    print(f"📝 Bloques de texto encontrados en/sobre imagen: {len(overlapping_blocks)}")

    # Encontrar dónde termina realmente la pregunta (bloques antes de la imagen)
    img_top = working_bbox[1]
    blocks_before_image = [
        b for b in text_blocks
        if b.get("bbox") and len(b.get("bbox", [])) == 4
        and b["bbox"][3] < img_top + 10  # Bloques que terminan antes o justo al inicio de la imagen
    ]

    # Obtener ancho de página para contexto
    page_width = page_data.get("structured_text", {}).get("width", 600.0)

    # Para imágenes PyMuPDF, si no hay bloques superpuestos dentro del área visual,
    # usar el bbox exacto sin ajustes
    adjusted_bbox = working_bbox.copy()
    was_adjusted = False

    # Solo ajustar si hay bloques de texto superpuestos dentro del área de la imagen
    if using_pymupdf and not overlapping_blocks:
        # Usar el bbox PyMuPDF exacto sin ajustes
        print(f"   ✅ Usando bbox PyMuPDF exacto (sin texto superpuesto): {[round(x, 1) for x in working_bbox]}")
    else:
        # Ajustar bbox para excluir texto
        adjusted_bbox, was_adjusted = adjust_image_bbox_to_exclude_text(
            working_bbox, overlapping_blocks, page_width=page_width
        )

    # Si estamos usando PyMuPDF exacto sin texto superpuesto, saltar todos los ajustes adicionales
    skip_additional_adjustments = (using_pymupdf and not overlapping_blocks)

    # Si hay bloques antes de la imagen y no estamos usando PyMuPDF exacto, usar el último como referencia
    if not skip_additional_adjustments and blocks_before_image:
        last_block_before = max(blocks_before_image, key=lambda b: b["bbox"][3])
        last_block_bottom = last_block_before["bbox"][3]

        # Si la imagen empieza muy cerca del último bloque de texto, ajustar
        if img_top - last_block_bottom < 40:  # Hay poco espacio entre texto e imagen
            new_y0 = last_block_bottom + 20  # Margen más generoso
            if new_y0 < working_bbox[3] - 50:  # Verificar que haya suficiente altura
                if not was_adjusted or new_y0 > adjusted_bbox[1]:
                    adjusted_bbox = working_bbox.copy()
                    adjusted_bbox[1] = new_y0
                    was_adjusted = True
                    print(f"   🔧 Ajuste basado en bloques anteriores: y0 {working_bbox[1]:.1f} → {new_y0:.1f}")

    # Para imágenes que tienen muchos bloques dentro (como Q47), excluir todos agresivamente
    if not skip_additional_adjustments and overlapping_blocks and len(overlapping_blocks) > 5:
        # Encontrar el bloque más bajo dentro de la imagen
        max_bottom = max(block["bottom"] for block in overlapping_blocks)
        # También considerar bloques que empiezan dentro
        blocks_starting_inside = [b for b in overlapping_blocks if b.get("top", b["bottom"]) >= img_top - 10]
        if blocks_starting_inside:
            max_bottom = max(block["bottom"] for block in blocks_starting_inside)

        new_y0 = max_bottom + 25  # Margen generoso
        if new_y0 < working_bbox[3] - 80:  # Necesitamos suficiente altura
            if not was_adjusted or new_y0 > adjusted_bbox[1]:
                adjusted_bbox = working_bbox.copy()
                adjusted_bbox[1] = new_y0
                was_adjusted = True
                print(f"   🔧 Ajuste agresivo para múltiples bloques: y0 {working_bbox[1]:.1f} → {new_y0:.1f} (excluyendo {len(overlapping_blocks)} bloques)")

    if not skip_additional_adjustments and not was_adjusted and overlapping_blocks:
        print("   ⚠️  No se pudo ajustar con bloques superpuestos, intentando enfoque alternativo")
        # Intentar otro enfoque: buscar el último bloque antes/sobre la imagen
        img_top = working_bbox[1]

        # Buscar bloques que terminan cerca del inicio de la imagen
        blocks_near_img = []
        for block in text_blocks:
            if block.get("type") != 0:
                continue
            block_bbox = block.get("bbox", [])
            if len(block_bbox) != 4:
                continue

            block_bottom = block_bbox[3]

            # Si el bloque termina cerca del inicio de la imagen
            if block_bottom >= img_top - 30 and block_bottom <= img_top + 50:
                blocks_near_img.append({
                    "block": block,
                    "bottom": block_bottom,
                })

        if blocks_near_img:
            # Usar el bloque más bajo
            last_block = max(blocks_near_img, key=lambda b: b["bottom"])
            last_bottom = last_block["bottom"]

            # Asegurar que la imagen empiece después del texto
            new_y0 = last_bottom + 25  # Margen generoso

            if new_y0 < working_bbox[3] - 50:  # Asegurar altura mínima
                adjusted_bbox = working_bbox.copy()
                adjusted_bbox[1] = new_y0
                was_adjusted = True
                print(f"   🔧 Ajuste alternativo: y0 {working_bbox[1]:.1f} → {new_y0:.1f}")

        # Si aún no se ajustó y la imagen empieza muy arriba (y < 50), buscar bloques de pregunta más agresivamente
        if not was_adjusted and img_top < 50:
            # Buscar cualquier bloque de texto que esté cerca del inicio de la imagen
            blocks_at_start = []
            for block in text_blocks:
                if block.get("type") != 0:
                    continue
                block_bbox = block.get("bbox", [])
                if len(block_bbox) != 4:
                    continue

                block_top = block_bbox[1]
                block_bottom = block_bbox[3]

                # Si el bloque está cerca del inicio de la imagen
                if block_bottom <= img_top + 50 and block_top < img_top + 80:
                    blocks_at_start.append({
                        "block": block,
                        "bottom": block_bottom,
                    })

            if blocks_at_start:
                last_block = max(blocks_at_start, key=lambda b: b["bottom"])
                new_y0 = last_block["bottom"] + 30  # Margen muy generoso para imágenes superiores

                if new_y0 < working_bbox[3] - 50 and new_y0 > img_top:
                    adjusted_bbox = working_bbox.copy()
                    adjusted_bbox[1] = new_y0
                    was_adjusted = True
                    print(f"   🔧 Ajuste para imagen superior: y0 {working_bbox[1]:.1f} → {new_y0:.1f}")

    # Esta sección ya fue procesada arriba, saltarla si estamos usando PyMuPDF exacto
    if not skip_additional_adjustments and using_pymupdf and pymupdf_image_blocks:
        img_top = working_bbox[1]
        img_bottom = working_bbox[3]
        needs_adjustment = False
        new_top = img_top
        new_bottom = img_bottom

        # Buscar bloques que se superponen significativamente con la imagen
        overlapping_large = [
            b for b in text_blocks
            if b.get("bbox") and len(b.get("bbox", [])) == 4
            and b["bbox"][1] < img_bottom and b["bbox"][3] > img_top
            and (b["bbox"][3] - b["bbox"][1]) > 50  # Bloques grandes que se superponen
            and (b["bbox"][2] - b["bbox"][0]) > 100  # Y anchos (probablemente texto de pregunta, no etiquetas)
        ]

        # Si NO hay bloques grandes superpuestos, usar el bbox PyMuPDF exacto
        if not overlapping_large:
            use_exact_pymupdf = True
            adjusted_bbox = working_bbox.copy()
            was_adjusted = False  # No ajustar, usar exacto
            print(f"   ✅ Usando bbox PyMuPDF exacto sin ajustes: {[round(x, 1) for x in working_bbox]}")

        # Si hay bloques grandes superpuestos, excluirlos completamente
        elif overlapping_large:
            # Para bloques grandes superpuestos, encontrar dónde terminan realmente
            # Encontrar el bloque superpuesto más grande (probablemente es el texto de pregunta)
            largest_overlap = max(overlapping_large, key=lambda b: (b["bbox"][3] - b["bbox"][1]))

            # Si el bloque grande empieza antes de la imagen, ajustar el inicio
            if largest_overlap["bbox"][1] < img_top:
                # Para bloques grandes que contienen la imagen, ser más conservador
                # Buscar el último bloque que termina ANTES del área de imagen PyMuPDF
                blocks_before_img = [
                    b for b in text_blocks
                    if b.get("bbox") and len(b.get("bbox", [])) == 4
                    and b["bbox"][3] < img_top  # Terminan antes de la imagen
                ]
                if blocks_before_img:
                    last_before = max(blocks_before_img, key=lambda b: b["bbox"][3])
                    # Asegurar que empezamos después del texto, pero no demasiado lejos del inicio PyMuPDF
                    suggested_top = last_before["bbox"][3] + 15  # Margen generoso
                    # No ajustar si esto nos aleja demasiado del bbox original PyMuPDF
                    if suggested_top <= img_top + 40:  # Permitir ajuste razonable
                        new_top = suggested_top
                        needs_adjustment = True
                        print(f"   🔧 Ajuste SUPERIOR: y0 {img_top:.1f} → {new_top:.1f} (después del último texto en y={last_before['bbox'][3]:.1f})")
                else:
                    # Si no hay bloque antes, usar el inicio del bloque grande + margen generoso
                    new_top = largest_overlap["bbox"][1] + 25
                    if new_top <= img_top + 40:
                        needs_adjustment = True
                        print(f"   🔧 Ajuste SUPERIOR: y0 {img_top:.1f} → {new_top:.1f} (margen del bloque grande)")

            # Si el bloque grande termina después de la imagen, ajustar el final
            if largest_overlap["bbox"][3] > img_bottom:
                # Buscar dónde empiezan las opciones (bloques después de la imagen)
                blocks_after_large = [
                    b for b in text_blocks
                    if b.get("bbox") and len(b.get("bbox", [])) == 4
                    and b["bbox"][1] > largest_overlap["bbox"][3] - 20
                ]
                if blocks_after_large:
                    first_option = min(blocks_after_large, key=lambda b: b["bbox"][1])
                    # Terminar la imagen antes de que empiecen las opciones
                    new_bottom = first_option["bbox"][1] - 10
                    needs_adjustment = True
                    print(f"   🔧 Ajuste INFERIOR: y1 {img_bottom:.1f} → {new_bottom:.1f} (antes de opciones que empiezan en {first_option['bbox'][1]:.1f})")
                else:
                    # Si no hay opciones claras, terminar un poco antes del final del bloque grande
                    new_bottom = largest_overlap["bbox"][3] - 20  # Margen más generoso
                    needs_adjustment = True
                    print(f"   🔧 Ajuste INFERIOR: y1 {img_bottom:.1f} → {new_bottom:.1f} (excluyendo bloque grande que termina en {largest_overlap['bbox'][3]:.1f})")
            else:
                # Buscar el primer bloque que empieza DESPUÉS del bloque grande
                blocks_after = [
                    b for b in text_blocks
                    if b.get("bbox") and len(b.get("bbox", [])) == 4
                    and b["bbox"][1] > largest_overlap["bbox"][3] - 10
                ]
                if blocks_after:
                    first_after = min(blocks_after, key=lambda b: b["bbox"][1])
                    new_bottom = first_after["bbox"][1] - 8  # Margen pequeño
                    needs_adjustment = True
                    print(f"   🔧 Ajuste INFERIOR: y1 {img_bottom:.1f} → {new_bottom:.1f}")
        else:
            # Si no hay bloques grandes superpuestos, solo ajustar por bloques cercanos
            # Buscar bloques que empiezan cerca del final (abajo)
            blocks_below_image = [
                b for b in text_blocks
                if b.get("bbox") and len(b.get("bbox", [])) == 4
                and b["bbox"][1] >= img_bottom - 15
                and b["bbox"][1] <= img_bottom + 50
            ]

            if blocks_below_image:
                first_below = min(blocks_below_image, key=lambda b: b["bbox"][1])
                new_bottom = first_below["bbox"][1] - 8
                needs_adjustment = True
                print(f"   🔧 Ajuste INFERIOR (cercano): y1 {img_bottom:.1f} → {new_bottom:.1f}")

        if needs_adjustment and new_bottom > new_top + 30:  # Asegurar altura mínima
            adjusted_bbox = working_bbox.copy()
            adjusted_bbox[1] = new_top
            adjusted_bbox[3] = new_bottom
            was_adjusted = True

    # Re-renderizar desde PDF
    print(f"📄 Cargando PDF: {pdf_path.name}")
    doc = fitz.open(str(pdf_path))

    try:
        page = doc.load_page(0)  # Primera página

        # Si hay múltiples imágenes de opciones, generar imágenes separadas para cada alternativa
        option_images = []  # Lista para almacenar las imágenes de cada opción
        # Para Q42, las imágenes detectadas pueden contener múltiples gráficos
        # Usar las imágenes detectadas y dividirlas verticalmente si es necesario
        if len(images_to_process) >= 2 and option_labels:
            print("   📊 Múltiples imágenes de opciones detectadas, generando imágenes separadas...")
            drawings = page.get_drawings()
            if drawings:
                # Agrupar dibujos por área vertical (clusters)
                drawing_clusters = {}
                for d in drawings:
                    rect = d.get("rect", fitz.Rect())
                    if rect and not rect.is_empty:
                        cluster_y = int(rect.y0 / 50) * 50
                        if cluster_y not in drawing_clusters:
                            drawing_clusters[cluster_y] = []
                        drawing_clusters[cluster_y].append(rect)

                # Crear diccionario de opciones con sus posiciones
                option_positions = {}
                for label, opt_bbox in option_labels:
                    if len(opt_bbox) == 4:
                        option_positions[label] = {
                            "y": (opt_bbox[1] + opt_bbox[3]) / 2,
                            "bbox": opt_bbox
                        }

                # Si no encontramos todas las opciones, buscar por orden (A, B, C, D)
                expected_options = ["A)", "B)", "C)", "D)"]
                if len(option_positions) < 4:
                    # Buscar bloques de texto que puedan ser opciones
                    for b in text_blocks:
                        text = ""
                        if b.get("lines"):
                            spans = b["lines"][0].get("spans", [])
                            if spans:
                                text = spans[0].get("text", "").strip()

                        # Buscar patrones como "A", "B", "C", "D" solos o seguidos de punto/parentesis
                        if text in ["A", "B", "C", "D"] or text in expected_options:
                            label = text if text in expected_options else f"{text})"
                            if label not in option_positions:
                                bbox = b.get("bbox", [])
                                if len(bbox) == 4:
                                    option_positions[label] = {
                                        "y": (bbox[1] + bbox[3]) / 2,
                                        "bbox": bbox
                                    }

                # Si aún no tenemos 4 opciones, inferirlas basándose en posición vertical
                if len(option_positions) >= 2:
                    sorted_options = sorted(option_positions.items(), key=lambda x: x[1]["y"])
                    # Si tenemos A y C, inferir B y D entre ellas
                    if len(option_positions) == 2:
                        first_label = sorted_options[0][0]
                        second_label = sorted_options[1][0]
                        first_y = sorted_options[0][1]["y"]
                        second_y = sorted_options[1][1]["y"]

                        # Calcular posiciones intermedias
                        step = (second_y - first_y) / 3
                        if first_label == "A)":
                            if second_label == "C)":
                                option_positions["B)"] = {"y": first_y + step, "bbox": [0, first_y + step - 10, 600, first_y + step + 10]}
                                option_positions["D)"] = {"y": first_y + 2*step, "bbox": [0, first_y + 2*step - 10, 600, first_y + 2*step + 10]}

                # Encontrar clusters que están cerca de las opciones
                cluster_list = []
                for cluster_y, cluster_rects in sorted(drawing_clusters.items()):
                    min_x = min(r.x0 for r in cluster_rects)
                    max_x = max(r.x1 for r in cluster_rects)
                    min_y = min(r.y0 for r in cluster_rects)
                    max_y = max(r.y1 for r in cluster_rects)
                    cluster_center_y = (min_y + max_y) / 2

                    # Encontrar la opción más cercana
                    closest_option = None
                    min_distance = float('inf')
                    for label, opt_info in option_positions.items():
                        distance = abs(cluster_center_y - opt_info["y"])
                        if distance < min_distance:
                            min_distance = distance
                            closest_option = label

                    # Solo incluir clusters que están razonablemente cerca de una opción
                    if min_distance < 150:  # Máximo 150px de distancia
                        cluster_list.append({
                            "label": closest_option,
                            "bbox": [min_x, min_y, max_x, max_y],
                            "center_y": cluster_center_y,
                            "distance": min_distance
                        })

                # Asignar cada cluster a una opción única (el más cercano a cada opción)
                option_clusters = []
                assigned_options = set()

                # Ordenar clusters por distancia a su opción más cercana
                cluster_list.sort(key=lambda c: c["distance"])

                for cluster in cluster_list:
                    if cluster["label"] not in assigned_options:
                        assigned_options.add(cluster["label"])
                        option_clusters.append(cluster)

                # Si tenemos 4 clusters, usarlos; si no, dividir las imágenes detectadas
                # Procesar clusters si hay 4, sino dividir las imágenes detectadas
                use_clusters = option_clusters and len(option_clusters) >= 4

                if use_clusters:
                    # Ordenar por posición vertical
                    option_clusters.sort(key=lambda c: c["center_y"])
                    print(f"   ✅ Encontrados {len(option_clusters)} clusters de gráficos de opciones")

                    # Procesar cada cluster por separado
                    margin_x = 12
                    margin_y = 15

                    for cluster in option_clusters:
                        label = cluster["label"]
                        cluster_bbox = cluster["bbox"]

                        # Crear bbox con margen para este cluster
                        cluster_bbox_with_margin = [
                            max(0, cluster_bbox[0] - margin_x),
                            max(0, cluster_bbox[1] - margin_y),
                            cluster_bbox[2] + margin_x,
                            cluster_bbox[3] + margin_y
                        ]

                        print(f"   🎨 Renderizando gráfico para opción {label}: {[round(x, 1) for x in cluster_bbox_with_margin]}")

                        # Renderizar esta imagen
                        rendered_cluster = render_image_area(
                            page=page,
                            final_bbox=cluster_bbox_with_margin,
                            original_bbox=cluster_bbox_with_margin,
                            idx=len(option_images),
                            mask_areas=None,
                        )

                        if rendered_cluster:
                            # Subir a S3 con nombre específico de la opción
                            image_base64 = rendered_cluster.get("image_base64", "")
                            if not image_base64.startswith("data:"):
                                image_base64 = f"data:image/png;base64,{image_base64}"

                            s3_url = upload_image_to_s3(
                                image_base64=image_base64,
                                question_id=f"{question_id}_choice_{label.replace(')', '')}",
                                test_name=test_name,
                            )

                            if s3_url:
                                option_images.append({
                                    "label": label,
                                    "s3_url": s3_url,
                                    "bbox": cluster_bbox_with_margin
                                })
                                print(f"   ✅ Imagen para {label} subida: {s3_url}")

                    has_option_images = len(option_images) >= 4
                else:
                    # Si no hay suficientes clusters (4), usar drawings para encontrar las 4 áreas exactas
                    print(f"   ⚠️  Encontrados {len(option_clusters) if option_clusters else 0} clusters, buscando las 4 áreas usando drawings...")

                    # Usar drawings para encontrar el área total y dividir en 2x2
                    drawings_all = page.get_drawings()
                    if drawings_all:
                        # Encontrar todos los rectángulos de dibujos válidos
                        all_drawing_rects = []
                        for d in drawings_all:
                            rect = d.get("rect", fitz.Rect())
                            if rect and not rect.is_empty and (rect.width > 20 or rect.height > 20):
                                all_drawing_rects.append(rect)

                        if all_drawing_rects:
                            # Encontrar los límites totales
                            min_x = min(r.x0 for r in all_drawing_rects)
                            max_x = max(r.x1 for r in all_drawing_rects)
                            min_y = min(r.y0 for r in all_drawing_rects)
                            max_y = max(r.y1 for r in all_drawing_rects)

                            # Dividir en 2x2 (cuadrícula)
                            center_x = (min_x + max_x) / 2
                            center_y = (min_y + max_y) / 2

                            margin = 12

                            # Crear bboxes para cada cuadrante
                            # Arriba-izq: A, Arriba-der: B, Abajo-izq: C, Abajo-der: D
                            quadrants = {
                                "A)": [min_x - margin, min_y - margin, center_x + margin/2, center_y + margin/2],
                                "B)": [center_x - margin/2, min_y - margin, max_x + margin, center_y + margin/2],
                                "C)": [min_x - margin, center_y - margin/2, center_x + margin/2, max_y + margin],
                                "D)": [center_x - margin/2, center_y - margin/2, max_x + margin, max_y + margin]
                            }

                            print(f"   📐 Área total: x={min_x:.1f}-{max_x:.1f}, y={min_y:.1f}-{max_y:.1f}")
                            print(f"   📐 Centro: x={center_x:.1f}, y={center_y:.1f}")

                            for label, quadrant_bbox in quadrants.items():
                                print(f"   🎨 Renderizando gráfico para opción {label}: {[round(x, 1) for x in quadrant_bbox]}")

                                rendered_quad = render_image_area(
                                    page=page,
                                    final_bbox=quadrant_bbox,
                                    original_bbox=quadrant_bbox,
                                    idx=len(option_images),
                                    mask_areas=None,
                                )

                                if rendered_quad:
                                    image_base64 = rendered_quad.get("image_base64", "")
                                    if not image_base64.startswith("data:"):
                                        image_base64 = f"data:image/png;base64,{image_base64}"

                                    s3_url = upload_image_to_s3(
                                        image_base64=image_base64,
                                        question_id=f"{question_id}_choice_{label.replace(')', '')}",
                                        test_name=test_name,
                                    )

                                    if s3_url:
                                        option_images.append({
                                            "label": label,
                                            "s3_url": s3_url,
                                            "bbox": quadrant_bbox
                                        })
                                        print(f"   ✅ Imagen para {label} subida: {s3_url}")

                            has_option_images = len(option_images) >= 4
                        else:
                            has_option_images = False
                    else:
                        has_option_images = False
            else:
                has_option_images = False
        else:
            has_option_images = False

        # Para imágenes detectadas por AI sin PyMuPDF, verificar si el bbox está capturando área vacía
        # Buscar dibujos/paths en el PDF para encontrar el contenido visual real
        if not using_pymupdf and not pymupdf_image_blocks and not was_adjusted:
            drawings = page.get_drawings()
            if drawings:
                # Encontrar el rango vertical de los dibujos
                drawing_ys = []
                drawing_xs = []
                for d in drawings:
                    rect = d.get("rect", fitz.Rect())
                    if rect and not rect.is_empty:
                        drawing_ys.append((rect.y0, rect.y1))
                        drawing_xs.append((rect.x0, rect.x1))

                if drawing_ys:
                    min_y = min(y[0] for y in drawing_ys)
                    max_y = max(y[1] for y in drawing_ys)
                    min_x = min(x[0] for x in drawing_xs) if drawing_xs else working_bbox[0]
                    max_x = max(x[1] for x in drawing_xs) if drawing_xs else working_bbox[2]

                    # Si los dibujos están muy lejos del bbox detectado, usar el bbox de los dibujos
                    current_y_center = (working_bbox[1] + working_bbox[3]) / 2
                    drawing_y_center = (min_y + max_y) / 2

                    if abs(current_y_center - drawing_y_center) > 100:  # Más de 100px de diferencia
                        print(f"   🔍 Dibujos encontrados en y={min_y:.1f}-{max_y:.1f}, bbox detectado está lejos")
                        print("   🔧 Usando bbox de dibujos en vez del detectado")
                        # Crear nuevo bbox basado en los dibujos con margen sutil
                        margin_x = 12  # Margen horizontal sutil
                        margin_y = 15  # Margen vertical sutil
                        adjusted_bbox = [
                            max(0, min_x - margin_x),
                            max(0, min_y - margin_y),
                            max_x + margin_x,
                            max_y + margin_y
                        ]
                        was_adjusted = True
                        print(f"   📏 Ajustado con margen sutil: {[round(x, 1) for x in adjusted_bbox]}")

        # Usar bbox ajustado o working_bbox (que es el original detectado)
        final_bbox = adjusted_bbox if was_adjusted else working_bbox

        print(f"🎨 Re-renderizando imagen con bbox: {final_bbox}")

        # Re-renderizar usando la función existente
        # Usar original_bbox como referencia (bbox detectado inicialmente)
        rendered_image = render_image_area(
            page=page,
            final_bbox=final_bbox,
            original_bbox=original_bbox,  # Bbox original detectado como referencia
            idx=0,
            mask_areas=None,  # Sin masking por ahora
        )

        if not rendered_image:
            return {
                "success": False,
                "error": "Error al renderizar imagen"
            }

        # Subir a S3
        image_base64 = rendered_image.get("image_base64", "")
        if not image_base64:
            return {
                "success": False,
                "error": "Imagen renderizada no tiene base64"
            }

        # Asegurar formato data URI
        if not image_base64.startswith("data:"):
            image_base64 = f"data:image/png;base64,{image_base64}"

        print("📤 Subiendo imagen corregida a S3...")
        s3_url = upload_image_to_s3(
            image_base64=image_base64,
            question_id=f"{question_id}_fixed",
            test_name=test_name,
        )

        if not s3_url:
            return {
                "success": False,
                "error": "Error al subir imagen a S3"
            }

        print(f"✅ Imagen subida: {s3_url}")

        # Actualizar XML
        xml_file = question_dir / "question.xml"
        if not xml_file.exists():
            return {
                "success": False,
                "error": "question.xml no encontrado"
            }

        with open(xml_file, "r", encoding="utf-8") as f:
            xml_content = f.read()

        # Si tenemos imágenes de opciones separadas, actualizar el XML para poner cada una en su alternativa
        if option_images and len(option_images) > 0:
            print(f"   📝 Actualizando XML con {len(option_images)} imágenes de opciones...")

            # Backup del XML original
            backup_file = question_dir / "question.xml.backup"
            if not backup_file.exists():
                with open(xml_file, "r", encoding="utf-8") as f:
                    backup_file.write_text(f.read())

            # Crear un diccionario de opciones a URLs
            option_urls = {opt["label"]: opt["s3_url"] for opt in option_images}

            # Buscar cada alternativa en el XML y agregar la imagen si no existe
            # Pattern para encontrar <qti-simple-choice identifier="ChoiceA"> o similar
            choice_pattern = r'<qti-simple-choice[^>]*identifier="(Choice[A-D])"[^>]*>'

            # Reemplazar cada alternativa individualmente con su imagen correspondiente
            for choice_id in ["ChoiceA", "ChoiceB", "ChoiceC", "ChoiceD"]:
                choice_letter = choice_id.replace("Choice", "")
                choice_label = f"{choice_letter})"

                # Buscar esta alternativa específica (patrón más robusto)
                # Buscar desde el inicio del tag hasta el siguiente tag o cierre
                choice_pattern_specific = rf'<qti-simple-choice[^>]*identifier="{choice_id}"[^>]*>.*?</qti-simple-choice>'

                def replace_specific_choice(match):
                    full_match = match.group(0)

                    # Extraer solo el tag de apertura (con atributos)
                    open_match = re.search(rf'(<qti-simple-choice[^>]*identifier="{choice_id}"[^>]*>)', full_match)
                    if not open_match:
                        return full_match

                    open_tag = open_match.group(1)

                    # Limpiar el contenido interno (remover todo lo que esté entre los tags)
                    # Remover imágenes anteriores y texto
                    content_match = re.search(rf'<qti-simple-choice[^>]*identifier="{choice_id}"[^>]*>(.*?)</qti-simple-choice>', full_match, re.DOTALL)
                    if content_match:
                        old_content = content_match.group(1)
                        # Limpiar: remover imágenes y texto de la letra
                        clean_text = re.sub(r'<img[^>]*/>', '', old_content).strip()
                        clean_text = re.sub(rf'^\s*{choice_letter}\s*$', '', clean_text).strip()
                        clean_text = re.sub(rf'^\s*{choice_letter}\s+', '', clean_text).strip()
                    else:
                        clean_text = ""

                    # Obtener URL de la imagen para esta opción
                    img_url = option_urls.get(choice_label, "")
                    if img_url:
                        img_tag = f'<img src="{img_url}" alt="Gráfico opción {choice_letter}"/>'
                        return f'{open_tag}{img_tag}</qti-simple-choice>'
                    else:
                        return f'{open_tag}{clean_text}</qti-simple-choice>'

                xml_content = re.sub(choice_pattern_specific, replace_specific_choice, xml_content, flags=re.DOTALL)

            new_xml = xml_content

            # Remover imágenes del body (ya que ahora están en las opciones)
            if option_images:
                # Buscar y remover todas las imágenes dentro de <p> tags en el body
                body_img_pattern = r'<p>\s*<img[^>]*src="[^"]*({}[^"]*\.png)"[^>]*/>\s*</p>'.format(
                    re.escape(question_id)
                )
                new_xml = re.sub(body_img_pattern, '', new_xml)

                # También limpiar cualquier texto duplicado después de los tags de cierre
                new_xml = re.sub(r'</qti-simple-choice>\s*([A-D])\s*</qti-simple-choice>', r'</qti-simple-choice>', new_xml)

            # Guardar XML actualizado
            with open(xml_file, "w", encoding="utf-8") as f:
                f.write(new_xml)

            print("✅ XML actualizado con imágenes de opciones en cada alternativa")
        else:
            # Caso normal: puede ser una o múltiples imágenes en el body
            # Verificar si hay múltiples imágenes en all_images que no sean de opciones
            if len(all_images) > 1 and not option_labels:
                print(f"   📝 Múltiples imágenes en body detectadas ({len(all_images)}), procesando cada una...")

                # Procesar cada imagen por separado
                body_images = []
                for img_idx, img_info in enumerate(all_images):
                    img_bbox = img_info.get("original_bbox") or img_info.get("bbox", [])

                    # Renderizar esta imagen específica
                    rendered_body_img = render_image_area(
                        page=page,
                        final_bbox=img_bbox,
                        original_bbox=img_bbox,
                        idx=img_idx,
                        mask_areas=None,
                    )

                    if rendered_body_img:
                        image_base64 = rendered_body_img.get("image_base64", "")
                        if not image_base64.startswith("data:"):
                            image_base64 = f"data:image/png;base64,{image_base64}"

                        s3_url_body = upload_image_to_s3(
                            image_base64=image_base64,
                            question_id=f"{question_id}_img{img_idx}",
                            test_name=test_name,
                        )

                        if s3_url_body:
                            body_images.append({
                                "index": img_idx,
                                "s3_url": s3_url_body,
                                "bbox": img_bbox
                            })
                            print(f"   ✅ Imagen {img_idx+1} subida: {s3_url_body}")

                # Actualizar XML con cada imagen en su posición
                if body_images:
                    # Backup del XML original
                    backup_file = question_dir / "question.xml.backup"
                    if not backup_file.exists():
                        with open(xml_file, "r", encoding="utf-8") as f:
                            backup_file.write_text(f.read())

                    # Encontrar todos los tags <img> en el body y reemplazarlos secuencialmente
                    # Buscar imágenes que contengan el question_id en su nombre
                    img_pattern = r'(<img[^>]*src=")([^"]*{}[^"]*\.png)("[^>]*/>)'.format(
                        re.escape(question_id)
                    )

                    img_matches = list(re.finditer(img_pattern, xml_content))
                    # Filtrar solo las imágenes que están fuera de qti-simple-choice (body images)
                    body_img_matches = []
                    for match in img_matches:
                        # Verificar que no esté dentro de un qti-simple-choice
                        start_pos = match.start()
                        # Buscar el tag más cercano antes de esta posición
                        before_text = xml_content[:start_pos]
                        # Si encontramos un qti-simple-choice abierto antes, no es una imagen del body
                        last_choice_start = before_text.rfind('<qti-simple-choice')
                        last_choice_end = before_text.rfind('</qti-simple-choice>')
                        if last_choice_start == -1 or (last_choice_end != -1 and last_choice_end > last_choice_start):
                            # No hay un choice abierto, es una imagen del body
                            body_img_matches.append(match)

                    if len(body_img_matches) == len(body_images):
                        # Reemplazar cada imagen en orden (de atrás hacia adelante para preservar índices)
                        new_xml = xml_content
                        for match_idx in range(len(body_img_matches) - 1, -1, -1):
                            if match_idx < len(body_images):
                                match = body_img_matches[match_idx]
                                replacement = rf'\1{body_images[match_idx]["s3_url"]}\3'
                                new_xml = new_xml[:match.start()] + replacement + new_xml[match.end():]

                        # Guardar XML actualizado
                        with open(xml_file, "w", encoding="utf-8") as f:
                            f.write(new_xml)

                        print(f"✅ XML actualizado con {len(body_images)} imágenes separadas")
                    else:
                        print(f"⚠️  Número de imágenes en XML ({len(img_matches)}) no coincide con imágenes procesadas ({len(body_images)})")
                        # Fallback: reemplazar todas con la primera imagen procesada
                        new_xml = re.sub(img_pattern, rf'\1{body_images[0]["s3_url"]}\3', xml_content)
                        with open(xml_file, "w", encoding="utf-8") as f:
                            f.write(new_xml)
                        print("⚠️  Se actualizó XML con imagen única como fallback")
                else:
                    print("⚠️  No se pudieron generar las imágenes separadas")
            else:
                # Caso normal: solo una imagen
                # Buscar y reemplazar la URL de la imagen
                pattern = r'(<img[^>]*src=")[^"]*({}[^"]*\.png)("[^>]*/>)'.format(
                    re.escape(question_id)
                )

                if re.search(pattern, xml_content):
                    new_xml = re.sub(pattern, rf'\1{s3_url}\3', xml_content)

                    # Backup del XML original
                    backup_file = question_dir / "question.xml.backup"
                    if not backup_file.exists():
                        with open(xml_file, "r", encoding="utf-8") as f:
                            backup_file.write_text(f.read())

                    # Guardar XML actualizado
                    with open(xml_file, "w", encoding="utf-8") as f:
                        f.write(new_xml)

                    print("✅ XML actualizado con nueva URL S3")
                else:
                    print("⚠️  No se encontró patrón de imagen en XML para reemplazar")

        # Actualizar s3_image_mapping.json si existe
        mapping_file = question_dir / "s3_image_mapping.json"
        s3_mapping = {}
        if mapping_file.exists():
            with open(mapping_file, "r", encoding="utf-8") as f:
                s3_mapping = json.load(f)

        # Agregar mapeo de la imagen corregida
        old_key = f"{question_id}_restored_0"
        s3_mapping[f"{question_id}_fixed_0"] = s3_url
        if old_key in s3_mapping:
            s3_mapping[f"{question_id}_restored_0"] = s3_url  # También actualizar el original

        with open(mapping_file, "w", encoding="utf-8") as f:
            json.dump(s3_mapping, f, indent=2)

        return {
            "success": True,
            "s3_url": s3_url,
            "bbox_adjusted": was_adjusted,
            "original_bbox": original_bbox,  # Bbox detectado inicialmente
            "current_bbox": current_bbox,  # Bbox actual (puede estar expandido)
            "adjusted_bbox": adjusted_bbox if was_adjusted else working_bbox,
        }

    finally:
        doc.close()


def main():
    """Función principal."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Corregir imágenes sin usar API"
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
        help="IDs de preguntas específicas a corregir (ej: Q2 Q55)",
    )

    args = parser.parse_args()

    questions_dir = Path(args.questions_dir)
    pdfs_dir = Path(args.pdfs_dir)

    # Preguntas a corregir
    if args.questions:
        question_ids = args.questions
    else:
        # Por defecto, todas las problemáticas
        question_ids = ["Q2", "Q10", "Q32", "Q42", "Q47", "Q53", "Q55", "Q60", "Q62"]

    print("=" * 60)
    print("🔧 CORRECCIÓN DE IMÁGENES (SIN API)")
    print("=" * 60)
    print(f"📋 Preguntas a corregir: {len(question_ids)}")
    print(f"   {', '.join(question_ids)}")
    print("=" * 60)

    results = []
    successful = 0
    failed = 0

    for q_id in question_ids:
        q_dir = questions_dir / q_id
        pdf_path = pdfs_dir / f"{q_id}.pdf"

        if not q_dir.exists():
            print(f"\n❌ {q_id}: Directorio no existe")
            failed += 1
            results.append({"question": q_id, "success": False, "error": "Directorio no existe"})
            continue

        if not pdf_path.exists():
            print(f"\n❌ {q_id}: PDF no encontrado")
            failed += 1
            results.append({"question": q_id, "success": False, "error": "PDF no encontrado"})
            continue

        result = fix_image_for_question(
            question_id=q_id,
            question_dir=q_dir,
            pdf_path=pdf_path,
            test_name=args.test_name,
        )

        if result.get("success"):
            successful += 1
            print(f"✅ {q_id} corregida exitosamente")
        else:
            failed += 1
            error_msg = result.get("error", "Unknown")
            print(f"❌ {q_id} falló: {error_msg}")

        results.append({
            "question": q_id,
            **result
        })

    print(f"\n{'='*60}")
    print("📊 RESUMEN")
    print(f"{'='*60}")
    print(f"✅ Exitosas: {successful}")
    print(f"❌ Fallidas: {failed}")
    print(f"{'='*60}")

    # Guardar resultados
    results_file = questions_dir / "image_fix_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n💾 Resultados guardados en: {results_file}")


if __name__ == "__main__":
    main()
