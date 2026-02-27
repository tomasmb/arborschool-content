"""Mapping tables for garbled character fixes.

Each hex-substitution pattern from garbled_report.py is mapped to its
correct Spanish form.  Word-level accent/tilde replacements are also
included for Classes 2-4b, 6, and 8.
"""
from __future__ import annotations

# ── Class 1: hex-substitution  garbled_string → correct_string ──
# Every entry from _HEX_PATTERNS in garbled_report.py, mapped to
# the intended Spanish word.  Case-sensitive — the script handles
# case preservation separately for word-boundary replacements.

HEX_TO_CORRECT: dict[str, str] = {
    # ¿Cuál variants
    "bfCue1l": "¿Cuál",
    "bfcue1l": "¿cuál",
    "bfCue1ntas": "¿Cuántas",
    "bfcue1ntas": "¿cuántas",
    "bfcue1les": "¿cuáles",
    "0bfcu01l": "¿cuál",
    "0bfcu0e1l": "¿cuál",
    "0bfcu03l": "¿cuál",
    "0bCu03l": "¿Cuál",
    "bf00Cue100l": "¿Cuál",
    "00Cu03l": "¿Cuál",
    "bbfCue1ntos": "¿Cuántos",
    "BFcuE1l": "¿Cuál",
    "bcue1l": "¿cuál",
    "bfEn": "¿En",
    "bfque9": "¿qué",
    "0bfCu01l": "¿Cuál",
    "bfen cue1l": "¿en cuál",
    # función variants
    "funcif3n": "función",
    "funci03n": "función",
    "Funcif3n": "Función",
    # relación variants
    "relacif3n": "relación",
    "relaci03n": "relación",
    "relaci53n": "relación",
    "elacif3n": "elación",
    # ecuación variants
    "ecuacif3n": "ecuación",
    "ecuaci03n": "ecuación",
    "cuacif3n": "cuación",
    # expresión variants
    "expresif3n": "expresión",
    "expresi03n": "expresión",
    # proporción variants
    "proporcif3n": "proporción",
    "proporci03n": "proporción",
    "porcif3n": "porción",
    # solución variants
    "solucif3n": "solución",
    "soluci03n": "solución",
    "olucif3n": "olución",
    # posición variants
    "posicif3n": "posición",
    "posici03n": "posición",
    "osicif3n": "osición",
    # evolución variants
    "evolucif3n": "evolución",
    "evoluci93n": "evolución",
    # sustitución variants
    "sustitucif3n": "sustitución",
    "itucif3n": "itución",
    # conclusión variants
    "conclusif3n": "conclusión",
    "Conclusif3n": "Conclusión",
    "clusif3n": "clusión",
    # inecuación variants
    "inecuacif3n": "inecuación",
    "inecuaci03n": "inecuación",
    # condición variants
    "condicif3n": "condición",
    "ndicif3n": "ndición",
    # situación variants
    "situacif3n": "situación",
    "situaci03n": "situación",
    "tuacif3n": "tuación",
    # other -ción words
    "fraccif3n": "fracción",
    "representacif3n": "representación",
    "informacif3n": "información",
    "rmacif3n": "rmación",
    "precisif3n": "precisión",
    "ecisif3n": "ecisión",
    "dispersif3n": "dispersión",
    "persif3n": "persión",
    "factorizacif3n": "factorización",
    "ntacif3n": "ntación",
    "minuci03on": "minución",
    "bitacif3n": "bitación",
    "bitaci03n": "bitación",
    "seccif3n": "sección",
    # Cómo variants
    "Cif3mo": "Cómo",
    "cf3mo": "cómo",
    "cb3mo": "cómo",
    "c03mo": "cómo",
    "c0f3mo": "cómo",
    "c3f3mo": "cómo",
    # número variants
    "n0dmero": "número",
    "n03mero": "número",
    "nf3mero": "número",
    "n0famero": "número",
    # gráfico variants
    "gr01fico": "gráfico",
    "gr03fico": "gráfico",
    "gre1fico": "gráfico",
    "gr0303fico": "gráfico",
    "gr0e1fico": "gráfico",
    "gr5ffico": "gráfico",
    "gr03afico": "gráfico",
    "gr1fico": "gráfico",
    "gr31fico": "gráfico",
    # -ón nouns
    "patrf3n": "patrón",
    "garzf3n": "garzón",
    "cajf3n": "cajón",
    "automf3vil": "automóvil",
    # Según variants
    "Seg03n": "Según",
    "Seg01n": "Según",
    "00Seg03n": "Según",
    "seg0dn": "según",
    # Además variants
    "Adem03s": "Además",
    "AdemE1s": "Además",
    "ademe1s": "además",
    # Después / Tendrán
    "Despue9s": "Después",
    "despue9s": "después",
    "Tendre1n": "Tendrán",
    # varía variants
    "var0da": "varía",
    "var01a": "varía",
    "var03a": "varía",
    "var3b0a": "varía",
    # cuadrática variants
    "cuadre1tic": "cuadrátic",
    "cuadre1ticas": "cuadráticas",
    "cuadre1tico": "cuadrático",
    # Matemática variants
    "Mateme1tica": "Matemática",
    "matemE1tica": "matemática",
    "Matem03ticas": "Matemáticas",
    "Matem3tica": "Matemática",
    # categoría / automático
    "categor01a": "categoría",
    "ategor01a": "ategoría",
    "autome1tico": "automático",
    # aritmética variants
    "aritme9tica": "aritmética",
    "aritm03tica": "aritmética",
    "aritm7tica": "aritmética",
    # debería variants
    "deber0da": "debería",
    "deber31a": "debería",
    # misc
    "le1pices": "lápices",
    "me9todo": "método",
    "Tome1s": "Tomás",
    "tamaf1os": "tamaños",
    "Me1ximo": "Máximo",
    "m5nimo": "mínimo",
    "m5ximo": "máximo",
    "mednimo": "mínimo",
    "fanica": "única",
    # cuántas variants
    "cu03ntas": "cuántas",
    "cu01ntas": "cuántas",
    "contin03an": "continúan",
    # líneas variants
    "ldneas": "líneas",
    "l0dneas": "líneas",
    "l33nea": "línea",
    # misc
    "pa0eds": "país",
    "a03os": "años",
    "af1o": "año",
    "03pidamente": "ápidamente",
    "r03pidamente": "rápidamente",
    "cart0dn": "cartón",
    "per0dmetro": "perímetro",
    "uni3n": "unión",
    "est01n": "están",
    "im03genes": "imágenes",
    "dise03o": "diseño",
    "Tambi03n": "También",
    "c9En": "cien",
    # lowercase variants
    "seg03n": "según",
    "seg01n": "según",
    # Sí variants (ed/0d = í)
    "S0d": "Sí",
    "Sed": "Sí",
    # ── Round 2: patterns discovered from GPT review ──
    # fa = ú patterns
    "Segfan": "Según",
    "segfan": "según",
    "algfan": "algún",
    "nfameros": "números",
    # e1 = á patterns (new words)
    "este1": "está",
    "me1s": "más",
    "gre1fica": "gráfica",
    "gre1ficas": "gráficas",
    "pare1bola": "parábola",
    "ime1genes": "imágenes",
    # ed = í patterns
    "podreda": "podría",
    "mayoreda": "mayoría",
    "categoredas": "categorías",
    "cedrculos": "círculos",
    "simetreda": "simetría",
    "d0da": "día",
    # f3 = ó patterns (new words)
    "leyf3": "leyó",
    "construyf3": "construyó",
    "distribucif3n": "distribución",
    "Construccif3n": "Construcción",
    "reflexif3n": "reflexión",
    "traslacif3n": "traslación",
    # Complex/double-hex patterns
    "cc03mo": "cómo",
    "c03lculos": "cálculos",
    "Sof03a": "Sofía",
    "ma0303ana": "mañana",
    "cu0303al": "cuál",
    "var0303a": "varía",
    "03c03en": "cien",
    # bf = ¿ patterns (new words)
    "bfse": "¿se",
    "bfentre": "¿entre",
    "bfcufl": "¿cuál",
    # Additional mangled ¿cuál forms
    "3fcu31l": "¿cuál",
    "0bcu03l": "¿cuál",
    "1cul": "¿cuál",
    "1cunto": "¿cuánto",
    "1en": "¿en",
    # ── Round 3: fixes for simetría, 0bf-prefix, cien ──
    "simetre1a": "simetría",
    "simetr e1a": "simetría",
    "0bfque9": "¿qué",
    "0bfcue1l": "¿cuál",
    # ── Round 3b: residual patterns in already-fixed items ──
    "Gre1fico": "Gráfico",
    "Gre1ficas": "Gráficas",
    "Gre1fica": "Gráfica",
    "he1bitos": "hábitos",
    "vareda": "varía",
    "ubicf3": "ubicó",
    "razf3n": "razón",
    "debereda": "debería",
    "cue1nto": "cuánto",
    "cue1ntas": "cuántas",
    "cue1ntos": "cuántos",
    "te1ndose": "tándose",
    "Cf3mo": "Cómo",
    # other misc round 2
    "m0dnimo": "mínimo",
    "dibuj03": "dibujó",
    "Mat31as": "Matías",
    "est03": "está",
    "fc1ntos": "¿cuántos",
    "qu03": "qué",
    "poblaci03n": "población",
    # special case: ¿Cuántas with prefix
    "bfCue1ntas": "¿Cuántas",
}

