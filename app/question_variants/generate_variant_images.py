"""generate_variant_images.py — Generate images for hard variants.

All images go through: LLM expands alt text into ultra-detailed prompt
→ Gemini generates image → GPT-5.1 validates → S3 upload.

Processes variants in parallel (ThreadPoolExecutor) for throughput.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from app.image_generation.core import ImageGenerationEngine
from app.llm_clients import (
    RateLimitError,
    ServiceUnavailableError,
    load_default_openai_client,
)
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


EXPAND_PROMPT = """\
Eres un director de arte de un examen estandarizado de matemáticas \
(PAES Chile). Convierte esta descripción de imagen en un prompt \
ULTRA-DETALLADO para Gemini.

DESCRIPCIÓN ORIGINAL:
{alt_text}

CONTEXTO DE LA PREGUNTA:
{stem_text}

Incluye:
1. COMPOSICIÓN: Dimensiones, posición de cada elemento
2. ELEMENTOS VISUALES: Formas, líneas, flechas, etiquetas exactas
3. COLORES: Simples y contrastantes
4. TEXTO/ETIQUETAS: Texto exacto, tamaño, posición
5. ESTILO: Fondo blanco, líneas negras gruesas, estilo educativo
6. PROHIBICIONES: Sin título, sin bordes decorativos, sin watermarks

