"""
Tagging Prompts

Contains all prompt templates and prompt-building functions for the AtomTagger.
Separates the large prompt strings from the core tagging logic.
"""

from __future__ import annotations

import json
from typing import Any


def build_atom_tagging_prompt(
    question_text: str,
    choices: list[str],
    atoms: list[dict[str, Any]]
) -> str:
    """
    Constructs the prompt for identifying relevant atoms.

    Args:
        question_text: The question text
        choices: List of answer choices
        atoms: List of atom dictionaries

    Returns:
        The complete prompt string
    """
    # Format atoms efficiently
    atoms_text = []
    for atom in atoms:
        atoms_text.append(
            f"ID: {atom['id']}\n"
            f"Title: {atom.get('titulo', '')}\n"
            f"Desc: {atom.get('descripcion', '')}\n"
        )

    atoms_block = "\n---\n".join(atoms_text)
    choices_text = "\n".join([f"- {c}" for c in choices])

    return f"""
Eres un experto en evaluación educativa y diseño curricular (matemáticas).

TAREA: Identificar los "Átomos" (Habilidades/Conocimientos) relevantes que coinciden con la siguiente pregunta.
Generalmente una pregunta evalúa un átomo principal, pero a veces puede involucrar múltiples habilidades distintas.
Selecciona uno o más átomos necesarios para resolver la pregunta.
Clasifícalos por relevancia (PRIMARY vs SECONDARY).
Si absolutamente ningún átomo coincide bien, retorna una lista vacía.
**IMPORTANTE**: El campo 'reasoning' y 'general_analysis' deben estar en **ESPAÑOL**.

PREGUNTA:
{question_text}

OPCIONES:
{choices_text}

ÁTOMOS DISPONIBLES:
{atoms_block}

FORMATO DE RESPUESTA (JSON):
Retorna un objeto JSON con:
{{
  "selected_atoms": [
      {{
          "atom_id": "ID_DEL_ATOMO",
          "relevance": "primary" o "secondary",
          "reasoning": "Por qué este átomo coincide (en Español)..."
      }}
  ],
  "general_analysis": "Breve análisis de las demandas cognitivas de la pregunta (en Español)."
}}

REGLAS DE RELEVANCIA:
- **PRIMARY**: Asígnalo si el Átomo describe el OBJETIVO MATEMÁTICO CENTRAL de la
  pregunta. No te dejes llevar solo por el verbo del título (ej: si el átomo dice
  'Construcción' pero el alumno debe 'Interpretar' ese objeto, sigue siendo PRIMARY).
- **SECONDARY**: Asígnalo a habilidades de soporte o requisitos previos necesarios
  pero que no son el foco de la evaluación.
- **IMPERATIVO**: DEBE HABER AL MENOS UN ÁTOMO MARCADO COMO 'PRIMARY'. Si dudas,
  elige el que mejor describa la acción principal que realiza el estudiante.
- Debe haber al menos un átomo PRIMARY si la pregunta tiene sentido matemático.
"""