# Post-fix corrections: words where null-byte decoding or hex
# substitution produces valid but WRONG Spanish.
POST_FIX_CORRECTIONS: dict[str, str] = {
    "tampocó": "tampoco",
    "ócien": "cien",
    "simetráa": "simetría",
}

# Word-boundary post-fix corrections (applied with \b).
# "cién" as standalone is wrong, but "recién" is correct.
POST_FIX_WORD_CORRECTIONS: list[tuple[str, str]] = [
    ("cién", "cien"),
]

# ── Classes 2 + 4b: word-boundary accent fixes ──────────────
# (bad_word, correct_word) — applied with \b word boundaries.
# Merged from _DELETED_WORDS and _UNAMBIGUOUS_ACCENT lists.
WORD_ACCENT_FIXES: list[tuple[str, str]] = [
    # char-deleted (Class 2)
    ("patrn", "patrón"),
    ("grfico", "gráfico"),
    ("grfica", "gráfica"),
    ("grficas", "gráficas"),
    ("grficos", "gráficos"),
    ("lnea", "línea"),
    ("reflexin", "reflexión"),
    ("funcin", "función"),
    ("relacin", "relación"),
    ("ecuacin", "ecuación"),
    ("solucin", "solución"),
    ("expresin", "expresión"),
    ("proporcin", "proporción"),
    ("informacin", "información"),
    ("conclusin", "conclusión"),
    ("situacin", "situación"),
    ("nmero", "número"),
    ("cmo", "cómo"),
    ("segn", "según"),
    ("adems", "además"),
    ("cul", "cuál"),
    ("tambin", "también"),
    ("imgenes", "imágenes"),
    ("razn", "razón"),
    ("representacin", "representación"),
    ("variacin", "variación"),
    ("anlisis", "análisis"),
    ("operacin", "operación"),
    ("disminucin", "disminución"),
    ("poblacin", "población"),
    ("mximo", "máximo"),
    ("ltimo", "último"),
    ("mnimo", "mínimo"),
    ("mtodo", "método"),
    # char-deleted round 2
    ("lneas", "líneas"),
    ("clculos", "cálculos"),
    ("mnima", "mínima"),
    ("sustitucin", "sustitución"),
    ("distribucin", "distribución"),
    ("evolucin", "evolución"),
    ("construccin", "construcción"),
    ("caractersticas", "características"),
    ("grficos", "gráficos"),
    # unambiguous accent→base (Class 4b)
    ("tambien", "también"),
    ("segun", "según"),
    ("ademas", "además"),
    ("analisis", "análisis"),
    ("conclusion", "conclusión"),
    ("situacion", "situación"),
    ("informacion", "información"),
    ("expresion", "expresión"),
    ("proporcion", "proporción"),
    ("linea", "línea"),
    ("triangulo", "triángulo"),
    ("rectangulo", "rectángulo"),
    ("perimetro", "perímetro"),
    ("angulo", "ángulo"),
    ("vertice", "vértice"),
    ("parabola", "parábola"),
    ("simbolo", "símbolo"),
    ("diametro", "diámetro"),
    ("grafico", "gráfico"),
    ("grafica", "gráfica"),
    ("graficos", "gráficos"),
    ("graficas", "gráficas"),
    ("numero", "número"),
    ("funcion", "función"),
    ("ecuacion", "ecuación"),
    ("fraccion", "fracción"),
    ("solucion", "solución"),
    ("relacion", "relación"),
    ("formula", "fórmula"),
    ("calculo", "cálculo"),
    ("razon", "razón"),
    ("patron", "patrón"),
    ("maximo", "máximo"),
    ("minimo", "mínimo"),
    ("ultimo", "último"),
    ("ultimos", "últimos"),
    ("metodo", "método"),
]

