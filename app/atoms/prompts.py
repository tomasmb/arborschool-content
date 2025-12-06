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

**IMPORTANTE sobre campos:**
- "habilidad_principal" y "habilidades_secundarias" SOLO pueden contener
  habilidades válidas del contexto proporcionado (revisa la sección "Habilidades
  del currículo" en el contexto).
- "tipo_atomico" es un campo COMPLETAMENTE DIFERENTE y puede ser:
  concepto, procedimiento, representacion, argumentacion, modelizacion, concepto_procedimental
- NO confundas "tipo_atomico" con "habilidades_secundarias". Son campos distintos.
- NO uses valores de "tipo_atomico" en "habilidades_secundarias".
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
   contexto proporcionado (puede estar vacía []). NO uses "tipo_atomico" como
   habilidad. Las habilidades válidas son SOLO las que aparecen en el contexto
   de habilidades proporcionado. Nada más.
9. "prerrequisitos": solo incluir IDs de otros átomos si hay dependencia
   cognitiva clara (prerequisite independence).
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
    
    **Variantes con algoritmos distintos**: Si un procedimiento tiene variantes
    que requieren algoritmos o métodos distintos (aunque compartan principios
    comunes), DEBEN ser átomos separados. Cada variante con algoritmo distinto
    debe ser evaluable por separado.

16. **Estrategias cognitivas diferentes**: Si dos procedimientos requieren
    estrategias cognitivas diferentes (ej: uno es conceptual/teórico y otro
    es procedimental/regla, o uno usa un método A y otro un método B distinto),
    DEBEN ser átomos separados. Un estudiante puede dominar uno y fallar en el
    otro, violando la independencia de evaluación.

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
      * **PASO 3 - HABILIDADES CONTEXTUALES**: Si el átomo integrador requiere
        "resolver problemas" o "aplicar" algo, incluye los átomos de COMPARACIÓN
        u ORDEN si el problema puede requerir interpretar, comparar o validar
        resultados. Si puede necesitar convertir entre representaciones, incluye
        los átomos de conversión. Si puede necesitar comparar, incluye los átomos
        de comparación.
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

20. **Consistencia habilidad_principal (CRÍTICO)**: La "habilidad_principal"
    declarada DEBE reflejarse claramente en los "criterios_atomicos". Antes de
    finalizar cada átomo, verifica:
    * Si declaras "argumentar", los criterios deben incluir elementos de
      justificación, razonamiento o evaluación de validez.
    * Si declaras "representar", los criterios deben incluir elementos de
      representación, traducción entre sistemas o interpretación de
      representaciones.
    * Si declaras "resolver_problemas", los criterios deben incluir elementos
      de modelamiento, selección de estrategias o interpretación contextual.
    * Si los criterios son puramente procedimentales (solo algoritmos o pasos),
      considera cambiar la habilidad a "resolver_problemas" o "representar"
      según corresponda.
    * Si los criterios son puramente conceptuales (solo definiciones o
      reconocimiento), considera cambiar la habilidad a "representar".
    La habilidad declarada debe ser evidente en lo que el estudiante hace según
    los criterios, no solo en el título o descripción.

21. **Notas de alcance obligatorias**: Usa "notas_alcance" para acotar la
    complejidad y evitar scope creep. Incluye:
    - Limitaciones de tamaño/complejidad (ej: "números pequeños", "2-3 pasos")
    - Exclusiones relevantes (ej: "no incluye X", "solo casos simples")
    - Contextos específicos si aplica (ej: "solo en contextos Y")
    Esto es especialmente importante para átomos procedimentales e integradores.
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
6. ¿Requiere múltiples algoritmos o procedimientos distintos? → Si SÍ, considerar dividir.
7. ¿Requieren estrategias cognitivas diferentes? (ej: conceptual vs procedimental,
   método A vs método B) → Si SÍ, dividir.
8. ¿Requiere más de 3-4 prerrequisitos complejos? → Si SÍ, probablemente está
   sobrecargado, considerar dividir.
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
     interpretar, comparar o validar resultados. Si puede necesitar comparar,
     DEBE incluir los átomos de comparación.
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
10. ¿La "habilidad_principal" se refleja en los "criterios_atomicos"? → Si NO,
   ajustar habilidad o criterios. Los criterios deben demostrar claramente
   la habilidad declarada. Si los criterios son puramente procedimentales,
   la habilidad probablemente deba ser "resolver_problemas". Si son puramente
   conceptuales, probablemente deba ser "representar". Verifica que la habilidad
   sea evidente en lo que el estudiante hace según los criterios.
11. ¿Tiene "notas_alcance" que acoten la complejidad? → Si NO, agregar.
    Las notas deben especificar rangos, límites, exclusiones y contextos,
    pero NO deben incluir conceptos que excedan el estándar original.
12. ¿La "descripcion" es descriptiva y completa? → Si es muy breve o genérica,
    expandir para que explique claramente qué hace el estudiante y en qué
    contexto.
13. ¿El átomo combina versiones simples y complejas del mismo procedimiento?
    → Si SÍ, considerar dividir en dos átomos (uno simple, uno complejo).

Prioriza la INDEPENDENCIA DE EVALUACIÓN sobre todo: si dos cosas pueden
evaluarse por separado, son átomos separados, incluso si son conceptualmente
relacionadas o comparten reglas similares.

Asegúrate de incluir átomos tanto CONCEPTUALES (qué es, cómo se define) como
PROCEDIMENTALES (cómo se hace) según lo que requiera el estándar.

**INSTRUCCIÓN FINAL CRÍTICA - ÁTOMOS INTEGRADORES**: Antes de generar el JSON
final, si has creado algún átomo integrador (que combina o integra múltiples
conceptos/procedimientos), DEBES hacer una revisión final exhaustiva de sus
prerrequisitos:
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

