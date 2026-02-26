"""Generate a report of questions with garbled accented characters.

Detects five classes of corruption:
1. Hex-digit substitution: accented chars replaced by hex (funcif3n)
2. Char-deleted accents: accented chars removed entirely (grfico)
3. Tilde-stripped ñ→n: (tamaño→tamano, año→ano)
4. Accent→base substitution: á→a, é→e, etc. (gráfico→grafico)
   Only flagged when 3+ words are affected (systemic issue).
5. Double-encoded entities / literal unicode escapes
"""
from __future__ import annotations

import html as _html
import json
import re
from collections import Counter
from pathlib import Path

QG_ROOT = Path("app/data/question-generation")
REPORT_PATH = QG_ROOT / "garbled_questions_report.txt"

# ── Class 1: hex-digit substitution patterns ──────────────────
_HEX_PATTERNS: list[str] = [
    "bfCue1l", "bfcue1l", "bfCue1ntas", "bfcue1ntas",
    "bfcue1les", "0bfcu01l", "0bfcu0e1l", "0bfcu03l",
    "0bCu03l", "bf00Cue100l", "00Cu03l", "bbfCue1ntos",
    "BFcuE1l", "bcue1l", "bfEn", "bfque9",
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
    "cb3mo", "c03mo", "c0f3mo",
    "n0dmero", "n03mero", "nf3mero", "n0famero",
    "gr01fico", "gr03fico", "gre1fico",
    "gr0303fico", "gr0e1fico", "gr5ffico",
    "gr03afico", "gr1fico",
    "patrf3n", "garzf3n", "cajf3n",
    "automf3vil",
    "Seg03n", "Seg01n",
    "Adem03s", "AdemE1s", "ademe1s",
    "Despue9s", "despue9s", "Tendre1n",
    "var0da", "var01a", "var03a", "seg0dn",
    "cuadre1tic", "cuadre1ticas", "cuadre1tico",
    "Mateme1tica", "matemE1tica",
    "Matem03ticas", "Matem3tica",
    "categor01a", "ategor01a", "autome1tico",
    "aritme9tica", "aritm03tica", "aritm7tica",
    "deber0da", "deber31a", "le1pices",
    "me9todo", "Tome1s", "tamaf1os",
    "cu03ntas", "cu01ntas", "contin03an",
    "Me1ximo", "m5nimo", "m5ximo",
    "mednimo", "fanica",
    "ldneas", "l0dneas",
    "pa0eds", "a03os",
    "03pidamente", "r03pidamente", "00Seg03n",
    "cart0dn", "per0dmetro", "0bfCu01l",
    "uni3n", "est01n",
    "im03genes", "dise03o", "Tambi03n",
    "c3f3mo", "var3b0a", "gr31fico", "l33nea",
    "af1o", "c9En", "bfen cue1l",
]

_REGEX_HEX: list[str] = [
    r"\\u[0-9a-fA-F]{4}",
]

_HEX_RE = re.compile(
    "|".join(re.escape(p) for p in _HEX_PATTERNS)
    + "|"
    + "|".join(_REGEX_HEX),
)

# ── Class 2: char-deleted accents (entire char missing) ───────
_DELETED_WORDS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(p, re.I), label)
    for p, label in [
        (r"\bpatrn\b", "patrón→patrn"),
        (r"\bgrfico\b", "gráfico→grfico"),
        (r"\bgrfica\b", "gráfica→grfica"),
        (r"\bgrficas\b", "gráficas→grficas"),
        (r"\bgrficos\b", "gráficos→grficos"),
        (r"\blnea\b", "línea→lnea"),
        (r"\breflexin\b", "reflexión→reflexin"),
        (r"\bfuncin\b", "función→funcin"),
        (r"\brelacin\b", "relación→relacin"),
        (r"\becuacin\b", "ecuación→ecuacin"),
        (r"\bsolucin\b", "solución→solucin"),
        (r"\bexpresin\b", "expresión→expresin"),
        (r"\bproporcin\b", "proporción→proporcin"),
        (r"\binformacin\b", "información→informacin"),
        (r"\bconclusin\b", "conclusión→conclusin"),
        (r"\bsituacin\b", "situación→situacin"),
        (r"\bnmero\b", "número→nmero"),
        (r"\bcmo\b", "cómo→cmo"),
        (r"\bsegn\b", "según→segn"),
        (r"\badems\b", "además→adems"),
        (r"\bcul\b", "cuál→cul"),
        (r"\btambin\b", "también→tambin"),
        (r"\bimgenes\b", "imágenes→imgenes"),
        (r"\brazn\b", "razón→razn"),
        (r"\brepresentacin\b", "representación→representacin"),
        (r"\bvariacin\b", "variación→variacin"),
        (r"\banlisis\b", "análisis→anlisis"),
        (r"\boperacin\b", "operación→operacin"),
        (r"\bdisminucin\b", "disminución→disminucin"),
        (r"\bpoblacin\b", "población→poblacin"),
        (r"\bmximo\b", "máximo→mximo"),
        (r"\bltimo\b", "último→ltimo"),
        (r"\bmnimo\b", "mínimo→mnimo"),
        (r"\bmtodo\b", "método→mtodo"),
    ]
]

