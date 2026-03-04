"""Preflight helpers for dry-run gate and payload preview."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.notation_batch import (
    build_confirm_template_requests,
    build_scan_requests,
    write_jsonl,
)
from scripts.notation_state import ScanItem

PIPELINE_DIR = Path("app/data/.notation_pipeline")
PREVIEW_DIR = PIPELINE_DIR / "preflight"
GATE_PATH = PREVIEW_DIR / "latest_gate.json"


def estimate_cost_range(items: list[ScanItem]) -> dict[str, float | int]:
    scan_input = scan_output = confirm_input = confirm_output = 0
    for _key, _source, _fp, content, _label in items:
        base_tokens = max(50, len(content) // 4)
        scan_input += base_tokens + 700
        scan_output += 180
        confirm_input += base_tokens + 450
        confirm_output += 220

    in_rate = 1.25
    out_rate = 10.0
    scan_cost = scan_input / 1e6 * in_rate + scan_output / 1e6 * out_rate
    max_total_cost = (
        (scan_input + confirm_input) / 1e6 * in_rate
        + (scan_output + confirm_output) / 1e6 * out_rate
    )
    return {
        "scan_requests": len(items),
        "confirm_requests_min": 0,
        "confirm_requests_max": len(items),
        "scan_input_tokens_est": scan_input,
        "scan_output_tokens_est": scan_output,
        "confirm_input_tokens_est_max": confirm_input,
        "confirm_output_tokens_est_max": confirm_output,
        "cost_usd_min": round(scan_cost, 2),
        "cost_usd_max": round(max_total_cost, 2),
    }


def source_counts(items: list[ScanItem]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for _, source, *_ in items:
        counts[source] = counts.get(source, 0) + 1
    return counts


def source_ids(items: list[ScanItem]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for key, source, *_ in items:
        out.setdefault(source, []).append(key)
    return out


def build_preflight_report(
    items: list[ScanItem],
    pool: str,
    limit: int | None,
) -> dict[str, Any]:
    digest = hashlib.sha256(
        "\n".join(sorted(k for k, *_ in items)).encode("utf-8"),
    ).hexdigest()
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "pool": pool,
        "limit": limit,
        "counts_by_source": source_counts(items),
        "total_items": len(items),
        "cost_estimate": estimate_cost_range(items),
        "candidate_digest_sha256": digest,
        "ids_by_source": source_ids(items),
        "all_ids": [k for k, *_ in items],
    }


def sample_requests(
    items: list[ScanItem],
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    by_source: dict[str, list[ScanItem]] = {}
    for item in items:
        by_source.setdefault(item[1], []).append(item)
    out: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for source, src_items in by_source.items():
        sample = src_items[:5]
        scan_reqs = build_scan_requests(sample)
        conf_reqs = build_confirm_template_requests(sample)
        out[source] = {
            "scan": [r.to_jsonl_dict() for r in scan_reqs[:5]],
            "confirm": [r.to_jsonl_dict() for r in conf_reqs[:5]],
        }
    return out


def validate_jsonl(path: Path) -> tuple[bool, str]:
    try:
        for ln, line in enumerate(path.read_text("utf-8").splitlines(), 1):
            row = json.loads(line)
            if not isinstance(row, dict):
                return False, f"Line {ln}: not an object"
            for key in ("custom_id", "method", "url", "body"):
                if key not in row:
                    return False, f"Line {ln}: missing '{key}'"
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


def write_gate(report: dict[str, Any]) -> None:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    gate = {
        "created_utc": report["generated_at_utc"],
        "pool": report["pool"],
        "limit": report["limit"],
        "total_items": report["total_items"],
        "candidate_digest_sha256": report["candidate_digest_sha256"],
    }
    GATE_PATH.write_text(
        json.dumps(gate, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_gate() -> dict[str, Any] | None:
    if not GATE_PATH.exists():
        return None
    try:
        return json.loads(GATE_PATH.read_text("utf-8"))
    except Exception:
        return None


def ensure_gate(
    *,
    force_run: bool,
    expected_pool: str,
) -> None:
    if force_run:
        return
    gate = load_gate()
    if not gate:
        raise RuntimeError(
            "Blocked: dry-run gate not found. "
            "Run with --dry-run first (or use --force-run).",
        )
    if gate.get("pool") != expected_pool:
        raise RuntimeError(
            "Blocked: latest dry-run gate pool mismatch. "
            f"Expected '{expected_pool}', found '{gate.get('pool')}'. "
            "Run dry-run for this pool or use --force-run.",
        )


def run_dry_run(
    *,
    items: list[ScanItem],
    pool: str,
    limit: int | None,
    report_path: Path,
    emit_jsonl_dir: Path | None,
) -> dict[str, Any]:
    report = build_preflight_report(items, pool, limit)
    report["sample_requests"] = sample_requests(items)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if emit_jsonl_dir:
        emit_jsonl_dir.mkdir(parents=True, exist_ok=True)
        scan_requests = build_scan_requests(items)
        confirm_requests = build_confirm_template_requests(items)
        scan_path = write_jsonl(
            scan_requests, emit_jsonl_dir / "scan_requests.jsonl",
        )
        confirm_path = write_jsonl(
            confirm_requests, emit_jsonl_dir / "confirm_requests.jsonl",
        )
        scan_ok, scan_msg = validate_jsonl(scan_path)
        conf_ok, conf_msg = validate_jsonl(confirm_path)
        report["jsonl_files"] = {
            "scan": str(scan_path),
            "confirm": str(confirm_path),
        }
        report["jsonl_validation"] = {
            "scan": {"ok": scan_ok, "message": scan_msg},
            "confirm": {"ok": conf_ok, "message": conf_msg},
        }
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    write_gate(report)
    return report
