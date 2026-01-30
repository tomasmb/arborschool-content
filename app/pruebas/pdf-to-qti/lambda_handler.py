#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AWS Lambda Handler for PDF to QTI Converter Service

This handler processes single question PDF files and converts them
to QTI 3.0 XML format, returning the XML and metadata.
"""

import base64
import json
import os
import tempfile
import time
import traceback
from typing import Any, Dict

import boto3
import requests

# Import our modules
from main import process_single_question_pdf


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for PDF to QTI conversion service.
    
    Expected event structure:
    {
        "pdf_url": "https://example.com/input.pdf",  # URL to download PDF
        "pdf_base64": "base64_encoded_pdf_data",     # OR base64 encoded PDF
        "openai_api_key": "sk-...",
        "validation_endpoint": "http://...",         # Optional QTI validation endpoint
        "aws_credentials": {                         # Optional for S3 upload
            "access_key_id": "AKIA...",
            "secret_access_key": "...",
            "region": "us-east-1"
        },
        "s3_config": {                               # Optional for S3 upload
            "bucket_name": "my-bucket",
            "path_prefix": "qti-xml/"
        }
    }
    
    Returns:
    {
        "statusCode": 200,
        "body": {
            "success": true,
            "question_type": "choice",
            "title": "Question Title",
            "description": "Question description",
            "qti_xml": "<?xml version='1.0'?>...",
            "xml_valid": true,
            "visual_validation": {...},
            "s3_url": "https://s3.../question.xml"  # If S3 upload enabled
        }
    }
    """

    try:
        # Parse the event - Function URLs vs API Gateway have different structures
        if 'body' in event:
            # API Gateway format
            if isinstance(event.get('body'), str):
                body = json.loads(event['body'])
            else:
                body = event['body']
        else:
            # Function URL format or direct invocation
            body = event

        # Validate required fields
        required_fields = ['openai_api_key']
        for field in required_fields:
            if field not in body:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'success': False,
                        'error': f'Missing required field: {field}'
                    })
                }

        # Validate PDF input (either URL or base64)
        if 'pdf_url' not in body and 'pdf_base64' not in body:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'success': False,
                    'error': 'Either pdf_url or pdf_base64 must be provided'
                })
            }

        # Get OpenAI API key
        openai_api_key = body['openai_api_key']

        # Get validation endpoint
        validation_endpoint = body.get('validation_endpoint')

        # Process the PDF
        start_time = time.time()

        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download or save PDF to temporary file
            pdf_path = os.path.join(temp_dir, "input.pdf")

            if 'pdf_url' in body:
                # Download PDF from URL
                response = requests.get(body['pdf_url'])
                response.raise_for_status()

                with open(pdf_path, 'wb') as f:
                    f.write(response.content)
            else:
                # Decode base64 PDF
                pdf_data = base64.b64decode(body['pdf_base64'])
                with open(pdf_path, 'wb') as f:
                    f.write(pdf_data)

            # Process the PDF
            output_dir = os.path.join(temp_dir, "output")
            result = process_single_question_pdf(
                pdf_path,
                output_dir,
                openai_api_key,
                validation_endpoint
            )

            # Upload to S3 if configured
            s3_url = None
            if result.get('success') and 'aws_credentials' in body and 's3_config' in body:
                s3_url = upload_to_s3(
                    result['qti_xml'],
                    result['title'],
                    body['aws_credentials'],
                    body['s3_config']
                )

        processing_time = time.time() - start_time

        # Prepare response
        response_body = {
            'success': result.get('success', False),
            'processing_time_seconds': round(processing_time, 2)
        }

        if result.get('success'):
            response_body.update({
                'question_type': result.get('question_type'),
                'title': result.get('title'),
                'description': result.get('description'),
                'qti_xml': result.get('qti_xml'),
                'xml_valid': result.get('xml_valid'),
                'question_validation': result.get('question_validation', {}),
                'validation_summary': result.get('validation_summary', ''),
                'validation_score': result.get('question_validation', {}).get('overall_score'),
                's3_url': s3_url
            })
        else:
            response_body.update({
                'error': result.get('error'),
                'question_type': result.get('question_type'),
                'can_represent': result.get('can_represent'),
                'validation_errors': result.get('validation_errors'),
                'question_validation': result.get('question_validation', {}),
                'validation_summary': result.get('validation_summary', '')
            })

        status_code = 200 if result.get('success') else 400

        return {
            'statusCode': status_code,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': json.dumps(response_body)
        }

    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        print(traceback.format_exc())

        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            })
        }


def upload_to_s3(qti_xml: str, title: str, aws_credentials: Dict[str, str], s3_config: Dict[str, str]) -> str:
    """
    Upload QTI XML to S3 and return the URL.
    
    Args:
        qti_xml: QTI XML content
        title: Question title for filename
        aws_credentials: AWS credentials
        s3_config: S3 configuration
        
    Returns:
        S3 URL of uploaded file
    """
    try:
        # Create S3 client
        session = boto3.Session(
            aws_access_key_id=aws_credentials['access_key_id'],
            aws_secret_access_key=aws_credentials['secret_access_key'],
            aws_session_token=aws_credentials.get('session_token'),
            region_name=aws_credentials.get('region', 'us-east-1')
        )
        s3_client = session.client('s3')

        # Generate filename
        import re
        safe_title = re.sub(r'[^a-zA-Z0-9_-]', '_', title)
        filename = f"{safe_title}.xml"

        # Add path prefix
        path_prefix = s3_config.get('path_prefix', 'qti-xml/')
        if path_prefix and not path_prefix.endswith('/'):
            path_prefix += '/'

        s3_key = f"{path_prefix}{filename}"

        # Upload to S3
        s3_client.put_object(
            Bucket=s3_config['bucket_name'],
            Key=s3_key,
            Body=qti_xml.encode('utf-8'),
            ContentType='application/xml'
        )

        # Generate URL
        s3_url = f"https://{s3_config['bucket_name']}.s3.amazonaws.com/{s3_key}"

        return s3_url

    except Exception as e:
        print(f"Failed to upload to S3: {str(e)}")
        return None
