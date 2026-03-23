"""generate_variant_images.py — Generate actual images for hard variants.

Dual-strategy approach:
  - Route A (chart/graph): LLM extracts data from alt → Matplotlib renders
  - Route B (illustration): LLM expands alt into ultra-detailed prompt → Gemini generates → OpenAI validates

Uses Gemini for image generation and GPT-5.1 vision for validation.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import logging
import re
import sys
from pathlib import Path

from app.image_generation.core import ImageGenerationEngine
from app.llm_clients import load_default_openai_client
from app.question_variants.llm_service import build_reasoning_kwargs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_S3_DOMAIN = "paes-question-images.s3"
_S3_PATH_PREFIX = "images/hard-variants/"
_IMAGE_TEXT_REASONING_LEVEL = "medium"


def _is_placeholder_src(src: str) -> bool:
    """Return True if the image src is a placeholder (not a real S3 URL)."""
    return not src.startswith("http") or _S3_DOMAIN not in src

# ─── Classification prompt ──────────────────────────────────────────

CLASSIFY_PROMPT = """\
Analiza esta descripción de imagen de un examen PAES y clasifícala.

DESCRIPCIÓN:
{alt_text}

Clasifica en UNA de estas categorías:
- "pie_chart" — gráfico circular / de torta
- "bar_chart" — gráfico de barras
- "line_chart" — gráfico de líneas
- "boxplot" — diagrama de cajón
- "dot_plot" — gráfico de puntos
- "scatter_plot" — gráfico de dispersión  
- "cartesian" — plano cartesiano con funciones/figuras geométricas
- "geometric" — figuras geométricas (prismas, cubos, triángulos, etc.)
- "illustration" — ilustración decorativa/contextual (cajas, objetos, escenas)

Responde SOLO con JSON:
{{"category": "...", "data": {{...}}}}

Para gráficos (pie/bar/line/boxplot/dot/scatter):
  "data" debe contener los valores numéricos extraídos, por ejemplo:
  - pie_chart: {{"labels": ["A", "B"], "values": [60, 40]}}
  - bar_chart: {{"labels": [...], "values": [...], "xlabel": "...", "ylabel": "..."}}
  - line_chart: {{"x": [...], "y": [...], "xlabel": "...", "ylabel": "..."}}
  - boxplot: {{"min": N, "q1": N, "median": N, "q3": N, "max": N, "xlabel": "..."}}
  - dot_plot: {{"values": [2,2,3,3,3,...], "xlabel": "..."}}

Para geometric/illustration/cartesian:
  "data" debe ser {{"prompt_detail": "descripción expandida ultra-detallada"}}
"""

# ─── Ultra-detailed prompt expansion ────────────────────────────────

EXPAND_PROMPT = """\
Eres un director de arte de un examen estandarizado de matemáticas (PAES Chile).
Tu trabajo es convertir descripciones cortas de imágenes en prompts ULTRA-DETALLADOS
para que un modelo generativo de imágenes (Gemini) produzca exactamente lo necesario.

DESCRIPCIÓN ORIGINAL:
{alt_text}

CONTEXTO DE LA PREGUNTA:
{stem_text}

Genera un prompt de imagen extremadamente específico que incluya:
1. COMPOSICIÓN: Dimensiones relativas, posición de cada elemento, distribución espacial
2. ELEMENTOS VISUALES: Cada forma, línea, flecha, etiqueta con su posición exacta
3. COLORES: Colores específicos para cada elemento (usar colores simples y contrastantes)
4. TEXTO/ETIQUETAS: Texto exacto que debe aparecer, tamaño relativo, posición
5. ESTILO: Fondo blanco, líneas negras gruesas, estilo de examen educativo profesional
6. PROHIBICIONES: Sin título, sin bordes decorativos, sin watermarks, sin sombras 3D innecesarias

El prompt debe ser TAN DETALLADO que no haya ambigüedad sobre qué dibujar.
Escribe el prompt en inglés para mejor resultado con Gemini.

