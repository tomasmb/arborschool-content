#!/usr/bin/env python3
"""
Add difficulty tags to exemplar questions using Knowledge Graph atom rubrics.

This script implements a 3-step process:
1. Find all atoms that align to the question's standard
2. Use LLM to determine THE primary atom the question evaluates (forced choice)
3. Evaluate question across that atom's difficulty areas and calculate score

Usage:
    python -m app.exemplars.add_difficulty [--pilot N] [--dry-run] [--single]
"""

import json
import sys
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from app.io import EXEMPLAR_PATH, KG_PATH
from app.utils.kg_utils import (
    calculate_difficulty_score,
    find_atoms_by_standard,
    get_atom_by_id,
    get_difficulty_profile,
)
from app.utils.qti_xml_utils import extract_question_info


load_dotenv()


class DifficultyTagger:
    """Tags questions with difficulty using KG atom rubrics."""

    def __init__(self, kg_data: dict[str, Any], model: str = "gpt-5"):
        self.kg_data = kg_data
        self.client = OpenAI()
        self.model = model

    def select_primary_atom(
        self, question_text: str, choices: list[str], candidate_atoms: list[dict[str, Any]], standard: str
    ) -> str | None:
        """Use LLM to select THE primary atom this question evaluates.

        Args:
            question_text: The question stem
            choices: Answer choices
            candidate_atoms: List of atoms that align to this standard
            standard: The standard code

        Returns:
            Selected atom ID or None if failed
        """
        if not candidate_atoms:
            return None

        # Build prompt
        atom_descriptions = []
        atom_ids = []
        for atom in candidate_atoms:
            atom_id = atom["id"]
            title = atom.get("title", "")
            dok = atom.get("dok", "")
            description = atom.get("short_description", "")

            atom_ids.append(atom_id)
            atom_descriptions.append(f"- **{atom_id}** (DOK {dok}): {title}\n  {description}")

        prompt = f"""<behavior>
goal: select primary atom with minimal reasoning overhead
reasoning_effort: low
verbosity: low
stop_when: single atom selected with brief rationale
</behavior>

<role>
You are an expert in elementary science assessment.
</role>

<task>
Determine which ONE cognitive operation this question primarily assesses.
</task>

<grounding>
sources: candidate atoms + standard
rule: select only from provided atoms; if none fit, respond "none"
</grounding>

**Standard**: {standard}

**Question**:
{question_text}

**Answer Choices**:
{self._format_choices(choices)}

**Candidate Atoms**:
{chr(10).join(atom_descriptions)}

<instructions>
Analyze the question and select exactly ONE atom that represents the primary cognitive operation.
Consider: cognitive skill type (recognize/apply/model/evidence), DOK level, and central task.
</instructions>
"""

        # Schema for structured output - force choice from atom IDs
        schema = {
            "type": "object",
            "properties": {
                "selected_atom_id": {
                    "type": "string",
                    "enum": atom_ids,
                    "description": "The ID of the primary atom this question evaluates",
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation (2-3 sentences) of why this atom was selected",
                },
            },
            "required": ["selected_atom_id", "reasoning"],
            "additionalProperties": False,
        }

        try:
            response = self.client.responses.create(
                model=self.model,
                input=[{"role": "user", "content": prompt}],
                reasoning={"effort": "low"},
                text={
                    "verbosity": "low",
                    "format": {"type": "json_schema", "name": "atom_selection", "schema": schema, "strict": True},
                },
            )

            # Extract content from Responses API output
            # response.output is a list: [ResponseReasoningItem, ResponseOutputMessage]
            # The actual text is in the message's content[0].text
            output_message = next((item for item in response.output if item.type == "message"), None)
            if not output_message:
                print("  ✗ No message in response output")
                return None, None

            # Check for refusal
            if hasattr(output_message, "refusal") and output_message.refusal:
                print(f"  ✗ Model refused: {output_message.refusal}")
                return None, None

            # Get text content
            if output_message.content and len(output_message.content) > 0:
                result_text = output_message.content[0].text
                result = json.loads(result_text)
                return result["selected_atom_id"], result["reasoning"]

            return None, None

        except Exception as e:
            import traceback

            print(f"  ✗ Error selecting atom: {e}")
            traceback.print_exc()
            return None, None

    def evaluate_difficulty_areas(
        self, question_text: str, choices: list[str], atom: dict[str, Any]
    ) -> dict[str, str] | None:
        """Use LLM to evaluate question across the atom's difficulty areas.

        Args:
            question_text: The question stem
            choices: Answer choices
            atom: The selected atom with difficulty_profile

        Returns:
            Dict mapping area_id -> level (e.g., {"representation_parsing": "diagram_or_table"})
        """
        difficulty_profile = get_difficulty_profile(atom)
        if not difficulty_profile:
            print("  ⚠️  Atom has no difficulty_profile")
            return None

        areas = difficulty_profile.get("areas", [])
        if not areas:
            print("  ⚠️  No difficulty areas defined")
            return None

        # Build prompt with area descriptions
        area_descriptions = []
        area_level_enums = {}  # For schema

        for area in areas:
            area_id = area["id"]
            levels = area["levels"]
            area_level_enums[area_id] = levels

            area_descriptions.append(f"**{area_id}**:\n  Levels: {' → '.join(levels)}")

        # Get anchors if available for context
        anchors = difficulty_profile.get("anchors", {})
        anchor_examples = ""
        if anchors:
            anchor_examples = "\n\n**Example patterns** (for reference):\n"
            for level in ["easy", "medium", "hard"]:
                examples = anchors.get(level, [])
                if examples:
                    anchor_examples += f"\n{level.title()}:\n"
                    for ex in examples[:2]:  # Limit to 2 examples per level
                        anchor_examples += f"- {ex}\n"

        prompt = f"""<behavior>
goal: evaluate question across difficulty dimensions with precision
reasoning_effort: medium
verbosity: low
stop_when: all areas assigned with brief rationale
</behavior>

<role>
You are an expert in elementary science assessment.
</role>

<task>
Evaluate this question across specific difficulty dimensions for the selected atom.
</task>

<grounding>
sources: atom difficulty profile + question content
rule: assign levels based only on actual question characteristics
</grounding>

**Atom**: {atom["id"]} - {atom.get("title", "")}

**Question**:
{question_text}

**Answer Choices**:
{self._format_choices(choices)}

**Difficulty Areas to Evaluate**:
{chr(10).join(area_descriptions)}
{anchor_examples}

<instructions>
For EACH area above, assign exactly ONE level based on the actual question characteristics.
Consider: representation types, distractor similarity, context familiarity, reasoning steps, data operations.
</instructions>
"""

        # Build schema with area_id -> level mapping
        properties = {}
        for area_id, levels in area_level_enums.items():
            properties[area_id] = {"type": "string", "enum": levels, "description": f"Level for {area_id}"}

        properties["reasoning"] = {
            "type": "string",
            "description": "Brief explanation (2-3 sentences) of the level assignments",
        }

        schema = {
            "type": "object",
            "properties": properties,
            "required": list(area_level_enums.keys()) + ["reasoning"],
            "additionalProperties": False,
        }

        try:
            response = self.client.responses.create(
                model=self.model,
                input=[{"role": "user", "content": prompt}],
                reasoning={"effort": "medium"},
                text={
                    "verbosity": "low",
                    "format": {
                        "type": "json_schema",
                        "name": "difficulty_evaluation",
                        "schema": schema,
                        "strict": True,
                    },
                },
            )

            # Extract content from Responses API output
            output_message = next((item for item in response.output if item.type == "message"), None)
            if not output_message:
                print("  ✗ No message in response output")
                return None, None

            # Check for refusal
            if hasattr(output_message, "refusal") and output_message.refusal:
                print(f"  ✗ Model refused: {output_message.refusal}")
                return None, None

            # Get text content
            if output_message.content and len(output_message.content) > 0:
                result_text = output_message.content[0].text
                result = json.loads(result_text)
                reasoning = result.pop("reasoning")
                return result, reasoning  # result now contains area_id -> level mappings

            return None, None

        except Exception as e:
            print(f"  ✗ Error evaluating difficulty: {e}")
            return None, None

    def tag_question(self, question: dict[str, Any]) -> dict[str, Any] | None:
        """Tag a single question with difficulty.

        Returns dict with difficulty tagging results or None if failed.
        """
        question_id = question.get("id", "unknown")
        standard = question.get("standard", "")

        print(f"\n{'=' * 60}")
        print(f"Question: {question_id}")
        print(f"Standard: {standard}")
        title = question.get("title") or "N/A"
        print(f"Title: {title[:60]}...")

        if not standard:
            print("  ⚠️  No standard found, skipping")
            return None

        # Step 1: Find atoms for this standard
        candidate_atoms = find_atoms_by_standard(self.kg_data, standard)
        print(f"  Found {len(candidate_atoms)} candidate atoms")

        if not candidate_atoms:
            print("  ⚠️  No atoms found for standard, cannot tag difficulty")
            return None

        # Extract question text
        qti_xml = question.get("qtiXml", "")
        question_info = extract_question_info(qti_xml)
        question_text = question_info.get("body_text", "")
        choices = [c["text"] for c in question_info.get("choices", [])]

        if not question_text:
            print("  ⚠️  Could not extract question text")
            return None

        print(f"  Question text: {question_text[:80]}...")
        print(f"  Choices: {len(choices)}")

        # Step 2: Select primary atom
        print("  Step 1/2: Selecting primary atom...")
        selected_atom_id, atom_reasoning = self.select_primary_atom(question_text, choices, candidate_atoms, standard)

        if not selected_atom_id:
            print("  ✗ Failed to select atom")
            return None

        # Validate that selected atom is in candidate list
        candidate_ids = [a["id"] for a in candidate_atoms]
        if selected_atom_id not in candidate_ids:
            print(f"  ✗ Selected atom {selected_atom_id} not in candidates: {candidate_ids}")
            return None

        print(f"  ✓ Selected atom: {selected_atom_id}")
        print(f"    Reasoning: {atom_reasoning}")

        selected_atom = get_atom_by_id(self.kg_data, selected_atom_id)
        if not selected_atom:
            print(f"  ✗ Could not retrieve atom {selected_atom_id}")
            return None

        # Step 3: Evaluate across atom's difficulty areas
        print("  Step 2/2: Evaluating difficulty areas...")
        level_assignments, eval_reasoning = self.evaluate_difficulty_areas(question_text, choices, selected_atom)

        if not level_assignments:
            print("  ✗ Failed to evaluate difficulty")
            return None

        print(f"  ✓ Area assignments: {level_assignments}")
        print(f"    Reasoning: {eval_reasoning}")

        # Calculate difficulty score
        difficulty_profile = get_difficulty_profile(selected_atom)
        score, difficulty = calculate_difficulty_score(level_assignments, difficulty_profile)

        print(f"  ✓ Difficulty: {difficulty} (score: {score})")

        # Build result
        return {
            "difficulty": difficulty,
            "difficulty_score": score,
            "difficulty_atom": selected_atom_id,
            "difficulty_atom_reasoning": atom_reasoning,
            "difficulty_area_assignments": level_assignments,
            "difficulty_evaluation_reasoning": eval_reasoning,
            "difficulty_profile_version": difficulty_profile.get("version", "unknown"),
        }

    def _format_choices(self, choices: list[str]) -> str:
        """Format choices as A, B, C, D..."""
        if not choices:
            return "(No choices)"
        return "\n".join(f"{chr(65 + i)}. {choice}" for i, choice in enumerate(choices))


