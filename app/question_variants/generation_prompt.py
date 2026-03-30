"""Prompt construction for the variant generation phase.

Builds the full LLM prompt from source question, blueprints, and
construct contract. Split into section helpers to keep each under
100 lines.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from app.question_variants.contracts.family_specs import build_family_prompt_rules
from app.question_variants.contracts.structural_profile import build_construct_contract
from app.question_variants.models import SourceQuestion, VariantBlueprint
from app.question_variants.prompt_context import build_prompt_source_snapshot
from app.question_variants.shared_helpers import (
    build_source_structural_profile,
    extract_visual_context,
)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


def build_generation_prompt(
    source: SourceQuestion,
    n: int,
    blueprints: list[VariantBlueprint] | None = None,
) -> str:
    """Build the complete generation prompt for a source question.

    Pure function with no side effects -- used by both the sync
    generator and the batch request builders.
    """
    atoms_desc = [
        f"- {a.get('atom_title', 'N/A')}: {a.get('reasoning', '')}"
        for a in source.primary_atoms
    ]
    atoms_text = "\n".join(atoms_desc) or "No atoms specified"

    diff = source.difficulty
    diff_text = (
        f"{diff.get('level', 'Medium')} (score: {diff.get('score', 0.5)})"
    )
    structural_profile = build_source_structural_profile(source)
    construct_contract = build_construct_contract(
        source.question_text,
        source.qti_xml,
        bool(source.image_urls),
        source.primary_atoms,
        source.metadata,
        source.choices,
        source.correct_answer,
    )
    visual_context = extract_visual_context(source.qti_xml)

    source_snapshot = build_prompt_source_snapshot(
        question_id=source.question_id,
        question_text=source.question_text,
        choices=source.choices,
        correct_answer=source.correct_answer,
        difficulty_text=diff_text,
        atoms_text=atoms_text,
        construct_contract=construct_contract,
        structural_profile=structural_profile,
        visual_context=visual_context,
        include_qti_xml=source.qti_xml,
    )

    image_instruction = _resolve_image_instruction(source)
    blueprint_instruction = _resolve_blueprint_instruction(blueprints, n)
    rules_block = _build_rules_block(
        structural_profile, construct_contract,
    )
    task_block = _build_task_format_block(n)

    return f"""
<role>
Eres un profesor de matemáticas creando variantes de ejercicios para
exámenes PAES. Tu tarea es generar variantes duras del mismo ítem,
manteniendo exactamente el constructo matemático evaluado y respetando
el contrato estructural.
</role>

{rules_block}

{image_instruction}
{blueprint_instruction}

{source_snapshot}

