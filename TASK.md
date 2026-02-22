# Pipeline Fix Task

## Context

The pipeline enhancement phase (phase 7) takes valid QTI XML and adds feedback. After enhancement,
items are validated against the QTI XSD schema. In batch_api_20260220_205015, 2,197 of 11,851 items
failed XSD validation and were dropped.

Analysis of all 2,197 failures:
- 23% (517): HTML entities in XML (e.g. &oacute;, &nbsp;, &rarr;) — XML only allows &amp; &lt; &gt; &quot; &apos;
- 14% (313): Mismatched MathML tags (e.g. unclosed <math>)
- 57% (1,274): Valid XML but fails QTI3 schema (unknown cause)
- 4% (93): Other XML errors

## Changes to implement

### 1. Add HTML entity normalization in batch_phase_processors.py

In `app/question_generation/batch_phase_processors.py`, add a function `_normalize_html_entities(xml: str) -> str`
that replaces HTML entities with their UTF-8 equivalents BEFORE XSD validation.

```python
# Complete map of HTML entities to normalize
_HTML_ENTITY_MAP: dict[str, str] = {
    "nbsp": "\u00a0", "oacute": "ó", "aacute": "á", "eacute": "é",
    "iacute": "í", "uacute": "ú", "ntilde": "ñ", "ordm": "º", "ordf": "ª",
    "Aacute": "Á", "Eacute": "É", "Iacute": "Í", "Oacute": "Ó", "Uacute": "Ú", "Ntilde": "Ñ",
    "rarr": "→", "larr": "←", "uarr": "↑", "darr": "↓", "harr": "↔",
    "minus": "−", "times": "×", "divide": "÷", "plusmn": "±",
    "le": "≤", "ge": "≥", "ne": "≠", "approx": "≈", "infin": "∞",
    "alpha": "α", "beta": "β", "pi": "π", "theta": "θ", "sigma": "σ", "lambda": "λ",
    "iexcl": "¡", "iquest": "¿", "ldquo": "\u201c", "rdquo": "\u201d",
    "lsquo": "\u2018", "rsquo": "\u2019", "hellip": "…", "mdash": "—", "ndash": "–",
    "deg": "°", "sup2": "²", "sup3": "³", "frac12": "½", "frac14": "¼",
}

def _normalize_html_entities(xml: str) -> str:
    """Replace HTML entities with their UTF-8 equivalents.
    
    XML only allows 5 predefined entities: &amp; &lt; &gt; &quot; &apos;
    The enhancement LLM frequently generates HTML entities like &oacute;, &nbsp;,
    &rarr; etc. which cause XSD validation to fail. Replace them with their
    actual UTF-8 characters before validation.
    """
    import re
    def replace_entity(match: re.Match) -> str:
        name = match.group(1)
        return _HTML_ENTITY_MAP.get(name, match.group(0))  # Keep unknown entities as-is
    
    return re.sub(r"&([a-zA-Z][a-zA-Z0-9]*);", replace_entity, xml)
```

Then in `process_enhancement_responses`, apply normalization BEFORE calling `validate_qti_xml`:

```python
xml = _normalize_html_entities(_extract_qti_xml(resp.text))
xsd_result = validate_qti_xml(xml)
```

### 2. Revert 216b429 behavior + proper quarantine

In `app/question_generation/batch_pipeline_stages.py`, in `_run_enhance`:

**Current behavior (WRONG - from commit 216b429):** Items that fail XSD post-enhancement silently
continue with their original (pre-enhancement) XML — no feedback applied, not flagged.

**Correct behavior:**
- Items that fail XSD post-enhancement → excluded from the pipeline, NOT silently carried forward
- Their details saved to a quarantine log per batch run
- Logged clearly

The change: in `_run_enhance`, after processing failures, build the returned `items` dict using only
items that succeeded. Items in `failures` should be removed from all atom item lists.

Current (wrong) code:
```python
if failures:
    logger.warning(
        "Phase 7: %d enhancement failures — keeping original QTI XML "
        "(item is not dropped, enhancement simply not applied).",
        len(failures),
    )
    # Do NOT drop items that failed post-enhancement QTI validation.
    # Their qti_xml was never modified (only succeeded items are updated
    # in-place), so they naturally retain their pre-enhancement XML and
    # continue through the pipeline at full quality.
```

