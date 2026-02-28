"""Persistent state management for the notation fix pipeline.

Tracks every scanned item through its lifecycle:
  ok -> (no issues)
  flagged -> (fix) -> pending_validate -> pending_revalidate
          -> pass -> applied -> verified
  fail / sanity_fail -> (retry) -> review

State is saved to JSON after every phase so the pipeline
can resume from crashes and retry failed items.
"""

from __future__ import annotations

import difflib
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_PIPELINE_DIR = Path("app/data/.notation_pipeline")

STATUSES = (
    "ok",                   # scanned, no issues
    "flagged",              # issues detected, awaiting fix (Pass 1)
    "pending_validate",     # has correction, awaiting sanity+validate
    "sanity_fail",          # failed deterministic checks
    "pending_revalidate",   # passed validation, awaiting revalidation
    "pass",                 # revalidated, ready to apply
    "fail",                 # LLM validation or revalidation failed
    "applied",              # fix written to disk
    "verified",             # post-apply re-scan came back clean
    "review",               # exhausted retries, needs manual fix
)


# ------------------------------------------------------------------
# Item data helpers
# ------------------------------------------------------------------


def new_item(
    *,
    source: str,
    item_key: str,
    file_path: str,
    original: str,
    status: str = "flagged",
) -> dict:
    """Create a fresh pipeline item dict."""
    return {
        "source": source,
        "item_key": item_key,
        "file_path": file_path,
        "status": status,
        "original": original,
        "corrected": None,
        "issues": [],
        "sanity_result": None,
        "validation_result": None,
        "retries": 0,
        "retry_feedback": [],
    }


# ------------------------------------------------------------------
# PipelineState: load / save / query
# ------------------------------------------------------------------


class PipelineState:
    """Manages the JSON state file for one pipeline run."""

    def __init__(self, pool: str, timestamp: str | None = None) -> None:
        self.pool = pool
        self.timestamp = timestamp or datetime.now().strftime(
            "%Y%m%d_%H%M%S",
        )
        _PIPELINE_DIR.mkdir(parents=True, exist_ok=True)
        self.path = _PIPELINE_DIR / f"{pool}_{self.timestamp}.json"
        self.items: dict[str, dict] = {}
        self.meta: dict = {
            "pool": pool,
            "created": self.timestamp,
            "model": "gpt-5.1",
            "total_input_tokens": 0,
            "total_output_tokens": 0,
        }

    # -- persistence --

    def save(self) -> Path:
        """Write state to disk and update the latest symlink."""
        data = {"meta": self.meta, "items": self.items}
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        _update_latest_symlink(self.pool, self.path)
        return self.path

    @classmethod
    def load(cls, path: Path) -> PipelineState:
        """Load state from an existing JSON file."""
        data = json.loads(path.read_text(encoding="utf-8"))
        meta = data.get("meta", {})
        state = cls(
            pool=meta.get("pool", "unknown"),
            timestamp=meta.get("created", ""),
        )
        state.path = path
        state.meta = meta
        state.items = data.get("items", {})
        return state

    @classmethod
    def load_latest(cls, pool: str) -> PipelineState | None:
        """Load the most recent state for a pool, or None."""
        link = _PIPELINE_DIR / f"latest_{pool}.json"
        if not link.exists():
            return None
        return cls.load(link.resolve())

    # -- item accessors --

    def set_item(self, key: str, item: dict) -> None:
        self.items[key] = item

    def get_item(self, key: str) -> dict | None:
        return self.items.get(key)

    def items_by_status(self, *statuses: str) -> list[tuple[str, dict]]:
        return [
            (k, v) for k, v in self.items.items()
            if v["status"] in statuses
        ]

    def add_tokens(self, tin: int, tout: int) -> None:
        self.meta["total_input_tokens"] += tin
        self.meta["total_output_tokens"] += tout

    # -- summary --

    def summary(self) -> dict[str, int]:
        """Count items by status."""
        counts: dict[str, int] = {}
        for item in self.items.values():
            s = item["status"]
            counts[s] = counts.get(s, 0) + 1
        return counts

    def print_summary(self) -> None:
        """Print a human-readable summary to stdout."""
        s = self.summary()
        total = len(self.items)
        tin = self.meta.get("total_input_tokens", 0)
        tout = self.meta.get("total_output_tokens", 0)
        cost = tin / 1e6 * 1.25 + tout / 1e6 * 10
        print(f"\n{'=' * 50}")
        print(f"Pipeline state: {self.pool} ({self.timestamp})")
        print(f"Total items: {total}")
        for status in STATUSES:
            n = s.get(status, 0)
            if n > 0:
                print(f"  {status:20s}: {n}")
        print(f"Tokens: {tin:,} in / {tout:,} out")
        print(f"Est. cost: ${cost:.2f}")
        print(f"State file: {self.path}")
        print("=" * 50)


# ------------------------------------------------------------------
# Populate state from scan results
# ------------------------------------------------------------------


