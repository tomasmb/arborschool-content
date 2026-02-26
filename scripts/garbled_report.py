"""Generate a report of questions with garbled accented characters.

Detects two classes of corruption:
1. Hex-digit substitution: accented chars replaced by hex (e.g. funcif3n)
2. Stripped accents: accented chars removed entirely (e.g. grfico)
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

QG_ROOT = Path("app/data/question-generation")
REPORT_PATH = QG_ROOT / "garbled_questions_report.txt"

# --- Class 1: hex-digit substitution patterns ---
_HEX_PATTERNS: list[str] = [
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
    # misc garbled words
    "me9todo", "Tome1s", "tamaf1os",
    "cu03ntas", "cu01ntas", "contin03an",
    "Me1ximo", "m5nimo", "m5ximo",
    "mednimo", "fanica",
    "ldneas", "l0dneas",
    "pa0eds", "a03os",
    "03pidamente", "r03pidamente",
    "00Seg03n",
    # round 2: additional hex-garbled words
    "cart0dn", "per0dmetro", "0bfCu01l",
    "uni3n", "est01n",
    "im03genes", "dise03o", "Tambi03n",
    "c3f3mo", "var3b0a", "gr31fico", "l33nea",
    "af1o", "c9En",
    "bfen cue1l",
]

# Regex patterns needing raw regex syntax
_REGEX_HEX: list[str] = [
    r"\\u00[0-9a-fA-F]{2}",
]

_HEX_RE = re.compile(
    "|".join(re.escape(p) for p in _HEX_PATTERNS)
    + "|"
    + "|".join(_REGEX_HEX),
)

# --- Class 2: stripped accent patterns (whole word, case-insensitive) ---
_STRIPPED_WORDS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bpatrn\b", re.I), "patrón→patrn"),
    (re.compile(r"\bgrfico\b", re.I), "gráfico→grfico"),
    (re.compile(r"\bgrfica\b", re.I), "gráfica→grfica"),
    (re.compile(r"\bgrficas\b", re.I), "gráficas→grficas"),
    (re.compile(r"\bgrficos\b", re.I), "gráficos→grficos"),
    (re.compile(r"\blnea\b", re.I), "línea→lnea"),
    (re.compile(r"\breflexin\b", re.I), "reflexión→reflexin"),
    (re.compile(r"\bfuncin\b", re.I), "función→funcin"),
    (re.compile(r"\brelacin\b", re.I), "relación→relacin"),
    (re.compile(r"\becuacin\b", re.I), "ecuación→ecuacin"),
    (re.compile(r"\bsolucin\b", re.I), "solución→solucin"),
    (re.compile(r"\bexpresin\b", re.I), "expresión→expresin"),
    (re.compile(r"\bproporcin\b", re.I), "proporción→proporcin"),
    (re.compile(r"\binformacin\b", re.I), "información→informacin"),
    (re.compile(r"\bconclusin\b", re.I), "conclusión→conclusin"),
    (re.compile(r"\bsituacin\b", re.I), "situación→situacin"),
    (re.compile(r"\bnmero\b", re.I), "número→nmero"),
    (re.compile(r"\bcmo\b", re.I), "cómo→cmo"),
    (re.compile(r"\bsegn\b", re.I), "según→segn"),
    (re.compile(r"\badems\b", re.I), "además→adems"),
    (re.compile(r"\bcul\b", re.I), "cuál→cul"),
    (re.compile(r"\btambin\b", re.I), "también→tambin"),
    (re.compile(r"\bimgenes\b", re.I), "imágenes→imgenes"),
    (re.compile(r"\brazn\b", re.I), "razón→razn"),
    (re.compile(r"\brepresentacin\b", re.I), "representación→representacin"),
    (re.compile(r"\bvariacin\b", re.I), "variación→variacin"),
    (re.compile(r"\banlisis\b", re.I), "análisis→anlisis"),
    (re.compile(r"\boperacin\b", re.I), "operación→operacin"),
    (re.compile(r"\bdisminucin\b", re.I), "disminución→disminucin"),
    (re.compile(r"\bpoblacin\b", re.I), "población→poblacin"),
    (re.compile(r"\bmximo\b", re.I), "máximo→mximo"),
    (re.compile(r"\bltimo\b", re.I), "último→ltimo"),
    (re.compile(r"\bmnimo\b", re.I), "mínimo→mnimo"),
]


def _strip_non_text(xml: str) -> str:
    """Remove MathML/tags and decode entities to get visible text."""
    import html as _html
    text = re.sub(r"<math[^>]*>.*?</math>", " ", xml, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = _html.unescape(text)
    return re.sub(r"\s+", " ", text)


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

            # Class 1: hex-digit substitutions (search raw XML)
            hex_matches = _HEX_RE.findall(xml)

            # Class 2: stripped accents (search visible text only)
            text = _strip_non_text(xml)
            stripped_matches = [
                label for pat, label in _STRIPPED_WORDS
                if pat.search(text)
            ]

            all_matches = sorted(set(hex_matches + stripped_matches))
            if all_matches:
                results.append((item_id, all_matches))

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
        "#",
        "# Two corruption classes detected:",
        "#   1) Hex substitution: accented chars replaced by hex digits",
        "#      e.g. función → funcif3n, gráfico → gr01fico",
        "#   2) Stripped accents: accented chars removed entirely",
        "#      e.g. gráfico → grfico, según → segn",
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
