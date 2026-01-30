"""Prompt builders for atom generation.

Follows Gemini best practices from
`docs/gemini-3-pro-prompt-engineering-best-practices.md` for `gemini-3-pro-preview`:
- Context first, then instructions
- Explicit output format with JSON schema
- Clear task description
- Negative constraints (what NOT to do)
- Anchor phrases like "Based on the information above..."
"""

from __future__ import annotations

import json
from typing import Any

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

EJE_PREFIX_MAP = {
    "numeros": "NUM",
    "algebra_y_funciones": "ALG",
    "geometria": "GEO",
    "probabilidad_y_estadistica": "PROB",
}

ATOM_GRANULARITY_GUIDELINES = """
## Criterios de Granularidad Atómica

Un átomo debe cumplir TODOS estos criterios. Si falla en CUALQUIERA, debe dividirse:

1. **Una sola intención cognitiva**: Cada átomo debe tener exactamente una
   intención cognitiva clara y específica. Si el título o descripción menciona
   "y" o "y/o" conectando dos conceptos distintos, probablemente deba dividirse.

2. **Carga de memoria de trabajo razonable**: No debe requerir más de ~4
   piezas novedosas de información a manipular simultáneamente. Si los
   criterios_atomicos requieren dominar múltiples algoritmos, procedimientos
   o conceptos independientes, DEBE dividirse. Cada algoritmo o procedimiento
   distinto cuenta como una pieza novedosa.

3. **Independencia de prerrequisitos**: Si la parte A debe aprenderse antes
   que la parte B (secuencia pedagógica natural), deben ser átomos separados
   con un prerrequisito explícito. Pregúntate: ¿puede un estudiante aprender
   B sin haber dominado A primero?

4. **Independencia de evaluación** (CRÍTICO): Si un profesor puede evaluar
   dos partes por separado con diferentes preguntas o rúbricas, DEBEN ser
   átomos separados. Este es el criterio más importante. Pregúntate:
   - ¿Puedo crear una pregunta de evaluación solo para la parte A?
   - ¿Puedo crear una pregunta de evaluación solo para la parte B?
   - ¿Las rúbricas de evaluación son diferentes?
   - ¿Requieren estrategias cognitivas diferentes? (ej: una parte es conceptual
     y otra procedimental, o una usa método A y otra método B)
   Si la respuesta es SÍ a cualquiera, son átomos separados.

5. **Límite de generalización**: Si dos habilidades se generalizan
   diferentemente en distintos contextos (una funciona en un dominio pero la
   otra no), no deben estar en el mismo átomo.

6. **Átomos integradores**: Si un átomo pretende "integrar" o "combinar"
   múltiples conceptos, procedimientos o habilidades que ya fueron cubiertos
   en otros átomos, debe ser extremadamente cuidadoso. Un átomo integrador
   solo es válido si:
   - Tiene una intención cognitiva única (ej: "aplicar jerarquía de operaciones")
   - No sobrecarga la memoria de trabajo (≤4 piezas novedosas)
   - Puede evaluarse con una rúbrica específica
   - NO simplemente "mezcla" múltiples procedimientos sin una intención unificada
   - **PRERREQUISITOS EXHAUSTIVOS**: Si requiere aplicar múltiples operaciones,
     conceptos o procedimientos, DEBE incluir TODOS los prerrequisitos necesarios.
     No omitas prerrequisitos porque parecen "obvios" o porque el átomo es
     "integrador". Si requiere A, B y C, lista explícitamente los átomos que
     cubren A, B y C.
   
   Si un átomo requiere más de 3-4 prerrequisitos complejos, probablemente
   esté intentando integrar demasiado y deba dividirse.

## Preguntas clave antes de combinar conceptos en un átomo

Antes de crear un átomo que combine dos conceptos (ej: "X e Y"), pregúntate:

1. ¿Puedo evaluar X sin evaluar Y? → Si SÍ, son átomos separados.
2. ¿Puedo evaluar Y sin evaluar X? → Si SÍ, son átomos separados.
3. ¿X debe aprenderse antes que Y? → Si SÍ, son átomos separados con prerrequisito.
4. ¿Los estudiantes recuerdan X e Y como una unidad o por separado? → Si por
   separado, son átomos separados.
5. ¿X e Y requieren diferentes rúbricas de evaluación? → Si SÍ, son átomos separados.

Si CUALQUIERA de estas respuestas es SÍ, crea átomos separados.

## Casos especiales: Conceptos relacionados pero evaluables por separado

Dos conceptos que están relacionados (inversos, complementarios, o que comparten
reglas/procedimientos comunes) DEBEN ser átomos separados si pueden evaluarse
independientemente, incluso si:
- Comparten reglas, principios o procedimientos comunes
- Son conceptualmente relacionadas o complementarias
- Se enseñan típicamente en secuencia cercana
- Parecen "parte del mismo tema"

Razón fundamental: Si pueden evaluarse por separado con diferentes preguntas o
rúbricas, son átomos separados. El hecho de compartir elementos comunes NO
justifica combinarlos en un solo átomo.

Principio general: La evaluación independiente es el criterio decisivo, no la
relación conceptual o la proximidad pedagógica.

## Ejemplos de buenos átomos (granularidad apropiada)

- Átomos con una sola intención cognitiva clara
- Átomos que pueden evaluarse con una pregunta o rúbrica específica
- Átomos que requieren ≤4 piezas novedosas de información
- Variaciones de un mismo concepto que requieren evaluación diferente
  (ej: "X con condición A" vs "X con condición B" si se evalúan por separado)

## Ejemplos de átomos demasiado grandes (deben dividirse)

- "Entender todo sobre [tema amplio]"
  → Dividir en conceptos más específicos que puedan evaluarse independientemente

- "[Concepto amplio] y [otro concepto amplio]"
  → Si cada parte puede evaluarse por separado, dividir

- "[Concepto A] y [Concepto B]" (si se pueden evaluar por separado)
  → Dividir en: "[Concepto A]" y "[Concepto B]" como átomos separados

- "Concepto y aplicación de [X]"
  → Dividir en: "Concepto de [X]" y "Aplicación de [X]"

- Átomos que requieren múltiples algoritmos o procedimientos distintos
  → Cada algoritmo/procedimiento distinto generalmente debe ser un átomo separado

- Átomos "integradores" que mezclan muchos conceptos previos sin una intención
  cognitiva unificada clara → Dividir en átomos más específicos

- Cualquier átomo cuyo título tenga "y" o "y/o" conectando dos conceptos,
  procedimientos o habilidades que puedan evaluarse independientemente.
"""


# -----------------------------------------------------------------------------
# Shared helpers
# -----------------------------------------------------------------------------

