#!/usr/bin/env python3
"""ARCHIVED 2026-03-02: Machine-specific local QA tool (hardcoded to
/Users/max/.openclaw/workspace). Not part of any pipeline.

Original description:
Granular low-cost QA over Phase 9 checkpoint items using local Ollama.

- Keeps persistent progress state
- Runs focused checks per item (question grammar + feedback A/B/C/D)
- Writes findings JSONL + summary markdown
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path('/Users/max/.openclaw/workspace')
CONTENT = ROOT / 'arborschool-content'
DATA_GLOB = 'app/data/question-generation/*/checkpoints/phase_9_final_validation.json'
REPORT_DIR = ROOT / 'reports' / 'validator'
STATE_PATH = REPORT_DIR / 'granular_state.json'
FINDINGS_PATH = REPORT_DIR / 'granular_findings.jsonl'


@dataclass
class ItemRef:
    atom: str
    item_id: str
    qti_xml: str


def strip_tags(x: str) -> str:
    x = re.sub(r'<[^>]+>', ' ', x)
    x = re.sub(r'\s+', ' ', x)
    return x.strip()


def extract_question_text(xml: str) -> str:
    # try item prompt first, fallback first long text fragment
    m = re.search(r'<qti-item-prompt[^>]*>(.*?)</qti-item-prompt>', xml, flags=re.S)
    if m:
        return strip_tags(m.group(1))
    body = re.search(r'<qti-item-body[^>]*>(.*?)</qti-item-body>', xml, flags=re.S)
    if body:
        return strip_tags(body.group(1))[:1200]
    return strip_tags(xml)[:1200]


def extract_feedback(xml: str, option: str) -> str:
    # In this dataset, per-option feedback is usually embedded in qti-simple-choice.
    pat_choice = rf'<qti-simple-choice[^>]*identifier=["\']{option}["\'][^>]*>(.*?)</qti-simple-choice>'
    m = re.search(pat_choice, xml, flags=re.S)
    if m:
        return strip_tags(m.group(1))

    # fallback for other QTI encodings
    pat_modal = rf'<qti-modal-feedback[^>]*identifier=["\'](?:FEEDBACK_|feedback_){option}["\'][^>]*>(.*?)</qti-modal-feedback>'
    mm = re.search(pat_modal, xml, flags=re.S)
    return strip_tags(mm.group(1)) if mm else ''


def load_items(limit_atoms: Optional[int] = None) -> List[ItemRef]:
    items: List[ItemRef] = []
    files = sorted(CONTENT.glob(DATA_GLOB))
    if limit_atoms:
        files = files[:limit_atoms]
    for fp in files:
        atom = fp.parts[-3]
        try:
            data = json.loads(fp.read_text(encoding='utf-8'))
        except Exception:
            continue
        for it in data.get('items', []):
            item_id = it.get('item_id')
            qti_xml = it.get('qti_xml')
            if not item_id or not qti_xml:
                continue
            items.append(ItemRef(atom=atom, item_id=item_id, qti_xml=qti_xml))
    return items


def load_state() -> Dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding='utf-8'))
    return {'index': 0, 'processed': 0, 'flagged': 0, 'last_run': None}


def save_state(state: Dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')


def ollama_check(model: str, check_name: str, text: str, timeout: int) -> Tuple[bool, str, float]:
    if not text.strip():
        return True, 'empty_text_skip', 0.0

    prompt = (
        f"Eres QA académico de preguntas PAES. Evalúa SOLO este aspecto: {check_name}. "
        "Responde SOLO JSON con forma {\"ok\":true|false,\"issue\":\"...\",\"confidence\":0-1}. "
        "Marca ok=false solo si hay un problema concreto y verificable.\n\n"
        f"TEXTO:\n{text[:2500]}"
    )

    t0 = time.time()
    p = subprocess.run(
        ['ollama', 'run', model, prompt],
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    dt = time.time() - t0
    raw = (p.stdout or '').strip()
    if p.returncode != 0:
        return False, f'ollama_error: {(p.stderr or raw)[:200]}', 0.0

    m = re.search(r'\{.*\}', raw, flags=re.S)
    if not m:
        return False, f'non_json_response: {raw[:200]}', 0.0
    try:
        obj = json.loads(m.group(0))
    except Exception:
        return False, f'invalid_json: {raw[:200]}', 0.0

    ok = bool(obj.get('ok', True))
    issue = str(obj.get('issue', '')).strip()[:400]
    conf = float(obj.get('confidence', 0.0) or 0.0)
    return ok, issue or ('ok' if ok else 'issue_detected'), conf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--batch-size', type=int, default=3)
    ap.add_argument('--model', default='qwen2.5:14b')
    ap.add_argument('--timeout', type=int, default=90)
    ap.add_argument('--limit-atoms', type=int, default=None)
    args = ap.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    items = load_items(args.limit_atoms)
    if not items:
        print('No items found')
        return

    state = load_state()
    idx = int(state.get('index', 0)) % len(items)

    checks = [
        ('question_grammar', lambda it: extract_question_text(it.qti_xml)),
        ('feedback_A', lambda it: extract_feedback(it.qti_xml, 'A')),
        ('feedback_B', lambda it: extract_feedback(it.qti_xml, 'B')),
        ('feedback_C', lambda it: extract_feedback(it.qti_xml, 'C')),
        ('feedback_D', lambda it: extract_feedback(it.qti_xml, 'D')),
    ]

    run_records = []
    flagged = 0
    for _ in range(args.batch_size):
        it = items[idx % len(items)]
        idx += 1
        item_flags = []
        for name, fn in checks:
            text = fn(it)
            ok, issue, conf = ollama_check(args.model, name, text, args.timeout)
            rec = {
                'ts': int(time.time()),
                'atom': it.atom,
                'item_id': it.item_id,
                'check': name,
                'ok': ok,
                'issue': issue,
                'confidence': conf,
            }
            run_records.append(rec)
            if not ok:
                item_flags.append(rec)

        if item_flags:
            flagged += 1
            # confirmation pass to reduce false positives
            confirm = []
            for f in item_flags:
                src_text = dict(checks)[f['check']](it) if f['check'] in dict(checks) else ''
                ok2, issue2, conf2 = ollama_check(args.model, f['check'] + '_confirm', src_text, args.timeout)
                confirm.append({'check': f['check'], 'confirm_ok': ok2, 'confirm_issue': issue2, 'confirm_conf': conf2})
            run_records.append({'ts': int(time.time()), 'atom': it.atom, 'item_id': it.item_id, 'confirmation': confirm})

    with FINDINGS_PATH.open('a', encoding='utf-8') as f:
        for r in run_records:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    state['index'] = idx % len(items)
    state['processed'] = int(state.get('processed', 0)) + args.batch_size
    state['flagged'] = int(state.get('flagged', 0)) + flagged
    state['last_run'] = int(time.time())
    save_state(state)

    stamp = time.strftime('%Y-%m-%d-%H%M')
    report = REPORT_DIR / f'granular-{stamp}.md'
    report.write_text(
        '\n'.join([
            f'# Ollama Granular QA Run {stamp}',
            f'- Model: {args.model}',
            f'- Batch size: {args.batch_size}',
            f'- Items total: {len(items)}',
            f'- Items flagged this run: {flagged}',
            f'- Progress index: {state["index"]}/{len(items)}',
            f'- Cumulative processed: {state["processed"]}',
            f'- Cumulative flagged: {state["flagged"]}',
            f'- Findings file: {FINDINGS_PATH}',
        ]),
        encoding='utf-8',
    )

    print(str(report))


if __name__ == '__main__':
    main()
