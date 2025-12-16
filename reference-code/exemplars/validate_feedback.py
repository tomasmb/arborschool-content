import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Any
from xml.etree import ElementTree as ET

from app.feedback.validator import FeedbackValidator
from app.io import EXEMPLAR_PATH
from app.utils.qti_xml_utils import extract_image_urls, extract_question_info, is_composite


def _extract_minimal_feedback_data(qti_xml_with_feedback: str, question_info: dict[str, Any]) -> dict[str, Any]:
    """Extract minimal feedback data structure from qtiXmlWithFeedback for validation."""
    try:
        root = ET.fromstring(qti_xml_with_feedback)
        ns = root.tag.split("}")[0] + "}" if "}" in root.tag else ""

        # Check if composite
        if "parts" in qti_xml_with_feedback and "RESPONSE_A" in qti_xml_with_feedback:
            # Composite question - extract parts
            parts = []
            part_letters = ["A", "B", "C", "D", "E", "F"]

            for letter in part_letters:
                response_id = f"RESPONSE_{letter}"
                # Check if this part exists
                if response_id not in qti_xml_with_feedback:
                    break

                # Determine if FRQ or MCQ based on presence of rubric
                rubric_block = root.find(f".//{ns}qti-rubric-block")
                is_frq = rubric_block is not None

                if is_frq:
                    parts.append(
                        {
                            "part_id": letter,
                            "rubric_criteria": ["Validation placeholder"],
                            "exemplar": {"title": "Placeholder", "steps": ["Validation"]},
                        }
                    )
                else:
                    parts.append(
                        {
                            "part_id": letter,
                            "correct_response": ["ChoiceA"],
                            "per_choice_feedback": [],
                            "worked_solution": {"title": "Placeholder", "steps": []},
                        }
                    )

            return {"parts": parts} if parts else {}

        # Single question
        interaction_type = question_info.get("interaction_type", "unknown")

        if interaction_type == "extended_text_interaction":
            # FRQ - just return placeholder structure
            return {
                "rubric_criteria": ["Validation placeholder"],
                "exemplar": {"title": "Placeholder", "steps": ["Validation"]},
            }
        # MCQ - extract correct response and feedback
        response_decl = root.find(f".//{ns}qti-response-declaration[@identifier='RESPONSE']")
        correct_response = []
        if response_decl is not None:
            for value in response_decl.findall(f".//{ns}qti-value"):
                if value.text:
                    correct_response.append(value.text)

        per_choice_feedback = []
        for choice in root.findall(f".//{ns}qti-simple-choice"):
            choice_id = choice.get("identifier")
            feedback_inline = choice.find(f"{ns}qti-feedback-inline")
            if feedback_inline is not None and feedback_inline.text:
                per_choice_feedback.append({"choice_identifier": choice_id, "rationale": feedback_inline.text.strip()})

        return {
            "correct_response": correct_response,
            "per_choice_feedback": per_choice_feedback,
            "worked_solution": {"title": "Placeholder", "steps": []},
        }

    except Exception as e:
        print(f"Error extracting feedback data: {e}")
        return {}


