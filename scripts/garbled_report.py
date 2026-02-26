"""Generate a report of questions with garbled accented characters."""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

QG_ROOT = Path("app/data/question-generation")
REPORT_PATH = QG_ROOT / "garbled_questions_report.txt"

_PATTERNS: list[str] = [
    # ¿ corrupted forms
    "bfCue1l", "bfcue1l", "bfCue1ntas", "bfcue1ntas",
    "bfcue1les", "0bfcu01l", "0bfcu0e1l", "0bfcu03l",
    "0bCu03l", "bf00Cue100l", "00Cu03l", "bbfCue1ntos",
    "BFcuE1l", "bcue1l", "bfEn", r"bfque9",
    # -ción/-sión with f3/03
    "funcif3n", "funci03n",
    "relacif3n", "relaci03n", "relaci53n",
    "ecuacif3n", "ecuaci03n",
    "expresif3n", "expresi03n",
    "proporcif3n", "proporci03n", "porcif3n",
    "solucif3n", "soluci03n",
    "posicif3n", "posici03n",
    "evolucif3n", "evoluci93n",
    "sustitucif3n", "itucif3n",
    "conclusif3n", "clusif3n",
    "inecuacif3n", "inecuaci03n",
    "condicif3n", "ndicif3n",
    "situacif3n", "situaci03n",
    "fraccif3n", "representacif3n",
    "informacif3n", "rmacif3n",
    "precisif3n", "ecisif3n",
    "dispersif3n", "persif3n",
    "factorizacif3n", "ntacif3n",
    "minuci03on", "bitacif3n", "bitaci03n",
    "Funcif3n", "Conclusif3n", "Cif3mo",
    "cuacif3n", "olucif3n", "osicif3n",
    "elacif3n", "seccif3n", "tuacif3n",
    # ó in common words
    "cb3mo", "c03mo", "c0f3mo",
    "n0dmero", "n03mero", "nf3mero", "n0famero",
    "gr01fico", "gr03fico", "gre1fico",
    "gr0303fico", "gr0e1fico", "gr5ffico",
    "gr03afico", "gr1fico",
    "patrf3n", "garzf3n", "cajf3n",
    "automf3vil",
    "Seg03n", "Seg01n",
    "Adem03s", "AdemE1s", "ademe1s",
    "Despue9s", "despue9s",
    "Tendre1n",
    # á in common words
    "var0da", "var01a", "var03a",
    "seg0dn",
    "cuadre1tic", "cuadre1ticas", "cuadre1tico",
    "Mateme1tica", "matemE1tica",
    "Matem03ticas", "Matem3tica",
    "categor01a", "ategor01a",
    "autome1tico",
    "aritme9tica", "aritm03tica", "aritm7tica",
    "deber0da", "deber31a",
    "le1pices",
    # misc
    "me9todo", "Tome1s", "tamaf1os",
    "cu03ntas", "cu01ntas", "contin03an",
    "Me1ximo", "m5nimo", "m5ximo",
    "mednimo", "fanica",
    "ldneas", "l0dneas",
    "pa0eds", "a03os",
    "03pidamente", "r03pidamente",
    "00Seg03n",
]

GARBLED_RE = re.compile("|".join(re.escape(p) for p in _PATTERNS))


def scan() -> None:
    results: list[tuple[str, list[str]]] = []
    total = 0

    for ckpt in sorted(QG_ROOT.glob(
        "*/checkpoints/phase_9_final_validation.json",
    )):
        data = json.loads(ckpt.read_text(encoding="utf-8"))
        for item in data.get("items", []):
            xml = item.get("qti_xml", "")
            if not xml:
                continue
            total += 1
            item_id = item.get("item_id", "?")
            matches = GARBLED_RE.findall(xml)
            if matches:
                results.append((item_id, sorted(set(matches))))

    atom_counts = Counter(
        r[0].rsplit("_", 1)[0] for r in results
    )

    lines = [
        "# Garbled Character Report",
        "# Generated: 2026-02-26",
        f"# Total questions scanned: {total}",
        f"# Garbled questions found: {len(results)}",
        f"# Clean questions: {total - len(results)}",
        f"# Percentage garbled: {len(results)/total*100:.1f}%",
        f"# Affected atoms: {len(atom_counts)} / 205",
        "#",
        "# Root cause: LLM occasionally emits corrupted UTF-8",
        "# for accented characters during generation.",
        "# Common corruptions:",
        "#   ¿Cuál → bfCue1l      ó → f3/03/b3",
        "#   á     → 01/e1        í/ú → 0d",
        "#   é     → e9           gráfico → gre1fico",
        "#   función → funcif3n",
        "#",
        "# Fix: regenerate these questions through the pipeline.",
        "",
    ]

    current_atom = None
    for item_id, matches in sorted(results):
        atom = item_id.rsplit("_", 1)[0]
        if atom != current_atom:
            current_atom = atom
            n = atom_counts[atom]
            lines.append(f"\n## {atom} ({n} questions)")
        lines.append(f"{item_id}\t{', '.join(matches)}")

    lines.append("")
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {len(results)} garbled questions to {REPORT_PATH}")
    print(f"Total: {total}, Garbled: {len(results)}")
    print(f"({len(results)/total*100:.1f}%)")


if __name__ == "__main__":
    scan()
