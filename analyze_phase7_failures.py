"""Analyze why 2,197 items failed XSD validation after phase 7 enhancement."""
import json
import pathlib
from app.question_generation.validation_checks import validate_qti_xml

batch_dir = pathlib.Path('app/data/question-generation/.batch_runs/batch_api_20260220_205015')

def extract_item_id(custom_id):
    parts = custom_id.split(':')
    return parts[-1] if len(parts) >= 3 else ''

def extract_qti_xml(text):
    cleaned = text.strip()
    if cleaned.startswith('```'):
        lines = cleaned.split('\n')[1:]
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        cleaned = '\n'.join(lines)
    if '<qti-assessment-item' in cleaned:
        start = cleaned.index('<qti-assessment-item')
        end_tag = '</qti-assessment-item>'
        end = cleaned.rindex(end_tag) + len(end_tag)
        cleaned = cleaned[start:end]
    return cleaned.strip()

# Get dropped IDs (enhanced but not in review)
review_ids = set()
with open(batch_dir / 'phase_78_review_input.jsonl') as f:
    for line in f:
        if line.strip():
            d = json.loads(line)
            review_ids.add(extract_item_id(d.get('custom_id', '')))

error_patterns = {}
error_examples = {}
sample_checked = 0
no_xml = 0
total_dropped = 0

with open(batch_dir / 'phase_78_enhance_results.jsonl') as f:
    for line in f:
        if not line.strip():
            continue
        d = json.loads(line)
        item_id = extract_item_id(d.get('custom_id', ''))
        if item_id in review_ids:
            continue
        total_dropped += 1
        if sample_checked >= 200:
            continue
        try:
            body = d.get('response', {}).get('body', {})
            content = body.get('choices', [{}])[0].get('message', {}).get('content', '')
            xml = extract_qti_xml(content)
            if not xml:
                no_xml += 1
                continue
            result = validate_qti_xml(xml)
            err = str(result.get('validation_errors', 'unknown'))
            # Normalize: take first line and truncate
            lines = [l.strip() for l in err.split('\n') if l.strip()]
            first_err = lines[0][:150] if lines else 'empty error'
            error_patterns[first_err] = error_patterns.get(first_err, 0) + 1
            if first_err not in error_examples:
                error_examples[first_err] = {'item_id': item_id, 'full_error': err[:500]}
        except Exception as e:
            key = f'exception: {type(e).__name__}: {str(e)[:100]}'
            error_patterns[key] = error_patterns.get(key, 0) + 1
        sample_checked += 1

print(f'Total dropped at phase 7 XSD: {total_dropped}')
print(f'Sample analyzed: {sample_checked}')
print(f'No XML in response: {no_xml}')
print()
print('=== TOP ERROR PATTERNS ===')
for err, count in sorted(error_patterns.items(), key=lambda x: -x[1])[:15]:
    pct = 100 * count / max(sample_checked, 1)
    print(f'\n[{count}x / {pct:.0f}%] {err}')
    if err in error_examples:
        ex = error_examples[err]
        print(f'  Example item: {ex["item_id"]}')
        print(f'  Full error: {ex["full_error"][:300]}')