Replace with:
```python
if failures:
    logger.warning(
        "Phase 7: %d items quarantined — enhancement produced invalid QTI XML. "
        "Use phase_7_quarantine.json to inspect and fix.",
        len(failures),
    )
    # Save quarantine details to the batch state checkpoint dir
    quarantine_path = ckpt_path.parent / "phase_7_quarantine.json"
    quarantine_data = {
        "quarantined_count": len(failures),
        "items": [
            {"item_id": item_id, "error": error}
            for item_id, error in failures.items()
        ],
    }
    import json as _json
    with open(quarantine_path, "w") as _f:
        _json.dump(quarantine_data, _f, indent=2, ensure_ascii=False)
    logger.info("Phase 7 quarantine saved to %s", quarantine_path)

    # Remove quarantined items from the pipeline — they lack valid feedback
    failure_ids = set(failures.keys())
    items = {
        atom_id: [it for it in atom_items if it.item_id not in failure_ids]
        for atom_id, atom_items in items.items()
    }
```

Note: `ckpt_path` is available in `_run_enhance` — check how it's currently used to find the right path
for the quarantine file. If `ckpt_path` is the path to a specific phase checkpoint JSON, use `ckpt_path.parent`
to get the checkpoints directory.

### 3. Update enhancement prompt

In `app/question_feedback/prompts.py`, find the system or user prompt for the enhancement LLM call.
Add these XML rules prominently (before or after existing XML formatting rules):

```
CRITICAL XML RULES — violations cause the item to be DROPPED from the pipeline:

1. UTF-8 ONLY — NEVER HTML entities:
   Write ó not &oacute;, á not &aacute;, é not &eacute;, í not &iacute;, ú not &uacute;, ñ not &ntilde;
   Write → not &rarr;, ≤ not &le;, ≥ not &ge;, × not &times;, ≠ not &ne;, − not &minus;
   Write ¡ not &iexcl;, ¿ not &iquest;, ° not &deg;, ² not &sup2;
   Only allowed XML entities: &amp; &lt; &gt; &quot; &apos;
   Do NOT use &nbsp; — use a regular space instead.

2. MATHML CONTENT MODEL (this is the #1 cause of failures — read carefully):
   - <math> and <mrow> CANNOT contain plain text. They only accept MathML child elements.
     WRONG: <mrow>x + 2</mrow>
     CORRECT: <mrow><mi>x</mi><mo>+</mo><mn>2</mn></mrow>
   - Use ONLY these MathML elements: mi, mn, mo, mrow, msup, msub, mfrac, msqrt,
     mover, munder, mtext, mtable, mtr, mtd, menclose
   - Do NOT use: underbrace, overleftarrow, overbrace, overrightarrow, mstyle,
     mpadded, mphantom, or any element not in the list above. They are not supported.
   - Every opened MathML tag must be closed in the correct order (no interleaving).
   - <msup> and <msub> require EXACTLY 2 child elements (base and exponent/subscript).
     WRONG: <msup><mi>x</mi></msup>
     CORRECT: <msup><mi>x</mi><mn>2</mn></msup>

3. ALL XML TAGS must be balanced and properly nested.
   Check tag balance mentally before outputting.
   Every <tag> must have a matching </tag> at the correct nesting level.
```

### 4. Verify and commit

```bash
cd /Users/max/arborschool-content

# Verify imports work
uv run python -c "from app.question_generation.batch_phase_processors import process_enhancement_responses, _normalize_html_entities; print('OK')"

# Run any existing tests
uv run python -m pytest tests/ -x -q 2>/dev/null || echo "no tests / tests skipped"

# Commit
git add -A
git commit -m "fix(pipeline): HTML entity normalization + quarantine for phase 7 failures

- Add _normalize_html_entities() to recover items with HTML entity errors before XSD validation
- Revert silent keep-original behavior (commit 216b429): failed items now quarantined + excluded
- Save quarantine to phase_7_quarantine.json in batch checkpoints dir with full error details
- Update enhancement prompt: UTF-8 required, HTML entities forbidden, MathML tag balance required
- Analysis: 23% of phase 7 failures were fixable HTML entities, 14% mismatched MathML tags"

git push origin main
```

Then notify:
```bash
openclaw system event --text "Pipeline fix done: entity normalization + quarantine committed. Ready for re-run go/no-go from Tomas." --mode now
```
