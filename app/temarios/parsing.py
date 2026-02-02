from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from PyPDF2 import PdfReader

BASE_DIR = Path(__file__).resolve().parents[1]  # points to app/
DATA_DIR = BASE_DIR / "data" / "temarios"
PDF_DIR = DATA_DIR / "pdf"
JSON_DIR = DATA_DIR / "json"


@dataclass
class UnitConfig:
    name_marker: str  # substring that uniquely identifies where the unit name starts


@dataclass
class AxisConfig:
    key: str
    marker: str  # substring that marks the start of this eje block
    units: list[UnitConfig]


@dataclass
class TemarioConfig:
    stem: str
    out_name: str
    temario_id: str
    tipo_aplicacion: str
    fuente_pdf: str
    axes: list[AxisConfig]


HAB_HEADER = "Habilidad Descripción Criterios de evaluación"
CONOC_HEADER = "CONOCIMIENTOS EVALUADOS EN LA PAES"
HAB_TABLE_TRAILER = "A continuación se presentan las habilidades y los conocimientos que evalúa esta "
HAB_BLOCK_TRAILER_FALLBACK = "CONOCIMIENTOS EVALUADOS EN LA PAES"
HAB_REPEAT_HEADER = "HABILIDADES\nResolver problemas Modelar Representar Argumentar"


def clean_text(raw: str) -> str:
    """
    Normalize a content string to plain text:
    - remove special DEMRE bullet glyph 'ӹ'
    - replace tabs/newlines with spaces
    - collapse repeated whitespace
    """
    s = raw.replace("ӹ", "")
    s = s.replace("\t", " ")
    s = s.replace("\n", " ")
    s = " ".join(s.split())
    return s


TEMARIO_CONFIGS: list[TemarioConfig] = [
    TemarioConfig(
        stem="2026-25-01-24-temario-paes-invierno-m1",
        out_name="2026-25-01-24-temario-paes-invierno-m1.json",
        temario_id="paes_m1_invierno_2026",
        tipo_aplicacion="invierno",
        fuente_pdf="data/temarios/pdf/2026-25-01-24-temario-paes-invierno-m1.pdf",
        axes=[
            AxisConfig(
                key="numeros",
                marker="NÚMEROSConjunto de los ",
                units=[
                    UnitConfig("Conjunto de los "),
                    UnitConfig("Porcentaje"),
                    UnitConfig("Potencias y raíces "),
                ],
            ),
            AxisConfig(
                key="algebra_y_funciones",
                marker="ÁLGEBRA Y ",
                units=[
                    UnitConfig("Expresiones algebraicas"),
                    UnitConfig("Proporcionalidad"),
                    UnitConfig("Ecuaciones e inecuaciones "),
                    UnitConfig("Sistemas de ecuaciones "),
                    UnitConfig("Función lineal y afín"),
                    UnitConfig("Función cuadrática"),
                ],
            ),
            AxisConfig(
                key="geometria",
                marker="GEOMETRÍAFiguras geométricas",
                units=[
                    UnitConfig("Figuras geométricas"),
                    UnitConfig("Cuerpos geométricos"),
                    UnitConfig("Transformaciones "),
                ],
            ),
            AxisConfig(
                key="probabilidad_y_estadistica",
                marker="PROBABILIDAD ",
                units=[
                    UnitConfig("Representación de datos "),
                    UnitConfig("Medidas de tendencia "),
                    UnitConfig("Medidas de posición"),
                    UnitConfig("Reglas de las "),
                ],
            ),
        ],
    ),
    TemarioConfig(
        stem="2026-25-03-20-temario-paes-regular-m1",
        out_name="2026-25-03-20-temario-paes-regular-m1.json",
        temario_id="paes_m1_regular_2026",
        tipo_aplicacion="regular",
        fuente_pdf="data/temarios/pdf/2026-25-03-20-temario-paes-regular-m1.pdf",
        axes=[
            AxisConfig(
                key="numeros",
                marker="NÚMEROSConjunto de los ",
                units=[
                    UnitConfig("Conjunto de los "),
                    UnitConfig("Porcentaje "),
                    UnitConfig("Potencias y raíces "),
                ],
            ),
            AxisConfig(
                key="algebra_y_funciones",
                marker="ÁLGEBRA Y ",
                units=[
                    UnitConfig("Expresiones algebraicas "),
                    UnitConfig("Proporcionalidad "),
                    UnitConfig("Ecuaciones e inecuaciones "),
                    UnitConfig("Sistemas de ecuaciones "),
                    UnitConfig("Función lineal y afín "),
                    UnitConfig("Función cuadrática "),
                ],
            ),
            AxisConfig(
                key="geometria",
                marker="GEOMETRÍAFiguras geométricas ",
                units=[
                    UnitConfig("Figuras geométricas "),
                    UnitConfig("Cuerpos geométricos "),
                    UnitConfig("Transformaciones "),
                ],
            ),
            AxisConfig(
                key="probabilidad_y_estadistica",
                marker="PROBABILIDAD ",
                units=[
                    UnitConfig("Representación de datos "),
                    UnitConfig("Medidas de posición "),
                    UnitConfig("Reglas de las "),
                ],
            ),
        ],
    ),
]


