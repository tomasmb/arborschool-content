"""
fix_encoding_rerun_p9.py
------------------------
⛔ DO NOT USE — DEPRECATED, KNOWN BUG ⛔

This script has a critical bug: the fix_encoding() regex replaces normal
letter combinations that look like hex (e.g. "ed" in "reducción" → "í",
producing "ríucción"). It introduces new errors instead of fixing the
original ones.

Additionally, some corruption was "character drop" (e.g. ó → deleted),
which cannot be recovered with regex — those items need Phase 4 re-generation.

Result: this script was run on 2026-02-23 and produced 14/2498 PASS (0.6%).

USE rerun_underperforming.py INSTEAD for atoms below the quality threshold.
"""

import sys

print("⛔ ABORTED: fix_encoding_rerun_p9.py is deprecated and has a known bug.")
print("   Use rerun_underperforming.py instead.")
sys.exit(1)

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

JOB_ID = "batch_api_20260222_133844"
BASE = Path(
    "app/data/question-generation/.batch_runs"
) / JOB_ID

P9_INPUT   = BASE / "phase_9_input.jsonl"
P9_RESULTS = BASE / "phase_9_results.jsonl"

MODEL = "gpt-5.1"
POLL_INTERVAL = 60  # seconds

# If resuming after a crash/power-off, set this to the existing batch ID
# to skip submission and go straight to polling.
RESUME_BATCH_ID: str | None = "batch_699c5e95b4748190830f1dca9b6949e4"

# Latin-1 hex → UTF-8 mapping for Spanish characters
LATIN1_MAP: dict[str, str] = {
    "e9": "é", "f3": "ó", "e1": "á", "fa": "ú",
    "ed": "í", "f1": "ñ", "fc": "ü", "bf": "¿",
    "a1": "¡", "c9": "É", "d3": "Ó", "c1": "Á",
    "da": "Ú", "cd": "Í", "d1": "Ñ", "e0": "à",
    "e8": "è", "f2": "ò", "f9": "ù",
}

# Regex: hex pair that looks like a Spanish char in a word context.
# Matches when flanked by letters OR ¿/¡ at start of a word-like sequence.
_HEX_PAIRS = "|".join(re.escape(k) for k in LATIN1_MAP)
_ENC_RE = re.compile(
    rf"(?<=[a-zA-ZáéíóúñüÁÉÍÓÚÑÜ])({_HEX_PAIRS})(?=[a-zA-ZáéíóúñüÁÉÍÓÚÑÜ])"
    rf"|(?:(?<=\s)|(?<=^)|(?<=>))({_HEX_PAIRS})(?=[A-ZÁÉÍÓÚÑ])",
    re.MULTILINE,
)


def _fix_match(m: re.Match) -> str:
    hex_val = (m.group(1) or m.group(2) or "").lower()
    return LATIN1_MAP.get(hex_val, m.group(0))


def fix_encoding(text: str) -> str:
    """Apply Latin-1 hex → UTF-8 substitution to a string."""
    return _ENC_RE.sub(_fix_match, text)


# ---------------------------------------------------------------------------
# Detection: which items failed ONLY due to encoding?
# ---------------------------------------------------------------------------

_ENC_SIGNALS = ("e9", "f3", "bf", "e1", "f1", "fa", "codificaci", "encoding", "corrupt")


