"""Prompts for the validation phases (Phase 6 solvability check).

The solvability prompt asks the model to independently solve a
QTI question and return its answer for comparison with the
declared correct option.
"""

from __future__ import annotations

SOLVABILITY_PROMPT = """\
<role>
Experto en matemáticas PAES M1 (Chile).
</role>

<context>
{qti_xml}
</context>

<chilean_number_format>
Formato numérico chileno: punto (.) = miles, coma (,) = decimal.
Ejemplo: "1.250,5" = mil doscientos cincuenta coma cinco.
</chilean_number_format>

<task>
1. Lee el enunciado y las 4 opciones (A-D).
2. Resuelve el problema paso a paso.
3. Determina cuál opción es correcta.
</task>

<output_format>
JSON puro:
{{
  "answer": "letra A, B, C o D",
  "steps": "razonamiento paso a paso breve"
}}
</output_format>
"""


def build_solvability_prompt(qti_xml: str) -> str:
    """Build the solvability check prompt for a QTI question.

    Args:
        qti_xml: The QTI XML to solve.

    Returns:
        Formatted prompt string.
    """
    return SOLVABILITY_PROMPT.format(qti_xml=qti_xml)