# ── Class 3: tilde-stripped ñ → n ────────────────────────────
TILDE_FIXES: list[tuple[str, str]] = [
    ("ano", "año"),
    ("anos", "años"),
    ("nino", "niño"),
    ("ninos", "niños"),
    ("nina", "niña"),
    ("ninas", "niñas"),
    ("pequeno", "pequeño"),
    ("pequena", "pequeña"),
    ("tamano", "tamaño"),
    ("tamanos", "tamaños"),
    ("diseno", "diseño"),
    ("espanol", "español"),
    ("senal", "señal"),
    ("ensenanza", "enseñanza"),
    ("compania", "compañía"),
    ("montana", "montaña"),
    ("manana", "mañana"),
    ("dueno", "dueño"),
    ("sueno", "sueño"),
    ("otono", "otoño"),
    ("dano", "daño"),
    ("bano", "baño"),
]

# ── Class 6: interrogative missing accent ────────────────────
# (pattern_str, replacement) — applied with re.sub
INTERROGATIVE_FIXES: list[tuple[str, str]] = [
    (r"¿\s*Cual\b", "¿Cuál"),
    (r"¿\s*cual\b", "¿cuál"),
    (r"¿\s*Que\b", "¿Qué"),
    (r"¿\s*que\b", "¿qué"),
    (r"¿\s*Cuantos\b", "¿Cuántos"),
    (r"¿\s*cuantos\b", "¿cuántos"),
    (r"¿\s*Cuantas\b", "¿Cuántas"),
    (r"¿\s*cuantas\b", "¿cuántas"),
    (r"¿\s*Cuanto\b", "¿Cuánto"),
    (r"¿\s*cuanto\b", "¿cuánto"),
    (r"¿\s*Cuanta\b", "¿Cuánta"),
    (r"¿\s*cuanta\b", "¿cuánta"),
]

