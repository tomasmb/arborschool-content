"""
Feedback Generator for QTI 3.0 assessment items.

Generates per-choice rationales and worked solutions using LLM,
then injects them into QTI XML.
"""

import os
from typing import Any
from xml.etree import ElementTree as ET

from dotenv import load_dotenv
from openai import OpenAI

from feedback_system.prompts import build_composite_generation_prompt, build_generation_prompt
from feedback_system.utils.openai_retry import call_with_retry

load_dotenv()


class FeedbackGenerator:
    """Generates and injects feedback into QTI 3.0 XML."""

    def __init__(self, api_key: str = None):
        """Initialize with OpenAI API key (from param or env)."""
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"), timeout=300.0)

    def _get_schema_for_part(self, interaction_type: str) -> dict:
        """Return schema for a single part based on interaction type."""
        if interaction_type == "extended_text_interaction":
            return {
                "type": "object",
                "properties": {
                    "rubric_criteria": {"type": "array", "items": {"type": "string"}, "minItems": 3},
                    "exemplar": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "steps": {"type": "array", "items": {"type": "string"}, "minItems": 3},
                        },
                        "required": ["title", "steps"],
                        "additionalProperties": False,
                    },
                },
                "required": ["rubric_criteria", "exemplar"],
                "additionalProperties": False,
            }
        return {
            "type": "object",
            "properties": {
                "correct_response": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                "per_choice_feedback": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "choice_identifier": {"type": "string"},
                            "rationale": {"type": "string"},
                        },
                        "required": ["choice_identifier", "rationale"],
                        "additionalProperties": False,
                    },
                },
                "worked_solution": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "steps": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["title", "steps"],
                    "additionalProperties": False,
                },
            },
            "required": ["correct_response", "per_choice_feedback", "worked_solution"],
            "additionalProperties": False,
        }

    def _get_composite_schema(self, parts_info: list[dict[str, Any]]) -> dict:
        """Return schema for composite question with multiple parts."""
        parts_schema = []
        for part in parts_info:
            part_schema = self._get_schema_for_part(part["interaction_type"])
            parts_schema.append({
                "type": "object",
                "properties": {
                    "part_id": {"type": "string", "enum": [part["part_id"]]},
                    **part_schema["properties"],
                },
                "required": ["part_id"] + part_schema["required"],
                "additionalProperties": False,
            })

        return {
            "type": "object",
            "properties": {
                "parts": {"type": "array", "items": {"anyOf": parts_schema}, "minItems": len(parts_info)},
            },
            "required": ["parts"],
            "additionalProperties": False,
        }

    def generate_feedback(
        self, question_info: dict[str, Any], qti_xml: str, image_urls: list[str] = None
    ) -> dict[str, Any]:
        """Generate feedback for a QTI question."""
        from feedback_system.utils.qti_xml_utils import extract_composite_parts_info, is_composite

        if is_composite(qti_xml):
            parts_info = extract_composite_parts_info(qti_xml)
            if not parts_info:
                print("Failed to extract composite parts info")
                return {}
            return self._generate_composite_feedback(qti_xml, parts_info, image_urls)

        prompt = build_generation_prompt(qti_xml, question_info, image_urls)
        interaction_type = question_info.get("interaction_type", "unknown")
        schema = self._get_schema_for_part(interaction_type)

        return call_with_retry(
            client=self.client,
            prompt=prompt,
            schema=schema,
            schema_name="feedback_generation",
            image_urls=image_urls,
        )

    def _generate_composite_feedback(
        self, qti_xml: str, parts_info: list[dict[str, Any]], image_urls: list[str] = None
    ) -> dict[str, Any]:
        """Generate feedback for composite question with multiple parts."""
        prompt = build_composite_generation_prompt(qti_xml, parts_info, image_urls)
        schema = self._get_composite_schema(parts_info)

        return call_with_retry(
            client=self.client,
            prompt=prompt,
            schema=schema,
            schema_name="composite_feedback_generation",
            image_urls=image_urls,
        )

    def inject_feedback_into_qti(
        self, qti_xml: str, feedback_data: dict[str, Any], question_info: dict[str, Any]
    ) -> str:
        """Inject generated feedback into QTI XML."""
        from feedback_system.utils.qti_xml_utils import is_composite

        try:
            ET.register_namespace("", "http://www.imsglobal.org/xsd/imsqtiasi_v3p0")
            root = ET.fromstring(qti_xml)
            ns = root.tag.split("}")[0] + "}" if "}" in root.tag else ""

            if is_composite(qti_xml) and "parts" in feedback_data:
                return self._inject_composite_feedback(qti_xml, feedback_data)

            interaction_type = question_info.get("interaction_type", "unknown")

            if interaction_type == "extended_text_interaction":
                self._create_frq_outcome_declaration(root, ns)
                self._inject_frq_feedback(root, ns, feedback_data)
                self._update_frq_response_processing(root, ns)
            else:
                if "correct_response" in feedback_data:
                    self._add_correct_response(root, ns, feedback_data["correct_response"])
                    question_info["correct_response"] = feedback_data["correct_response"]

                self._create_outcome_declarations(root, ns)

                if interaction_type.startswith("choice_interaction"):
                    choice_interaction = root.find(f".//{ns}qti-choice-interaction")
                    if choice_interaction is not None:
                        self._inject_choice_feedback(
                            choice_interaction, ns, feedback_data, feedback_data["correct_response"]
                        )
                        self._update_response_processing(root, ns)

                self._add_worked_solution(root, ns, feedback_data)

            return ET.tostring(root, encoding="unicode")

        except Exception as e:
            print(f"Error injecting feedback into QTI: {e}")
            return qti_xml

    def _add_correct_response(
        self, root, ns: str, correct_response: list[str], response_identifier: str = "RESPONSE"
    ) -> None:
        """Add or update correct response declaration."""
        response_decl = root.find(f".//{ns}qti-response-declaration[@identifier='{response_identifier}']")

        if response_decl is None:
            cardinality = "multiple" if len(correct_response) > 1 else "single"
            response_decl = ET.Element(f"{ns}qti-response-declaration")
            response_decl.set("identifier", response_identifier)
            response_decl.set("cardinality", cardinality)
            response_decl.set("base-type", "identifier")

            insert_pos = 0
            for i, child in enumerate(root):
                if "outcome-declaration" in child.tag or "response-declaration" in child.tag:
                    insert_pos = i + 1
            root.insert(insert_pos, response_decl)

        existing_correct = response_decl.find(f"{ns}qti-correct-response")
        if existing_correct is not None:
            response_decl.remove(existing_correct)

        correct_response_elem = ET.Element(f"{ns}qti-correct-response")
        for value in correct_response:
            value_elem = ET.SubElement(correct_response_elem, f"{ns}qti-value")
            value_elem.text = value

        response_decl.insert(0, correct_response_elem)

    def _create_outcome_declarations(self, root, ns: str) -> None:
        """Create feedback and solution outcome declarations."""
        feedback_outcome = ET.Element(f"{ns}qti-outcome-declaration")
        feedback_outcome.set("identifier", "FEEDBACK")
        feedback_outcome.set("cardinality", "single")
        feedback_outcome.set("base-type", "identifier")

        solution_outcome = ET.Element(f"{ns}qti-outcome-declaration")
        solution_outcome.set("identifier", "SOLUTION")
        solution_outcome.set("cardinality", "single")
        solution_outcome.set("base-type", "identifier")

        insert_pos = 0
        last_response_pos = -1
        for i, child in enumerate(root):
            if "response-declaration" in child.tag:
                last_response_pos = i

        insert_pos = last_response_pos + 1 if last_response_pos >= 0 else 0
        root.insert(insert_pos, feedback_outcome)
        root.insert(insert_pos + 1, solution_outcome)

    def _inject_choice_feedback(
        self, interaction_elem, ns: str, feedback_data: dict[str, Any], correct_response: list[str]
    ) -> None:
        """Inject per-choice feedback for a choice interaction."""
        per_choice_fb = {
            fb["choice_identifier"]: fb["rationale"] for fb in feedback_data.get("per_choice_feedback", [])
        }

        for choice in interaction_elem.findall(f".//{ns}qti-simple-choice"):
            choice_id = choice.get("identifier")
            if choice_id and choice_id in per_choice_fb:
                is_correct = choice_id in correct_response
                prefix = "Correct! " if is_correct else "Incorrect. "

                feedback_inline = ET.Element(f"{ns}qti-feedback-inline")
                feedback_inline.set("outcome-identifier", "FEEDBACK")
                feedback_inline.set("identifier", choice_id)
                feedback_inline.set("show-hide", "show")
                feedback_inline.text = " " + prefix + per_choice_fb[choice_id]
                choice.append(feedback_inline)

    def _inject_frq_feedback(
        self, root, ns: str, feedback_data: dict[str, Any], response_identifier: str = "RESPONSE"
    ) -> None:
        """Inject rubric and exemplar for FRQ (extended text interaction)."""
        item_body = root.find(f".//{ns}qti-item-body")
        if item_body is None:
            return

        interaction = None
        for elem in item_body.iter():
            if "extended-text-interaction" in elem.tag and elem.get("response-identifier") == response_identifier:
                interaction = elem
                break

        if interaction is None:
            return

        rubric_criteria = feedback_data.get("rubric_criteria", [])
        if rubric_criteria:
            rubric_block = ET.Element(f"{ns}qti-rubric-block")
            rubric_block.set("use", "ext:criteria")
            rubric_block.set("view", "scorer")

            content_body = ET.SubElement(rubric_block, f"{ns}qti-content-body")
            ul = ET.SubElement(content_body, f"{ns}ul")

            for criterion in rubric_criteria:
                li = ET.SubElement(ul, f"{ns}li")
                li.text = criterion

            interaction_parent = None
            for parent in item_body.iter():
                if interaction in list(parent):
                    interaction_parent = parent
                    break

            if interaction_parent is not None:
                idx = list(interaction_parent).index(interaction)
                interaction_parent.insert(idx, rubric_block)

        exemplar = feedback_data.get("exemplar")
        if exemplar:
            exemplar_block = ET.Element(f"{ns}qti-feedback-block")
            exemplar_block.set("identifier", f"EXEMPLAR_{response_identifier}")
            exemplar_block.set("outcome-identifier", f"SHOW_EXEMPLAR_{response_identifier}")
            exemplar_block.set("show-hide", "show")

            content_body = ET.SubElement(exemplar_block, f"{ns}qti-content-body")

            title = exemplar.get("title", "Exemplar outline")
            p_title = ET.SubElement(content_body, f"{ns}p")
            strong = ET.SubElement(p_title, f"{ns}strong")
            strong.text = title

            steps = exemplar.get("steps", [])
            if isinstance(steps, list):
                ol = ET.SubElement(content_body, f"{ns}ol")
                for step in steps:
                    li = ET.SubElement(ol, f"{ns}li")
                    li.text = step

            interaction_parent = None
            for parent in item_body.iter():
                if interaction in list(parent):
                    interaction_parent = parent
                    break

            if interaction_parent is not None:
                idx = list(interaction_parent).index(interaction)
                interaction_parent.insert(idx + 1, exemplar_block)

    def _create_frq_outcome_declaration(self, root, ns: str, response_identifier: str = "RESPONSE") -> None:
        """Create SCORE and SHOW_EXEMPLAR outcome declarations for FRQ."""
        score_outcome = ET.Element(f"{ns}qti-outcome-declaration")
        score_outcome.set("identifier", f"SCORE_{response_identifier}")
        score_outcome.set("cardinality", "single")
        score_outcome.set("base-type", "float")

        exemplar_outcome = ET.Element(f"{ns}qti-outcome-declaration")
        exemplar_outcome.set("identifier", f"SHOW_EXEMPLAR_{response_identifier}")
        exemplar_outcome.set("cardinality", "single")
        exemplar_outcome.set("base-type", "identifier")

        insert_pos = 0
        last_response_pos = -1
        for i, child in enumerate(root):
            if "response-declaration" in child.tag:
                last_response_pos = i

        insert_pos = last_response_pos + 1 if last_response_pos >= 0 else 0
        root.insert(insert_pos, score_outcome)
        root.insert(insert_pos + 1, exemplar_outcome)

    def _update_frq_response_processing(self, root, ns: str, response_identifier: str = "RESPONSE") -> None:
        """Update response processing for FRQ."""
        for idx, child in enumerate(list(root)):
            if "response-processing" in child.tag:
                root.remove(child)

                rp = ET.Element(f"{ns}qti-response-processing")

                set_score = ET.SubElement(rp, f"{ns}qti-set-outcome-value", identifier=f"SCORE_{response_identifier}")
                custom_op = ET.SubElement(set_score, f"{ns}qti-custom-operator")
                custom_op.set("class", "com.alpha-1edtech.FRQGraderScore")

                set_exemplar = ET.SubElement(
                    rp, f"{ns}qti-set-outcome-value", identifier=f"SHOW_EXEMPLAR_{response_identifier}"
                )
                exemplar_val = ET.SubElement(set_exemplar, f"{ns}qti-base-value")
                exemplar_val.set("base-type", "identifier")
                exemplar_val.text = f"EXEMPLAR_{response_identifier}"

                root.insert(idx, rp)
                break

    def _update_response_processing(self, root, ns: str, response_identifier: str = "RESPONSE") -> None:
        """Update response processing for MCQ."""
        for idx, child in enumerate(list(root)):
            if "response-processing" in child.tag:
                root.remove(child)

                rp = ET.Element(f"{ns}qti-response-processing")

                rc = ET.SubElement(rp, f"{ns}qti-response-condition")
                ri = ET.SubElement(rc, f"{ns}qti-response-if")
                match = ET.SubElement(ri, f"{ns}qti-match")
                ET.SubElement(match, f"{ns}qti-variable", identifier=response_identifier)
                ET.SubElement(match, f"{ns}qti-correct", identifier=response_identifier)

                set_score = ET.SubElement(ri, f"{ns}qti-set-outcome-value", identifier="SCORE")
                score_val = ET.SubElement(set_score, f"{ns}qti-base-value")
                score_val.set("base-type", "float")
                score_val.text = "1"

                re = ET.SubElement(rc, f"{ns}qti-response-else")
                set_score_else = ET.SubElement(re, f"{ns}qti-set-outcome-value", identifier="SCORE")
                score_val_else = ET.SubElement(set_score_else, f"{ns}qti-base-value")
                score_val_else.set("base-type", "float")
                score_val_else.text = "0"

                set_feedback = ET.SubElement(rp, f"{ns}qti-set-outcome-value", identifier="FEEDBACK")
                ET.SubElement(set_feedback, f"{ns}qti-variable", identifier=response_identifier)

                set_solution = ET.SubElement(rp, f"{ns}qti-set-outcome-value", identifier="SOLUTION")
                solution_val = ET.SubElement(set_solution, f"{ns}qti-base-value")
                solution_val.set("base-type", "identifier")
                solution_val.text = "show"

                root.insert(idx, rp)
                break

    def _add_worked_solution(self, root, ns: str, feedback_data: dict[str, Any], solution_id: str = "show") -> None:
        """Add worked solution feedback block."""
        worked_solution = feedback_data.get("worked_solution")
        if not worked_solution:
            return

        item_body = root.find(f".//{ns}qti-item-body")
        if item_body is None:
            return

        solution_block = ET.Element(f"{ns}qti-feedback-block")
        solution_block.set("identifier", solution_id)
        solution_block.set("outcome-identifier", "SOLUTION")
        solution_block.set("show-hide", "show")

        content_body = ET.SubElement(solution_block, f"{ns}qti-content-body")

        title = worked_solution.get("title", "Worked example")
        p_title = ET.SubElement(content_body, f"{ns}p")
        strong = ET.SubElement(p_title, f"{ns}strong")
        strong.text = title

        steps = worked_solution.get("steps", [])
        if isinstance(steps, list):
            ol = ET.SubElement(content_body, f"{ns}ol")
            for step in steps:
                li = ET.SubElement(ol, f"{ns}li")
                li.text = step
        else:
            p = ET.SubElement(content_body, f"{ns}p")
            p.text = str(steps)

        item_body.append(solution_block)

    def _inject_composite_feedback(self, qti_xml: str, feedback_data: dict[str, Any]) -> str:
        """Inject feedback for composite question with multiple parts."""
        try:
            ET.register_namespace("", "http://www.imsglobal.org/xsd/imsqtiasi_v3p0")
            root = ET.fromstring(qti_xml)
            ns = root.tag.split("}")[0] + "}" if "}" in root.tag else ""

            parts = feedback_data.get("parts", [])
            if not parts:
                return qti_xml

            for part in parts:
                part_id = part.get("part_id")
                response_id = f"RESPONSE_{part_id}"
                is_frq = "rubric_criteria" in part

                if is_frq:
                    self._create_frq_outcome_declaration(root, ns, response_id)
                    self._inject_frq_feedback(root, ns, part, response_id)
                    self._update_frq_response_processing(root, ns, response_id)
                else:
                    if "correct_response" in part:
                        self._add_correct_response(root, ns, part["correct_response"], response_id)

                    item_body = root.find(f".//{ns}qti-item-body")
                    if item_body:
                        for interaction in item_body.iter():
                            if (
                                "choice-interaction" in interaction.tag
                                and interaction.get("response-identifier") == response_id
                            ):
                                self._inject_choice_feedback(interaction, ns, part, part["correct_response"])
                                break

                    self._add_worked_solution(root, ns, part, f"show_{part_id}")

            self._create_outcome_declarations(root, ns)
            self._update_composite_response_processing(root, ns, parts)

            return ET.tostring(root, encoding="unicode")

        except Exception as e:
            print(f"Error injecting composite feedback: {e}")
            return qti_xml

    def _update_composite_response_processing(self, root, ns: str, parts: list[dict[str, Any]]) -> None:
        """Update response processing for composite question."""
        for idx, child in enumerate(list(root)):
            if "response-processing" in child.tag:
                root.remove(child)

                rp = ET.Element(f"{ns}qti-response-processing")

                for part in parts:
                    part_id = part.get("part_id")
                    response_id = f"RESPONSE_{part_id}"
                    is_frq = "rubric_criteria" in part

                    if is_frq:
                        set_score = ET.SubElement(rp, f"{ns}qti-set-outcome-value", identifier=f"SCORE_{response_id}")
                        custom_op = ET.SubElement(set_score, f"{ns}qti-custom-operator")
                        custom_op.set("class", "com.alpha-1edtech.FRQGraderScore")

                        set_exemplar = ET.SubElement(
                            rp, f"{ns}qti-set-outcome-value", identifier=f"SHOW_EXEMPLAR_{response_id}"
                        )
                        exemplar_val = ET.SubElement(set_exemplar, f"{ns}qti-base-value")
                        exemplar_val.set("base-type", "identifier")
                        exemplar_val.text = f"EXEMPLAR_{response_id}"
                    else:
                        rc = ET.SubElement(rp, f"{ns}qti-response-condition")
                        ri = ET.SubElement(rc, f"{ns}qti-response-if")
                        match = ET.SubElement(ri, f"{ns}qti-match")
                        ET.SubElement(match, f"{ns}qti-variable", identifier=response_id)
                        ET.SubElement(match, f"{ns}qti-correct", identifier=response_id)

                        set_score = ET.SubElement(ri, f"{ns}qti-set-outcome-value", identifier=f"SCORE_{response_id}")
                        score_val = ET.SubElement(set_score, f"{ns}qti-base-value")
                        score_val.set("base-type", "float")
                        score_val.text = "1"

                        re = ET.SubElement(rc, f"{ns}qti-response-else")
                        set_score_else = ET.SubElement(
                            re, f"{ns}qti-set-outcome-value", identifier=f"SCORE_{response_id}"
                        )
                        score_val_else = ET.SubElement(set_score_else, f"{ns}qti-base-value")
                        score_val_else.set("base-type", "float")
                        score_val_else.text = "0"

                if parts:
                    first_resp_id = f"RESPONSE_{parts[0].get('part_id')}"
                    set_feedback = ET.SubElement(rp, f"{ns}qti-set-outcome-value", identifier="FEEDBACK")
                    ET.SubElement(set_feedback, f"{ns}qti-variable", identifier=first_resp_id)

                set_solution = ET.SubElement(rp, f"{ns}qti-set-outcome-value", identifier="SOLUTION")
                solution_val = ET.SubElement(set_solution, f"{ns}qti-base-value")
                solution_val.set("base-type", "identifier")
                solution_val.text = "show"

                root.insert(idx, rp)
                break