Responde SOLO con el prompt expandido, sin explicación adicional.
"""


# ─── Matplotlib rendering functions ─────────────────────────────────

def _render_pie_chart(data: dict) -> bytes:
    """Render a pie chart with matplotlib."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = data.get("labels", [])
    values = data.get("values", [])
    colors = plt.cm.Set3.colors[:len(labels)]

    fig, ax = plt.subplots(1, 1, figsize=(6, 6), dpi=150)
    wedges, texts, autotexts = ax.pie(
        values, labels=labels, autopct="%1.0f%%",
        colors=colors, startangle=90,
        textprops={"fontsize": 14, "fontweight": "bold"},
    )
    for at in autotexts:
        at.set_fontsize(12)
        at.set_color("white")
        at.set_fontweight("bold")
    ax.set_aspect("equal")
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _render_bar_chart(data: dict) -> bytes:
    """Render a bar chart with matplotlib."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = data.get("labels", [])
    values = data.get("values", [])
    xlabel = data.get("xlabel", "")
    ylabel = data.get("ylabel", "")
    colors = plt.cm.Set2.colors[:len(labels)]

    fig, ax = plt.subplots(1, 1, figsize=(8, 5), dpi=150)
    bars = ax.bar(labels, values, color=colors, edgecolor="black", linewidth=1.2)

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                str(val), ha="center", va="bottom", fontsize=12, fontweight="bold")

    ax.set_xlabel(xlabel, fontsize=13, fontweight="bold")
    ax.set_ylabel(ylabel, fontsize=13, fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=11)
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _render_line_chart(data: dict) -> bytes:
    """Render a line chart with matplotlib."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    x = data.get("x", [])
    y = data.get("y", [])
    xlabel = data.get("xlabel", "")
    ylabel = data.get("ylabel", "")

    fig, ax = plt.subplots(1, 1, figsize=(8, 5), dpi=150)
    ax.plot(x, y, color="#2196F3", linewidth=2.5, marker="o", markersize=6)
    ax.set_xlabel(xlabel, fontsize=13, fontweight="bold")
    ax.set_ylabel(ylabel, fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=11)
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _render_boxplot(data: dict) -> bytes:
    """Render a boxplot with matplotlib from summary statistics."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    mn = data.get("min", 0)
    q1 = data.get("q1", 0)
    med = data.get("median", 0)
    q3 = data.get("q3", 0)
    mx = data.get("max", 0)
    xlabel = data.get("xlabel", "")

    fig, ax = plt.subplots(1, 1, figsize=(8, 3), dpi=150)

    # Draw boxplot manually for precision
    box_height = 0.4
    y_center = 0.5

    # Whiskers
    ax.plot([mn, q1], [y_center, y_center], color="black", linewidth=2)
    ax.plot([q3, mx], [y_center, y_center], color="black", linewidth=2)
    # Whisker caps
    ax.plot([mn, mn], [y_center - box_height / 3, y_center + box_height / 3],
            color="black", linewidth=2)
    ax.plot([mx, mx], [y_center - box_height / 3, y_center + box_height / 3],
            color="black", linewidth=2)
    # Box
    box = mpatches.FancyBboxPatch(
        (q1, y_center - box_height / 2), q3 - q1, box_height,
        boxstyle="square,pad=0", facecolor="#90CAF9", edgecolor="black", linewidth=2,
    )
    ax.add_patch(box)
    # Median
    ax.plot([med, med], [y_center - box_height / 2, y_center + box_height / 2],
            color="red", linewidth=2.5)

    ax.set_xlim(mn - 0.5, mx + 0.5)
    ax.set_ylim(-0.2, 1.2)
    ax.set_xlabel(xlabel, fontsize=13, fontweight="bold")
    ax.set_yticks([])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.tick_params(labelsize=11)
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _render_dot_plot(data: dict) -> bytes:
    """Render a dot plot with matplotlib."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from collections import Counter

    values = data.get("values", [])
    xlabel = data.get("xlabel", "")
    counts = Counter(values)

    fig, ax = plt.subplots(1, 1, figsize=(8, 4), dpi=150)
    for val, count in sorted(counts.items()):
        for i in range(count):
            ax.plot(val, i + 1, "o", color="#1976D2", markersize=12)

    ax.set_xlabel(xlabel, fontsize=13, fontweight="bold")
    ax.set_ylabel("Frecuencia", fontsize=13, fontweight="bold")
    all_vals = sorted(counts.keys())
    ax.set_xticks(range(int(min(all_vals)), int(max(all_vals)) + 1))
    ax.set_yticks(range(1, max(counts.values()) + 1))
    ax.grid(True, axis="y", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=11)
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