# ── Class 3: ñ → n (tilde stripped) ──────────────────────────
_TILDE_WORDS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(p, re.I), label)
    for p, label in [
        (r"\bano\b", "año→ano"), (r"\banos\b", "años→anos"),
        (r"\bnino\b", "niño→nino"), (r"\bninos\b", "niños→ninos"),
        (r"\bnina\b", "niña→nina"), (r"\bninas\b", "niñas→ninas"),
        (r"\bpequeno\b", "pequeño→pequeno"),
        (r"\bpequena\b", "pequeña→pequena"),
        (r"\btamano\b", "tamaño→tamano"),
        (r"\btamanos\b", "tamaños→tamanos"),
        (r"\bdiseno\b", "diseño→diseno"),
        (r"\bespanol\b", "español→espanol"),
        (r"\bsenal\b", "señal→senal"),
        (r"\bensenanza\b", "enseñanza→ensenanza"),
        (r"\bcompania\b", "compañía→compania"),
        (r"\bmontana\b", "montaña→montana"),
        (r"\bmanana\b", "mañana→manana"),
        (r"\bdueno\b", "dueño→dueno"),
        (r"\bsueno\b", "sueño→sueno"),
        (r"\botono\b", "otoño→otono"),
        (r"\bdano\b", "daño→dano"),
        (r"\bbano\b", "baño→bano"),
    ]
]

# ── Class 4: accent→base (á→a, é→e, …) — systemic only ──────
_ACCENT_PAIRS: list[tuple[re.Pattern[str], re.Pattern[str], str]] = [
    (re.compile(bad, re.I), re.compile(good, re.I), label)
    for bad, good, label in [
        (r"\bgrafico\b", r"\bgráfico\b", "gráfico→grafico"),
        (r"\bgrafica\b", r"\bgráfica\b", "gráfica→grafica"),
        (r"\bgraficos\b", r"\bgráficos\b", "gráficos→graficos"),
        (r"\bgraficas\b", r"\bgráficas\b", "gráficas→graficas"),
        (r"\bfuncion\b", r"\bfunción\b", "función→funcion"),
        (r"\brelacion\b", r"\brelación\b", "relación→relacion"),
        (r"\becuacion\b", r"\becuación\b", "ecuación→ecuacion"),
        (r"\bsolucion\b", r"\bsolución\b", "solución→solucion"),
        (r"\bexpresion\b", r"\bexpresión\b", "expresión→expresion"),
        (r"\bproporcion\b", r"\bproporción\b", "proporción→proporcion"),
        (r"\binformacion\b", r"\binformación\b", "información→informacion"),
        (r"\bconclusion\b", r"\bconclusión\b", "conclusión→conclusion"),
        (r"\bsituacion\b", r"\bsituación\b", "situación→situacion"),
        (r"\bnumero\b", r"\bnúmero\b", "número→numero"),
        (r"\bsegun\b", r"\bsegún\b", "según→segun"),
        (r"\bademas\b", r"\bademás\b", "además→ademas"),
        (r"\btambien\b", r"\btambién\b", "también→tambien"),
        (r"\banalisis\b", r"\banálisis\b", "análisis→analisis"),
        (r"\bmaximo\b", r"\bmáximo\b", "máximo→maximo"),
        (r"\bminimo\b", r"\bmínimo\b", "mínimo→minimo"),
        (r"\bultimo\b", r"\búltimo\b", "último→ultimo"),
        (r"\bultimos\b", r"\búltimos\b", "últimos→ultimos"),
        (r"\bmetodo\b", r"\bmétodo\b", "método→metodo"),
        (r"\blinea\b", r"\blínea\b", "línea→linea"),
        (r"\bformula\b", r"\bfórmula\b", "fórmula→formula"),
        (r"\bangulo\b", r"\bángulo\b", "ángulo→angulo"),
        (r"\btriangulo\b", r"\btriángulo\b", "triángulo→triangulo"),
        (r"\brectangulo\b", r"\brectángulo\b", "rectángulo→rectangulo"),
        (r"\bdiametro\b", r"\bdiámetro\b", "diámetro→diametro"),
        (r"\bperimetro\b", r"\bperímetro\b", "perímetro→perimetro"),
        (r"\bcalculo\b", r"\bcálculo\b", "cálculo→calculo"),
        (r"\bparabola\b", r"\bparábola\b", "parábola→parabola"),
        (r"\bvertice\b", r"\bvértice\b", "vértice→vertice"),
        (r"\bsimbolo\b", r"\bsímbolo\b", "símbolo→simbolo"),
        (r"\brazon\b", r"\brazón\b", "razón→razon"),
        (r"\bpatron\b", r"\bpatrón\b", "patrón→patron"),
    ]
]

