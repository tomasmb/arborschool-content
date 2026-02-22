"""
Run QTI validator on all 2,197 items that failed phase 7 XSD validation.
Groups errors by type, generates actionable report.
"""
import json
import pathlib
import re
import time
import concurrent.futures
from collections import Counter, defaultdict
from typing import Optional

import requests

BATCH_DIR = pathlib.Path("app/data/question-generation/.batch_runs/batch_api_20260220_205015")
VALIDATOR_URL = "http://qti-validator-prod.eba-dvye2j6j.us-east-2.elasticbeanstalk.com/validate?schema=qti3"
OUTPUT_PATH = pathlib.Path("app/data/question-generation/phase7_failure_analysis.json")
MAX_WORKERS = 12  # parallel requests


def extract_item_id(custom_id: str) -> str:
    parts = custom_id.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def extract_atom_id(custom_id: str) -> str:
    parts = custom_id.split(":")
    return parts[-2] if len(parts) >= 3 else ""


def extract_qti_xml(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)
    if "<qti-assessment-item" in cleaned:
        start = cleaned.index("<qti-assessment-item")
        end_tag = "</qti-assessment-item>"
        if end_tag in cleaned:
            end = cleaned.rindex(end_tag) + len(end_tag)
            cleaned = cleaned[start:end]
    # Strip control chars
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", cleaned)
    return cleaned.strip()


def validate_xml(xml: str) -> dict:
    """Call the QTI validator. Returns {'valid': bool, 'errors': [...]}"""
    try:
        resp = requests.post(
            VALIDATOR_URL,
            data=xml.encode("utf-8", errors="replace"),
            headers={"Content-Type": "application/xml"},
            timeout=20,
        )
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 422:
            try:
                return resp.json()
            except Exception:
                return {"valid": False, "errors": [{"message": f"HTTP 422: {resp.text[:200]}"}]}
        else:
            return {"valid": False, "errors": [{"message": f"HTTP {resp.status_code}"}]}
    except requests.Timeout:
        return {"valid": False, "errors": [{"message": "timeout"}]}
    except Exception as e:
        return {"valid": False, "errors": [{"message": f"request_error: {e}"}]}


def categorize_error(errors: list[dict]) -> str:
    """Normalize error message to a category."""
    if not errors:
        return "unknown"
    msg = errors[0].get("message", "")
    # Normalize
    if "must be terminated" in msg or "end-tag" in msg or "mismatched tag" in msg:
        return "mismatched_tag"
    if "undefined entity" in msg or "entity" in msg.lower():
        entity = re.search(r'entity\s+"?&?(\w+)', msg)
        return f"entity_{entity.group(1)}" if entity else "undefined_entity"
    if "not well-formed" in msg or "invalid token" in msg or "illegal" in msg.lower():
        return "malformed_xml"
    if "is not allowed" in msg and "element" in msg.lower():
        # Extract element name
        el = re.search(r'element "([^"]+)"', msg)
        return f"invalid_element_{el.group(1)}" if el else "invalid_element"
    if "attribute" in msg.lower() and ("not allowed" in msg or "invalid" in msg.lower()):
        attr = re.search(r'attribute "([^"]+)"', msg)
        return f"invalid_attr_{attr.group(1)}" if attr else "invalid_attribute"
    if "content model" in msg.lower() or "unexpected" in msg.lower():
        return "content_model_violation"
    if "timeout" in msg:
        return "timeout"
    # Truncate long messages
    return msg[:80]


def process_item(item_data: dict) -> dict:
    """Validate one item, return result."""
    item_id = item_data["item_id"]
    atom_id = item_data["atom_id"]
    xml = item_data["xml"]
    result = validate_xml(xml)
    errors = result.get("errors", [])
    category = categorize_error(errors)
    return {
        "item_id": item_id,
        "atom_id": atom_id,
        "valid": result.get("valid", False),
        "category": category,
        "errors": errors[:3],  # keep first 3 errors
    }


