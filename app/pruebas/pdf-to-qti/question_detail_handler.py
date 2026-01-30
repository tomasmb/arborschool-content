#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AWS Lambda Handler for Question Detail Evaluation Service.
This function extracts detailed question metrics via GPT-5.1.
"""

import base64
import json
import os
import tempfile
import traceback
from typing import Any, Dict

import fitz  # type: ignore
import requests
from modules.question_evaluator import evaluate_question_detail
from modules.utils.page_utils import create_combined_image


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for extracting detailed question metrics.

    Expected event (Function URL or API Gateway formats):
    {
      "pdf_url": "...",          # optional
      "pdf_base64": "...",       # optional
      "openai_api_key": "sk-..."
    }

    Returns:
        A 200 response with body {"success": true, "questionDetail": { ... }} or
        appropriate 4xx/5xx on errors.
    """
    try:
        # Parse body for API Gateway
        if 'body' in event:
            body = event['body']
            if isinstance(body, str):
                body = json.loads(body)
        else:
            body = event

        # Validate API key
        openai_api_key = body.get('openai_api_key')
        if not openai_api_key:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'success': False, 'error': 'Missing openai_api_key'})
            }

        # Load PDF data
        if body.get('pdf_url'):
            resp = requests.get(body['pdf_url'])
            resp.raise_for_status()
            pdf_bytes = resp.content
        elif body.get('pdf_base64'):
            pdf_bytes = base64.b64decode(body['pdf_base64'])
        else:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'success': False, 'error': 'Missing pdf_url or pdf_base64'})
            }

        # Write PDF to temp file and render entire PDF as one combined image
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, 'input.pdf')
            with open(pdf_path, 'wb') as f:
                f.write(pdf_bytes)
            # Open and render entire PDF as one combined image
            doc = fitz.open(pdf_path)
            combined_b64 = create_combined_image(doc)
            doc.close()
            print(f"📄 Combined image generated, length={len(combined_b64)} characters")
            # Build minimal content for evaluation using combined image
            pdf_content = {
                "pages": [{"page_image_base64": combined_b64}],
                "pdf_base64": base64.b64encode(pdf_bytes).decode("utf-8")
            }

        # Read subject and gradeLevel from request if provided
        subject = body.get('subject', '')
        grade_level = body.get('gradeLevel', '')
        print(f"🔎 Received request metadata: subject={subject}, gradeLevel={grade_level}")
        # Evaluate question details with only the combined page image
        print("🔍 Calling evaluate_question_detail...")
        question_detail = evaluate_question_detail(
            pdf_content,
            openai_api_key,
            subject,
            grade_level
        )
        print(f"✅ question_detail returned with keys: {list(question_detail.keys())}")

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'success': True, 'questionDetail': question_detail})
        }

    except Exception as e:
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'success': False, 'error': str(e)})
        }