# ── Null-byte split in image_description ─────────────────────
# \u0000XX → the correct Unicode character
NULL_BYTE_FIXES: dict[str, str] = {
    "\u0000e1": "á",
    "\u0000e9": "é",
    "\u0000ed": "í",
    "\u0000f3": "ó",
    "\u0000fa": "ú",
    "\u0000f1": "ñ",
    "\u0000bf": "¿",
    "\u0000a1": "¡",
    "\u0000fc": "ü",
}

# ── Classes 9-11: wrong-script / invisible / unusual whitespace ──
# Applied only to non-protected text in fix_xml().
UNICODE_CHAR_FIXES: dict[str, str] = {
    # Wrong-script punctuation that appears as garbling in Spanish.
    "।": ".",
    # Invisible/control characters.
    "\u00ad": "",
    "\u200b": "",
    "\u200c": "",
    "\u200d": "",
    "\u200e": "",
    "\u200f": "",
    "\u202a": "",
    "\u202b": "",
    "\u202c": "",
    "\u202d": "",
    "\u202e": "",
    "\u2060": "",
    "\ufeff": "",
    # Unusual whitespace normalized to a standard space.
    "\u00a0": " ",
    "\u2002": " ",
    "\u2003": " ",
    "\u2004": " ",
    "\u2005": " ",
    "\u2006": " ",
    "\u2007": " ",
    "\u2008": " ",
    "\u2009": " ",
    "\u200a": " ",
    "\u205f": " ",
    "\u3000": " ",
}
