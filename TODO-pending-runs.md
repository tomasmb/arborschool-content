# Pending Pipeline Runs

## Required environment

All API keys must be set in `.env` at repo root:

- `OPENAI_API_KEY` — used by both pipelines (text + image validation)
- `GEMINI_API_KEY` — primary key for Gemini image generation
- `FALLBACK_GEMINI_API_KEY`, `FALLBACK_GEMINI_API_KEY_2`,
  `FALLBACK_GEMINI_API_KEY_3` — rotated automatically when primary hits quota

---

## 1. Variant images — ~103 remaining (Gemini quota hit)

Three tests still have variants with placeholder images (`requiere_nueva_imagen.png`).
Gemini Image daily quota (250/key) was exhausted across all 4 keys.

**Quota resets:** ~6:00 PM Chile time on March 31, 2026.

| Test | Failed | Total |
|------|--------|-------|
| prueba-invierno-2026 | 82 | 531 |
| prueba-invierno-2025 | 18 | 545 |
| seleccion-regular-2025 | 3 | 443 |

**How to run** (from repo root, inside `.venv`):

```bash
source .venv/bin/activate

# Run all 3 in parallel (each resumes automatically — skips already-done variants)
python -m app.question_variants.generate_variant_images \
  --test "prueba-invierno-2026" --all-approved --workers 3 &
python -m app.question_variants.generate_variant_images \
  --test "prueba-invierno-2025" --all-approved --workers 3 &
python -m app.question_variants.generate_variant_images \
  --test "seleccion-regular-2025" --all-approved --workers 3 &
wait
```

**How it works:** For each variant XML, the pipeline checks if `src` already
points to S3. If so, it skips (idempotent). Only placeholders are processed.
Flow: OpenAI expands alt text → Gemini generates image → GPT-5.1 validates
→ upload to S3 → update XML with S3 URL.

**How to verify** (should return 0 when done):

```bash
grep -rl "requiere_nueva_imagen" app/data/pruebas/hard_variants/ | wc -l
```

**After success:** Run `/git-commit` (follows `.cursor/commands/git-commit.md`).
Stage **all** changes — both code (`.py`) and data (`.xml`, `.json`) files.

---

## Commit protocol

After each pipeline completes, use `/git-commit` which follows the full
code-review protocol in `.cursor/commands/git-commit.md`. Key points:

- **Stage everything** (`git add .`) — data files (XML, JSON) AND any
  code changes (`.py`) should be committed together.
- Code review checks only apply to `.py` files (skip `.xml`, `.json`, `.md`).
- The commit message should describe what the pipeline produced
  (e.g., "generate remaining variant images").
- Push automatically after commit.

*Delete this file once the variant images pipeline is complete.*