def format_habilidades_context(habilidades: dict[str, Any]) -> str:
    """Format habilidades dict as readable context for prompts."""
    lines: list[str] = []
    for hab_id, hab_data in habilidades.items():
        lines.append(f"### {hab_id}")
        lines.append(f"Descripción: {hab_data['descripcion']}")
        lines.append("Criterios de evaluación:")
        for criterio in hab_data["criterios_evaluacion"]:
            lines.append(f"  - {criterio}")
        lines.append("")
    return "\n".join(lines)


def format_atom_schema_example() -> str:
    """Return example atom JSON schema for prompts."""
    return """{
  "id": "A-M1-NUM-01-01",
  "eje": "numeros",
  "standard_ids": ["M1-NUM-01"],
  "habilidad_principal": "resolver_problemas",
  "habilidades_secundarias": ["representar"],
  "tipo_atomico": "concepto_procedimental",
  "titulo": "Ejemplo de título atómico",
  "descripcion": "El estudiante puede [acción específica] usando [herramienta/método], interpretando [concepto clave].",
  "criterios_atomicos": [
    "El estudiante puede [criterio evaluable 1].",
    "El estudiante interpreta [criterio evaluable 2]."
  ],
  "ejemplos_conceptuales": [
    "Ejemplo conceptual 1 que ilustra el concepto sin ser un ejercicio completo.",
    "Ejemplo conceptual 2 que muestra una variación del concepto."
  ],
  "prerrequisitos": [],
  "notas_alcance": [
    "Exclusión relevante 1.",
    "Exclusión relevante 2."
  ]
}"""


# -----------------------------------------------------------------------------
# Atom generation prompt
# -----------------------------------------------------------------------------