def process_questions(
    kg_data: dict[str, Any], questions_data: dict[str, Any], pilot_count: int | None = None, dry_run: bool = False
) -> dict[str, Any]:
    """Process questions and add difficulty tags."""
    tagger = DifficultyTagger(kg_data)

    updated_data = questions_data.copy()
    total_questions = sum(len(test["questions"]) for test in updated_data["tests"])
    processed = 0
    tagged = 0
    failed = 0

    print(f"\n{'=' * 60}")
    print("DIFFICULTY TAGGING")
    print(f"{'=' * 60}")
    print(f"Total questions: {total_questions}")
    if pilot_count:
        print(f"Pilot mode: processing only first {pilot_count} questions")
    if dry_run:
        print("DRY RUN: No files will be modified")
    print(f"{'=' * 60}")

    for test in updated_data["tests"]:
        for question in test["questions"]:
            if pilot_count and processed >= pilot_count:
                break

            # Skip if already tagged
            if question.get("difficulty"):
                continue

            processed += 1
            result = tagger.tag_question(question)

            if result:
                # Add all difficulty fields to question
                for key, value in result.items():
                    question[key] = value
                tagged += 1
                print(f"  ✓ Tagged [{tagged}/{processed}]")
            else:
                failed += 1
                print(f"  ✗ Failed [{failed}/{processed}]")

        if pilot_count and processed >= pilot_count:
            break

    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print(f"Processed: {processed}/{total_questions}")
    print(f"Successfully tagged: {tagged}")
    print(f"Failed: {failed}")
    print(f"{'=' * 60}\n")

    return updated_data