def populate_from_scan(
    state: PipelineState,
    scan_results: list[dict],
    atoms: list[tuple[str, Path, list[dict]]],
    mcs: list[tuple[str, Path, str]],
    exs: list[tuple[str, Path, str]],
    vas: list[tuple[str, Path, str]],
) -> None:
    """Convert raw scan results into tracked state items.

    Scan-only results have ``issues`` but no ``corrected`` content.
    Items are created with ``flagged`` status.
    """
    atoms_map = {aid: (p, items) for aid, p, items in atoms}
    single_orig: dict[str, str] = {}
    single_path: dict[str, str] = {}
    for aid, p, html in mcs:
        single_orig[f"mini-class:{aid}"] = html
        single_path[f"mini-class:{aid}"] = str(p)
    for label, p, xml in exs:
        single_orig[f"exemplar:{label}"] = xml
        single_path[f"exemplar:{label}"] = str(p)
    for label, p, xml in vas:
        single_orig[f"variant:{label}"] = xml
        single_path[f"variant:{label}"] = str(p)

    total_ok = total_errors = 0
    for r in scan_results:
        state.add_tokens(
            r.get("input_tokens", 0), r.get("output_tokens", 0),
        )
        if r.get("error"):
            total_errors += 1
            continue
        if not r["has_issues"]:
            total_ok += 1
            continue
        src, iid = r["source"], r["item_id"]
        if src == "question":
            _populate_question_items(state, r, atoms_map)
        else:
            key = f"{src}:{iid}"
            si = new_item(
                source=src, item_key=key,
                file_path=single_path.get(key, ""),
                original=single_orig.get(key, ""),
            )
            si["issues"] = r["issues"]
            state.set_item(key, si)

    state.meta["total_scanned"] = len(scan_results)
    state.meta["total_ok"] = total_ok
    state.meta["total_errors"] = total_errors


def _populate_question_items(
    state: PipelineState,
    r: dict,
    atoms_map: dict[str, tuple[Path, list[dict]]],
) -> None:
    """Expand a batch scan result into per-question state items.

    Scan-only results have ``flagged_items`` with issues but no
    corrected XML. Items are created with ``flagged`` status.
    """
    aid = r["item_id"]
    if aid not in atoms_map:
        return
    p9_path, atom_items = atoms_map[aid]
    item_map = {it["item_id"]: it for it in atom_items}
    for fi in r["flagged_items"]:
        qid = fi.get("item_id", "")
        orig_item = item_map.get(qid)
        if not orig_item:
            continue
        key = f"q:{aid}:{qid}"
        si = new_item(
            source="question", item_key=key,
            file_path=str(p9_path),
            original=orig_item.get("qti_xml", ""),
        )
        si["issues"] = fi.get("issues", [])
        si["atom_id"] = aid
        si["question_id"] = qid
        state.set_item(key, si)


# ------------------------------------------------------------------
# Review queue export
# ------------------------------------------------------------------


def export_review_queue(state: PipelineState) -> Path | None:
    """Write a review queue JSON for items stuck in fail/review."""
    reviewable = state.items_by_status("fail", "review", "sanity_fail")
    if not reviewable:
        print("No items need manual review.")
        return None

    entries: list[dict] = []
    for key, item in reviewable:
        diff = _unified_diff(
            item.get("original", ""),
            item.get("corrected", ""),
            key,
        )
        entries.append({
            "item_key": key,
            "file_path": item.get("file_path", ""),
            "status": item["status"],
            "retries": item.get("retries", 0),
            "issues": item.get("issues", []),
            "sanity_reasons": (
                item.get("sanity_result", {}) or {}
            ).get("reasons", []),
            "validation_reasons": (
                item.get("validation_result", {}) or {}
            ).get("reasons", []),
            "retry_feedback": item.get("retry_feedback", []),
            "diff": diff,
        })

    out_path = _PIPELINE_DIR / f"review_queue_{state.pool}.json"
    out_path.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Review queue: {len(entries)} items -> {out_path}")
    _print_review_summary(entries)
    return out_path


def _print_review_summary(entries: list[dict]) -> None:
    """Print a concise summary of items needing review."""
    for e in entries:
        reasons = (
            e["sanity_reasons"]
            or e["validation_reasons"]
            or ["unknown"]
        )
        print(f"  [{e['status']}] {e['item_key']}")
        for r in reasons:
            print(f"    - {r}")


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _unified_diff(
    original: str, corrected: str | None, label: str,
) -> str:
    """Generate a unified diff string."""
    if not corrected:
        return "(no corrected version available)"
    orig_lines = original.splitlines(keepends=True)
    corr_lines = corrected.splitlines(keepends=True)
    diff = difflib.unified_diff(
        orig_lines, corr_lines,
        fromfile=f"original/{label}",
        tofile=f"corrected/{label}",
        n=3,
    )
    return "".join(diff) or "(no differences)"


def _update_latest_symlink(pool: str, target: Path) -> None:
    """Create/update the latest_{pool}.json symlink."""
    link = _PIPELINE_DIR / f"latest_{pool}.json"
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(target.resolve())
