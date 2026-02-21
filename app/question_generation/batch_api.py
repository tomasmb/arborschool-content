"""OpenAI Batch API client for async request processing.

Provides JSONL serialization, file upload, batch submission, polling,
result download, and orphan batch recovery.  Used by the batch pipeline
to submit large sets of LLM requests at 50% cost discount.

All disk I/O uses atomic temp-file + rename to prevent partial writes.
"""

from __future__ import annotations

import hashlib
import json
import logging
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests as http_requests

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.openai.com/v1"
_FILES_URL = f"{_BASE_URL}/files"
_BATCHES_URL = f"{_BASE_URL}/batches"

DEFAULT_POLL_INTERVAL = 30
DEFAULT_MAX_WAIT = 86400  # 24 hours

_TERMINAL_STATUSES = frozenset({
    "completed", "failed", "expired", "cancelled",
})


# ------------------------------------------------------------------
# Data classes
# ------------------------------------------------------------------


@dataclass
class BatchRequest:
    """Single request for inclusion in a Batch API JSONL file."""

    custom_id: str
    model: str
    messages: list[dict[str, Any]]
    reasoning_effort: str | None = None
    response_format: dict[str, str] | None = None
    temperature: float | None = None

    def to_jsonl_dict(self) -> dict[str, Any]:
        """Serialize to the JSONL line format expected by the Batch API."""
        body: dict[str, Any] = {
            "model": self.model,
            "messages": self.messages,
        }

        is_reasoning = "gpt-5" in self.model or "o1" in self.model
        uses_reasoning = (
            self.reasoning_effort is not None
            and self.reasoning_effort != "none"
        )

        if is_reasoning and uses_reasoning:
            body["reasoning_effort"] = self.reasoning_effort
        elif self.temperature is not None:
            body["temperature"] = self.temperature
        else:
            body["temperature"] = 0.0

        if self.response_format:
            body["response_format"] = self.response_format

        return {
            "custom_id": self.custom_id,
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": body,
        }


@dataclass
class BatchResponse:
    """Parsed response from a single row in the Batch API results file."""

    custom_id: str
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    error: str | None = None


# ------------------------------------------------------------------
# Client
# ------------------------------------------------------------------


