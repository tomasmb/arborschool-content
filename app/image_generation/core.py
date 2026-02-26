"""Shared image generation core: generate, validate, upload.

Pipeline-agnostic logic reused by both question-generation and
mini-lessons. Callers provide a domain-specific context extractor
and post-processing callback.

Responsibilities:
- Rate-limited Gemini image generation with retry
- GPT-5.1 vision validation
- S3 upload with configurable path prefix
"""

from __future__ import annotations

import base64
import io
import json
import logging
import threading
import time
from collections import deque
from typing import Any

from PIL import Image

from app.llm_clients import (
    GeminiImageClient,
    OpenAIClient,
    RateLimitError,
    ServiceUnavailableError,
    load_default_gemini_image_client,
    load_fallback_gemini_image_clients,
)

logger = logging.getLogger(__name__)

_VALIDATION_REASONING = "low"
_MAX_503_RETRIES = 3
_DEFAULT_GEMINI_RPM = 10


# ------------------------------------------------------------------
# Rate limiter (thread-safe sliding-window)
# ------------------------------------------------------------------


class RateLimiter:
    """Thread-safe sliding-window rate limiter."""

    def __init__(self, max_rpm: int) -> None:
        self._max = max_rpm
        self._times: deque[float] = deque()
        self._lock = threading.Lock()

    def wait(self) -> None:
        """Block until a slot is available."""
        while True:
            with self._lock:
                now = time.monotonic()
                while (self._times
                       and now - self._times[0] >= 60.0):
                    self._times.popleft()
                if len(self._times) < self._max:
                    self._times.append(now)
                    return
                delay = 60.0 - (now - self._times[0])
            time.sleep(delay + 0.1)


# ------------------------------------------------------------------
# Prompt templates (shared across pipelines)
# ------------------------------------------------------------------

GENERATION_PROMPT = """\
Generate a clean, educational image for a math exam question.

CONTENT (what to draw):
{generation_prompt}

STYLE (how to draw it):
- Clean white background
- Black lines with subtle color accents where needed
- High contrast, easy to read at small sizes
- Minimal labels only (axis labels, point names, measurements)
- No title, header text, or explanatory text
- No watermarks or logos
- Professional, exam-quality visual
"""

RETRY_PROMPT = """\
Generate a clean, educational image for a math exam question.

CONTENT (what to draw):
{generation_prompt}

PREVIOUS ATTEMPT WAS REJECTED — you MUST fix this specific issue:
{rejection_reason}

STYLE (how to draw it):
- Clean white background
- Black lines with subtle color accents where needed
- High contrast, easy to read at small sizes
- Minimal labels only (axis labels, point names, measurements)
- No title, header text, or explanatory text
- No watermarks or logos
- Professional, exam-quality visual
"""

VALIDATION_PROMPT = """\
<role>
Eres un validador de imagenes educativas para preguntas \
PAES M1 (Chile).
</role>

<context>
DESCRIPCION ESPERADA:
{image_description}

CONTEXTO:
{stem_context}
</context>

<task>
Analiza la imagen adjunta y determina si cumple con la \
descripcion esperada. Verifica:
1. Los elementos matematicos correctos estan presentes.
2. Los valores numericos y etiquetas son correctos y legibles.
3. La imagen es coherente con el contexto.
4. No hay errores matematicos visibles.
</task>

<rules>
- Tolera variaciones estilisticas menores.
- NO toleres errores matematicos.
- Si la imagen es generica o no contiene los elementos \
especificos descritos, marca como "fail".
</rules>

<output_format>
JSON puro:
{{
  "result": "pass" o "fail",
  "reason": "explicacion breve del veredicto"
}}
</output_format>
"""


# ------------------------------------------------------------------
# Core image generation engine
# ------------------------------------------------------------------