MATPLOTLIB_RENDERERS = {
    "pie_chart": _render_pie_chart,
    "bar_chart": _render_bar_chart,
    "line_chart": _render_line_chart,
    "boxplot": _render_boxplot,
    "dot_plot": _render_dot_plot,
}


# ─── Core logic ─────────────────────────────────────────────────────

def _extract_stem_text(qti_xml: str) -> str:
    """Extract plain text from the QTI item body for context."""
    match = re.search(r"<qti-item-body[^>]*>(.*?)</qti-item-body>", qti_xml, re.DOTALL)
    if match:
        return re.sub(r"<[^>]+>", " ", match.group(1)).strip()
    return ""


def _classify_image(alt_text: str, llm_service) -> tuple[str, dict]:
    """Use LLM to classify image type and extract data."""
    prompt = CLASSIFY_PROMPT.format(alt_text=alt_text)
    raw = llm_service.generate_text(
        prompt,
        response_mime_type="application/json",
        temperature=0.0,
        **build_reasoning_kwargs("gemini", _IMAGE_TEXT_REASONING_LEVEL),
    )
    # TextService returns str directly
    text = raw.text if hasattr(raw, 'text') else str(raw)
    result = json.loads(text)
    category = result.get("category", "illustration")
    data = result.get("data", {})
    return category, data


def _expand_prompt(alt_text: str, stem_text: str, llm_service) -> str:
    """Use LLM to expand alt text into an ultra-detailed image generation prompt."""
    prompt = EXPAND_PROMPT.format(alt_text=alt_text, stem_text=stem_text)
    raw = llm_service.generate_text(
        prompt,
        temperature=0.3,
        **build_reasoning_kwargs("gemini", _IMAGE_TEXT_REASONING_LEVEL),
    )
    text = raw.text if hasattr(raw, 'text') else str(raw)
    return text.strip()


def main() -> None:
    from app.question_variants.llm_service import build_text_service

    parser = argparse.ArgumentParser(description="Generate images for hard variants")
    parser.add_argument("--test", required=True, help="Test ID (e.g. Prueba-invierno-2025)")
    parser.add_argument("--question", required=True, help="Question ID (e.g. Q65)")
    parser.add_argument("--dry-run", action="store_true", help="Classify only, don't generate")
    args = parser.parse_args()

    base_dir = Path("app/data/pruebas/hard_variants") / args.test / args.question / "variants" / "approved"
    if not base_dir.exists():
        logger.error(f"Directory not found: {base_dir}")
        sys.exit(1)

    # Load LLM services
    openai_client = load_default_openai_client()
    engine = ImageGenerationEngine(
        openai_client=openai_client,
        gemini_image_client=None,
    )
    engine.ensure_gemini()

    llm_service = build_text_service("gemini")  # For classification & prompt expansion