# ── Class 5: double-encoded entities ─────────────────────────
_DBL_ENC_RE = re.compile(
    r"&amp;(?:aacute|eacute|iacute|oacute|uacute|ntilde"
    r"|Aacute|iquest|iexcl|#x[0-9a-fA-F]+|#\d+);?"
)

# Min unaccented words to flag as systemic (Class 4)
_MIN_ACCENT_BASE_HITS = 3

# ── Class 4b: single unambiguous accent→base ─────────────────
# Words that have NO valid unaccented form in ANY context.
# Flagged even if only 1 occurrence.
_UNAMBIGUOUS_ACCENT: list[tuple[re.Pattern[str], re.Pattern[str], str]] = [
    (re.compile(bad, re.I), re.compile(good, re.I), label)
    for bad, good, label in [
        (r"\btambien\b", r"\btambién\b", "también→tambien"),
        (r"\bsegun\b", r"\bsegún\b", "según→segun"),
        (r"\bademas\b", r"\bademás\b", "además→ademas"),
        (r"\banalisis\b", r"\banálisis\b", "análisis→analisis"),
        (r"\bconclusion\b", r"\bconclusión\b", "conclusión→conclusion"),
        (r"\bsituacion\b", r"\bsituación\b", "situación→situacion"),
        (r"\binformacion\b", r"\binformación\b", "información→informacion"),
        (r"\bexpresion\b", r"\bexpresión\b", "expresión→expresion"),
        (r"\bproporcion\b", r"\bproporción\b", "proporción→proporcion"),
        (r"\blinea\b", r"\blínea\b", "línea→linea"),
        (r"\btriangulo\b", r"\btriángulo\b", "triángulo→triangulo"),
        (r"\brectangulo\b", r"\brectángulo\b", "rectángulo→rectangulo"),
        (r"\bperimetro\b", r"\bperímetro\b", "perímetro→perimetro"),
        (r"\bangulo\b", r"\bángulo\b", "ángulo→angulo"),
        (r"\bvertice\b", r"\bvértice\b", "vértice→vertice"),
        (r"\bparabola\b", r"\bparábola\b", "parábola→parabola"),
        (r"\bsimbolo\b", r"\bsímbolo\b", "símbolo→simbolo"),
        (r"\bdiametro\b", r"\bdiámetro\b", "diámetro→diametro"),
    ]
]


def _visible_text(xml: str) -> str:
    """Remove MathML/tags and decode entities to get visible text."""
    text = re.sub(r"<math[^>]*>.*?</math>", " ", xml, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = _html.unescape(text)
    return re.sub(r"\s+", " ", text)


def _check_item(xml: str) -> list[str]:
    """Return list of corruption labels found in a single item."""
    matches: list[str] = []

    # Class 1: hex-digit substitutions (raw XML)
    matches.extend(_HEX_RE.findall(xml))

    text = _visible_text(xml)

    # Class 2: char-deleted accents
    for pat, label in _DELETED_WORDS:
        if pat.search(text):
            matches.append(label)

    # Class 3: ñ → n
    for pat, label in _TILDE_WORDS:
        if pat.search(text):
            matches.append(label)

    # Class 4: accent→base (only if systemic — 3+ hits)
    base_hits = [
        label for bad, good, label in _ACCENT_PAIRS
        if bad.search(text) and not good.search(text)
    ]
    if len(base_hits) >= _MIN_ACCENT_BASE_HITS:
        matches.extend(base_hits)

    # Class 4b: unambiguous accent→base (even 1 hit is enough)
    for bad, good, label in _UNAMBIGUOUS_ACCENT:
        if bad.search(text) and not good.search(text):
            matches.append(label)

    # Class 5: double-encoded entities (raw XML)
    dbl = _DBL_ENC_RE.findall(xml)
    if dbl:
        matches.extend(f"dbl:{d}" for d in set(dbl))

    return sorted(set(matches))


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
            matches = _check_item(xml)
            if matches:
                results.append((item_id, matches))

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
        "# Root cause: LLM occasionally corrupts accented characters.",
        "#",
        "# Five corruption classes detected:",
        "#   1) Hex substitution  — función → funcif3n",
        "#   2) Char deleted      — gráfico → grfico",
        "#   3) Tilde stripped    — tamaño → tamano, año → ano",
        "#   4) Accent→base      — gráfico → grafico (3+ per Q)",
        "#   4b) Unambiguous     — según → segun (always wrong)",
        "#   5) Double-encoded   — &amp;#xD7; instead of &#xD7;",
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
