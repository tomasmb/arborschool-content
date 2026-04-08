"""Prompt builders for the prerequisite atom fix pipeline.

Mirrors the M1 fix prompt structure but adapted for prerequisite atoms:
  - Uses prereq ID patterns (A-{grade}-{EJE}-{STD}-{SEQ})
  - Grade-level-appropriate role text
  - No question references or pruebas metadata
"""

from __future__ import annotations

import json
from typing import Any

from app.atoms.fixing.models import FixAction, FixType


def build_prereq_fix_prompt(
    action: FixAction,
    standard: dict[str, Any],
    target_atoms: list[dict[str, Any]],
    all_standard_atoms: list[dict[str, Any]],
    next_atom_number: int,
) -> str:
    """Build the full prompt for a given prereq FixAction."""
    spec = _SPECS[action.fix_type]
    return _assemble(
        spec=spec,
        action=action,
        standard=standard,
        target_atoms=target_atoms,
        all_standard_atoms=all_standard_atoms,
        next_atom_number=next_atom_number,
    )


_PREREQ_ATOM_SCHEMA = """\
{
  "id": "A-<GRADE>-<EJE>-<STD_NUM>-<SEQ>",
  "grade_level": "<EB1..EM2>",
  "eje": "<numeros | algebra_y_funciones | geometria | probabilidad_y_estadistica>",
  "standard_ids": ["<GRADE-EJE-NN>"],
  "habilidad_principal": "<resolver_problemas | modelar | representar | argumentar>",
  "habilidades_secundarias": [],
  "tipo_atomico": "<concepto | procedimiento | representacion | argumentacion | modelizacion | concepto_procedimental>",
  "titulo": "<short student-facing title>",
  "descripcion": "<>=50 chars, single cognitive intention>",
  "criterios_atomicos": ["<success criterion 1>", "..."],
  "ejemplos_conceptuales": ["<1-4 non-exercise examples>"],
  "prerrequisitos": ["<atom IDs>"],
  "notas_alcance": ["<what is excluded>"],
  "en_alcance_m1": false
}"""


def _output_schema() -> str:
    return (
        '{\n'
        '  "fixed_atoms": [<atom objects>],\n'
        '  "removed_atom_ids": ["<IDs to delete, empty if none>"],\n'
        '  "id_mapping": {"<old_id>": ["<new_id>", "..."]},\n'
        '  "prerequisite_updates": {"<atom_id>": ["<new prereqs>"]}\n'
        '}'
    )


