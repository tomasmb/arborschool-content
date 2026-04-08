"""Prompt for Phase 3: connecting prerequisite atoms to M1 atoms.

Identifies which prerequisite atoms should be added as prerequisites
of which M1 atoms, creating the bridge between the two graphs.
"""

from __future__ import annotations

import json
from typing import Any


def build_graph_connection_prompt(
    m1_leaf_atoms: list[dict[str, Any]],
    prereq_top_atoms: list[dict[str, Any]],
) -> str:
    """Build prompt for connecting prerequisite graph to M1 graph.

    Args:
        m1_leaf_atoms: M1 atoms that currently have no prerequisites
            (the "entry points" of the M1 graph).
        prereq_top_atoms: Highest-level prerequisite atoms (EM1, EM2,
            or the top of each chain) that could serve as prerequisites
            for M1 atoms.

    Returns:
        Complete prompt string for GPT-5.1.
    """
    m1_json = json.dumps(m1_leaf_atoms, ensure_ascii=False, indent=2)
    prereq_json = json.dumps(prereq_top_atoms, ensure_ascii=False, indent=2)

    return f"""<role>
Eres un experto en diseño curricular de matemáticas. Tu tarea es conectar
átomos prerequisito con átomos de nivel PAES M1, estableciendo las
relaciones de prerrequisito que faltan.
</role>

<context>
## Átomos M1 sin prerrequisitos (necesitan conexión)

{m1_json}

## Átomos prerequisito de nivel más alto disponibles

{prereq_json}
</context>

<task>
Para cada átomo M1 sin prerrequisitos, identifica cuáles de los átomos
prerequisito deben ser sus prerrequisitos directos. Reglas:

1. Solo asigna prerrequisitos DIRECTOS — no transitivos. Si el átomo
   prereq A ya es prerrequisito del átomo prereq B, y el M1 necesita B,
   no necesita listar A.
2. Un átomo M1 puede tener 0 a N prerrequisitos prerequisite.
3. Si un átomo M1 ya es suficientemente básico para no necesitar ningún
   prerrequisito adicional, no le asignes ninguno.
4. Prioriza la precisión: un prerrequisito incorrecto es peor que un
   prerrequisito faltante.
5. Justifica brevemente cada conexión.
</task>

<output_format>
Responde SOLO con un objeto JSON:

{{
  "connections": [
    {{
      "m1_atom_id": "A-M1-NUM-01-01",
      "new_prerequisites": ["A-EM2-NUM-03-01", "A-EM1-ALG-02-01"],
      "justification": "Breve justificación de por qué estos
        prerrequisitos son necesarios."
    }}
  ],
  "unconnected_m1_atoms": [
    {{
      "m1_atom_id": "A-M1-GEO-01-01",
      "reason": "Ya es suficientemente básico / no hay prereqs aplicables."
    }}
  ],
  "summary": {{
    "total_connections": 0,
    "m1_atoms_connected": 0,
    "m1_atoms_unconnected": 0
  }}
}}
</output_format>

<rules>
1. Todo en español.
2. Los IDs deben ser exactos — copia los IDs tal cual aparecen.
3. Solo referencia átomos prerequisito que aparecen en la lista
   proporcionada.
4. Preferir el prerrequisito de nivel más alto que cubra la necesidad
   (si EM2-NUM-01-01 cubre lo que se necesita, no referencies también
   EB8-NUM-05-01 que es transitivo).
</rules>"""
