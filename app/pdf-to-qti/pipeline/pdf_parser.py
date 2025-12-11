"""PDF Parser - Converts PDF to structured markdown using Extend.ai API.

This is the first step in the pipeline: PDF → Parsed JSON (markdown chunks).
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Extend.ai API endpoints
EXTEND_API_BASE = "https://api.extend.ai/v1"
EXTEND_UPLOAD_URL = f"{EXTEND_API_BASE}/files"
EXTEND_PARSE_URL = f"{EXTEND_API_BASE}/parser-runs"


class PDFParser:
    """
    Parses PDF files using Extend.ai API.
    
    Converts PDF to structured chunks with:
    - Correct reading order (multi-column handling)
    - Block-level segmentation
    - Figure/image extraction with URLs
    - Table detection
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize PDF parser.
        
        Args:
            api_key: Extend.ai API key (or set EXTEND_API_KEY env var)
        """
        self.api_key = api_key or os.environ.get("EXTEND_API_KEY")
        if not self.api_key:
            logger.warning(
                "No Extend.ai API key provided. "
                "Set EXTEND_API_KEY env var or pass api_key parameter."
            )
    
    def parse(
        self, 
        pdf_path: str, 
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Parse a PDF file and return the parsed structure.
        
        Args:
            pdf_path: Path to the PDF file
            output_dir: Optional directory to save parsed.json
            
        Returns:
            Parsed PDF data structure (same format as Extend.ai API response)
            
        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ValueError: If API key is not set
            Exception: If API call fails
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        if not self.api_key:
            raise ValueError(
                "Extend.ai API key not set. "
                "Set EXTEND_API_KEY env var or pass api_key to constructor."
            )
        
        logger.info(f"Parsing PDF: {pdf_path.name}")
        
        # Step 1: Upload the file
        file_id = self._upload_file(pdf_path)
        logger.info(f"Uploaded file, ID: {file_id}")
        
        # Step 2: Create parser run
        parser_run_id = self._create_parser_run(file_id)
        logger.info(f"Created parser run, ID: {parser_run_id}")
        
        # Step 3: Wait for completion and get results
        parsed_data = self._wait_for_completion(parser_run_id)
        logger.info(f"Parsing complete: {len(parsed_data.get('chunks', []))} chunks")
        
        # Save to file if output_dir specified
        if output_dir:
            output_path = Path(output_dir) / "parsed.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(parsed_data, f, indent=2)
            logger.info(f"Saved parsed data to: {output_path}")
        
        return parsed_data
    
    def parse_from_json(self, json_path: str) -> Dict[str, Any]:
        """
        Load previously parsed data from a JSON file.
        
        Args:
            json_path: Path to the parsed.json file
            
        Returns:
            Parsed PDF data structure
        """
        json_path = Path(json_path)
        if not json_path.exists():
            raise FileNotFoundError(f"JSON file not found: {json_path}")
        
        with open(json_path, 'r') as f:
            return json.load(f)
    
    def _upload_file(self, pdf_path: Path) -> str:
        """Upload PDF file to Extend.ai and return file ID."""
        import requests
        
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        with open(pdf_path, 'rb') as f:
            files = {'file': (pdf_path.name, f, 'application/pdf')}
            response = requests.post(
                EXTEND_UPLOAD_URL,
                headers=headers,
                files=files,
                timeout=120
            )
        
        if response.status_code != 200:
            raise Exception(f"Failed to upload file: {response.status_code} - {response.text}")
        
        return response.json()["id"]
    
    def _create_parser_run(self, file_id: str) -> str:
        """Create a parser run for the uploaded file."""
        import requests
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "fileId": file_id,
            "options": {
                "chunking": {
                    "strategy": "page",
                    "maxChunkSize": 50000
                },
                "output": {
                    "format": "markdown",
                    "includeBlocks": True,
                    "includeBoundingBoxes": True
                }
            }
        }
        
        response = requests.post(
            EXTEND_PARSE_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to create parser run: {response.status_code} - {response.text}")
        
        return response.json()["id"]
    
    def _wait_for_completion(
        self, 
        parser_run_id: str, 
        timeout: int = 300,
        poll_interval: int = 2
    ) -> Dict[str, Any]:
        """Poll for parser run completion and return results."""
        import requests
        
        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = f"{EXTEND_PARSE_URL}/{parser_run_id}"
        
        start_time = time.time()
        
        while True:
            if time.time() - start_time > timeout:
                raise Exception(f"Parser run timed out after {timeout}s")
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                raise Exception(
                    f"Failed to get parser run status: "
                    f"{response.status_code} - {response.text}"
                )
            
            data = response.json()
            status = data.get("status")
            
            if status == "completed":
                return data
            elif status == "failed":
                error = data.get("error", "Unknown error")
                raise Exception(f"Parser run failed: {error}")
            elif status in ["pending", "processing"]:
                logger.debug(f"Parser run status: {status}, waiting...")
                time.sleep(poll_interval)
            else:
                raise Exception(f"Unknown parser run status: {status}")

