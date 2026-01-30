"""
Question Evaluator Module

This module evaluates questions for detailed metrics using GPT-5.1.
"""
import json
from typing import Any, Dict

from openai import OpenAI


def evaluate_question_detail(
    pdf_content: Dict[str, Any],
    openai_api_key: str,
    subject: str,
    grade_level: str
) -> Dict[str, Any]:
    """
    Evaluate the question and return detailed metrics as JSON.

    Args:
        pdf_content: Extracted PDF content with page images.
        openai_api_key: API key for LLM calls.
        subject: Subject of the question.
        grade_level: Grade level of the question.

    Returns:
        Dictionary with evaluation fields.
    """
    # Log invocation
    print(f"🔔 Starting question evaluation: subject={subject}, grade_level={grade_level}")

    # Step 1: Prepare PDF file input for direct metrics extraction
    # Assume pdf_content contains a 'pdf_base64' key with the PDF data
    pdf_base64 = pdf_content.get('pdf_base64')
    if not pdf_base64:
        raise ValueError("pdf_content must include 'pdf_base64' with the PDF data.")
    import base64
    import tempfile
    pdf_bytes = base64.b64decode(pdf_base64)
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_pdf:
        tmp_pdf.write(pdf_bytes)
        tmp_pdf_path = tmp_pdf.name

    # Determine allowed standards based on subject
    subj = subject.lower().strip() if subject else ''
    if subj in ['math', 'ela', 'english language arts']:
        standard_enum = ['CCSS']
    elif subj == 'science':
        standard_enum = ['NGSS']
    elif subj in ['social studies', 'socialstudies', 'social_studies', 'history']:
        standard_enum = ['C3']
    else:
        standard_enum = ['CCSS', 'NGSS', 'C3']

    # Step 2: Extract metrics using function-calling and JSON schema, passing the PDF file directly
    function_spec = {
        "name": "extract_question_metrics",
        "description": "Extract structured question metrics from the provided PDF.",
        "parameters": {
            "type": "object",
            "properties": {
                "qtiInteractionType": {
                    "type": "string",
                    "enum": ["choiceInteraction","orderInteraction","extendedTextInteraction"]
                },
                "mediaTypesPresent": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "stemWordCount": {"type": "integer"},
                "estimatedTimeSeconds": {"type": "integer"},
                "dokLevel": {"type": "integer","minimum":1,"maximum":4},
                "dokReason": {"type": "string"},
                "bloomLevel": {"type":"string","enum":["remember","understand","apply","analyze","evaluate","create"]},
                "bloomReason": {"type": "string"},
                "standards": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "standardSet": {"type":"string","enum": standard_enum},
                            "standardCode": {"type":"string"}
                        },
                        "required":["standardSet","standardCode"]
                    }
                },
                "correctAnswerKey": {
                    "type": "object",
                    "properties": {
                        "obtentionMethod": {"type":"string","enum":["extractedFromQuestion","llmGuess"],"description": "If correct answer was directly marked as correct in the original image or was guessed by the LLM"},
                        "answer": {"type":"string"}
                    },
                    "required":["obtentionMethod","answer"]
                }
            },
            "required":[
                "qtiInteractionType","mediaTypesPresent","stemWordCount",
                "estimatedTimeSeconds","dokLevel","dokReason",
                "bloomLevel","bloomReason","standards","correctAnswerKey"
            ]
        }
    }
    client = OpenAI(api_key=openai_api_key)
    print("🎯 Invoking extract_question_metrics function with PDF file input")
    # Upload PDF file to OpenAI
    with open(tmp_pdf_path, 'rb') as pdf_file:
        file_response = client.files.create(
            file=pdf_file,
            purpose="user_data"
        )
    print(f"PDF uploaded with ID: {file_response.id}")
    response = client.chat.completions.create(
        model="gpt-5.1",
        messages=[
            {"role": "system", "content": (
                f"Subject: {subject}, Grade: {grade_level}. "
                f"This question is from a test administered to students in grade {grade_level}. "
                "Standards do not have to match the exact grade; select those that are most appropriate for the question and the test context. "
                "Use chain-of-thought reasoning internally and output JSON only via the function."
            )},
            {"role": "user", "content": [
                {"type": "file", "file": {"file_id": file_response.id}},
                {"type": "text", "text": "Extract the question metrics as specified in the schema."}
            ]}
        ],
        functions=[function_spec],
        function_call={"name": function_spec["name"]},
        reasoning_effort="high",
    )
    choice = response.choices[0].message
    arguments = choice.function_call.arguments
    detail = json.loads(arguments)
    print(f"📊 Extracted metrics: {detail}")

    # Step 3: Validate critical fields via function-calling
    validate_spec = {
        "name": "validate_question_metrics",
        "description": "Validate and correct critical fields against the PDF.",
        "parameters": {
            "type": "object",
            "properties": {
                "standards": function_spec["parameters"]["properties"]["standards"],
                "bloomLevel": function_spec["parameters"]["properties"]["bloomLevel"],
                "bloomReason": function_spec["parameters"]["properties"]["bloomReason"],
                "dokLevel": function_spec["parameters"]["properties"]["dokLevel"],
                "dokReason": function_spec["parameters"]["properties"]["dokReason"]
            }
        }
    }
    print("🛡️ Invoking validate_question_metrics function for critical fields with PDF file input")
    validate_response = client.chat.completions.create(
        model="gpt-5.1",
        messages=[
            {"role": "system", "content": (
                "Validate the metrics against the PDF. "
                f"This question is from a test administered to students in grade {grade_level}. "
                "Standards do not have to match the exact grade; select those that are most appropriate for the question and the test context."
            )},
            {"role": "user", "content": [
                {"type": "file", "file": {"file_id": file_response.id}},
                {"type": "text", "text": "Validate and correct the extracted metrics as needed."}
            ]},
            {"role": "assistant", "content": json.dumps(detail)}
        ],
        functions=[validate_spec],
        function_call={"name": validate_spec["name"]},
        reasoning_effort="high",
    )
    corrections = json.loads(validate_response.choices[0].message.function_call.arguments)
    print(f"🛠️ Corrections applied: {corrections}")
    for k in corrections:
        detail[k] = corrections[k]

    # Compute cognitiveRigorCell = BloomWeight*BloomRank + DokWeight*DokLevel
    bloom_rank_map = {"remember":1,"understand":2,"apply":3,"analyze":4,"evaluate":5,"create":6}
    bloom_rank = bloom_rank_map.get(detail.get("bloomLevel",""),0)
    dok_level = detail.get("dokLevel",0)
    detail["cognitiveRigorCell"] = bloom_rank + dok_level*2
    print(f"🔢 cognitiveRigorCell computed: {detail['cognitiveRigorCell']}")
    return detail