{task_block}
"""


def build_variant_metadata(
    source: SourceQuestion,
    variant_data: Dict[str, Any],
    blueprint: VariantBlueprint | None = None,
) -> Dict[str, Any]:
    """Build metadata for a variant, inheriting from source.

    Pure function -- shared by sync and batch paths.
    """
    metadata: Dict[str, Any] = {
        "selected_atoms": source.atoms.copy(),
        "general_analysis": source.metadata.get("general_analysis", ""),
        "difficulty": source.difficulty.copy(),
        "validation": {},
        "habilidad_principal": source.metadata.get(
            "habilidad_principal", {},
        ),
        "construct_contract": build_construct_contract(
            source.question_text,
            source.qti_xml,
            bool(source.image_urls),
            source.primary_atoms,
            source.metadata,
            source.choices,
            source.correct_answer,
        ),
        "source_info": {
            "source_question_id": source.question_id,
            "source_test_id": source.test_id,
            "change_description": variant_data.get(
                "change_description", "",
            ),
        },
        "generator_self_check": variant_data.get("self_check", {}),
        "generator_declared_correct_identifier": str(
            variant_data.get("correct_choice_identifier", ""),
        ).strip(),
    }
    if blueprint:
        metadata["planning_blueprint"] = {
            "variant_id": blueprint.variant_id,
            "scenario_description": blueprint.scenario_description,
            "non_mechanizable_axes": blueprint.non_mechanizable_axes,
            "required_reasoning": blueprint.required_reasoning,
            "difficulty_target": blueprint.difficulty_target,
            "requires_image": blueprint.requires_image,
            "image_description": blueprint.image_description,
            "selected_shape_id": blueprint.selected_shape_id,
        }
    return metadata


# ------------------------------------------------------------------
# Section helpers (each < 100 lines)
# ------------------------------------------------------------------


def _resolve_image_instruction(source: SourceQuestion) -> str:
    image_info = source.metadata.get("image_info", {})
    if image_info.get("image_type") == "decorative":
        return (
            "7. ESTA PREGUNTA CONTIENE UNA IMAGEN DECORATIVA (Support "
            "visual). DEBES INCLUIR LA ETIQUETA <img ...> EXACTAMENTE "
            "IGUAL QUE EN LA ORIGINAL dentro del texto."
        )
    if source.image_urls:
        return (
            "7. ESTA PREGUNTA DEPENDE DE SOPORTE VISUAL. Si el contrato "
            "requiere interpretación de representación (ej. gráficos, "
            "infografías, geometría), DEBES MANTENER la representación "
            "visual como evidencia primaria. NO la reemplaces por una "
            "tabla o lista de texto explícita que evite la interpretación "
            "visual. Para la nueva imagen, incluye una etiqueta "
            "<img src='requiere_nueva_imagen.png' alt='[DESCRIBE "
            "EXACTAMENTE CÓMO DEBE DIBUJARSE LA NUEVA IMAGEN, CON TODOS "
            "LOS DATOS Y FORMAS NECESARIAS]'/>."
        )
    return (
        "7. LA PREGUNTA FUENTE NO USA SOPORTE VISUAL. "
        "NO introduzcas figura, gráfico, diagrama, infografía, tabla "
        "ni imagen en la variante."
    )


def _resolve_blueprint_instruction(
    blueprints: list[VariantBlueprint] | None,
    n: int,
) -> str:
    if not blueprints:
        return ""
    bp_payload = [
        {
            "variant_id": bp.variant_id,
            "scenario_description": bp.scenario_description,
            "non_mechanizable_axes": bp.non_mechanizable_axes,
            "required_reasoning": bp.required_reasoning,
            "difficulty_target": bp.difficulty_target,
            "requires_image": bp.requires_image,
            "image_description": bp.image_description,
            "selected_shape_id": bp.selected_shape_id,
        }
        for bp in blueprints[:n]
    ]
    return (
        "8. DEBES respetar exactamente estos blueprints por variante "
        "(mismo orden):\n"
        f"{json.dumps(bp_payload, ensure_ascii=False, indent=2)}\n"
        "Cada variante debe incorporar sus ejes no mecanizables."
    )


def _build_rules_block(
    structural_profile: dict[str, Any],
    construct_contract: dict[str, Any],
) -> str:
    """Return the <reglas_estrictas> XML block."""
    family_rules = "\n".join(
        f"{idx}. {rule}"
        for idx, rule in enumerate(
            build_family_prompt_rules(construct_contract), start=8,
        )
    )
    expectation = str(
        construct_contract.get("non_mechanizable_expectation") or "medium",
    )
    min_axes = 1 if expectation == "low" else 2
    axes_policy = (
        "En esta familia intrínsecamente rutinaria, puede bastar con 1 "
        "eje estructural fuerte si la variante no es superficial, los "
        "distractores siguen siendo plausibles y la forma del ítem no "
        "queda casi idéntica."
        if min_axes == 1
        else "Debes materializar al menos 2 ejes estructurales relevantes "
        "o un cambio equivalente en profundidad."
    )
    auxiliary_policy = _resolve_auxiliary_policy(
        construct_contract, expectation,
    )
    hard_constraints = construct_contract.get("hard_constraints", [])
    if hard_constraints:
        clist = "\n".join(f"    - {c}" for c in hard_constraints)
        constraints_instruction = (
            "17. RESTRICCIONES DURAS DEL CONTRATO OBLIGATORIAS:\n" + clist
        )
    else:
        constraints_instruction = ""
    shape_instruction = (
        "18. POLÍTICA DE SHAPE (Family-Constrained): Usa el "
        "'selected_shape_id' y la 'scenario_description' del blueprint "
        "como guía estructural principal. Debes cubrir los cambios "
        "obligatorios de la Shape elegida y evitar sus cambios prohibidos. "
        "Puedes ajustar la redacción superficial, pero no ignorar la "
        "lógica de transformación definida por esa Shape."
    )

    return f"""<reglas_estrictas>
1. La variante DEBE evaluar EXACTAMENTE el mismo concepto que la original
2. La variante DEBE mantenerse dentro del objetivo de dificultad del blueprint/contrato
   (igual o, cuando corresponda, levemente más difícil sin cambiar de constructo).
