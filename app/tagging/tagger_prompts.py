"""
Tagging Prompts

Contains all prompt templates and prompt-building functions for the AtomTagger.
Separates the large prompt strings from the core tagging logic.
"""

from __future__ import annotations

import json
from typing import Any


def build_atom_tagging_prompt(question_text: str, choices: list[str], atoms: list[dict[str, Any]]) -> str:
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
        atoms_text.append(f"ID: {atom['id']}\nTitle: {atom.get('titulo', '')}\nDesc: {atom.get('descripcion', '')}\n")

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


def build_analysis_prompt(question_text: str, choices: list[str], selected_atoms: list[dict[str, Any]], correct_answer: str | None = None) -> str:
    """
    Constructs the prompt for difficulty evaluation.

    Note: Feedback generation has been moved to the question_feedback pipeline
    which embeds feedback directly in QTI XML.

    Args:
        question_text: The question text
        choices: List of answer choices
        selected_atoms: List of selected atom dictionaries
        correct_answer: The correct answer text (optional, for context)

    Returns:
        The complete prompt string
    """
    correct_info = f"\nRESPUESTA CORRECTA: {correct_answer}\n" if correct_answer else ""

    return f"""
Eres un experto en evaluación educativa y diseño curricular (matemáticas).

TAREA: Evaluar el **Nivel de Dificultad** de la siguiente pregunta basado en la demanda cognitiva.
**IMPORTANTE**: Todo el texto generado debe estar en **ESPAÑOL**.

PREGUNTA:
{question_text}

OPCIONES:
{json.dumps(choices, ensure_ascii=False)}
{correct_info}

ÁTOMOS RELEVANTES (HABILIDADES):
{json.dumps([a.get("titulo") for a in selected_atoms], ensure_ascii=False)}

RÚBRICA DE DIFICULTAD:
- **Low (Baja)**: Procedimiento rutinario, recuerdo directo, ejecución de un solo paso.
- **Medium (Media)**: Pensamiento estratégico, multi-paso, interpretación de datos/gráficos.
- **High (Alta)**: Razonamiento complejo, síntesis, transferencia, justificación abstracta.

FORMATO DE RESPUESTA (JSON):
Retorna un objeto JSON con:
{{
  "difficulty": {{
      "level": "Low" | "Medium" | "High",
      "score": 0.0 a 1.0,
      "analysis": "Explicación de la demanda cognitiva (en Español)..."
  }}
}}
"""


def build_validation_prompt(question_text: str, choices: list[str], result: dict[str, Any], correct_answer: str | None = None) -> str:
    """
    Constructs the prompt for validating generated tags and difficulty.

    Note: Feedback validation is handled by the question_feedback pipeline
    which embeds feedback directly in QTI XML.

    Args:
        question_text: The question text
        choices: List of answer choices
        result: The generated result to validate (atoms + difficulty)
        correct_answer: The correct answer text (optional)

    Returns:
        The complete prompt string
    """
    correct_info = f"\nRESPUESTA CORRECTA OFICIAL (La Verdad Absoluta): {correct_answer}\n" if correct_answer else ""

    return f"""
Eres un Especialista en Aseguramiento de Calidad (QA) para contenido educativo.

TAREA: Revisar los metadatos generados por IA para una pregunta de matemáticas.
Verificar consistencia y precisión.

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
3. **Idioma**: ¿Todo en ESPAÑOL fluido?
4. **Exactitud Matemática**: Si se provee una RESPUESTA OFICIAL, asume que es CORRECTA
   (La Verdad Absoluta). NO cuestiones la aritmética básica (ej: 20*1.05 = 21, eso es
   un hecho, no un error de redondeo). Si tu cálculo difiere, asume que tú estás
   equivocado o te falta contexto.
5. **Tipificación**: Verifica que el tipo de problema (ej: Ecuación Lineal vs Cuadrática) coincida con el Átomo seleccionado.
6. **Existencia de Primary**: RECHAZA (FAIL) si no hay ningún átomo marcado como PRIMARY.

FORMATO DE RESPUESTA (JSON):
Retorna un objeto JSON:
{{
  "status": "PASS" o "FAIL",
  "issues": ["Lista de problemas detectados (en Español)"],
  "score": 1 a 5
}}
"""
