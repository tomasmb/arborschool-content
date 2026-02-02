"""Final instruction for atom generation prompts.

Contains the comprehensive checklist and final verification steps.
"""

from __future__ import annotations


def build_final_instruction() -> str:
    """Build the final instruction section for atom generation prompts."""
    return """
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
"""