def is_encoding_only_failure(result: dict) -> bool:
    resp = result.get("response") or {}
    body = (resp.get("body") or {})
    choices = body.get("choices") or []
    if not choices:
        return False
    content = choices[0].get("message", {}).get("content", "") or ""
    try:
        r = json.loads(content)
    except Exception:
        return False

    fails = {
        k: v for k, v in r.items()
        if isinstance(v, dict) and v.get("status") == "fail"
    }
    if len(fails) != 1 or "content_quality_check" not in fails:
        return False

    cq = fails["content_quality_check"]
    all_text = " ".join(
        str(x) for x in
        cq.get("character_issues", []) + cq.get("typos_found", [])
    ).lower()
    return any(sig in all_text for sig in _ENC_SIGNALS)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    # 1. Load Phase 9 results and identify encoding failures
    logger.info("Loading Phase 9 results...")
    p9_results: list[dict] = []
    with open(P9_RESULTS) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    p9_results.append(json.loads(line))
                except Exception:
                    pass

    encoding_failed_ids: set[str] = set()
    for r in p9_results:
        if is_encoding_only_failure(r):
            encoding_failed_ids.add(r.get("custom_id", ""))

    logger.info(f"Encoding-only failures: {len(encoding_failed_ids)}")
    if not encoding_failed_ids:
        logger.info("Nothing to fix.")
        return

    # 2. Load Phase 9 input and find requests for those items
    logger.info("Loading Phase 9 inputs...")
    p9_inputs_by_id: dict[str, dict] = {}
    with open(P9_INPUT) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                cid = d.get("custom_id", "")
                if cid in encoding_failed_ids:
                    p9_inputs_by_id[cid] = d
            except Exception:
                pass

    logger.info(f"Found {len(p9_inputs_by_id)} matching inputs")
    missing = encoding_failed_ids - set(p9_inputs_by_id.keys())
    if missing:
        logger.warning(f"{len(missing)} items not found in phase_9_input.jsonl — skipping")

    # 3. Fix encoding in the request XML and build new JSONL
    logger.info("Fixing encoding in XML content...")
    fixed_requests: list[dict] = []
    for cid, req in p9_inputs_by_id.items():
        req_copy = json.loads(json.dumps(req))  # deep copy
        try:
            msgs = req_copy["body"]["messages"]
            for msg in msgs:
                content = msg.get("content", [])
                if isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            part["text"] = fix_encoding(part["text"])
                elif isinstance(content, str):
                    msg["content"] = fix_encoding(content)
        except Exception as e:
            logger.warning(f"Could not fix encoding for {cid}: {e}")
        fixed_requests.append(req_copy)

    logger.info(f"Built {len(fixed_requests)} fixed requests")

    # 4. Upload and submit batch (skip if resuming existing batch)
    if RESUME_BATCH_ID:
        logger.info(f"Resuming existing batch: {RESUME_BATCH_ID}")
        batch = client.batches.retrieve(RESUME_BATCH_ID)
    else:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
        ) as tmp:
            for req in fixed_requests:
                tmp.write(json.dumps(req, ensure_ascii=False) + "\n")
            tmp_path = tmp.name

        logger.info(f"Uploading batch file ({len(fixed_requests)} requests)...")
        with open(tmp_path, "rb") as f:
            upload = client.files.create(file=f, purpose="batch")
        logger.info(f"Uploaded file: {upload.id}")

        batch = client.batches.create(
            input_file_id=upload.id,
            endpoint="/v1/chat/completions",
            completion_window="24h",
            metadata={"job_id": JOB_ID, "phase": "phase_9_encoding_fix"},
        )
        logger.info(f"Batch created: {batch.id}")

    # 5. Poll until complete
    while True:
        batch = client.batches.retrieve(batch.id)
        counts = batch.request_counts
        logger.info(
            f"Batch {batch.id}: status={batch.status} "
            f"completed={counts.completed}/{counts.total} "
            f"failed={counts.failed}"
        )
        if batch.status in ("completed", "failed", "expired", "cancelled"):
            break
        time.sleep(POLL_INTERVAL)

    if batch.status != "completed":
        raise RuntimeError(f"Batch ended with status={batch.status}")

    # 6. Download results
    logger.info(f"Downloading results from file {batch.output_file_id}...")
    content_stream = client.files.content(batch.output_file_id)
    raw = content_stream.read()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")

    new_results: dict[str, dict] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
            new_results[d.get("custom_id", "")] = d
        except Exception:
            pass

    logger.info(f"Downloaded {len(new_results)} results")

    # 7. Patch phase_9_results.jsonl
    logger.info("Patching phase_9_results.jsonl...")
    patched: list[dict] = []
    replaced = 0
    kept_fail = 0
    for r in p9_results:
        cid = r.get("custom_id", "")
        if cid in new_results:
            patched.append(new_results[cid])
            replaced += 1
        else:
            patched.append(r)
            if cid in encoding_failed_ids:
                kept_fail += 1  # was in encoding_failed but no new result

    with open(P9_RESULTS, "w", encoding="utf-8") as f:
        for r in patched:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    logger.info(f"Replaced {replaced} results, kept {kept_fail} encoding failures without new result")

    # 8. Summary
    now_pass = 0
    now_fail = 0
    for cid in encoding_failed_ids:
        nr = new_results.get(cid)
        if nr is None:
            now_fail += 1
            continue
        resp = nr.get("response") or {}
        body = (resp.get("body") or {})
        choices = body.get("choices") or []
        if not choices:
            now_fail += 1
            continue
        content_str = choices[0].get("message", {}).get("content", "") or ""
        try:
            r = json.loads(content_str)
        except Exception:
            now_fail += 1
            continue
        fails = [k for k, v in r.items() if isinstance(v, dict) and v.get("status") == "fail"]
        if fails:
            now_fail += 1
        else:
            now_pass += 1

    logger.info("=" * 50)
    logger.info(f"SUMMARY: {len(encoding_failed_ids)} encoding-failed items re-processed")
    logger.info(f"  Now PASS: {now_pass} ({100*now_pass/len(encoding_failed_ids):.1f}%)")
    logger.info(f"  Still FAIL: {now_fail} ({100*now_fail/len(encoding_failed_ids):.1f}%)")
    logger.info("phase_9_results.jsonl updated.")


if __name__ == "__main__":
    main()