def main():
    print("Loading phase 7 results...")

    # Get items that went to review (passed XSD)
    review_ids: set[str] = set()
    with open(BATCH_DIR / "phase_78_review_input.jsonl") as f:
        for line in f:
            if line.strip():
                d = json.loads(line)
                review_ids.add(extract_item_id(d.get("custom_id", "")))

    # Collect failed items
    failed_items = []
    with open(BATCH_DIR / "phase_78_enhance_results.jsonl") as f:
        for line in f:
            if not line.strip():
                continue
            d = json.loads(line)
            item_id = extract_item_id(d.get("custom_id", ""))
            if item_id in review_ids:
                continue
            atom_id = extract_atom_id(d.get("custom_id", ""))
            body = d.get("response", {}).get("body", {})
            content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
            xml = extract_qti_xml(content)
            failed_items.append({"item_id": item_id, "atom_id": atom_id, "xml": xml})

    total = len(failed_items)
    print(f"Found {total} failed items. Running validator with {MAX_WORKERS} workers...")
    print("(This will take ~3-5 minutes)")

    results = []
    done = 0
    start = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_item, item): item for item in failed_items}
        for future in concurrent.futures.as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                item = futures[future]
                results.append({
                    "item_id": item["item_id"],
                    "atom_id": item["atom_id"],
                    "valid": False,
                    "category": f"exception_{e}",
                    "errors": [],
                })
            done += 1
            if done % 100 == 0:
                elapsed = time.time() - start
                rate = done / elapsed
                remaining = (total - done) / rate
                print(f"  {done}/{total} validated ({rate:.1f}/s, ~{remaining:.0f}s remaining)")

    elapsed = time.time() - start
    print(f"\nDone in {elapsed:.0f}s. Analyzing results...")

    # Group by category
    by_category = Counter(r["category"] for r in results)
    by_atom: dict[str, dict] = defaultdict(lambda: {"total": 0, "categories": Counter()})
    for r in results:
        by_atom[r["atom_id"]]["total"] += 1
        by_atom[r["atom_id"]]["categories"][r["category"]] += 1

    # Fixability assessment
    FIXABLE_BY_POST_PROCESSING = {  # Can fix without re-run
        "mismatched_tag", "malformed_xml",
    }
    FIXABLE_BY_ENTITY_NORMALIZATION = {  # HTML entity fix
        c for c in by_category if c.startswith("entity_") or c == "undefined_entity"
    }
    FIXABLE_BY_PROMPT = {  # Needs prompt improvement + re-run
        "content_model_violation", "invalid_element", "invalid_attribute",
    } | {c for c in by_category if c.startswith("invalid_element_") or c.startswith("invalid_attr_")}

    fixable_entity = sum(by_category[c] for c in FIXABLE_BY_ENTITY_NORMALIZATION)
    fixable_prompt = sum(by_category[c] for c in FIXABLE_BY_PROMPT)
    timeout_count = by_category.get("timeout", 0)
    unknown = by_category.get("unknown", 0)

    print("\n=== PHASE 7 FAILURE ANALYSIS ===")
    print(f"\nTotal failed: {total}")
    print(f"\nTop error categories:")
    for cat, count in by_category.most_common(20):
        pct = 100 * count // total
        print(f"  [{count:4d} / {pct:2d}%] {cat}")

    print(f"\nFixability summary:")
    print(f"  HTML entity normalization (post-process fix): {fixable_entity} items")
    print(f"  Prompt improvement (re-run needed): {fixable_prompt} items")
    print(f"  Timeouts (need retry): {timeout_count} items")
    print(f"  Unknown/other: {total - fixable_entity - fixable_prompt - timeout_count} items")

    # Save full report
    report = {
        "total_failed": total,
        "runtime_seconds": elapsed,
        "by_category": dict(by_category.most_common()),
        "fixable_entity_normalization": fixable_entity,
        "fixable_by_prompt": fixable_prompt,
        "timeouts": timeout_count,
        "items": results,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nFull report saved to: {OUTPUT_PATH}")
    print("\nDone. Share results with Tomás.")


if __name__ == "__main__":
    main()