def _fmt(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def _std_ctx(std: dict[str, Any]) -> str:
    keys = [
        "id", "titulo", "eje", "grade_level",
        "incluye", "no_incluye", "descripcion_general",
    ]
    return _fmt({k: std[k] for k in keys if k in std})


def _issues_block(action: FixAction) -> str:
    lines = [f"- Issue: {i}" for i in action.issues]
    lines += [f"- Recommendation: {r}" for r in action.recommendations]
    return "\n".join(lines) or "(none)"


class _Spec:
    """Lightweight spec capturing the variable parts of a prompt."""

    __slots__ = (
        "role_focus", "task_template", "rules",
        "constraints", "needs_all_atoms",
    )

    def __init__(
        self,
        *,
        role_focus: str,
        task_template: str,
        rules: list[str],
        constraints: list[str],
        needs_all_atoms: bool = False,
    ) -> None:
        self.role_focus = role_focus
        self.task_template = task_template
        self.rules = rules
        self.constraints = constraints
        self.needs_all_atoms = needs_all_atoms


_SPECS: dict[FixType, _Spec] = {
    FixType.SPLIT: _Spec(
        role_focus="learning-atom decomposition",
        task_template=(
            "Split atom {atom_id} into two or more atoms, each with "
            "exactly one cognitive intention. Assign new IDs starting "
            "at {next_id}. Update prerequisites so dependents of "
            "{atom_id} reference the correct replacement(s)."
        ),
        rules=[
            "Each new atom must have a single cognitive intention.",
            "Preserve all content from the original atom.",
            "Assign IDs sequentially from the next available number.",
            "Update prerrequisitos of every atom that referenced "
            "the split atom.",
        ],
        constraints=[
            "DO NOT invent content not in the original atom or standard.",
            "DO NOT change atoms that are not targets or dependents.",
            "DO NOT create atoms with overlapping cognitive intentions.",
        ],
        needs_all_atoms=True,
    ),
    FixType.MERGE: _Spec(
        role_focus="learning-atom consolidation",
        task_template=(
            "Merge atoms {atom_ids_str} into a single atom. Keep the "
            "lowest existing ID. Remove the other ID(s). Redirect "
            "prerequisites to the surviving atom."
        ),
        rules=[
            "The merged atom must cover all non-redundant content.",
            "Keep exactly one cognitive intention.",
            "Use the lowest existing ID as the surviving ID.",
            "List removed IDs in removed_atom_ids.",
            "Update prerrequisitos of all atoms that referenced "
            "removed IDs.",
        ],
        constraints=[
            "DO NOT invent content beyond what the source atoms contain.",
            "DO NOT produce a merged atom with multiple cognitive "
            "intentions.",
        ],
        needs_all_atoms=True,
    ),
    FixType.FIX_CONTENT: _Spec(
        role_focus="content quality review",
        task_template=(
            "Fix the content quality issues in atom {atom_id}. "
            "Keep the same ID."
        ),
        rules=[
            "Preserve the atom's cognitive intention and scope.",
            "Align habilidad_principal with what the criteria assess.",
            "Make examples unambiguous and self-contained.",
            "Ensure terminology matches the standard.",
        ],
        constraints=[
            "DO NOT change the atom ID.",
            "DO NOT alter scope beyond what the issues require.",
            "DO NOT add content outside the standard's incluye list.",
        ],
    ),
    FixType.FIX_FIDELITY: _Spec(
        role_focus="fidelity enforcement to standard boundaries",
        task_template=(
            "Reformulate atom {atom_id} so it stays strictly within "
            "the standard's incluye boundary. Keep the same ID."
        ),
        rules=[
            "Remove or rephrase any reference to excluded content.",
            "Preserve the atom's core learning objective.",
            "Ensure criteria and examples only use included content.",
        ],
        constraints=[
            "DO NOT change the atom ID.",
            "DO NOT introduce content from no_incluye.",
            "DO NOT remove content that IS within scope.",
        ],
    ),
    FixType.FIX_COMPLETENESS: _Spec(
        role_focus="completeness assurance",
        task_template=(
            "Add the missing criteria or clarifications to atom "
            "{atom_id} as indicated by the issues. Keep the same ID."
        ),
        rules=[
            "Add only what the issues specifically identify as missing.",
            "Keep existing criteria and examples intact.",
            "New criteria must be assessable with a single task.",
        ],
        constraints=[
            "DO NOT change the atom ID.",
            "DO NOT remove existing content.",
            "DO NOT add content outside the standard's scope.",
        ],
    ),
    FixType.FIX_PREREQUISITES: _Spec(
        role_focus="prerequisite chain auditing",
        task_template=(
            "Update the prerrequisitos list of atom {atom_id} to "
            "correctly reflect the dependencies. Keep the same ID."
        ),
        rules=[
            "Only add prerequisites that are actual atoms.",
            "Remove prerequisites flagged as incorrect.",
            "Ensure no circular dependencies are introduced.",
        ],
        constraints=[
            "DO NOT change the atom ID.",
            "DO NOT modify anything other than the prerrequisitos field.",
            "DO NOT reference atom IDs that do not exist.",
        ],
        needs_all_atoms=True,
    ),
    FixType.ADD_MISSING: _Spec(
        role_focus="new atom generation for coverage gaps",
        task_template=(
            "Generate new atom(s) covering the missing areas listed "
            "below. Assign sequential IDs starting at {next_id}. Set "
            "appropriate prerequisites from existing atoms."
        ),
        rules=[
            "Each new atom must have exactly one cognitive intention.",
            "Cover all listed missing areas.",
            "Set prerrequisitos to existing atoms that logically precede.",
            "Follow the same quality standards as existing atoms.",
        ],
        constraints=[
            "DO NOT duplicate content already in existing atoms.",
            "DO NOT create atoms outside the standard's incluye boundary.",
        ],
        needs_all_atoms=True,
    ),
}


def _assemble(
    spec: _Spec,
    action: FixAction,
    standard: dict[str, Any],
    target_atoms: list[dict[str, Any]],
    all_standard_atoms: list[dict[str, Any]],
    next_atom_number: int,
) -> str:
    """Assemble a complete prompt from a _Spec and runtime data."""
    std_id = standard.get("id", "")
    grade = standard.get("grade_level", "EB1")
    parts = std_id.split("-")
    eje_suffix = "-".join(parts[1:]) if len(parts) >= 3 else std_id
    next_id = f"A-{grade}-{eje_suffix}-{next_atom_number:02d}"
    atom_id = action.atom_ids[0] if action.atom_ids else "(new)"
    atom_ids_str = ", ".join(action.atom_ids)

    task_text = spec.task_template.format(
        atom_id=atom_id,
        atom_ids_str=atom_ids_str,
        next_id=next_id,
    )

    ctx_parts = [f"Standard definition:\n{_std_ctx(standard)}"]
    if target_atoms:
        label = (
            "Atom(s) to fix"
            if action.fix_type != FixType.ADD_MISSING else "Reference"
        )
        ctx_parts.append(f"{label}:\n{_fmt(target_atoms)}")
    if spec.needs_all_atoms:
        ctx_parts.append(
            f"All atoms in this standard:\n{_fmt(all_standard_atoms)}",
        )
    ctx_parts.append(f"Validation issues:\n{_issues_block(action)}")
    if action.missing_areas:
        missing = "\n".join(f"- {a}" for a in action.missing_areas)
        ctx_parts.append(f"Coverage gaps:\n{missing}")
    if action.fix_type in (FixType.SPLIT, FixType.ADD_MISSING):
        ctx_parts.append(f"Next available atom number: {next_atom_number}")

    context_body = "\n".join(ctx_parts)
    rules_text = "\n".join(
        f"{i}. {r}" for i, r in enumerate(spec.rules, 1)
    )
    constraints_text = "\n".join(f"- {c}" for c in spec.constraints)

    return (
        f"<role>\n"
        f"You are an expert instructional designer specialising in "
        f"{spec.role_focus} for Chilean school-level mathematics "
        f"(level {grade}).\n"
        f"</role>\n\n"
        f"<context>\n{context_body}\n</context>\n\n"
        f"<task>\n{task_text}\n</task>\n\n"
        f"<rules>\n{rules_text}\n</rules>\n\n"
        f"<constraints>\n{constraints_text}\n"
        f"- Every atom MUST pass the PrereqAtom JSON schema.\n"
        f"- en_alcance_m1 MUST be false.\n"
        f"</constraints>\n\n"
        f"<output_format>\n"
        f"Return ONLY valid JSON matching this schema:\n"
        f"{_output_schema()}\n\n"
        f"Atom schema:\n{_PREREQ_ATOM_SCHEMA}\n"
        f"</output_format>\n\n"
        f"<final_instruction>\n"
        f"Based on the context above, apply the fix and return JSON.\n"
        f"</final_instruction>"
    )