def build_analysis_prompt(
    question_text: str,
    choices: list[str],
    selected_atoms: list[dict[str, Any]],
    correct_answer: str | None = None
) -> str:
    """
    Constructs the prompt for difficulty evaluation and feedback generation.

    Args:
        question_text: The question text
        choices: List of answer choices
        selected_atoms: List of selected atom dictionaries
        correct_answer: The correct answer text (optional)

    Returns:
        The complete prompt string
    """
    correct_info = f"\nRESPUESTA CORRECTA: {correct_answer}\n" if correct_answer else ""

    return f"""
Eres un experto en evaluación educativa y diseño curricular (matemáticas).

TAREA: Analizar en profundidad la siguiente pregunta.
1. Evaluar su **Nivel de Dificultad** basado en la demanda cognitiva.
2. Proveer **Feedback Instruccional** para el estudiante.
**IMPORTANTE**: Todo el texto generado (análisis y explicaciones) debe estar en **ESPAÑOL**.
**ADVERTENCIA**: Si generas feedback perezoso (solo repitiendo el texto de la opción),
la respuesta será RECHAZADA automáticamente. Debes explicar pedagógicamente.

PREGUNTA:
{question_text}

OPCIONES:
{json.dumps(choices, ensure_ascii=False)}
{correct_info}

ÁTOMOS RELEVANTES (HABILIDADES):
{json.dumps([a.get('titulo') for a in selected_atoms], ensure_ascii=False)}

RÚBRICA DE DIFICULTAD:
- **Low (Baja)**: Procedimiento rutinario, recuerdo directo, ejecución de un solo paso.
- **Medium (Media)**: Pensamiento estratégico, multi-paso, interpretación de datos/gráficos.
- **High (Alta)**: Razonamiento complejo, síntesis, transferencia, justificación abstracta.

GUÍAS PARA EL FEEDBACK:
- **Respuesta Correcta**: Explica POR QUÉ es correcta usando los conceptos de los átomos.
- **Distractores**: Explica el error conceptual o de cálculo probable que lleva a esta opción. Evita decir solo "es incorrecta".
- **Tono**: Constructivo, educativo, alentador (estilo tutor).

FORMATO DE RESPUESTA (JSON):
Retorna un objeto JSON con:
{{
  "difficulty": {{
      "level": "Low" | "Medium" | "High",
      "score": 0.0 a 1.0,
      "analysis": "Explicación de la demanda cognitiva (en Español)..."
  }},
  "thought_process": "Razonamiento paso a paso ANTES de generar el feedback. Analiza
      aquí la resolución del problema y por qué cada opción es correcta o incorrecta.",
  "feedback": {{
      "general_guidance": "Cómo abordar este tipo de problemas (en Español)...",
      "per_option_feedback": {{
          "ChoiceA": "Explicación detalla del por qué es incorrecta o qué error conceptual cometió el alumno (en Español)...",
          "ChoiceB": "Explicación detalla de por qué es la correcta y qué conceptos aplica (en Español)...",
          ... (para todas las opciones)
      }}
  }}
}}

REGLA DE ORO DEL FEEDBACK:
1. **CRÍTICO**: Sigue el orden del JSON. Primero piensa en "thought_process", luego escribe el "feedback".
2. **PROHIBIDO**: Devolver solo el valor de la opción o frases cortas como "Es incorrecta".
3. Cada opción debe tener al menos 2 oraciones de explicación pedagógica.
4. **EJEMPLO MALO (RECHAZADO)**: "ChoiceA": "21"
5. **EJEMPLO BUENO (APROBADO)**: "ChoiceA": "Esta opción corresponde al cálculo de 20 + 1, pero ignora el aumento porcentual..."
6. Si no puedes proveer una explicación pedagógica completa, MEJOR NO RETORNES NADA (el sistema lo marcará como fallo para revisión humana).
"""


def build_validation_prompt(
    question_text: str,
    choices: list[str],
    result: dict[str, Any],
    correct_answer: str | None = None
) -> str:
    """
    Constructs the prompt for validating generated tags and feedback.

    Args:
        question_text: The question text
        choices: List of answer choices
        result: The generated result to validate
        correct_answer: The correct answer text (optional)

    Returns:
        The complete prompt string
    """
    correct_info = (
        f"\nRESPUESTA CORRECTA OFICIAL (La Verdad Absoluta): {correct_answer}\n"
        if correct_answer else ""
    )

    return f"""
Eres un Especialista en Aseguramiento de Calidad (QA) para contenido educativo.

TAREA: Revisar los metadatos generados por IA para una pregunta de matemáticas.
Verificar consistencia, precisión y calidad pedagógica.

PREGUNTA:
{question_text}

OPCIONES:
{json.dumps(choices, ensure_ascii=False)}
{correct_info}

METADATOS GENERADOS:
{json.dumps(result, ensure_ascii=False, indent=2)}

CHECKLIST (VERIFICAR):
1. **Átomos**: ¿El átomo PRIMARY refleja el concepto central? (Ignora si el verbo no encaja perfecto, prioriza el concepto).
2. **Dificultad**: ¿Es plausible la clasificación de dificultad?
3. **Feedback**: ¿Es pedagógico? ¿Explica el error o el acierto? **RECHAZA (FAIL)**
   si el feedback solo repite el valor de la opción o es muy corto.
4. **Idioma**: ¿Todo en ESPAÑOL fluido?
5. **Exactitud Matemática**: Si se provee una RESPUESTA OFICIAL, asume que es CORRECTA
   (La Verdad Absoluta). NO cuestiones la aritmética básica (ej: 20*1.05 = 21, eso es
   un hecho, no un error de redondeo). Si tu cálculo difiere, asume que tú estás
   equivocado o te falta contexto.
6. **Tipificación**: Verifica que el tipo de problema (ej: Ecuación Lineal vs Cuadrática) coincida con el Átomo seleccionado.
7. **Existencia de Primary**: RECHAZA (FAIL) si no hay ningún átomo marcado como PRIMARY.

FORMATO DE RESPUESTA (JSON):
Retorna un objeto JSON:
{{
  "status": "PASS" o "FAIL",
  "issues": ["Lista de problemas detectados (en Español)"],
  "score": 1 a 5
}}
"""