def slice_habilidades(text: str) -> list[str]:
    """Return exact lines of the habilidades table from the raw text."""
    start = text.index(HAB_HEADER)
    try:
        end = text.index(HAB_TABLE_TRAILER, start)
    except ValueError:
        end = text.index(HAB_BLOCK_TRAILER_FALLBACK, start)
    block = text[start:end]
    return block.splitlines()


def parse_habilidades(lines: list[str]) -> dict[str, dict[str, list[str] | str]]:
    """
    Parse habilidades into a structured dict, preserving exact wording.

    Keys:
      resolver_problemas, modelar, representar, argumentar
    Fields:
      descripcion: single string (starting at “Es la habilidad…”, plain text)
      criterios_evaluacion: list of strings (one per bullet, plain text)
    """
    bullet_markers = ("▶", "ӹ")
    block = "\n".join(lines)

    patterns = [
        ("resolver_problemas", "Resolver \nProblemasEs la habilidad"),
        ("modelar", "ModelarEs la habilidad"),
        ("representar", "RepresentarEs la habilidad"),
        ("argumentar", "ArgumentarEs la habilidad"),
    ]

    segments: list[tuple[int, str]] = []
    for key, marker in patterns:
        idx = block.index(marker)
        segments.append((idx, key))
    segments.sort(key=lambda t: t[0])

    habilidades: dict[str, dict[str, object]] = {}

    for i, (start, key) in enumerate(segments):
        end = segments[i + 1][0] if i + 1 < len(segments) else len(block)
        seg = block[start:end]

        # description: from “Es la habilidad…” up to first bullet marker
        desc_pos = seg.index("Es la habilidad")
        desc_start = desc_pos
        bullet_positions = [p for c in bullet_markers for p in [seg.find(c, desc_start)] if p != -1]
        first_bullet_pos = min(bullet_positions) if bullet_positions else len(seg)

        desc_text = seg[desc_start:first_bullet_pos].rstrip("\n")
        bullets_region = seg[first_bullet_pos:]

        bullets: list[str] = []
        if bullets_region:
            b_lines = bullets_region.splitlines()
            current: list[str] = []
            header_prefixes = [
                "===== PAGE BREAK =====",
                "TEMARIO PRUEBA DE",
            ]
            for line in b_lines:
                if any(line.startswith(p) for p in header_prefixes):
                    break
                if any(m in line for m in bullet_markers):
                    if current:
                        bullets.append("\n".join(current))
                        current = []
                    current.append(line)
                else:
                    if current:
                        current.append(line)
            if current:
                bullets.append("\n".join(current))

        habilidades[key] = {
            "descripcion": clean_text(desc_text),
            "criterios_evaluacion": [clean_text(b) for b in bullets],
        }

    return habilidades


def slice_conocimientos(text: str) -> str:
    """Return raw conocimientos block as a single string."""
    start = text.index(CONOC_HEADER)
    return text[start:]


