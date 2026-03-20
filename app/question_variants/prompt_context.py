"""Prompt-context compaction helpers for the hard-variants pipeline."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from typing import Any


def build_prompt_source_snapshot(
    *,
    question_id: str,
    question_text: str,
    choices: list[str],
    correct_answer: str,
    difficulty_text: str,
    atoms_text: str,
    construct_contract: dict[str, Any],
    structural_profile: dict[str, Any],
    visual_context: str,
    include_qti_xml: str | None = None,
) -> str:
    """Build a compact, non-redundant prompt snapshot of the source item."""
    compact_contract = {
        key: construct_contract.get(key)
        for key in (
            "family_id",
            "task_form",
            "operation_signature",
            "main_skill",
            "difficulty_level",
            "difficulty_score",
            "cognitive_action",
            "solution_structure",
            "evidence_mode",
            "visual_role",
            "auxiliary_transformations",
            "reference_relation_count",
            "data_burden_score",
            "formula_shape",
            "model_family",
            "percentage_band",
            "percentage_change_pattern",
            "selection_load",
            "base_domain",
            "power_base_family",
            "result_property_type",
            "measure_transition",
            "rate_reference_frame",
            "parameter_statement_form",
            "extremum_polarity",
            "presentation_style",
            "representation_series_count",
            "proportional_reasoning_mode",
            "response_mode",
            "distractor_archetypes",
            "correct_claim_archetype",
            "correct_justification_archetype",
            "hard_constraints",
        )
        if key in construct_contract
    }
    compact_profile = {
        key: structural_profile.get(key)
        for key in (
            "family_id",
            "task_form",
            "operation_signature",
            "introduces_unknowns",
            "claim_evaluation",
            "representation_interpretation",
            "requires_direct_computation",
            "appears_multi_step",
            "expects_explicit_dataset",
            "visual_role",
        )
        if key in structural_profile
    }

    parts = [
        "<fuente>",
        f"ID: {question_id}",
        f"Texto: {question_text}",
        f"Opciones: {json.dumps(choices, ensure_ascii=False)}",
        f"Respuesta correcta: {correct_answer}",
        f"Dificultad: {difficulty_text}",
        f"Átomos principales:\n{atoms_text}",
        f"Perfil estructural: {json.dumps(compact_profile, ensure_ascii=False)}",
        f"Contrato de constructo: {json.dumps(compact_contract, ensure_ascii=False)}",
        f"Soporte visual fuente: {visual_context or 'N/A'}",
    ]
    if include_qti_xml:
        parts.extend(["<qti_fuente>", build_qti_prompt_snapshot(include_qti_xml), "</qti_fuente>"])
    parts.append("</fuente>")
    return "\n".join(parts)


def build_qti_prompt_snapshot(qti_xml: str) -> str:
    """Summarize the source QTI structure without embedding the full XML."""
    try:
        root = ET.fromstring(qti_xml)
    except ET.ParseError:
        return "QTI source unavailable"

    item_body = root.find(".//{*}qti-item-body")
    response_decl = root.find(".//{*}qti-response-declaration")
    choice_nodes = root.findall(".//{*}qti-simple-choice")

    tag_counts = {
        "math_blocks": len(root.findall(".//{*}math")),
        "tables": len(root.findall(".//{*}table")) + len(root.findall(".//{*}qti-table")),
        "images": len(root.findall(".//{*}img")) + len(root.findall(".//{*}object")) + len(root.findall(".//{*}qti-object")),
        "lists": len(root.findall(".//{*}ul")) + len(root.findall(".//{*}ol")) + len(root.findall(".//{*}li")),
    }
    body_children = [child.tag.split("}")[-1] for child in list(item_body)] if item_body is not None else []
    choice_ids = [node.attrib.get("identifier", "") for node in choice_nodes]
    prompt_node = root.find(".//{*}qti-prompt")

    snapshot = {
        "root_tag": root.tag.split("}")[-1],
        "response_identifier": response_decl.attrib.get("identifier", "") if response_decl is not None else "",
        "choice_count": len(choice_nodes),
        "choice_ids": choice_ids,
        "has_prompt_tag": prompt_node is not None,
        "item_body_children": body_children,
        "structure_counts": tag_counts,
        "uses_mathml": tag_counts["math_blocks"] > 0,
        "uses_table": tag_counts["tables"] > 0,
        "uses_visual_object": tag_counts["images"] > 0,
    }
    return json.dumps(snapshot, ensure_ascii=False)
