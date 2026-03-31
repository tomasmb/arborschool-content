"""Atom JSON schema example for prompt building."""

from __future__ import annotations


def format_atom_schema_example(grade_level: str = "M1") -> str:
    """Return example atom JSON schema for prompts.

    Args:
        grade_level: Grade prefix for the example ID (e.g. "M1", "EB5").
            Defaults to "M1" so existing M1 callers are unaffected.
    """
    return f"""{{
  "id": "A-{grade_level}-NUM-01-01",
  "eje": "numeros",
  "standard_ids": ["{grade_level}-NUM-01"],
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
}}"""
