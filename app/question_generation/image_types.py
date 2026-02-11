"""Image type taxonomy for PAES M1 question generation.

Each type is a rich specification so LLMs can make informed decisions
about which image types an atom requires. Types are classified as
generatable (Gemini can produce them) or not generatable (block).

Used by:
- Enrichment (Phase 1): LLM picks from the catalog for each atom.
- Generatability gate: blocks atoms needing unsupported types.
- Planning (Phase 2): LLM assigns types to individual plan slots.
- Image generation (Phase 4b): drives the generation pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Image type specification
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ImageTypeSpec:
    """Full specification for a single image type."""

    key: str
    name_es: str
    description: str
    examples: tuple[str, ...]
    when_to_use: str
    generatable: bool
    why_not_generatable: str = ""


# ---------------------------------------------------------------------------
# Generatable image types (Gemini can produce these)
# ---------------------------------------------------------------------------

FUNCTION_GRAPH = ImageTypeSpec(
    key="function_graph",
    name_es="Gráfico de función en plano cartesiano",
    description=(
        "Plano cartesiano con una o más funciones graficadas. "
        "Ejes X e Y etiquetados, cuadrícula sutil, curvas "
        "claramente trazadas, puntos notables marcados "
        "(interceptos, vértices, asíntotas)."
    ),
    examples=(
        "Parábola y=x²-4 con interceptos marcados",
        "Comparación de f(x)=2x+1 y g(x)=-x+3",
        "Función exponencial con asíntota horizontal",
        "sen(x) en [0, 2π] con amplitud y período",
    ),
    when_to_use=(
        "Cuando la pregunta requiere interpretar, analizar o "
        "comparar funciones en representación gráfica: lineales, "
        "cuadráticas, exponenciales, logarítmicas, "
        "trigonométricas, valor absoluto, por partes."
    ),
    generatable=True,
)

GEOMETRIC_FIGURE = ImageTypeSpec(
    key="geometric_figure",
    name_es="Figura geométrica 2D",
    description=(
        "Figuras geométricas planas con medidas, ángulos y "
        "vértices etiquetados. Marcas de igualdad en lados, "
        "arcos para ángulos, líneas auxiliares."
    ),
    examples=(
        "Triángulo ABC con lados y ángulos para Pitágoras",
        "Círculo con radio, cuerda y ángulo central",
        "Paralelas cortadas por transversal con ángulos alternos",
        "Transformación: reflexión de triángulo respecto a eje",
    ),
    when_to_use=(
        "Cuando la pregunta involucra áreas, perímetros, ángulos, "
        "teoremas geométricos (Pitágoras, Tales, Euclides) o "
        "transformaciones isométricas. Solo figuras 2D."
    ),
    generatable=True,
)

STATISTICAL_CHART = ImageTypeSpec(
    key="statistical_chart",
    name_es="Gráfico estadístico",
    description=(
        "Visualización de datos con ejes etiquetados y valores "
        "visibles. Tipos: barras, histograma, circular (torta), "
        "diagrama de caja (boxplot), dispersión, ojiva."
    ),
    examples=(
        "Histograma de frecuencias con intervalos etiquetados",
        "Boxplot con mediana, cuartiles y extremos",
        "Gráfico circular con porcentajes",
        "Dispersión con línea de tendencia",
    ),
    when_to_use=(
        "Cuando la pregunta requiere interpretar datos gráficos, "
        "calcular medidas estadísticas desde un gráfico, o "
        "comparar distribuciones. NO para tablas de datos."
    ),
    generatable=True,
)

NUMBER_LINE = ImageTypeSpec(
    key="number_line",
    name_es="Recta numérica",
    description=(
        "Recta numérica horizontal con puntos, intervalos o "
        "desigualdades. Valores etiquetados, puntos rellenos "
        "(incluido) o vacíos (excluido) según corresponda."
    ),
    examples=(
        "Solución de |x-3| < 2 como intervalo",
        "Ubicación de √2, π/2 y 1.5 en la recta real",
        "Solución de sistema de inecuaciones",
        "Intervalo (-∞, 3] ∪ [5, +∞)",
    ),
    when_to_use=(
        "Cuando la pregunta involucra ordenar números reales, "
        "representar soluciones de inecuaciones, ubicar valores "
        "irracionales, o visualizar intervalos."
    ),
    generatable=True,
)


# ---------------------------------------------------------------------------
# Non-generatable image types (BLOCK the atom)
# ---------------------------------------------------------------------------

PRECISE_CONSTRUCTION = ImageTypeSpec(
    key="precise_construction",
    name_es="Construcción geométrica precisa",
    description=(
        "Construcciones con compás y regla: bisectrices, "
        "mediatrices, ángulos específicos, inscripción "
        "de polígonos regulares."
    ),
    examples=(
        "Mediatriz de un segmento con arcos de compás",
        "Bisectriz de un ángulo con marcas de construcción",
        "Hexágono inscrito en un círculo paso a paso",
    ),
    when_to_use=(
        "Cuando se necesita mostrar el PROCESO de construcción "
        "geométrica, no solo el resultado final."
    ),
    generatable=False,
    why_not_generatable=(
        "Gemini no puede producir la precisión geométrica "
        "exacta requerida para arcos de compás y pasos "
        "secuenciales de construcción."
    ),
)

COMPLEX_3D = ImageTypeSpec(
    key="complex_3d",
    name_es="Figura tridimensional",
    description=(
        "Figuras 3D con perspectiva y dimensiones etiquetadas. "
        "Aristas visibles/ocultas diferenciadas: prismas, "
        "pirámides, cilindros, conos, esferas."
    ),
    examples=(
        "Prisma rectangular con largo, ancho y alto",
        "Cono con altura, radio y generatriz",
        "Esfera con plano secante",
        "Pirámide con apotema lateral marcado",
    ),
    when_to_use=(
        "Cuando la pregunta requiere visualizar cuerpos 3D "
        "para calcular volumen o área superficial."
    ),
    generatable=False,
    why_not_generatable=(
        "Gemini no produce perspectivas 3D precisas con "
        "aristas ocultas diferenciadas ni proporciones "
        "dimensionales confiables."
    ),
)

TECHNICAL_SCHEMATIC = ImageTypeSpec(
    key="technical_schematic",
    name_es="Esquema técnico o diagrama lógico",
    description=(
        "Diagramas con símbolos estandarizados y conexiones "
        "precisas: Venn, diagramas de árbol, flujogramas, grafos."
    ),
    examples=(
        "Diagrama de Venn con 3 conjuntos etiquetados",
        "Diagrama de árbol para probabilidad condicional",
        "Grafo con nodos y aristas ponderadas",
    ),
    when_to_use=(
        "Cuando se necesitan diagramas con símbolos "
        "estandarizados y relaciones topológicas exactas."
    ),
    generatable=False,
    why_not_generatable=(
        "Gemini no produce layouts simbólicos ni relaciones "
        "topológicas confiables (conexiones, inclusiones)."
    ),
)


# ---------------------------------------------------------------------------
# Registries (derived from specs)
# ---------------------------------------------------------------------------

GENERATABLE_SPECS: tuple[ImageTypeSpec, ...] = (
    FUNCTION_GRAPH,
    GEOMETRIC_FIGURE,
    STATISTICAL_CHART,
    NUMBER_LINE,
)

NOT_GENERATABLE_SPECS: tuple[ImageTypeSpec, ...] = (
    PRECISE_CONSTRUCTION,
    COMPLEX_3D,
    TECHNICAL_SCHEMATIC,
)

ALL_SPECS: tuple[ImageTypeSpec, ...] = (
    GENERATABLE_SPECS + NOT_GENERATABLE_SPECS
)

# Frozensets for fast lookup (preserves existing public API)
GENERATABLE_TYPES: frozenset[str] = frozenset(
    s.key for s in GENERATABLE_SPECS
)
NOT_GENERATABLE_TYPES: frozenset[str] = frozenset(
    s.key for s in NOT_GENERATABLE_SPECS
)
ALL_IMAGE_TYPES: frozenset[str] = (
    GENERATABLE_TYPES | NOT_GENERATABLE_TYPES
)

# Single-source table prohibition text
NOT_IMAGES_DESCRIPTION: str = (
    "Tablas, datos numéricos, matrices, sistemas de ecuaciones "
    "y expresiones algebraicas NO son imágenes. Se representan "
    "como HTML/MathML directamente dentro del XML QTI."
)


# ---------------------------------------------------------------------------
# Prompt catalog builder
# ---------------------------------------------------------------------------


def build_image_type_catalog(
    specs: tuple[ImageTypeSpec, ...] | None = None,
) -> str:
    """Build a detailed catalog of image types for LLM prompts.

    Each type is presented with name, description, examples,
    and usage guidance so the LLM can make informed decisions.

    Args:
        specs: Which specs to include. Defaults to generatable only.

    Returns:
        Formatted catalog string in Spanish.
    """
    if specs is None:
        specs = GENERATABLE_SPECS

    lines: list[str] = []
    for i, spec in enumerate(specs, 1):
        lines.append(
            f"{i}. `{spec.key}` — {spec.name_es}\n"
            f"   Descripción: {spec.description}\n"
            f"   Ejemplos: {'; '.join(spec.examples[:3])}\n"
            f"   Usar cuando: {spec.when_to_use}"
        )
    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Helper functions (preserves existing public API)
# ---------------------------------------------------------------------------


def can_generate_all(image_types: list[str]) -> bool:
    """Check if all requested image types are generatable.

    Args:
        image_types: List of image type strings from enrichment.

    Returns:
        True if every type is in GENERATABLE_TYPES (or list empty).
    """
    return all(t in GENERATABLE_TYPES for t in image_types)


def get_unsupported_types(image_types: list[str]) -> list[str]:
    """Return image types that we cannot currently generate.

    Args:
        image_types: List of image type strings from enrichment.

    Returns:
        List of types not in GENERATABLE_TYPES.
    """
    return [t for t in image_types if t not in GENERATABLE_TYPES]


def filter_valid_types(image_types: list[str]) -> list[str]:
    """Strip unrecognized values, keeping only known image types.

    Args:
        image_types: Raw list from LLM response.

    Returns:
        Filtered list containing only types in ALL_IMAGE_TYPES.
    """
    return [t for t in image_types if t in ALL_IMAGE_TYPES]