def build_atom_generation_prompt(
    standard: dict[str, Any],
    habilidades: dict[str, Any],
    atom_counter: int,
) -> str:
    """
    Build a prompt for generating atoms from a single standard.

    Follows Gemini best practices: context first, clear task, explicit output format.
    """
    standard_id = standard["id"]
    eje_key = standard["eje"]
    eje_prefix = EJE_PREFIX_MAP[eje_key]
    standard_number = standard_id.split("-")[2]

    habilidades_context = format_habilidades_context(habilidades)
    standard_json = json.dumps(standard, ensure_ascii=False, indent=2)
    atom_schema_example = format_atom_schema_example()

    return f"""<role>
Eres un experto en diseño de aprendizaje granular.
Tu tarea es descomponer estándares curriculares en átomos de aprendizaje atómicos.
</role>

<context>
## Habilidades del currículo

{habilidades_context}

## Estándar canónico a procesar

{standard_json}

## Guías de granularidad atómica

{ATOM_GRANULARITY_GUIDELINES}

## Ejemplo de átomo canónico

{atom_schema_example}

**IMPORTANTE sobre campos (CRÍTICO - NO CONFUNDIR):**
- "habilidad_principal" y "habilidades_secundarias" SOLO pueden contener
  habilidades válidas del contexto proporcionado (revisa la sección "Habilidades
  del currículo" en el contexto). Estas habilidades son las que aparecen en el
  contexto de habilidades proporcionado, no valores de "tipo_atomico".
- "tipo_atomico" es un campo COMPLETAMENTE DIFERENTE y puede ser:
  concepto, procedimiento, representacion, argumentacion, modelizacion, concepto_procedimental
- **CRÍTICO**: "tipo_atomico" NO es lo mismo que "habilidad_principal".
  - "tipo_atomico" describe el TIPO de contenido del átomo (concepto, procedimiento, etc.)
  - "habilidad_principal" describe la HABILIDAD del currículo que el átomo desarrolla
  - NO uses valores de "tipo_atomico" (como "procedimiento", "concepto", "representacion",
    "argumentacion", "modelizacion") en "habilidad_principal" o "habilidades_secundarias"
  - NO uses valores de "habilidad_principal" (las habilidades del contexto) en "tipo_atomico"
- Son campos completamente independientes y con propósitos diferentes.
</context>

<task>
Genera una lista de átomos de aprendizaje (JSON array) que descompongan este estándar.
Cada átomo debe:

1. Tener exactamente UNA intención cognitiva
2. Ser evaluable independientemente
3. Estar vinculado a una habilidad principal (y opcionalmente secundarias)
4. Tener un ID único: A-M1-{eje_prefix}-{standard_number}-MM (MM = contador 01, 02, ...)
5. Incluir "standard_ids": ["{standard_id}"]
6. Respetar los criterios de granularidad atómica

IMPORTANTE: Asegúrate de cubrir tanto aspectos CONCEPTUALES (qué es, cómo se
define, cómo se reconoce) como PROCEDIMENTALES (cómo se hace, qué pasos seguir)
del estándar. No te enfoques solo en procedimientos; incluye también átomos
conceptuales cuando el estándar lo requiera.
</task>

<rules>
1. Todo en español.
2. FIEL AL ESTÁNDAR: no agregar contenido fuera del alcance del estándar.
   Esto aplica también a "notas_alcance": no introduzcas conceptos que
   excedan el estándar original, incluso si parecen relacionados o útiles.
   
   **VERIFICACIÓN DE FIDELIDAD (CRÍTICO)**: Antes de finalizar cada átomo:
   - Revisa descripción, criterios_atomicos y notas_alcance contra los campos
     "incluye" y "no_incluye" del estándar
   - Si mencionas conceptos, operaciones, procedimientos o herramientas que NO
     están explícitamente listados en el estándar:
     * Elimina la mención, O
     * Aclara en notas_alcance que se asume como conocimiento previo (solo si
       el estándar lo permite como herramienta), O
     * Restringe el alcance para no mencionarlo
   - **REGLA DE ORO**: Respeta EXACTAMENTE lo que dice el estándar. No agregues
     conceptos relacionados aunque parezcan obvios o comunes en el dominio.
   - **VERIFICACIÓN OBLIGATORIA**: Cada mención de conceptos/procedimientos debe
     poder justificarse con referencia explícita al estándar.
3. Granularidad atómica: cada átomo = una sola intención cognitiva.
4. Mínimo 1 criterio_atomico por átomo.
5. 1-3 ejemplos_conceptuales por átomo (NO ejercicios completos).
6. NO usar LaTeX; usar texto plano para notación matemática.
7. "tipo_atomico" debe ser uno de: concepto, procedimiento, representacion,
   argumentacion, modelizacion, concepto_procedimental.
   IMPORTANTE: "tipo_atomico" NO es lo mismo que "habilidad_principal" ni
   "habilidades_secundarias". Son campos completamente diferentes.
8. "habilidad_principal" debe ser una de las habilidades relacionadas del
   estándar (revisa las habilidades proporcionadas en el contexto).
   "habilidades_secundarias" debe ser una lista de habilidades válidas del
   contexto proporcionado (puede estar vacía []). **CRÍTICO**: NO uses valores
   de "tipo_atomico" (como "procedimiento", "concepto", "representacion",
   "argumentacion", "modelizacion") en "habilidad_principal" o
   "habilidades_secundarias". Las habilidades válidas son SOLO las que aparecen
   en el contexto de habilidades proporcionado. Nada más. "tipo_atomico" es un
   campo completamente diferente que describe el tipo de contenido, no la
   habilidad del currículo.
9. "prerrequisitos": solo incluir IDs de otros átomos si hay dependencia
   cognitiva clara (prerequisite independence).
   
   **TRANSITIVIDAD DE PRERREQUISITOS (CRÍTICO)**: Los prerrequisitos son TRANSITIVOS.
   Si A es prerrequisito de B, y B es prerrequisito de C, entonces C solo necesita
   listar B como prerrequisito, NO necesita listar A explícitamente. La transitividad
   se asume automáticamente.
   
   **REGLA DE ORO**: NO listes prerrequisitos transitivos. Solo lista prerrequisitos
   DIRECTOS. Si un átomo requiere un concepto o procedimiento que ya está cubierto
   transitivamente por otro prerrequisito, NO lo agregues como prerrequisito adicional.
   
   **OPTIMIZACIÓN DE PRERREQUISITOS COMUNES**: Si muchos átomos necesitan el mismo
   conjunto de prerrequisitos (ej: todos los átomos de fracciones necesitan operaciones
   con enteros), considera agregar esos prerrequisitos a un punto común en la cadena
   de dependencias (un átomo del que todos dependen transitivamente) en lugar de
   agregarlos individualmente a cada átomo. Esto respeta la transitividad y evita
   redundancia. Por ejemplo, si A-09 es prerrequisito de todos los átomos de fracciones
   y decimales, y todos necesitan operaciones con enteros, agrega las operaciones con
   enteros a A-09 en lugar de a cada átomo individual.
   
   **VERIFICACIÓN**: Antes de agregar un prerrequisito, verifica si ya está cubierto
   transitivamente por otro prerrequisito. Si A → B → C, y C necesita A, solo lista B.
10. "notas_alcance": incluir exclusiones relevantes para evitar scope creep.
    DEBE acotar la complejidad especificando:
    - Rangos o límites de tamaño/complejidad (ej: "números pequeños", "hasta X cifras")
    - Exclusiones específicas (ej: "no incluye X", "solo casos simples")
    - Contextos específicos si aplica
    - NO incluir conceptos que excedan el estándar original
11. "descripcion": debe ser descriptiva y completa, explicando claramente qué
    hace el estudiante y en qué contexto. Evita descripciones muy breves o
    genéricas que no aporten información específica sobre el átomo.

## Reglas críticas de granularidad

12. **EVALUACIÓN INDEPENDIENTE (MÁS IMPORTANTE)**: Si dos conceptos, procedimientos
    o habilidades pueden evaluarse por separado, DEBEN ser átomos separados.
    No combines en un solo átomo cosas que requieren diferentes preguntas de
    evaluación o diferentes rúbricas. Esto aplica INCLUSO si comparten reglas,
    principios o procedimientos comunes. La relación conceptual NO justifica
    combinarlos si son evaluables independientemente.
    
    **Conceptos inversos o complementarios (CRÍTICO)**: Si dos conceptos,
    procedimientos o habilidades son inversos o complementarios entre sí (uno
    es la operación inversa del otro, o son operaciones complementarias), pero
    pueden evaluarse por separado con diferentes preguntas o rúbricas, DEBEN
    ser átomos separados. No los combines solo porque son "relacionados",
    "similares" o porque comparten reglas, principios o procedimientos comunes.
    El hecho de que sean inversos o complementarios NO justifica combinarlos
    si requieren evaluación independiente. Pregúntate: ¿Puedo crear una pregunta
    de evaluación solo para la operación A? ¿Puedo crear una pregunta de
    evaluación solo para la operación B? Si ambas respuestas son SÍ, son
    átomos separados.

13. **Títulos con "y" o "y/o"**: Si el título de un átomo contiene "y" o "y/o"
    conectando dos conceptos distintos, pregúntate si pueden evaluarse
    independientemente. Si la respuesta es SÍ, crea átomos separados.

14. **Secuencia pedagógica**: Si un concepto normalmente se enseña antes que
    otro, son átomos separados con prerrequisito explícito.

15. **Procedimientos distintos**: Si dos conceptos requieren algoritmos,
    procedimientos o pasos distintos para ejecutarse o evaluarse, DEBEN ser
    átomos separados. Esto aplica incluso si comparten principios o reglas
    comunes.

    **Complejidad diferente**: Si un procedimiento tiene una versión simple
    (requiere pocos pasos o conceptos básicos) y otra versión compleja
    (requiere pasos adicionales, conceptos avanzados o mayor carga cognitiva),
    DEBEN ser átomos separados. No combines versiones simples y complejas
    del mismo procedimiento en un solo átomo, ya que requieren diferentes
    niveles de dominio y pueden evaluarse independientemente.
    
    **Variantes con algoritmos distintos (CRÍTICO)**: Si un procedimiento tiene
    variantes que requieren algoritmos o métodos distintos (aunque compartan principios
    comunes), DEBEN ser átomos separados. Cada variante con algoritmo distinto debe
    ser evaluable por separado.
    
    **Múltiples algoritmos en un solo átomo (CRÍTICO)**: Si un átomo menciona o requiere
    aplicar múltiples algoritmos DISTINTOS para el mismo procedimiento, DEBES evaluar si
    son realmente diferentes o si son el mismo método explicado de forma diferente. Si los
    algoritmos son cognitivamente tan diferentes que requieren evaluación separada (diferentes
    estrategias cognitivas, diferentes rúbricas), DEBES crear átomos separados. No combines
    múltiples algoritmos en un solo átomo si requieren diferentes estrategias cognitivas o
    diferentes rúbricas de evaluación. **REGLA DE ORO**: Si en los criterios_atomicos o en
    la descripción mencionas múltiples algoritmos distintos (ej: "usando método A" y "usando
    método B"), y estos métodos requieren diferentes pasos, principios o estrategias cognitivas,
    DEBES crear átomos separados. NO es válido tener un criterio que diga "Convierte X usando
    método A" y otro que diga "Convierte Y usando método B" si A y B son algoritmos
    fundamentalmente distintos. Cada algoritmo distinto debe tener su propio átomo.
    
    **VERIFICACIÓN OBLIGATORIA DE CRITERIOS**: Antes de finalizar cada átomo, revisa los
    criterios_atomicos UNO POR UNO. Si encuentras que un criterio menciona un algoritmo/método
    A y otro criterio menciona un algoritmo/método B, y A y B requieren diferentes pasos,
    principios o estrategias cognitivas, DEBES crear átomos separados. NO es válido tener
    múltiples algoritmos distintos en los criterios_atomicos de un mismo átomo. Si los
    algoritmos son fundamentalmente distintos, cada uno debe tener su propio átomo con sus
    propios criterios. **TEST RÁPIDO**: Si puedes crear dos preguntas de evaluación diferentes
    (una para algoritmo A y otra para algoritmo B) con rúbricas distintas, son átomos separados.
    
    **Método estándar preferente**: Si existen múltiples métodos que son realmente distintos
    (no solo diferentes formas de explicar el mismo método), elige UNO como método preferente
    y descríbelo en el átomo. Si un método es estándar, claro y ampliamente aceptado, úsalo
    como preferente. Si necesitas mencionar métodos alternativos que son realmente distintos,
    hazlo solo en notas_alcance, no en la descripción principal ni en los criterios_atomicos.
    El objetivo es que cada átomo tenga un método claro y evaluable, no múltiples opciones
    que generen ambigüedad. **IMPORTANTE**: Si dos métodos son en realidad el mismo método
    explicado de forma diferente (ej: método A explicado como "hacer X" vs "hacer Y que es
    equivalente a X"), no es necesario separarlos ni mencionarlos como métodos distintos.

16. **Estrategias cognitivas diferentes (CRÍTICO)**: Si dos procedimientos requieren
    estrategias cognitivas diferentes (ej: uno es conceptual/teórico y otro
    es procedimental/regla, o uno usa un método A y otro un método B distinto),
    DEBEN ser átomos separados. Un estudiante puede dominar uno y fallar en el
    otro, violando la independencia de evaluación.
    
    **Representaciones diferentes**: Si un procedimiento puede aplicarse a diferentes
    representaciones del mismo concepto (ej: representación A vs representación B), y
    cada representación requiere estrategias cognitivas diferentes o algoritmos distintos,
    DEBEN ser átomos separados. No combines procedimientos que trabajan con representaciones
    diferentes si requieren estrategias cognitivas diferentes o pueden evaluarse
    independientemente. Si puedes crear una pregunta de evaluación solo para la
    representación A y otra solo para la representación B, son átomos separados.
    
    **Variantes con algoritmos fundamentalmente distintos (CRÍTICO)**: Si un procedimiento
    tiene variantes que requieren algoritmos fundamentalmente distintos (ej: un algoritmo
    basado en un principio A vs otro basado en un principio B completamente diferente),
    DEBEN ser átomos separados. Cada variante con un algoritmo fundamentalmente distinto
    debe ser evaluable por separado, ya que un estudiante puede dominar una variante y
    fallar en la otra. No combines variantes que requieren estrategias cognitivas
    fundamentalmente diferentes en un solo átomo.
    
    **Criterios para identificar algoritmos fundamentalmente distintos**:
    - Si puedes crear una pregunta de evaluación solo para la variante A y otra solo
      para la variante B, con rúbricas diferentes, son átomos separados.
    - Si un estudiante puede dominar la variante A y fallar completamente en la variante
      B (o viceversa), son átomos separados.
    - Si las variantes requieren diferentes pasos, diferentes principios o diferentes
      estrategias cognitivas para ejecutarse, son átomos separados.
    - Si las variantes se basan en principios completamente diferentes (ej: un algoritmo
      basado en valor posicional vs otro basado en transformaciones algebraicas), son
      átomos separados.
    
    **IMPORTANTE**: Si dos métodos son en realidad el mismo método explicado de forma
    diferente (mismo algoritmo, misma estrategia cognitiva, solo diferente explicación o
    notación), NO es necesario separarlos. Solo separa cuando los algoritmos son realmente
    distintos y requieren diferentes estrategias cognitivas o diferentes rúbricas de
    evaluación.
    
    **COMPLETITUD (CRÍTICO)**: Si identificas que un procedimiento tiene variantes con
    algoritmos fundamentalmente distintos (incluso si solo lo reconoces al escribir
    notas_alcance), DEBES crear átomos separados para TODAS las variantes relevantes del
    estándar. NO es suficiente mencionar en notas_alcance que "la variante X requiere un
    algoritmo distinto y se excluye". Si reconoces que hay algoritmos distintos, DEBES
    crear el átomo separado para esa variante. El objetivo es cobertura completa y
    granularidad apropiada, no solo reconocer que existen variantes sin crearlas.
    
    **INFERENCIA DE VARIANTES (CRÍTICO)**: Si creas un átomo para una variante de un
    procedimiento y reconoces que hay otra variante con algoritmo distinto, DEBES evaluar
    si esa variante es lógicamente necesaria para cubrir el contenido del estándar. Por
    ejemplo, si el estándar menciona conversión entre representaciones (A→B y B→A), y creas
    un átomo para la variante X de B→A, pero existe una variante Y de B→A con algoritmo
    distinto que es el proceso inverso de A→B (que sí incluye ambas variantes), DEBES crear
    el átomo para la variante Y también. No te limites solo a lo explícitamente mencionado
    en el estándar si la lógica del contenido requiere ambas variantes.
    
    **REGLA DE ORO PARA INFERENCIA**: Si en las notas_alcance de un átomo escribes que
    "excluye la variante Y porque requiere un algoritmo distinto", o "la variante Y requiere
    un algoritmo distinto", o "solo variante X (no variante Y) ya que el algoritmo es distinto",
    DEBES crear inmediatamente el átomo separado para la variante Y. NO es suficiente reconocer
    que existe una variante con algoritmo distinto sin crearla. Si reconoces que hay algoritmos
    distintos, DEBES crear TODOS los átomos correspondientes. Esta es una regla de completitud:
    reconocer que existen variantes con algoritmos distintos implica la obligación de crear átomos
    para todas esas variantes.
    
    **VERIFICACIÓN FINAL OBLIGATORIA**: Antes de finalizar la generación de átomos, revisa TODAS
    las notas_alcance de TODOS los átomos generados. Si encuentras cualquier mención de que se
    excluye una variante porque requiere un algoritmo distinto, DEBES crear inmediatamente el
    átomo para esa variante. Esta verificación es OBLIGATORIA y debe hacerse al final del proceso
    de generación.

17. **Antes de combinar**: Siempre pregunta: "¿Puedo evaluar cada parte por
    separado?" Si SÍ, son átomos separados.

18. **Átomos integradores - PRERREQUISITOS EXHAUSTIVOS (CRÍTICO)**: Si estás
    creando un átomo que "integra" o "combina" múltiples conceptos/procedimientos
    de otros átomos, verifica que:
    - Tiene una intención cognitiva única y clara (no solo "mezcla todo")
    - Requiere ≤4 piezas novedosas de información
    - Puede evaluarse con una rúbrica específica
    - No requiere más de 3-4 prerrequisitos complejos simultáneamente
    - **PRERREQUISITOS EXHAUSTIVOS (CRÍTICO - NO OMITIR)**: Si el átomo integrador
      requiere aplicar múltiples conceptos, procedimientos o habilidades que ya
      fueron cubiertos en otros átomos, DEBES incluir TODOS los prerrequisitos
      necesarios. Esto es OBLIGATORIO. Revisa exhaustivamente:
      * **PASO 1 - IDENTIFICACIÓN COMPLETA**: Identifica TODAS las habilidades,
        conceptos o procedimientos que el átomo integrador puede requerir o
        involucrar. No dejes ninguna fuera.
      * **PASO 2 - TIPOS DE ÁTOMOS**: Incluye tanto los átomos PROCEDIMENTALES
        (operaciones, algoritmos, transformaciones) como los átomos CONCEPTUALES
        (definiciones, representaciones, comparaciones, orden) que son necesarios
        para el átomo integrador. **CRÍTICO**: Si el átomo integrador trabaja con,
        menciona, o requiere entender cualquier concepto fundamental del dominio,
        DEBE incluir el átomo conceptual que define ese concepto, incluso si parece
        "obvio" o "básico". Si el átomo integrador requiere una operación, DEBE
        incluir el átomo procedimental que la cubre. Si el átomo integrador menciona
        o trabaja con un concepto fundamental, el átomo conceptual que define ese
        concepto es un prerrequisito OBLIGATORIO, sin excepciones.
        
        **ALGORITMOS BASE Y CONCEPTOS FUNDAMENTALES**: Si el átomo integrador requiere
        aplicar un algoritmo o procedimiento que se basa en otro algoritmo o concepto
        fundamental (ej: un procedimiento que requiere un algoritmo base A, o un concepto
        que requiere un concepto fundamental B para su interpretación), DEBE incluir el
        átomo que cubre ese algoritmo base o concepto fundamental como prerrequisito,
        incluso si parece "implícito" o "obvio". Los algoritmos base y conceptos
        fundamentales son prerrequisitos OBLIGATORIOS cuando son necesarios para el
        procedimiento o concepto del átomo integrador.
      * **PASO 3 - HABILIDADES CONTEXTUALES (CRÍTICO)**: Si el átomo integrador requiere
        aplicar habilidades del currículo o trabajar con conceptos del dominio, incluye
        los átomos de COMPARACIÓN u ORDEN si el problema puede requerir interpretar,
        comparar, validar resultados o establecer relaciones de orden.
        **OBLIGATORIO**: Si el átomo integrador trabaja con un concepto fundamental del
        dominio (cualquier concepto que sea parte del estándar), y existe un átomo que
        cubre la comparación u orden de ese concepto, DEBE incluirlo como prerrequisito,
        incluso si parece "opcional" o "solo en algunos casos". Si puede necesitar
        convertir entre representaciones, incluye los átomos de conversión. Si puede
        necesitar comparar o establecer orden, DEBE incluir los átomos de comparación u
        orden correspondientes. Esta revisión es OBLIGATORIA.
      * **PASO 4 - REVISIÓN EXHAUSTIVA OBLIGATORIA**: Antes de finalizar un átomo
        integrador, DEBES revisar TODOS los átomos generados (uno por uno) y
        preguntar para cada uno: "¿Este átomo integrador puede necesitar o
        involucrar la habilidad/concepto/procedimiento/transformación que cubre
        este otro átomo?" Si la respuesta es SÍ (incluso si es solo en algunos
        casos, incluso si parece "opcional", incluso si parece "obvio"), DEBES
        incluirlo como prerrequisito. Esta revisión es OBLIGATORIA y debe hacerse
        para TODOS los átomos generados, sin excepción.
      * **PASO 5 - LISTADO EXPLÍCITO**: Para cada habilidad, concepto, procedimiento
        o transformación identificada, identifica el átomo correspondiente que lo
        cubre y lista explícitamente TODOS estos átomos como prerrequisitos. No
        omitas ninguno.
      * **REGLA DE ORO**: Si un átomo integrador puede necesitar algo en CUALQUIER
        escenario (incluso si es raro, incluso si es opcional, incluso si parece
        obvio), ese algo DEBE estar en los prerrequisitos. No hay excepciones.
        No omitas prerrequisitos porque parecen "obvios", "básicos", "evidentes"
        o porque el átomo es "integrador". Si un átomo integrador requiere aplicar
        conceptos A, B y C, debe listar explícitamente los átomos que cubren A, B
        y C como prerrequisitos, sin excepción.
    Si falla en cualquiera, divide en átomos más específicos.

19. **Múltiples algoritmos**: Si un átomo requiere aplicar múltiples algoritmos
    o procedimientos distintos (cada uno con pasos diferentes), generalmente
    deben ser átomos separados. Cada algoritmo distinto = potencialmente un
    átomo separado.

20. **Consistencia habilidad_principal (CRÍTICO - VERIFICACIÓN OBLIGATORIA)**: 
    La "habilidad_principal" declarada DEBE reflejarse claramente en los "criterios_atomicos".
    
    **ANTES DE FINALIZAR CADA ÁTOMO, DEBES VERIFICAR**:
    
    * Lee los criterios_atomicos y pregunta: "¿Un evaluador externo podría identificar
      claramente que el estudiante está desarrollando la habilidad declarada solo
      leyendo los criterios?" Si NO, ajusta la habilidad o los criterios.
    
    * Si la habilidad requiere justificación/razonamiento/evaluación: los criterios deben
      incluir elementos explícitos de justificación, razonamiento o evaluación de validez.
      Si los criterios son principalmente procedimentales sin justificación, la habilidad
      probablemente no sea la apropiada.
    
    * Si la habilidad requiere representación/traducción: los criterios deben incluir
      elementos explícitos de representación, traducción entre sistemas o interpretación
      de representaciones. Si los criterios son principalmente procedimentales sin
      representación explícita, la habilidad probablemente no sea la apropiada.
    
    * Si la habilidad requiere aplicación/modelamiento: los criterios deben incluir
      elementos explícitos de modelamiento, selección de estrategias o interpretación
      contextual. Si los criterios son puramente algorítmicos sin modelamiento, la
      habilidad probablemente no sea la apropiada.
    
    * Si los criterios son puramente procedimentales: la habilidad probablemente deba
      reflejar procedimientos o resolución de problemas, no una que requiera
      justificación o argumentación.
    
    * Si los criterios son puramente conceptuales: la habilidad probablemente deba
      reflejar representación o comprensión conceptual, no una que requiera
      argumentación o resolución de problemas.
    
    **TEST DE CONSISTENCIA**: Los criterios deben ser autosuficientes para demostrar
    la habilidad. No asumas que el título o descripción compensan criterios que no
    reflejan la habilidad. La habilidad declarada debe ser evidente y demostrable en
    lo que el estudiante hace según los criterios, no solo en el título o descripción.
    Si los criterios no demuestran claramente la habilidad declarada, ajusta la habilidad
    o agrega criterios que evalúen explícitamente esa habilidad.

21. **Notas de alcance obligatorias**: Usa "notas_alcance" para acotar la
    complejidad y evitar scope creep. Incluye:
    - Limitaciones de tamaño/complejidad (ej: "números pequeños", "2-3 pasos")
    - Exclusiones relevantes (ej: "no incluye X", "solo casos simples")
    - Contextos específicos si aplica (ej: "solo en contextos Y")
    Esto es especialmente importante para átomos procedimentales e integradores.

22. **Cobertura exhaustiva de estrategias del estándar (CRÍTICO)**: 
    El estándar puede mencionar múltiples estrategias, métodos o enfoques para un mismo
    procedimiento o concepto. DEBES asegurar que todas las estrategias mencionadas
    estén cubiertas:
    
    * Revisa los campos "incluye" y "subcontenidos_clave" del estándar
    * Si el estándar menciona "utilizando diversas estrategias" o lista múltiples métodos,
      verifica que haya átomos que cubran todas las estrategias mencionadas, o que un
      átomo integrador mencione explícitamente todas en sus criterios
    * Si el estándar lista múltiples métodos o enfoques, no asumas que uno es suficiente
    * **VERIFICACIÓN FINAL**: Antes de finalizar, revisa cada mención de estrategias/métodos
      en el estándar y verifica que estén representadas en los átomos generados

23. **Herramientas y conocimientos previos (CRÍTICO)**: 
    Si un átomo requiere una herramienta, concepto o procedimiento que NO está explícitamente
    en el estándar pero el estándar lo permite como herramienta auxiliar:
    
    * DEBES aclarar explícitamente en notas_alcance que esa herramienta se asume como
      conocimiento previo
    * DEBES mencionar que no es objetivo de aprendizaje en este estándar, solo herramienta
    * NO debes crear un átomo separado para esa herramienta si el estándar no la lista como
      contenido a enseñar
    * La aclaración debe ser explícita: "Requiere el uso de [herramienta] como herramienta
      [tipo]. [Herramienta] se asume como conocimiento previo (no está explícitamente en
      este estándar, pero es herramienta necesaria según el estándar)."

24. **Cobertura de procedimientos completos vs pasos intermedios (CRÍTICO)**: 
    Cuando el estándar menciona en "subcontenidos_clave" un procedimiento o proceso completo,
    el átomo debe cubrir el procedimiento COMPLETO, no solo un paso intermedio:
    
    * Si un subcontenido_clave menciona un procedimiento que requiere múltiples pasos
      (preparación inicial, pasos intermedios, pasos finales), el átomo debe cubrir TODOS
      los pasos necesarios para completar el procedimiento desde el inicio hasta el
      resultado final
    * Distingue entre:
      - Procedimiento completo: requiere pasos iniciales + pasos intermedios + pasos finales
        para obtener el resultado
      - Paso intermedio: solo una parte del procedimiento (ej: simplificación, reducción,
        transformación parcial)
    * Si el estándar menciona "Procedimiento X", el átomo debe cubrir el procedimiento completo
      desde el inicio (preparación, manejo de elementos iniciales) hasta el resultado final,
      no solo un paso intermedio
    * Si un subcontenido_clave menciona un procedimiento que requiere manejo de elementos
      iniciales (preparación, organización, transformación inicial), pasos intermedios
      (procesamiento, transformación) y pasos finales (simplificación, reducción, resultado),
      el átomo debe cubrir TODOS
    * **VERIFICACIÓN**: Antes de finalizar, revisa cada subcontenido_clave que mencione un
      procedimiento y verifica que el átomo correspondiente cubra el procedimiento completo,
      no solo un paso intermedio

25. **Correspondencia con subcontenidos_clave (CRÍTICO)**: 
    Si el estándar lista múltiples subcontenidos_clave como elementos separados, cada uno
    debe tener su átomo correspondiente:
    
    * Revisa cada subcontenido_clave del estándar
    * Si un subcontenido_clave está listado como elemento separado, generalmente debe
      tener su átomo separado
    * Si un subcontenido_clave combina múltiples conceptos (ej: "X y Y"), puede dividirse
      según las reglas de granularidad (independencia de evaluación, estrategias cognitivas
      diferentes)
    * Solo combina subcontenidos_clave separados en un solo átomo si TODAS estas condiciones
      se cumplen:
      - Requieren la misma estrategia cognitiva fundamental
      - No pueden evaluarse completamente de forma independiente
      - Son variaciones del mismo procedimiento base (no procedimientos distintos)
      - La diferencia es solo una regla o extensión, no un algoritmo diferente
    * **VERIFICACIÓN**: Antes de finalizar, revisa cada subcontenido_clave y verifica que
      tenga un átomo correspondiente. Si un subcontenido_clave está listado como elemento
      separado, debe tener su átomo separado, a menos que puedas justificar claramente por
      qué deben combinarse según los criterios anteriores
</rules>

<output_format>
Responde SOLO con un array JSON de átomos. Sin markdown, sin explicaciones.
Cada átomo debe seguir exactamente el schema del ejemplo.
</output_format>

<final_instruction>
Basándote en el estándar y las guías de granularidad, genera los átomos de
aprendizaje que descompongan este estándar.

ANTES de generar cada átomo, aplica este checklist:
1. ¿Tiene exactamente una intención cognitiva?
2. ¿Puede evaluarse independientemente (sin necesidad de evaluar otro concepto)?
3. ¿Requiere ≤4 piezas novedosas de información? (cada algoritmo/procedimiento
   distinto cuenta como una pieza)
4. ¿Si el título tiene "y", pueden las partes evaluarse por separado? → Si SÍ, dividir.
5. ¿Combina operaciones inversas o complementarias? (ej: A y su inversa B) →
   Si SÍ, y pueden evaluarse por separado, dividir.
6. ¿Requiere múltiples algoritmos o procedimientos distintos? → Si SÍ, elegir UNO como
   preferente (método estándar) y describir solo ese método. NO menciones múltiples
   métodos en la descripción o criterios, incluso si ambos son válidos. Si los algoritmos
   requieren diferentes estrategias cognitivas o diferentes rúbricas, dividir en átomos
   separados. Si necesitas mencionar métodos alternativos, hazlo solo en notas_alcance.
7. ¿Requieren estrategias cognitivas diferentes? (ej: conceptual vs procedimental,
   método A vs método B, representación A vs representación B) → Si SÍ, dividir.
   Si trabajan con representaciones diferentes y requieren estrategias diferentes, son
   átomos separados.
8. ¿Requiere más de 3-4 prerrequisitos complejos? → Si SÍ, probablemente está
   sobrecargado, considerar dividir.
8b. **VERIFICACIÓN DE TRANSITIVIDAD**: Antes de agregar un prerrequisito, verifica
   si ya está cubierto transitivamente por otro prerrequisito. Si A → B → C, y C
   necesita A, solo lista B. NO listes prerrequisitos transitivos. Si muchos átomos
   necesitan los mismos prerrequisitos, considera agregarlos a un punto común en la
   cadena de dependencias en lugar de agregarlos individualmente.
9. **Si es átomo integrador**: ¿Incluye TODOS los prerrequisitos necesarios?
   **ESTE PASO ES OBLIGATORIO Y DEBE HACERSE EXHAUSTIVAMENTE**. Revisa
   exhaustivamente: identifica TODAS las habilidades, conceptos, procedimientos
   o transformaciones que el átomo puede requerir o involucrar (tanto conceptuales
   como procedimentales), y lista explícitamente los átomos correspondientes
   como prerrequisitos. Incluye:
   * Átomos CONCEPTUALES (definiciones, representaciones) si el átomo integrador
     trabaja con esos conceptos. **CRÍTICO**: Si el átomo integrador menciona,
     trabaja con, o requiere entender un concepto fundamental (cualquier concepto
     que sea parte del dominio del estándar), DEBE incluir el átomo conceptual que
     define ese concepto, incluso si parece "obvio", "básico" o "evidente". Si el
     átomo integrador trabaja con un concepto, el átomo conceptual que lo define es
     un prerrequisito OBLIGATORIO, sin excepciones.
   * Átomos de COMPARACIÓN u ORDEN si el átomo integrador puede requerir
     interpretar, comparar, validar resultados o establecer relaciones de orden.
     **CRÍTICO**: Si el átomo integrador trabaja con un concepto fundamental del
     dominio, y existe un átomo que cubre la comparación u orden de ese concepto,
     DEBE incluirlo como prerrequisito, incluso si parece "opcional" o "solo en
     algunos casos". Si puede necesitar comparar o establecer orden, DEBE incluir
     los átomos de comparación u orden correspondientes. Esta revisión es OBLIGATORIA.
   * Átomos de CONVERSIÓN o TRANSFORMACIÓN si el átomo integrador puede requerir
     cambiar entre representaciones. Si puede necesitar convertir, DEBE incluir
     los átomos de conversión.
   * CUALQUIER otro átomo que cubra una habilidad, procedimiento o
     transformación que el átomo integrador pueda necesitar en algún escenario,
     incluso si parece "opcional", "solo en algunos casos", "obvio" o "básico".
     Si puede necesitarlo en CUALQUIER escenario, DEBE estar en los prerrequisitos.
   * Átomos PROCEDIMENTALES (operaciones, algoritmos) que el átomo integrador
     puede necesitar aplicar. Si puede necesitar una operación, DEBE incluir
     el átomo procedimental correspondiente.
   * **REVISIÓN FINAL OBLIGATORIA**: Antes de finalizar, DEBES revisar TODOS
     los átomos generados (uno por uno, sin excepción) y preguntar para cada
     uno: "¿Este átomo integrador puede necesitar o involucrar lo que cubre
     este otro átomo?" Si la respuesta es SÍ (incluso si es solo en algunos
     casos, incluso si parece opcional, incluso si parece obvio), DEBES
     incluirlo como prerrequisito. Esta revisión es OBLIGATORIA.
   **REGLA DE ORO**: No omitas ninguno porque parezcan "obvios", "opcionales",
   "básicos", "evidentes" o porque el átomo es "integrador". Si puede necesitarlo,
   DEBE estar en los prerrequisitos. Sin excepciones.
   
   **ÁTOMOS INTEGRADORES - VERIFICACIÓN DE CARGA COGNITIVA (CRÍTICO)**:
   Si un átomo integra múltiples operaciones, representaciones, procedimientos o conceptos:
   
   * Pregúntate: "¿Un estudiante puede fallar en este átomo por dominar algunas partes
     pero no otras?" Si SÍ, considera subdividir
   * Pregúntate: "¿Este átomo requiere mantener en memoria de trabajo más de 3-4 elementos
     complejos simultáneamente?" Si SÍ, considera subdividir o crear variantes graduadas
   * Si el átomo combina múltiples elementos complejos (conversiones + operaciones +
     transformaciones + validaciones), considera si es demasiado complejo para un solo
     salto de aprendizaje
   * **OPCIÓN**: Puedes crear dos átomos: uno "básico" (versión simplificada) y otro
     "avanzado" o "integrador" (versión completa), etiquetando claramente cuál es cuál
   * Si decides mantener un solo átomo integrador complejo, DEBES etiquetarlo claramente
     como "integrador" o "de cierre" en notas_alcance y asegurar que todos los prerrequisitos
     estén exhaustivamente listados
10. ¿La "habilidad_principal" es una habilidad válida del contexto (NO un valor
   de "tipo_atomico")? → **CRÍTICO**: Verifica que "habilidad_principal" sea
   una de las habilidades válidas del contexto proporcionado (revisa la sección
   "Habilidades del currículo"). NO uses valores de "tipo_atomico" (como
   "procedimiento", "concepto", "representacion", "argumentacion", "modelizacion")
   en "habilidad_principal". Son campos completamente diferentes. "tipo_atomico"
   describe el tipo de contenido, "habilidad_principal" describe la habilidad
   del currículo que el átomo desarrolla.
11. ¿La "habilidad_principal" se refleja en los "criterios_atomicos"? → Si NO,
   ajustar habilidad o criterios. Los criterios deben demostrar claramente
   la habilidad declarada. Revisa las habilidades válidas del contexto
   proporcionado y asegúrate de que la habilidad declarada sea una de ellas y
   que se refleje claramente en los criterios. Si los criterios son puramente
   procedimentales o puramente conceptuales, considera si la habilidad
   declarada es la apropiada según las habilidades válidas del contexto.
   Verifica que la habilidad sea evidente en lo que el estudiante hace según
   los criterios.
12. ¿Tiene "notas_alcance" que acoten la complejidad? → Si NO, agregar.
    Las notas deben especificar rangos, límites, exclusiones y contextos,
    pero NO deben incluir conceptos que excedan el estándar original.
13. ¿La "descripcion" es descriptiva y completa? → Si es muy breve o genérica,
    expandir para que explique claramente qué hace el estudiante y en qué
    contexto.
14. ¿El átomo combina versiones simples y complejas del mismo procedimiento?
    → Si SÍ, considerar dividir en dos átomos (uno simple, uno complejo).
15. ¿El átomo menciona múltiples algoritmos o métodos distintos para el mismo
    procedimiento? → Si SÍ, evaluar si son realmente distintos o el mismo método explicado
    de forma diferente. Si son algoritmos fundamentalmente distintos (requieren diferentes
    pasos, principios o estrategias cognitivas), DEBES dividir en átomos separados. **CRÍTICO**:
    NO es válido tener criterios_atomicos que mencionen múltiples algoritmos distintos. Si
    un criterio dice "Convierte X usando método A" y otro dice "Convierte Y usando método B",
    y A y B son algoritmos fundamentalmente distintos, DEBES crear átomos separados. Si los
    métodos son realmente distintos, cada uno debe tener su propio átomo. Si son el mismo
    método explicado de forma diferente, elegir UNO como preferente y describir solo ese método.
    NO menciones múltiples métodos distintos en la descripción o criterios. Si necesitas
    mencionar métodos alternativos que son realmente distintos, crea átomos separados, no
    los menciones solo en notas_alcance. **VERIFICACIÓN OBLIGATORIA**: Revisa cada criterio
    individualmente. Si encuentras que diferentes criterios requieren diferentes algoritmos
    o métodos que son fundamentalmente distintos, DEBES separar en átomos distintos. **TEST
    RÁPIDO**: Si un criterio dice "Convierte variante X usando método A" y otro dice
    "Convierte variante Y usando método B", y A y B son algoritmos distintos, son átomos
    separados. NO combines variantes con algoritmos distintos en un solo átomo.
16. ¿El átomo trabaja con diferentes representaciones del mismo concepto que
    requieren estrategias cognitivas diferentes? → Si SÍ, dividir en átomos separados
    (uno por representación).
17. ¿El átomo combina variantes de un procedimiento que requieren algoritmos
    fundamentalmente distintos? → Si SÍ, dividir en átomos separados. Pregúntate:
    - ¿Puedo crear una pregunta de evaluación solo para la variante A?
    - ¿Puedo crear una pregunta de evaluación solo para la variante B?
    - ¿Un estudiante puede dominar la variante A y fallar en la variante B?
    - ¿Las variantes requieren diferentes pasos, principios o estrategias cognitivas?
    Si la respuesta es SÍ a cualquiera, son átomos separados. No combines variantes
    que requieren algoritmos fundamentalmente distintos en un solo átomo. **CRÍTICO**:
    Si reconoces que hay variantes con algoritmos distintos (incluso si solo lo
    mencionas en notas_alcance), DEBES crear átomos separados para TODAS las variantes
    relevantes del estándar. NO es suficiente mencionar en notas_alcance que "la
    variante X requiere un algoritmo distinto y se excluye". Si reconoces que hay
    algoritmos distintos, DEBES crear el átomo separado. **REGLA DE ORO**: Si en las
    notas_alcance escribes que "excluye la variante Y porque requiere un algoritmo
    distinto", o "la variante Y requiere un algoritmo distinto", DEBES crear
    inmediatamente el átomo separado para la variante Y. NO es suficiente reconocer
    que existe una variante con algoritmo distinto sin crearla. **INFERENCIA**: Si creas
    un átomo para una variante y reconoces que hay otra variante con algoritmo distinto,
    evalúa si esa variante es lógicamente necesaria para cubrir el contenido del
    estándar (ej: si el estándar incluye conversión A→B que cubre variantes X e Y, y
    creas un átomo para conversión B→A variante X, también debes crear el átomo para
    conversión B→A variante Y).

18. ¿El átomo menciona conceptos, operaciones o procedimientos que NO están
    explícitamente en el estándar? → Si SÍ, eliminar la mención o aclarar en
    notas_alcance que es conocimiento previo. Revisa especialmente términos
    compuestos, acrónimos o conceptos relacionados que pueden incluir elementos
    no listados en el estándar.

19. ¿Todas las estrategias/métodos mencionados en el estándar están cubiertas en
    los átomos? → Si NO, crear átomos adicionales o agregar criterios que las
    cubran explícitamente. No asumas que una estrategia es suficiente si el
    estándar menciona múltiples.

20. ¿Los átomos integradores tienen carga cognitiva razonable?
    → Si un átomo integra más de 3-4 elementos complejos simultáneamente, considerar
    subdividir en versión básica y avanzada, o etiquetar claramente como "integrador
    de cierre" con prerrequisitos exhaustivos.

Prioriza la INDEPENDENCIA DE EVALUACIÓN sobre todo: si dos cosas pueden
evaluarse por separado, son átomos separados, incluso si son conceptualmente
relacionadas o comparten reglas similares.

Asegúrate de incluir átomos tanto CONCEPTUALES (qué es, cómo se define) como
PROCEDIMENTALES (cómo se hace) según lo que requiera el estándar.

**INSTRUCCIÓN FINAL CRÍTICA - VERIFICACIÓN DE COMPLETITUD**: Antes de generar el JSON
final, DEBES hacer una revisión final exhaustiva:

1. **VERIFICACIÓN DE VARIANTES CON ALGORITMOS DISTINTOS**: Revisa TODAS las notas_alcance
   de TODOS los átomos generados. Si encuentras cualquier mención de que se excluye una
   variante porque requiere un algoritmo distinto (ej: "solo variante X, no variante Y ya
   que el algoritmo es distinto"), DEBES crear inmediatamente el átomo para esa variante
   faltante. Esta verificación es OBLIGATORIA y debe hacerse ANTES de finalizar.

2. **ÁTOMOS INTEGRADORES - PRERREQUISITOS**: Si has creado algún átomo integrador (que
   combina o integra múltiples conceptos/procedimientos), DEBES hacer una revisión final
   exhaustiva de sus prerrequisitos:
1. Lista TODOS los átomos que has generado.
2. Para cada átomo integrador, identifica TODOS los conceptos fundamentales que
   menciona, trabaja con, o requiere entender. Para cada concepto identificado,
   encuentra el átomo conceptual que lo define y asegúrate de incluirlo como
   prerrequisito. Esto es OBLIGATORIO, incluso si el concepto parece "obvio" o
   "básico".
3. Para cada átomo integrador, revisa UNO POR UNO todos los demás átomos y
   pregunta: "¿Este átomo integrador puede necesitar o involucrar lo que cubre
   este otro átomo?" (habilidad, concepto, procedimiento, transformación,
   comparación, conversión, etc.)
4. Si la respuesta es SÍ (incluso si es solo en algunos casos, incluso si parece
   opcional, incluso si parece obvio), DEBES incluirlo como prerrequisito.
5. Asegúrate de incluir: conceptos fundamentales (OBLIGATORIO), comparaciones,
   conversiones, operaciones, transformaciones, y cualquier otra habilidad que el
   átomo integrador pueda necesitar.
6. No omitas ninguno. Esta revisión es OBLIGATORIA y debe hacerse exhaustivamente
   antes de generar el JSON final.
</final_instruction>"""

