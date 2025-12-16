import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Any

from app.feedback.generator import FeedbackGenerator
from app.feedback.validator import FeedbackValidator
from app.io import EXEMPLAR_PATH
from app.utils.qti_xml_utils import extract_image_urls, extract_question_info, is_composite, validate_qti_xml


def process_question(
    question: dict[str, Any], generator: FeedbackGenerator, validator: FeedbackValidator
) -> dict[str, Any]:
    print(f"\nProcessing question: {question.get('id')}")
    print(f"Title: {question.get('title')}")

    # Check if already processed
    if "qtiXmlWithFeedback" in question:
        print("⊘ Skipping - already has qtiXmlWithFeedback")
        return {"success": False, "reason": "already_processed"}

    qti_xml = question.get("qtiXml", "")

    # Check if composite
    if is_composite(qti_xml):
        print("Processing composite question with multiple parts")
        question_info = {}  # Not used for composites, generator extracts internally
    else:
        # Single-interaction question
        question_info = extract_question_info(qti_xml)
        print(f"Interaction type: {question_info.get('interaction_type')}")

    image_urls = extract_image_urls(qti_xml)
    if image_urls:
        print(f"Found {len(image_urls)} image(s)...")

    print("Generating feedback with GPT-5 (high reasoning)...")
    feedback_data = generator.generate_feedback(question_info, qti_xml, image_urls if image_urls else None)

    if not feedback_data:
        print("✗ Failed to generate feedback")
        return {"success": False, "reason": "feedback_generation_failed"}

    print("Injecting feedback into QTI XML...")
    qti_xml_with_feedback = generator.inject_feedback_into_qti(qti_xml, feedback_data, question_info)

    print("Validating QTI XML schema...")
    xsd_validation_result = validate_qti_xml(qti_xml_with_feedback)

    if not xsd_validation_result.get("valid"):
        print(f"✗ QTI XML schema validation failed: {xsd_validation_result.get('errors')}")
        return {"success": False, "reason": "xsd_validation_failed", "errors": xsd_validation_result.get("errors")}

    print("✓ QTI XML schema validation passed")

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

        return {"success": False, "reason": "llm_validation_failed", "validation_details": llm_validation_result}

    print("✓ LLM validation passed")
    if "parts" in llm_validation_result:
        print(f"  All {len(llm_validation_result['parts'])} parts validated successfully")
    else:
        print("  Correct Answer: ✓")
        print("  Feedback Correctness: ✓")
        print("  Quality & Pedagogy: ✓")

    return {"success": True, "qtiXmlWithFeedback": qti_xml_with_feedback, "validation_details": llm_validation_result}


def process_all_questions(input_file: str):
    print(f"\n{'=' * 60}")
    print("PROCESSING ALL QUESTIONS WITH LLM VALIDATION (10 PARALLEL)")
    print(f"{'=' * 60}")

    with open(input_file) as f:
        data = json.load(f)

    generator = FeedbackGenerator()
    validator = FeedbackValidator()
    file_lock = Lock()

    total_questions = 0
    processed = 0
    failed = 0

    questions_to_process = []
    for test_idx, test in enumerate(data["tests"]):
        for q_idx, question in enumerate(test["questions"]):
            total_questions += 1
            # Skip if already processed
            if "qtiXmlWithFeedback" not in question:
                questions_to_process.append((test_idx, q_idx, question))

    print(
        f"Found {len(questions_to_process)} questions to process (skipping {total_questions - len(questions_to_process)} already processed)"
    )

    def process_and_save(item):
        test_idx, q_idx, question = item
        result = process_question(question, generator, validator)

        if result.get("success"):
            with file_lock:
                with open(input_file) as f:
                    current_data = json.load(f)

                # Save qtiXmlWithFeedback
                current_data["tests"][test_idx]["questions"][q_idx]["qtiXmlWithFeedback"] = result["qtiXmlWithFeedback"]

                with open(input_file, "w") as f:
                    json.dump(current_data, f, indent=2)

        return (test_idx, q_idx, result)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_and_save, item): item for item in questions_to_process}

        for future in as_completed(futures):
            test_idx, q_idx, result = future.result()

            if result.get("success"):
                processed += 1
                print(f"✓ Processed {processed}/{len(questions_to_process)} - Saved to JSON")
            else:
                failed += 1
                print(f"✗ Failed {failed}/{len(questions_to_process)} - Reason: {result.get('reason')}")

    skipped = total_questions - len(questions_to_process)

    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total questions: {total_questions}")
    print(f"Successfully processed: {processed}")
    print(f"Already had feedback: {skipped}")
    print(f"Failed validation: {failed}")
    print(f"\n✓ All updates saved dynamically to: {input_file}")
    print(f"{'=' * 60}\n")


def process_single_question(input_file: str):
    print(f"\n{'=' * 60}")
    print("PROCESSING NEXT UNPROCESSED QUESTION")
    print(f"{'=' * 60}")

    with open(input_file) as f:
        data = json.load(f)

    generator = FeedbackGenerator()
    validator = FeedbackValidator()

    question_found = None
    test_index = None
    question_index = None

    for t_idx, test in enumerate(data["tests"]):
        for q_idx, question in enumerate(test["questions"]):
            # Find first question without feedback
            if "qtiXmlWithFeedback" not in question:
                question_found = question
                test_index = t_idx
                question_index = q_idx
                break
        if question_found:
            break

    if not question_found:
        print("\n✓ All questions already processed!")
        print(f"{'=' * 60}\n")
        return

    print(f"Found unprocessed question at test[{test_index}].questions[{question_index}]")

    result = process_question(question_found, generator, validator)

    if result.get("success"):
        # Save qtiXmlWithFeedback
        data["tests"][test_index]["questions"][question_index]["qtiXmlWithFeedback"] = result["qtiXmlWithFeedback"]

        with open(input_file, "w") as f:
            json.dump(data, f, indent=2)

        print(f"\n{'=' * 60}")
        print("✓ TEST PASSED")
        print(f"{'=' * 60}")
        print("\n✓ qtiXmlWithFeedback added to question in JSON")
        print(f"✓ Saved updated JSON to: {input_file}")
        print(f"{'=' * 60}\n")
    else:
        print(f"\n{'=' * 60}")
        print("✗ TEST FAILED")
        print(f"{'=' * 60}")
        print(f"\nReason: {result.get('reason')}")
        if result.get("validation_details"):
            print("\nValidation details:")
            print(json.dumps(result.get("validation_details"), indent=2))
        print("\n⚠ Question NOT saved to JSON (validation failed)")
        print(f"{'=' * 60}\n")


def run(process_all: bool = False) -> None:
    """Add feedback to exemplar questions."""
    input_file = EXEMPLAR_PATH

    if process_all:
        process_all_questions(input_file)
    else:
        process_single_question(input_file)


def main():
    """CLI entrypoint for backward compatibility."""
    process_all = "--all" in sys.argv
    run(process_all)


if __name__ == "__main__":
    main()