def validate_question(question: dict[str, Any], validator: FeedbackValidator) -> dict[str, Any]:
    """Validate a single question's qtiXmlWithFeedback."""
    print(f"\nValidating question: {question.get('id')}")
    print(f"Title: {question.get('title')}")

    # Check if has qtiXmlWithFeedback
    if "qtiXmlWithFeedback" not in question:
        print("⊘ Skipping - no qtiXmlWithFeedback to validate")
        return {"success": True, "reason": "no_feedback_to_validate"}

    qti_xml = question.get("qtiXml", "")
    qti_xml_with_feedback = question.get("qtiXmlWithFeedback", "")

    # Extract question info
    if is_composite(qti_xml):
        print("Validating composite question with multiple parts")
        question_info = {}
    else:
        question_info = extract_question_info(qti_xml)
        print(f"Interaction type: {question_info.get('interaction_type')}")

    image_urls = extract_image_urls(qti_xml)
    if image_urls:
        print(f"Found {len(image_urls)} image(s)...")

    # Create a minimal feedback_data structure for validation
    # The validator will examine the qtiXmlWithFeedback directly
    feedback_data = _extract_minimal_feedback_data(qti_xml_with_feedback, question_info)

    if not feedback_data:
        print("✗ Failed to extract feedback data from qtiXmlWithFeedback")
        return {"success": False, "reason": "feedback_extraction_failed", "should_delete": True}

    print("Validating with LLM judge (GPT-5 high reasoning)...")
    llm_validation_result = validator.validate_feedback(
        qti_xml, qti_xml_with_feedback, feedback_data, question_info, image_urls if image_urls else None
    )

    if llm_validation_result.get("validation_result") != "pass":
        print("✗ LLM validation failed")

        # Handle composite validation output (has parts)
        if "parts" in llm_validation_result:
            for part_result in llm_validation_result.get("parts", []):
                part_id = part_result.get("part_id")
                print(f"\n  Part {part_id}:")
                print(f"    Correct Answer Check: {part_result.get('correct_answer_check', {}).get('status')}")
                if part_result.get("correct_answer_check", {}).get("issues"):
                    for issue in part_result.get("correct_answer_check", {}).get("issues", []):
                        print(f"      - {issue}")

                print(
                    f"    Feedback Correctness Check: {part_result.get('feedback_correctness_check', {}).get('status')}"
                )
                if part_result.get("feedback_correctness_check", {}).get("issues"):
                    for issue in part_result.get("feedback_correctness_check", {}).get("issues", []):
                        print(f"      - {issue}")

                print(f"    Quality & Pedagogy Check: {part_result.get('quality_pedagogy_check', {}).get('status')}")
                if part_result.get("quality_pedagogy_check", {}).get("issues"):
                    for issue in part_result.get("quality_pedagogy_check", {}).get("issues", []):
                        print(f"      - {issue}")
        else:
            # Handle single question validation output
            print(f"  Correct Answer Check: {llm_validation_result.get('correct_answer_check', {}).get('status')}")
            if llm_validation_result.get("correct_answer_check", {}).get("issues"):
                for issue in llm_validation_result.get("correct_answer_check", {}).get("issues", []):
                    print(f"    - {issue}")

            print(
                f"  Feedback Correctness Check: {llm_validation_result.get('feedback_correctness_check', {}).get('status')}"
            )
            if llm_validation_result.get("feedback_correctness_check", {}).get("issues"):
                for issue in llm_validation_result.get("feedback_correctness_check", {}).get("issues", []):
                    print(f"    - {issue}")

            print(
                f"  Quality & Pedagogy Check: {llm_validation_result.get('quality_pedagogy_check', {}).get('status')}"
            )
            if llm_validation_result.get("quality_pedagogy_check", {}).get("issues"):
                for issue in llm_validation_result.get("quality_pedagogy_check", {}).get("issues", []):
                    print(f"    - {issue}")

        print(f"\n  Overall: {llm_validation_result.get('overall_reasoning')}")
        print("⚠ Will delete qtiXmlWithFeedback for this question")

        return {
            "success": False,
            "reason": "llm_validation_failed",
            "should_delete": True,
            "validation_details": llm_validation_result,
        }

    print("✓ LLM validation passed")
    if "parts" in llm_validation_result:
        print(f"  All {len(llm_validation_result['parts'])} parts validated successfully")
    else:
        print("  Correct Answer: ✓")
        print("  Feedback Correctness: ✓")
        print("  Quality & Pedagogy: ✓")

    return {"success": True, "validation_details": llm_validation_result}


def validate_all_questions(input_file: str):
    """Validate all questions with qtiXmlWithFeedback and remove invalid ones."""
    print(f"\n{'=' * 60}")
    print("FINAL VALIDATION - CHECKING ALL FEEDBACK (10 PARALLEL)")
    print(f"{'=' * 60}")

    with open(input_file) as f:
        data = json.load(f)

    validator = FeedbackValidator()
    file_lock = Lock()

    total_questions = 0
    validated = 0
    deleted = 0
    skipped = 0

    questions_to_validate = []
    for test_idx, test in enumerate(data["tests"]):
        for q_idx, question in enumerate(test["questions"]):
            total_questions += 1
            # Only validate questions that have feedback
            if "qtiXmlWithFeedback" in question:
                questions_to_validate.append((test_idx, q_idx, question))

    print(
        f"Found {len(questions_to_validate)} questions with feedback to validate (skipping {total_questions - len(questions_to_validate)} without feedback)"
    )

    def validate_and_update(item):
        test_idx, q_idx, question = item
        result = validate_question(question, validator)

        if not result.get("success") and result.get("should_delete"):
            with file_lock:
                with open(input_file) as f:
                    current_data = json.load(f)

                # Delete qtiXmlWithFeedback
                if "qtiXmlWithFeedback" in current_data["tests"][test_idx]["questions"][q_idx]:
                    del current_data["tests"][test_idx]["questions"][q_idx]["qtiXmlWithFeedback"]

                with open(input_file, "w") as f:
                    json.dump(current_data, f, indent=2)

        return (test_idx, q_idx, result)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(validate_and_update, item): item for item in questions_to_validate}

        for future in as_completed(futures):
            test_idx, q_idx, result = future.result()

            if result.get("success"):
                validated += 1
                print(f"✓ Validated {validated}/{len(questions_to_validate)} - Passed")
            elif result.get("should_delete"):
                deleted += 1
                print(f"✗ Deleted {deleted}/{len(questions_to_validate)} - Removed qtiXmlWithFeedback")
            else:
                skipped += 1

    print(f"\n{'=' * 60}")
    print("VALIDATION SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total questions: {total_questions}")
    print(f"With feedback: {len(questions_to_validate)}")
    print(f"Passed validation: {validated}")
    print(f"Failed & deleted: {deleted}")
    print(f"Skipped (no feedback): {total_questions - len(questions_to_validate)}")
    print(f"\n✓ All updates saved to: {input_file}")
    print(f"{'=' * 60}\n")


def run() -> None:
    """Run final validation on all exemplar questions with feedback."""
    input_file = EXEMPLAR_PATH
    validate_all_questions(input_file)


def main():
    """CLI entrypoint."""
    run()


if __name__ == "__main__":
    main()