def process_variant_images(
    test_id: str,
    question_id: str,
    variant_id: str,
    xml_path: Path,
    engine: ImageGenerationEngine,
    llm_service: Any,
    dry_run: bool = False,
) -> None:
    """Process a single variant XML file to generate and replace placeholder images."""
    qti_xml = xml_path.read_text(encoding="utf-8")

    # Find all img tags and check if any have non-S3 src
    img_pattern = re.compile(
        r'<img[^>]*src=[\'"]([^\'"]+)[\'"][^>]*alt=[\'"]([^\'"]+)[\'"][^>]*/?>',
    )
    all_imgs = list(img_pattern.finditer(qti_xml))
    placeholder_imgs = [(m, m.group(1), m.group(2)) for m in all_imgs if _is_placeholder_src(m.group(1))]

    if not placeholder_imgs:
        logger.info(f"  {variant_id}: no placeholders, skipping.")
        return

    logger.info(f"\n{'='*60}")
    logger.info(f"Processing {variant_id} ({len(placeholder_imgs)} images)")
    logger.info(f"{'='*60}")

    stem_text = _extract_stem_text(qti_xml)

    for idx, (match, old_src, alt_text) in enumerate(placeholder_imgs):
        file_id = f"{question_id}-{variant_id}-img{idx}"

        logger.info(f"\n  [img {idx}] src: {old_src}")
        logger.info(f"  [img {idx}] alt: {alt_text[:80]}...")

        # Step 1: Classify
        category, data = _classify_image(alt_text, llm_service)
        logger.info(f"  [img {idx}] Category: {category}")

        if dry_run:
            logger.info(f"  [img {idx}] Data: {json.dumps(data, ensure_ascii=False)[:200]}")
            continue

        # Step 2: Generate
        image_bytes: bytes | None = None

        if category in MATPLOTLIB_RENDERERS:
            # Route A: Matplotlib
            logger.info(f"  [img {idx}] Using MATPLOTLIB for {category}")
            try:
                renderer = MATPLOTLIB_RENDERERS[category]
                image_bytes = renderer(data)
                logger.info(f"  [img {idx}] ✅ Matplotlib rendered ({len(image_bytes)} bytes)")
            except Exception as e:
                logger.error(f"  [img {idx}] Matplotlib failed: {e}")
                # Fallback to Gemini
                logger.info(f"  [img {idx}] Falling back to Gemini...")
                expanded_prompt = _expand_prompt(alt_text, stem_text, llm_service)
                image_bytes = engine.generate_validated_image(
                    expanded_prompt, stem_text, max_retries=2,
                )
        else:
            # Route B: Gemini with ultra-detailed prompt
            logger.info(f"  [img {idx}] Using GEMINI with expanded prompt for {category}")
            expanded_prompt = _expand_prompt(alt_text, stem_text, llm_service)
            logger.info(f"  [img {idx}] Expanded prompt: {expanded_prompt[:120]}...")
            image_bytes = engine.generate_validated_image(
                expanded_prompt, stem_text, max_retries=2,
            )

        if not image_bytes:
            logger.error(f"  [img {idx}] ❌ Generation failed completely.")
            continue

        # Step 3: Upload to S3
        existing = engine.check_s3_exists(file_id, _S3_PATH_PREFIX, test_id)
        if existing:
            s3_url = existing
            logger.info(f"  [img {idx}] S3 hit: {s3_url}")
        else:
            s3_url = engine.upload_to_s3(image_bytes, file_id, _S3_PATH_PREFIX, test_id)
            if not s3_url:
                logger.error(f"  [img {idx}] ❌ S3 upload failed.")
                continue
            logger.info(f"  [img {idx}] ✅ Uploaded: {s3_url}")

        # Step 4: Replace in XML
        old_tag = match.group(0)
        new_tag = old_tag.replace(old_src, s3_url)
        qti_xml = qti_xml.replace(old_tag, new_tag)

    xml_path.write_text(qti_xml, encoding="utf-8")
    logger.info(f"\n  💾 Saved {xml_path}")


def main() -> None:
    from app.question_variants.llm_service import build_text_service

    parser = argparse.ArgumentParser(description="Generate images for hard variants")
    parser.add_argument("--test", required=True, help="Test ID (e.g. Prueba-invierno-2025)")
    parser.add_argument("--question", help="Specific Question ID (e.g. Q65). Required if --all-approved is not set.")
    parser.add_argument("--all-approved", action="store_true", help="Process all approved variants for the given test.")
    parser.add_argument("--dry-run", action="store_true", help="Classify only, don't generate")
    args = parser.parse_args()

    if not args.question and not args.all_approved:
        parser.error("You must specify either --question or --all-approved")

    # Load LLM services
    openai_client = load_default_openai_client()
    engine = ImageGenerationEngine(
        openai_client=openai_client,
        gemini_image_client=None,
    )
    engine.ensure_gemini()
    llm_service = build_text_service("gemini")  # For classification & prompt expansion

    base_test_dir = Path("app/data/pruebas/hard_variants") / args.test
    if not base_test_dir.exists():
        logger.error(f"Test directory not found: {base_test_dir}")
        sys.exit(1)

    questions_to_process = []
    if args.all_approved:
        questions_to_process = [d for d in base_test_dir.iterdir() if d.is_dir()]
    else:
        questions_to_process = [base_test_dir / args.question]

    for q_dir in sorted(questions_to_process):
        q_id = q_dir.name
        approved_dir = q_dir / "variants" / "approved"
        
        if not approved_dir.exists() or not approved_dir.is_dir():
            continue
            
        for variant_dir in sorted(approved_dir.iterdir()):
            if not variant_dir.is_dir():
                continue
            xml_path = variant_dir / "question.xml"
            if not xml_path.exists():
                continue
            
            process_variant_images(
                test_id=args.test,
                question_id=q_id,
                variant_id=variant_dir.name,
                xml_path=xml_path,
                engine=engine,
                llm_service=llm_service,
                dry_run=args.dry_run,
            )

if __name__ == "__main__":
    main()
