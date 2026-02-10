"""Rules for atom generation prompts.

Contains the detailed rules that guide the LLM in generating learning atoms.
"""

from __future__ import annotations

ATOM_GENERATION_RULES = """
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
5. 1-4 ejemplos_conceptuales por átomo (NO ejercicios completos).
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
"""
