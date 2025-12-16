#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AWS Lambda Handler for PDF Splitter Service

This handler processes PDF files and uploads question PDFs to S3,
returning URLs for each generated question PDF.
"""

import json
import os
import tempfile
import boto3
from typing import List, Dict, Any
import traceback
from botocore.exceptions import ClientError

# Import our existing modules
from modules.pdf_processor import process_pdf_to_s3


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for PDF splitting service.
    
    Expected event structure:
    {
        "pdf_url": "https://example.com/input.pdf",  # URL to download PDF
        "pdf_base64": "base64_encoded_pdf_data",     # OR base64 encoded PDF
        "openai_api_key": "sk-...",
        "aws_credentials": {
            "access_key_id": "AKIA...",
            "secret_access_key": "...",
            "region": "us-east-1"
        },
        "s3_config": {
            "bucket_name": "my-bucket",
            "path_prefix": "questions/"  # Optional, defaults to "questions/"
        },
        "initial_chunk_size": 10  # Optional, defaults to 20. Use smaller for complex PDFs
    }
    
    Returns:
    {
        "statusCode": 200,
        "body": {
            "success": true,
            "question_urls": ["https://s3.../question_001.pdf", ...],
            "total_questions": 5,
            "processing_time_seconds": 45.2
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
        required_fields = ['openai_api_key', 'aws_credentials', 's3_config', 'test_id']
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
        
        # Set OpenAI API key
        os.environ['OPENAI_API_KEY'] = body['openai_api_key']
        
        # Configure AWS credentials
        aws_creds = body['aws_credentials']
        session = boto3.Session(
            aws_access_key_id=aws_creds['access_key_id'],
            aws_secret_access_key=aws_creds['secret_access_key'],
            aws_session_token=aws_creds.get('session_token'),
            region_name=aws_creds.get('region', 'us-east-1')
        )
        # Test AWS credentials before proceeding
        sts_client = session.client('sts')
        try:
            sts_client.get_caller_identity()
        except ClientError as e:
            return {
                'statusCode': 403,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'error': f'Invalid AWS credentials: {str(e)}'
                })
            }

        # S3 configuration
        s3_config = body['s3_config']
        bucket_name = s3_config['bucket_name']
        path_prefix = s3_config.get('path_prefix', 'questions/')
        
        # Ensure path_prefix ends with /
        if path_prefix and not path_prefix.endswith('/'):
            path_prefix += '/'
        
        # Process the PDF
        import time
        start_time = time.time()
        
        # Optional chunk size parameter for complex PDFs
        initial_chunk_size = body.get('initial_chunk_size', 20)
        
        question_urls = process_pdf_to_s3(
            pdf_source=body.get('pdf_url') or body.get('pdf_base64'),
            is_base64=bool(body.get('pdf_base64')),
            session=session,
            bucket_name=bucket_name,
            path_prefix=path_prefix,
            test_id=body['test_id'],
            initial_chunk_size=initial_chunk_size
        )
        
        processing_time = time.time() - start_time
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': json.dumps({
                'success': True,
                'question_urls': question_urls,
                'total_questions': len(question_urls),
                'processing_time_seconds': round(processing_time, 2)
            })
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