3. SOLO puedes cambiar lo que el contrato permita cambiar:
   - Valores numéricos
   - Nombres, objetos o escenario
   - Forma de presentación o ejes estructurales no mecanizables, siempre dentro del mismo contrato
4. NO puedes cambiar:
   - El tipo de operación matemática requerida
   - Sustancialmente la cantidad de pasos para resolver
   - El nivel de abstracción o complejidad
   Se permite, solo cuando el contrato/familia lo admite, un paso cognitivo adicional breve
   o un cálculo intermedio conceptual que des-mecanice el ítem sin cambiar el constructo.
5. La respuesta correcta DEBE poder calcularse con el MISMO procedimiento
6. Los distractores DEBEN representar errores lógicos o procedimentales plausibles y documentados.
7. DEBES respetar estas invariantes estructurales:
   {json.dumps(structural_profile, ensure_ascii=False)}
8. Si la fuente no usa incógnitas algebraicas, NO puedes introducir x, y, z ni ecuaciones a resolver.
9. Debes respetar el contrato de constructo completo, especialmente el modo de evidencia.
    Si el contrato dice "representation_primary", NO reemplaces la interpretación de representación
    por una tabla o lista de datos que permita responder sin interpretar la representación.
10. Debes respetar la accion cognitiva y la estructura de solucion del contrato.
    No conviertas una tarea de interpretacion en una de calculo directo, ni una de un paso
    en una de varios pasos, ni una de sustitucion algebraica en una modelacion distinta.
11. {auxiliary_policy}
12. FORMA ALGEBRAICA (CRÍTICO): Si el contrato define la propiedad "formula_shape", tu variante DEBE preservar
    esa misma forma algebraica o una formulación verbal estrictamente equivalente permitida por la familia.
13. Si el contrato incluye "distractor_archetypes", conserva esos mismos arquetipos de error.
    No reemplaces distractores conceptuales por valores arbitrarios ni por errores de otro tipo.
14. NO aumentes la carga de relaciones de referencia de la fuente: no agregues múltiples equivalencias,
    tasas de cambio o listados de referencia si la fuente sólo necesita una.
15. Si las opciones son numéricas, cada distractor debe corresponder a un error concreto y explicable.
    No uses valores arbitrarios o absurdos; mantén coherencia de escala con la respuesta correcta.
16. Debes realizar de verdad al menos {min_axes} eje(s) no mecanizable(s) y poder declararlos
    explícitamente en el self-check final.
    Política específica: {axes_policy}
17. PROTECCIÓN CONTRA DRIFT DE CONSTRUCTO:
    - NO cambies la polaridad argumentativa (ej. si la fuente pide refutar, no pidas justificar).
    - NO cambies la polaridad extrema (si la fuente pide el "máximo/mayor", no pidas el "mínimo/menor").
    - NO cambies el patrón de cambio porcentual (ej. aumento vs descuento deben mantenerse).
    - NO modifiques la cantidad de series en un gráfico (si hay una serie, no agregues dos).
    - No cambies el dominio/subdominio estadístico o matemático evaluado por la pregunta.
    - Solo modifica los datos en evaluación, no el tipo de conclusión.
{family_rules}
{constraints_instruction}
{shape_instruction}
</reglas_estrictas>"""


def _resolve_auxiliary_policy(
    construct_contract: dict[str, Any],
    expectation: str,
) -> str:
    hard = construct_contract.get("hard_constraints", [])
    if "must_not_add_auxiliary_transformations" in hard:
        return (
            "NO agregues conversiones, equivalencias ni pasos intermedios "
            "adicionales respecto de la fuente."
        )
    if expectation == "low":
        return (
            "Evita agregar transformaciones auxiliares gratuitas. Puedes "
            "introducir, como máximo, un paso cognitivo o intermedio breve "
            "si ayuda a des-mecanizar sin cambiar el constructo ni la "
            "banda de dificultad objetivo."
        )
    return (
        "Evita agregar transformaciones auxiliares gratuitas. Solo se "
        "permite un paso intermedio corto y justificado si mejora la "
        "no-mecanizabilidad y conserva el mismo método central."
    )


def _build_task_format_block(n: int) -> str:
    """Return the <tarea>, <formato_respuesta>, and <restriccion_critica> blocks."""
    return f"""<tarea>