class ImageGenerationEngine:
    """Pipeline-agnostic image generation + validation + upload.

    Owns the Gemini client lifecycle, rate limiting, retry logic,
    GPT-5.1 validation, and S3 upload. Does NOT know about QTI
    XML, HTML, or any domain-specific content format.
    """

    def __init__(
        self,
        openai_client: OpenAIClient,
        gemini_image_client: GeminiImageClient | None = None,
        gemini_max_rpm: int = _DEFAULT_GEMINI_RPM,
    ) -> None:
        self._openai = openai_client
        self._gemini: GeminiImageClient | None = gemini_image_client
        self._rate_limiter = RateLimiter(gemini_max_rpm)
        self._fallbacks: list[GeminiImageClient] = []
        self._fallbacks_loaded = False
        self._swap_lock = threading.Lock()

    def ensure_gemini(self) -> GeminiImageClient:
        """Lazily load the Gemini image client."""
        if self._gemini is None:
            self._gemini = load_default_gemini_image_client()
        return self._gemini

    def try_swap_to_fallback(self) -> bool:
        """Swap to next available fallback key."""
        with self._swap_lock:
            if not self._fallbacks_loaded:
                self._fallbacks = (
                    load_fallback_gemini_image_clients()
                )
                self._fallbacks_loaded = True
            if not self._fallbacks:
                return False
            self._gemini = self._fallbacks.pop(0)
            logger.info(
                "Switched to fallback Gemini key "
                "(%d more available)", len(self._fallbacks),
            )
            return True

    # -- Core pipeline: generate -> validate -> upload -----------

    def generate_validated_image(
        self,
        description: str,
        context_text: str,
        max_retries: int = 1,
    ) -> bytes | None:
        """Generate and validate an image. Returns PNG bytes."""
        self.ensure_gemini()
        max_attempts = max_retries + 1
        rejection: str | None = None
        attempt = 0

        while attempt < max_attempts:
            try:
                image_bytes = self._generate(
                    description, rejection,
                )
            except RateLimitError as rle:
                if rle.is_daily:
                    if self.try_swap_to_fallback():
                        continue
                    raise
                logger.warning(
                    "Per-minute rate limit — sleeping 60s",
                )
                time.sleep(60)
                continue

            if image_bytes is None:
                attempt += 1
                continue

            passed, reason = self._validate(
                image_bytes, description, context_text,
            )
            if not passed:
                rejection = reason
                attempt += 1
                continue

            return image_bytes
        return None

    def check_s3_exists(
        self, file_id: str, path_prefix: str, folder_name: str,
    ) -> str | None:
        """Return existing S3 URL if the image is already uploaded."""
        return _check_s3_url(file_id, path_prefix, folder_name)

    def upload_to_s3(
        self,
        image_bytes: bytes,
        file_id: str,
        path_prefix: str,
        folder_name: str,
    ) -> str | None:
        """Upload PNG to S3. Returns public URL or None."""
        upload_fn = _load_s3_upload_fn()
        if upload_fn is None:
            return None
        return upload_fn(
            image_base64=base64.b64encode(image_bytes).decode(),
            question_id=file_id,
            path_prefix=path_prefix,
            test_name=folder_name,
        )

    # -- Internal helpers ----------------------------------------

    def _generate(
        self,
        description: str,
        previous_rejection: str | None = None,
    ) -> bytes | None:
        """Generate image via Gemini with 503 retry."""
        self._rate_limiter.wait()
        gemini = self.ensure_gemini()
        prompt = (
            RETRY_PROMPT.format(
                generation_prompt=description,
                rejection_reason=previous_rejection,
            ) if previous_rejection
            else GENERATION_PROMPT.format(
                generation_prompt=description,
            )
        )
        for retry_503 in range(_MAX_503_RETRIES + 1):
            if retry_503 > 0:
                delay = 30 * (2 ** (retry_503 - 1))
                logger.warning(
                    "503 backoff %ds (%d/%d)",
                    delay, retry_503, _MAX_503_RETRIES,
                )
                time.sleep(delay)
            try:
                return gemini.generate_image(prompt)
            except RateLimitError:
                raise
            except (TimeoutError, OSError) as exc:
                logger.error(
                    "Gemini image timed out: %s", exc,
                )
                return None
            except Exception as exc:
                msg = str(exc).lower()
                if "429" in msg and "resource_exhausted" in msg:
                    is_daily = (
                        "per_day" in msg
                        or "per day" in msg
                        or "rpd" in msg
                    )
                    raise RateLimitError(
                        str(exc), is_daily=is_daily,
                    ) from exc
                if "503" in msg and "unavailable" in msg:
                    continue
                logger.error(
                    "Gemini image failed: %s", exc,
                )
                return None
        raise ServiceUnavailableError(
            "503 persists after retries",
        )

    def _validate(
        self,
        image_bytes: bytes,
        description: str,
        context_text: str,
    ) -> tuple[bool, str]:
        """Validate via GPT-5.1 vision."""
        prompt = VALIDATION_PROMPT.format(
            image_description=description,
            stem_context=context_text[:500],
        )
        pil_img = Image.open(io.BytesIO(image_bytes))
        try:
            resp = self._openai.call_with_images(
                prompt,
                [pil_img],
                reasoning_effort=_VALIDATION_REASONING,
                response_mime_type="application/json",
            )
            data: dict[str, Any] = json.loads(resp.text)
            result = data.get("result", "fail")
            reason = data.get("reason", "no reason")
            if result == "pass":
                return True, reason
            return False, reason
        except Exception as exc:
            logger.error("Image validation error: %s", exc)
            return False, f"validation error: {exc}"


# ------------------------------------------------------------------
# S3 helpers
# ------------------------------------------------------------------

_S3_BUCKET = "paes-question-images"
_S3_REGION = "us-east-1"


def _check_s3_url(
    file_id: str, path_prefix: str, folder_name: str,
) -> str | None:
    """Check if image already exists in S3 via HTTP HEAD.

    Returns the public URL if it exists, None otherwise.
    """
    import httpx

    safe_id = "".join(
        c for c in file_id if c.isalnum() or c in "-_"
    )
    safe_folder = "".join(
        c for c in folder_name.lower() if c.isalnum() or c in "-_"
    )
    if path_prefix and not path_prefix.endswith("/"):
        path_prefix += "/"
    s3_key = f"{path_prefix}{safe_folder}/{safe_id}.png"
    url = (
        f"https://{_S3_BUCKET}.s3.{_S3_REGION}"
        f".amazonaws.com/{s3_key}"
    )
    try:
        resp = httpx.head(url, timeout=5)
        if resp.status_code == 200:
            return url
    except Exception:
        pass
    return None


_s3_upload_fn: Any = None


def _load_s3_upload_fn() -> Any:
    """Lazily load upload_image_to_s3 from pdf-to-qti module."""
    global _s3_upload_fn  # noqa: PLW0603
    if _s3_upload_fn is not None:
        return _s3_upload_fn
    import importlib
    from pathlib import Path
    spec_path = (
        Path(__file__).resolve().parents[1]
        / "pruebas" / "pdf-to-qti" / "modules" / "utils"
        / "s3_uploader.py"
    )
    if not spec_path.exists():
        return None
    try:
        spec = importlib.util.spec_from_file_location(
            "s3_uploader", spec_path,
        )
        mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        _s3_upload_fn = mod.upload_image_to_s3
        return _s3_upload_fn
    except Exception:
        return None