Escribe el prompt en inglés. Responde SOLO con el prompt.
"""


def _extract_stem_text(qti_xml: str) -> str:
    """Extract plain text from the QTI item body for context."""
    match = re.search(
        r"<qti-item-body[^>]*>(.*?)</qti-item-body>",
        qti_xml, re.DOTALL,
    )
    if match:
        return re.sub(r"<[^>]+>", " ", match.group(1)).strip()
    return ""


def _expand_prompt(
    alt_text: str, stem_text: str, llm_service: Any,
) -> str:
    """Expand alt text into an ultra-detailed image prompt via LLM."""
    prompt = EXPAND_PROMPT.format(alt_text=alt_text, stem_text=stem_text)
    raw = llm_service.generate_text(
        prompt,
        temperature=0.3,
        **build_reasoning_kwargs("gemini", _IMAGE_TEXT_REASONING_LEVEL),
    )
    text = raw.text if hasattr(raw, 'text') else str(raw)
    return text.strip()


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

        if dry_run:
            continue

        # Step 1: Expand alt text into detailed image prompt
        expanded_prompt = _expand_prompt(alt_text, stem_text, llm_service)
        logger.info(
            "  [img %d] Prompt: %s...", idx, expanded_prompt[:120],
        )

        # Step 2: Generate image (Gemini) + validate (GPT-5.1)
        image_bytes = engine.generate_validated_image(
            expanded_prompt, stem_text, max_retries=2,
        )
        if not image_bytes:
            logger.error(f"  [img {idx}] Generation failed.")
            continue

        # Step 3: Upload to S3 (idempotent — reuses existing)
        existing = engine.check_s3_exists(
            file_id, _S3_PATH_PREFIX, test_id,
        )
        if existing:
            s3_url = existing
            logger.info(f"  [img {idx}] S3 hit: {s3_url}")
        else:
            s3_url = engine.upload_to_s3(
                image_bytes, file_id, _S3_PATH_PREFIX, test_id,
            )
            if not s3_url:
                logger.error(f"  [img {idx}] S3 upload failed.")
                continue
            logger.info(f"  [img {idx}] Uploaded: {s3_url}")

        # Step 4: Replace in XML
        old_tag = match.group(0)
        new_tag = old_tag.replace(old_src, s3_url)
        qti_xml = qti_xml.replace(old_tag, new_tag)

    xml_path.write_text(qti_xml, encoding="utf-8")
    logger.info(f"\n  💾 Saved {xml_path}")


_DEFAULT_WORKERS = 3


def _collect_variant_tasks(
    base_test_dir: Path,
    test_id: str,
    question_id: str | None,
    all_approved: bool,
) -> list[dict[str, Any]]:
    """Scan the filesystem and return a list of variant task dicts."""
    q_dirs: list[Path] = []
    if all_approved:
        q_dirs = [d for d in base_test_dir.iterdir() if d.is_dir()]
    elif question_id:
        q_dirs = [base_test_dir / question_id]

    tasks: list[dict[str, Any]] = []
    for q_dir in sorted(q_dirs):
        approved_dir = q_dir / "variants" / "approved"
        if not approved_dir.exists() or not approved_dir.is_dir():
            continue
        for variant_dir in sorted(approved_dir.iterdir()):
            if not variant_dir.is_dir():
                continue
            xml_path = variant_dir / "question.xml"
            if not xml_path.exists():
                continue
            tasks.append({
                "test_id": test_id,
                "question_id": q_dir.name,
                "variant_id": variant_dir.name,
                "xml_path": xml_path,
            })
    return tasks


def _run_parallel(
    tasks: list[dict[str, Any]],
    engine: ImageGenerationEngine,
    llm_service: Any,
    workers: int,
    dry_run: bool,
) -> tuple[int, int]:
    """Process variant images in parallel. Returns (ok, failed)."""
    total = len(tasks)
    lock = threading.Lock()
    counters = {"ok": 0, "skipped": 0, "failed": 0}

    def _worker(task: dict[str, Any]) -> None:
        try:
            process_variant_images(
                test_id=task["test_id"],
                question_id=task["question_id"],
                variant_id=task["variant_id"],
                xml_path=task["xml_path"],
                engine=engine,
                llm_service=llm_service,
                dry_run=dry_run,
            )
            with lock:
                counters["ok"] += 1
                done = counters["ok"] + counters["failed"]
            logger.info(
                "[%d/%d] %s done", done, total, task["variant_id"],
            )
        except Exception as exc:
            with lock:
                counters["failed"] += 1
                done = counters["ok"] + counters["failed"]
            logger.error(
                "[%d/%d] %s FAILED: %s",
                done, total, task["variant_id"], exc,
            )

    logger.info(
        "Processing %d variants with %d workers", total, workers,
    )
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_worker, t): t for t in tasks}
        for future in as_completed(futures):
            try:
                future.result()
            except (RateLimitError, ServiceUnavailableError) as exc:
                kind = (
                    "Daily quota"
                    if isinstance(exc, RateLimitError)
                    else "503 unavailable"
                )
                logger.error(
                    "%s — cancelling remaining images", kind,
                )
                for f in futures:
                    f.cancel()
                break

    return counters["ok"], counters["failed"]


def main() -> None:
    from app.question_variants.llm_service import build_text_service

    parser = argparse.ArgumentParser(
        description="Generate images for hard variants",
    )
    parser.add_argument(
        "--test", required=True,
        help="Test ID (e.g. prueba-invierno-2025)",
    )
    parser.add_argument(
        "--question",
        help="Specific Question ID (e.g. Q65).",
    )
    parser.add_argument(
        "--all-approved", action="store_true",
        help="Process all approved variants for the given test.",
    )
    parser.add_argument(
        "--workers", type=int, default=_DEFAULT_WORKERS,
        help=f"Parallel workers (default {_DEFAULT_WORKERS}).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Classify only, don't generate",
    )
    args = parser.parse_args()

    if not args.question and not args.all_approved:
        parser.error(
            "You must specify either --question or --all-approved",
        )

    base_test_dir = Path("app/data/pruebas/hard_variants") / args.test
    if not base_test_dir.exists():
        logger.error("Test directory not found: %s", base_test_dir)
        sys.exit(1)

    tasks = _collect_variant_tasks(
        base_test_dir, args.test, args.question, args.all_approved,
    )
    if not tasks:
        logger.info("No variant tasks found. Nothing to do.")
        sys.exit(0)

    openai_client = load_default_openai_client()
    engine = ImageGenerationEngine(
        openai_client=openai_client, gemini_image_client=None,
    )
    engine.ensure_gemini()
    llm_service = build_text_service("gemini")

    ok, failed = _run_parallel(
        tasks, engine, llm_service, args.workers, args.dry_run,
    )
    logger.info(
        "Done. %d succeeded, %d failed out of %d total.",
        ok, failed, len(tasks),
    )


if __name__ == "__main__":
    main()