def run(pilot: int | None = None, dry_run: bool = False, single: bool = False) -> None:
    """Run difficulty tagging."""
    # Load data
    print("Loading data...")
    with open(KG_PATH) as f:
        kg_data = json.load(f)
    print(f"  ✓ Loaded KG: {len(kg_data.get('nodes', []))} nodes")

    with open(EXEMPLAR_PATH) as f:
        questions_data = json.load(f)
    total_qs = sum(len(t["questions"]) for t in questions_data["tests"])
    print(f"  ✓ Loaded exemplars: {total_qs} questions")

    # Process
    if single:
        pilot = 1
        dry_run = True

    updated_data = process_questions(kg_data, questions_data, pilot, dry_run)

    # Save
    if not dry_run:
        print(f"Saving results to {EXEMPLAR_PATH}...")
        with open(EXEMPLAR_PATH, "w") as f:
            json.dump(updated_data, f, indent=2)
        print("✓ Done!")
    else:
        print("✓ Dry run complete. No files written.")


def main():
    """CLI entrypoint."""
    pilot = None
    dry_run = False
    single = False

    for arg in sys.argv[1:]:
        if arg.startswith("--pilot="):
            pilot = int(arg.split("=")[1])
        elif arg == "--dry-run":
            dry_run = True
        elif arg == "--single":
            single = True

    run(pilot=pilot, dry_run=dry_run, single=single)


if __name__ == "__main__":
    main()
