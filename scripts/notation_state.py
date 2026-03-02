"""Persistent state management for the notation scan pipeline.

Tracks every scanned item through its lifecycle:
  ok              -> no issues found
  flagged         -> issues detected by scan (Pass 1, low reasoning)
  confirmed       -> issues validated by confirm pass (Pass 2, medium)
  false_positive  -> all flagged issues rejected as false positives
  fix_ok          -> fix applied and validated (sanity + re-scan)
  fix_fail        -> fix failed validation (sanity or re-scan)
  review          -> needs manual inspection

State is saved to JSON after every phase so the pipeline
can resume from crashes.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_PIPELINE_DIR = Path("app/data/.notation_pipeline")

STATUSES = (
    "ok",
    "flagged",
    "confirmed",
    "false_positive",
    "fix_ok",
    "fix_fail",
    "review",
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
        "issues": [],
        "confirmed_issues": [],
        "rejected_issues": [],
    }


# ------------------------------------------------------------------
# PipelineState: load / save / query
# ------------------------------------------------------------------


class PipelineState:
    """Manages the JSON state file for one pipeline run."""

    def __init__(
        self, pool: str, timestamp: str | None = None,
    ) -> None:
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

    def items_by_status(
        self, *statuses: str,
    ) -> list[tuple[str, dict]]:
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

    def category_summary(self) -> dict[str, int]:
        """Count confirmed issues by fix category."""
        counts: dict[str, int] = {}
        for item in self.items.values():
            for ci in item.get("confirmed_issues", []):
                cat = ci.get("category", "unknown")
                counts[cat] = counts.get(cat, 0) + 1
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
        cats = self.category_summary()
        if cats:
            print("\nConfirmed issues by category:")
            for cat, n in sorted(
                cats.items(), key=lambda x: -x[1],
            ):
                print(f"  {cat:35s}: {n}")
        print(f"\nTokens: {tin:,} in / {tout:,} out")
        print(f"Est. cost: ${cost:.2f}")
        print(f"State file: {self.path}")
        print("=" * 50)


# ------------------------------------------------------------------
# Populate state from scan results
# ------------------------------------------------------------------

# ScanItem: (key, source, file_path, content, label)
ScanItem = tuple[str, str, str, str, str]


def populate_from_scan(
    state: PipelineState,
    items: list[ScanItem],
    results: list[dict],
) -> None:
    """Convert scan results into tracked state items.

    Each result maps 1:1 to an input item. Items with issues
    get ``flagged`` status; clean items are counted as ok.
    """
    content_map = {
        key: (source, fp, content)
        for key, source, fp, content, _ in items
    }
    total_ok = total_errors = 0
    for r in results:
        state.add_tokens(
            r.get("input_tokens", 0),
            r.get("output_tokens", 0),
        )
        if r.get("error"):
            total_errors += 1
            continue
        if not r["has_issues"]:
            total_ok += 1
            continue
        key = r["key"]
        source, fp, content = content_map[key]
        si = new_item(
            source=source, item_key=key,
            file_path=fp, original=content,
        )
        si["issues"] = r["issues"]
        state.set_item(key, si)

    state.meta["total_scanned"] = len(results)
    state.meta["total_ok"] = total_ok
    state.meta["total_errors"] = total_errors


# ------------------------------------------------------------------
# Export helpers
# ------------------------------------------------------------------


def export_review_queue(state: PipelineState) -> Path | None:
    """Write a review queue JSON for items needing manual review."""
    reviewable = state.items_by_status("review")
    if not reviewable:
        print("No items need manual review.")
        return None

    entries: list[dict] = []
    for key, item in reviewable:
        entries.append({
            "item_key": key,
            "file_path": item.get("file_path", ""),
            "issues": item.get("issues", []),
            "confirmed_issues": item.get("confirmed_issues", []),
        })

    out_path = _PIPELINE_DIR / f"review_queue_{state.pool}.json"
    out_path.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Review queue: {len(entries)} items -> {out_path}")
    return out_path


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _update_latest_symlink(pool: str, target: Path) -> None:
    """Create/update the latest_{pool}.json symlink."""
    link = _PIPELINE_DIR / f"latest_{pool}.json"
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(target.resolve())