Genera exactamente {n} variantes. Cada variante DEBE:
1. Tener una respuesta correcta DIFERENTE a la original (distintos números)
2. Mantener exactamente 4 opciones (A, B, C, D) con distractores plausibles
3. Usar el MISMO formato QTI 3.0 que la original
4. Incorporar cambios no mecanizables reales dentro del contrato
   (no basta con cambio superficial de nombres o números)
5. NO agregues bloques de feedback, solución, ni retroalimentación inline
6. Antes de responder, verifica internamente que NO cambiaste la forma de tarea
7. Si usas soporte visual, deja los porcentajes, cantidades o relaciones también en texto visible.
8. Si la fuente evalúa afirmaciones sobre datos, tu variante DEBE incluir un conjunto de datos explícito
   (tabla o lista estructurada) y las alternativas deben seguir siendo afirmaciones sobre esos datos.
9. INTEGRIDAD QTI (CRÍTICA): Incluye obligatoriamente <responseDeclaration> con
   <correctResponse><value>LETTER</value></correctResponse> al inicio del item.
9.b Declara "correct_choice_identifier" en el JSON con el identifier exacto de la alternativa correcta.
10. DISTRACTORES RAZONADOS (CRÍTICO): Antes de cada opción distractora en tu XML, escribe un comentario
    XML documentando qué error matemático específico representa ese distractor.
    NUNCA documentes la opción correcta con comentarios como "correcta" o equivalentes.

Para cada variante, genera:
- El XML QTI 3.0 completo
- Una breve explicación del cambio realizado
- Un self-check breve del contrato:
  - "task_form_preserved", "evidence_mode_preserved", "cognitive_action_preserved",
    "solution_structure_preserved", "auxiliary_transformations_preserved",
    "distractor_logic_preserved": true/false
  - "realized_non_mechanizable_axes": ["eje1", "eje2"]
  - "main_risk_checked": "texto breve"
</tarea>

<formato_respuesta>
Responde con un JSON con esta estructura:
{{{{
  "variants": [
    {{{{
      "qti_xml": "<qti-assessment-item ...>...</qti-assessment-item>",
      "correct_choice_identifier": "ChoiceB",
      "change_description": "Cambié los valores de X a Y...",
      "self_check": {{{{
        "task_form_preserved": true,
        "evidence_mode_preserved": true,
        "cognitive_action_preserved": true,
        "solution_structure_preserved": true,
        "auxiliary_transformations_preserved": true,
        "distractor_logic_preserved": true,
        "realized_non_mechanizable_axes": ["representacion", "distractor_dominante"],
        "main_risk_checked": "No reemplacé la representación por una tabla explícita."
      }}}}
    }}}}
  ]
}}}}
</formato_respuesta>

<reglas_encoding>
CRÍTICO — ENCODING UTF-8:
- Escribe SIEMPRE los caracteres españoles directamente en UTF-8.
- CORRECTO: é, ó, á, ú, í, ñ, ü, ¿, ¡, Á, É, Í, Ó, Ú, Ñ
- INCORRECTO: &oacute; &aacute; &eacute; &iacute; &uacute; &ntilde; &nbsp;
  (esas son entidades HTML — NUNCA las uses, rompen el XML)
- Escribe símbolos directamente: × ÷ ≥ ≤ → ° · « » − ² ³
  NO uses &times; &divide; &ge; &le; &rarr; &deg; &middot; etc.
- Las ÚNICAS entidades permitidas en XML son: &amp; &lt; &gt; &quot; &apos;
</reglas_encoding>

<restriccion_critica>
IMPORTANTE — ESTRUCTURA XML:
- Usar namespace xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0"
- INCLUIR OBLIGATORIAMENTE 'title' y 'timeDependent="false"' en la etiqueta raíz
- Tener un identifier único (diferente al original)
- Mantener la estructura exacta de la pregunta original
- Usar MathML para expresiones matemáticas si la original las usa
- CRÍTICO: Si la pregunta contiene <mtable>, <mtr>, <mtd>, INCLUIRLAS COMPLETAS.

IMPORTANTE — CALIDAD XML:
- Usa SIEMPRE nombres de etiqueta QTI 3.0 kebab-case:
  CORRECTO: qti-simple-choice, qti-item-body, qti-choice-interaction
  INCORRECTO: simpleChoice, qti-simpleChoice, choiceInteraction, itemBody
- Etiquetas vacías deben cerrarse: <img src="..." alt="..." />  (NO <img ...>)
- NO uses comillas escapadas (\") dentro del XML. Usa comillas normales.
- NO incluyas declaración <?xml ...?> al inicio.
</restriccion_critica>"""
