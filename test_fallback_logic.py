import os
import unittest
from unittest.mock import MagicMock, patch
from PIL import Image
import io
from app.gemini_client import load_default_gemini_service, OpenAIClient
from google.api_core import exceptions as google_exceptions

class TestFallback(unittest.TestCase):
    def test_openai_abstraction(self):
        # Test if OpenAIClient can handle PIL images
        client = OpenAIClient(api_key="test_key")
        img = Image.new('RGB', (100, 100), color='red')
        
        # Mock requests.post to avoid hitting real API
        with patch('requests.post') as mock_post:
            mock_post.return_value.json.return_value = {
                "choices": [{"message": {"content": "OpenAI Success"}}]
            }
            mock_post.return_value.status_code = 200
            
            resp = client.generate_text(["Hello", img])
            self.assertEqual(resp, "OpenAI Success")
            
            # Check if image was converted to base64 in data
            args, kwargs = mock_post.call_args
            content = kwargs['json']['messages'][0]['content']
            self.assertEqual(content[0]['type'], 'text')
            self.assertEqual(content[1]['type'], 'image_url')
            self.assertTrue(content[1]['image_url']['url'].startswith('data:image/jpeg;base64,'))

    def test_service_fallback(self):
        service = load_default_gemini_service()
        
        # Mock Gemini client to raise 429
        service._client.generate_text = MagicMock(side_effect=google_exceptions.ResourceExhausted("429"))
        
        # Mock OpenAI client success
        service._openai = MagicMock()
        service._openai.generate_text.return_value = "Fallback Success"
        service._openai._model = "gpt-5.1"
        
        result = service.generate_text("Test prompt")
        self.assertEqual(result, "Fallback Success")
        print("Fallback test PASSED")

if __name__ == '__main__':
    unittest.main()