def parse_unit_block(block: str) -> dict[str, object]:
    """
    Given a substring that starts at the unit name marker and ends before the next unit,
    return:
      - nombre: unit name (normalized whitespace, but same words)
      - descripcion: list of bullet strings (plain text, one per bullet).
    """
    bullet_markers = ("▶", "ӹ")
    first_bullet_pos = min(
        (i for i in (block.find("▶"), block.find("ӹ")) if i != -1),
        default=-1,
    )
    if first_bullet_pos == -1:
        name_region = block
        bullets_region = ""
    else:
        name_region = block[:first_bullet_pos]
        bullets_region = block[first_bullet_pos:]

    nombre = " ".join(name_region.split())

    bullets: list[str] = []
    if bullets_region:
        lines = bullets_region.splitlines()
        current: list[str] = []
        header_prefixes = [
            "===== PAGE BREAK =====",
            "TEMARIO PRUEBA DE",
            "HABILIDADES",
            "Resolver problemas Modelar Representar Argumentar",
            "EJE ",
            "EJE TEMÁTICO UNIDADES TEMÁTICAS DESCRIPCIÓN",
            "EJE TEMÁTICO UNIDADES TEMÁTICAS DESCRIPCIÓN DE LAS UNIDADES TEMÁTICAS",
        ]
        for line in lines:
            if any(line.startswith(p) for p in header_prefixes):
                break
            if any(m in line for m in bullet_markers):
                if current:
                    bullets.append("\n".join(current))
                    current = []
                current.append(line)
            else:
                if current:
                    current.append(line)
        if current:
            bullets.append("\n".join(current))

    # Remove any trailing habilidades header accidentally glued to the last bullet
    if bullets:
        cleaned: list[str] = []
        for b in bullets:
            if HAB_REPEAT_HEADER in b:
                b = b.split(HAB_REPEAT_HEADER, 1)[0]
            if "HABILIDADES" in b:
                b = b.split("HABILIDADES", 1)[0]
            cleaned.append(b)
        bullets = cleaned

    bullets_plain = [clean_text(b) for b in bullets]

    return {"nombre": nombre, "descripcion": bullets_plain}


def parse_axes(text: str, cfg: TemarioConfig) -> dict[str, object]:
    """
    Parse ejes temáticos and unidades from the conocimientos block,
    using the axis/unit configuration, preserving exact wording.
    """
    conocimientos_text = slice_conocimientos(text)
    axes_result: dict[str, object] = {}

    # Pre-compute axis start positions within the conocimientos block
    axis_starts = [conocimientos_text.index(axis.marker) for axis in cfg.axes]
    axis_starts.append(len(conocimientos_text))

    for idx, axis in enumerate(cfg.axes):
        start = axis_starts[idx]
        end = axis_starts[idx + 1]
        axis_block = conocimientos_text[start:end]

        units_result: list[dict[str, object]] = []

        # for each unit within this axis, slice based on configured markers
        unit_starts: list[int] = []
        for ucfg in axis.units:
            pos = axis_block.index(ucfg.name_marker)
            unit_starts.append(pos)
        # sort indices along with their config order
        indexed = sorted(zip(unit_starts, axis.units), key=lambda t: t[0])

        for i, (pos, ucfg) in enumerate(indexed):
            unit_start = pos
            unit_end = indexed[i + 1][0] if i + 1 < len(indexed) else len(axis_block)
            unit_block = axis_block[unit_start:unit_end]
            unit_parsed = parse_unit_block(unit_block)
            units_result.append(unit_parsed)

        axes_result[axis.key] = {"unidades": units_result}

    return axes_result


def build_structured_temario(cfg: TemarioConfig) -> dict[str, object]:
    pdf_path = PDF_DIR / f"{cfg.stem}.pdf"
    reader = PdfReader(str(pdf_path))
    pages: list[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    text = "\n\n===== PAGE BREAK =====\n\n".join(pages)

    habilidades_lines = slice_habilidades(text)
    habilidades = parse_habilidades(habilidades_lines)
    ejes = parse_axes(text, cfg)

    return {
        "id": cfg.temario_id,
        "proceso_admision": 2026,
        "tipo_aplicacion": cfg.tipo_aplicacion,
        "nombre_prueba": "Prueba de Competencia Matemática 1 (M1)",
        "fuente_pdf": cfg.fuente_pdf,
        "habilidades": habilidades,
        "conocimientos": ejes,
    }


def build_all_temarios() -> None:
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    for cfg in TEMARIO_CONFIGS:
        data = build_structured_temario(cfg)
        out_path = JSON_DIR / cfg.out_name
        out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {out_path}")


def main() -> None:
    """Regenerate all structured temario JSON files from their PDFs."""
    build_all_temarios()


if __name__ == "__main__":
    main()