class OpenAIBatchSubmitter:
    """Client for the OpenAI Batch API.

    Handles: JSONL writing, file upload, batch creation, polling,
    result download, and orphan batch recovery.
    """

    def __init__(
        self,
        api_key: str,
        poll_interval: int = DEFAULT_POLL_INTERVAL,
        max_wait: int = DEFAULT_MAX_WAIT,
    ) -> None:
        self._api_key = api_key
        self._poll_interval = poll_interval
        self._max_wait = max_wait
        self._headers = {"Authorization": f"Bearer {api_key}"}

    # ---- JSONL -------------------------------------------------------

    def write_jsonl(
        self,
        requests: list[BatchRequest],
        output_path: Path,
    ) -> tuple[Path, str]:
        """Write requests to a JSONL file.

        Returns (path, sha256_hex) for integrity verification.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        hasher = hashlib.sha256()

        fd, tmp = tempfile.mkstemp(
            dir=str(output_path.parent), suffix=".tmp",
        )
        try:
            with open(fd, "w", encoding="utf-8") as f:
                for req in requests:
                    line = json.dumps(
                        req.to_jsonl_dict(), ensure_ascii=False,
                    )
                    f.write(line + "\n")
                    hasher.update(line.encode("utf-8"))
            Path(tmp).replace(output_path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

        sha = hasher.hexdigest()
        logger.info(
            "Wrote %d requests to %s (sha256: %s…)",
            len(requests), output_path.name, sha[:12],
        )
        return output_path, sha

    # ---- File upload -------------------------------------------------

    def upload_file(self, jsonl_path: Path) -> str:
        """Upload JSONL to OpenAI Files API.  Returns file_id."""
        with open(jsonl_path, "rb") as f:
            resp = http_requests.post(
                _FILES_URL,
                headers=self._headers,
                data={"purpose": "batch"},
                files={
                    "file": (jsonl_path.name, f, "application/jsonl"),
                },
                timeout=300,
            )
        resp.raise_for_status()
        file_id = resp.json()["id"]
        logger.info(
            "Uploaded %s -> file_id=%s", jsonl_path.name, file_id,
        )
        return file_id

    # ---- Batch creation ----------------------------------------------

    def create_batch(
        self,
        file_id: str,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """Create a batch job.  Returns batch_id."""
        body: dict[str, Any] = {
            "input_file_id": file_id,
            "endpoint": "/v1/chat/completions",
            "completion_window": "24h",
        }
        if metadata:
            body["metadata"] = metadata

        resp = http_requests.post(
            _BATCHES_URL,
            headers={
                **self._headers,
                "Content-Type": "application/json",
            },
            json=body,
            timeout=60,
        )
        if not resp.ok:
            # Provide a clear error for common billing failures so the user
            # knows exactly what to fix rather than seeing a generic 400/429.
            try:
                err_body = resp.json()
                err_code = err_body.get("error", {}).get("code", "")
                err_msg = err_body.get("error", {}).get("message", "")
            except Exception:
                err_code, err_msg = "", resp.text[:200]
            if err_code in ("billing_hard_limit_reached", "insufficient_quota"):
                raise RuntimeError(
                    f"OpenAI billing limit reached — add credits at "
                    f"platform.openai.com/settings/organization/billing "
                    f"then re-run the pipeline. (API: {err_msg})"
                )
            resp.raise_for_status()
        batch_id = resp.json()["id"]
        logger.info("Created batch %s for file %s", batch_id, file_id)
        return batch_id

    # ---- Polling -----------------------------------------------------

    def poll_until_done(
        self,
        batch_id: str,
        poll_interval: int | None = None,
        max_wait: int | None = None,
    ) -> dict[str, Any]:
        """Poll batch until it reaches a terminal status.

        Returns the full batch object.
        Raises TimeoutError if max_wait is exceeded.
        """
        interval = poll_interval or self._poll_interval
        limit = max_wait or self._max_wait
        elapsed = 0
        status = "unknown"

        while elapsed < limit:
            batch = self._retrieve_batch(batch_id)
            status = batch["status"]
            counts = batch.get("request_counts", {})

            logger.info(
                "Batch %s: status=%s  completed=%d/%d  "
                "failed=%d  (elapsed %ds)",
                batch_id, status,
                counts.get("completed", 0),
                counts.get("total", 0),
                counts.get("failed", 0),
                elapsed,
            )

            if status in _TERMINAL_STATUSES:
                return batch

            time.sleep(interval)
            elapsed += interval

        raise TimeoutError(
            f"Batch {batch_id} not done within {limit}s "
            f"(last status: {status})",
        )

    # ---- Result download ---------------------------------------------

    def download_file(
        self,
        file_id: str,
        save_path: Path,
    ) -> Path:
        """Download a file from OpenAI Files API to disk (atomic)."""
        url = f"{_FILES_URL}/{file_id}/content"
        resp = http_requests.get(
            url, headers=self._headers, timeout=300,
        )
        resp.raise_for_status()

        save_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(
            dir=str(save_path.parent), suffix=".tmp",
        )
        try:
            with open(fd, "wb") as f:
                f.write(resp.content)
            Path(tmp).replace(save_path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

        logger.info(
            "Downloaded %s -> %s (%d bytes)",
            file_id, save_path.name, len(resp.content),
        )
        return save_path

    # ---- Result parsing ----------------------------------------------

    def parse_results_file(
        self,
        results_path: Path,
    ) -> list[BatchResponse]:
        """Parse a downloaded results JSONL into BatchResponse list."""
        responses: list[BatchResponse] = []

        with open(results_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                responses.append(_parse_result_row(row))

        ok = sum(1 for r in responses if r.error is None)
        logger.info(
            "Parsed %d results: %d ok, %d errors",
            len(responses), ok, len(responses) - ok,
        )
        return responses

    # ---- Orphan batch recovery ---------------------------------------

    def list_recent_batches(
        self, limit: int = 20,
    ) -> list[dict[str, Any]]:
        """List recent batches for orphan recovery."""
        resp = http_requests.get(
            _BATCHES_URL,
            headers=self._headers,
            params={"limit": limit},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json().get("data", [])

    def find_orphan_batch(
        self,
        file_id: str | None = None,
        metadata_match: dict[str, str] | None = None,
    ) -> dict[str, Any] | None:
        """Find an in-flight or completed batch by file_id or metadata.

        Returns the batch object if found, None otherwise.
        """
        for batch in self.list_recent_batches():
            status = batch.get("status", "")
            if status in ("cancelled", "expired"):
                continue

            if file_id and batch.get("input_file_id") == file_id:
                logger.info(
                    "Found orphan batch %s (file match: %s)",
                    batch["id"], file_id,
                )
                return batch

            if metadata_match:
                batch_meta = batch.get("metadata") or {}
                if all(
                    batch_meta.get(k) == v
                    for k, v in metadata_match.items()
                ):
                    logger.info(
                        "Found orphan batch %s (metadata match)",
                        batch["id"],
                    )
                    return batch

        return None

    # ---- Internal helpers --------------------------------------------

    def _retrieve_batch(
        self, batch_id: str,
    ) -> dict[str, Any]:
        url = f"{_BATCHES_URL}/{batch_id}"
        resp = http_requests.get(
            url, headers=self._headers, timeout=60,
        )
        resp.raise_for_status()
        return resp.json()


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def build_text_messages(prompt: str) -> list[dict[str, Any]]:
    """Build Chat Completions messages for a text-only prompt.

    Mirrors OpenAIClient._build_content() for string prompts.
    """
    return [{
        "role": "user",
        "content": [{"type": "text", "text": prompt}],
    }]


def build_multimodal_messages(
    prompt: str,
    image_b64s: list[str],
) -> list[dict[str, Any]]:
    """Build Chat Completions messages with text + base64 JPEG images.

    Mirrors OpenAIClient._build_content() for multimodal prompts.
    """
    content: list[dict[str, Any]] = [
        {"type": "text", "text": prompt},
    ]
    for b64 in image_b64s:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{b64}",
            },
        })
    return [{"role": "user", "content": content}]


def _parse_result_row(row: dict[str, Any]) -> BatchResponse:
    """Parse a single JSONL row from the Batch API results file."""
    custom_id = row["custom_id"]
    error = row.get("error")

    if error:
        return BatchResponse(
            custom_id=custom_id,
            text="",
            error=json.dumps(error),
        )

    response = row.get("response", {})
    status_code = response.get("status_code", 200)
    body = response.get("body", {})

    choices = body.get("choices", [])
    text = ""
    if choices:
        text = (
            choices[0].get("message", {}).get("content", "")
        )

    usage = body.get("usage", {})
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)

    if status_code != 200:
        return BatchResponse(
            custom_id=custom_id,
            text=text,
            error=f"HTTP {status_code}",
        )

    return BatchResponse(
        custom_id=custom_id,
        text=text,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
