"""
Example usage of the feedback system.

This shows how to generate and validate feedback for a QTI question.
"""

from feedback_system.generator import FeedbackGenerator
from feedback_system.validator import FeedbackValidator
from feedback_system.utils.qti_xml_utils import extract_question_info, extract_image_urls


# Example QTI XML (multiple choice question)
EXAMPLE_QTI_XML = """<?xml version="1.0" encoding="UTF-8"?>
<qti-assessment-item xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0"
    identifier="example-001" title="Water Cycle Question" adaptive="false" time-dependent="false">

    <qti-response-declaration identifier="RESPONSE" cardinality="single" base-type="identifier"/>
    <qti-outcome-declaration identifier="SCORE" cardinality="single" base-type="float"/>

    <qti-item-body>
        <p>What happens to water when it evaporates?</p>
        <qti-choice-interaction response-identifier="RESPONSE" shuffle="true" max-choices="1">
            <qti-simple-choice identifier="ChoiceA">It turns into ice</qti-simple-choice>
            <qti-simple-choice identifier="ChoiceB">It turns into water vapor</qti-simple-choice>
            <qti-simple-choice identifier="ChoiceC">It turns into a solid</qti-simple-choice>
            <qti-simple-choice identifier="ChoiceD">It disappears completely</qti-simple-choice>
        </qti-choice-interaction>
    </qti-item-body>

    <qti-response-processing>
        <qti-response-condition>
            <qti-response-if>
                <qti-match>
                    <qti-variable identifier="RESPONSE"/>
                    <qti-correct identifier="RESPONSE"/>
                </qti-match>
                <qti-set-outcome-value identifier="SCORE">
                    <qti-base-value base-type="float">1</qti-base-value>
                </qti-set-outcome-value>
            </qti-response-if>
        </qti-response-condition>
    </qti-response-processing>

</qti-assessment-item>"""


def main():
    """Run the feedback generation example."""
    print("=" * 60)
    print("QTI FEEDBACK GENERATION EXAMPLE")
    print("=" * 60)

    # Initialize generator and validator
    generator = FeedbackGenerator()
    validator = FeedbackValidator()

    # Extract question metadata
    question_info = extract_question_info(EXAMPLE_QTI_XML)
    image_urls = extract_image_urls(EXAMPLE_QTI_XML)

    print(f"\nExtracted question info:")
    print(f"  - Interaction type: {question_info.get('interaction_type')}")
    print(f"  - Choices: {len(question_info.get('choices', []))}")
    print(f"  - Images: {len(image_urls)}")

    # Generate feedback
    print("\nGenerating feedback...")
    feedback_data = generator.generate_feedback(question_info, EXAMPLE_QTI_XML, image_urls)

    if not feedback_data:
        print("ERROR: Failed to generate feedback")
        return

    print("\nGenerated feedback:")
    print(f"  - Correct response: {feedback_data.get('correct_response')}")
    print(f"  - Per-choice feedback: {len(feedback_data.get('per_choice_feedback', []))} items")
    print(f"  - Worked solution: {feedback_data.get('worked_solution', {}).get('title')}")

    # Inject feedback into QTI
    print("\nInjecting feedback into QTI XML...")
    qti_xml_with_feedback = generator.inject_feedback_into_qti(EXAMPLE_QTI_XML, feedback_data, question_info)

    # Validate (optional but recommended)
    print("\nValidating feedback...")
    validation_result = validator.validate_feedback(
        EXAMPLE_QTI_XML, qti_xml_with_feedback, feedback_data, question_info, image_urls
    )

    print(f"\nValidation result: {validation_result.get('validation_result')}")

    if validation_result.get("validation_result") == "pass":
        print("\n✓ Feedback validated successfully!")
        print(f"\nQTI XML with feedback ({len(qti_xml_with_feedback)} chars):")
        print("-" * 40)
        # Print first 1000 chars as preview
        print(qti_xml_with_feedback[:1000])
        if len(qti_xml_with_feedback) > 1000:
            print(f"... ({len(qti_xml_with_feedback) - 1000} more chars)")
    else:
        print("\n✗ Validation failed:")
        print(f"  - Correct answer: {validation_result.get('correct_answer_check', {}).get('status')}")
        print(f"  - Feedback correctness: {validation_result.get('feedback_correctness_check', {}).get('status')}")
        print(f"  - Quality/pedagogy: {validation_result.get('quality_pedagogy_check', {}).get('status')}")
        print(f"\nOverall: {validation_result.get('overall_reasoning')}")


if __name__ == "__main__":
    main()
