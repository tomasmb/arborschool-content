"""Configuration handling for PDF to QTI pipeline.

Loads settings from environment variables and/or .env file.
"""

import os
from pathlib import Path
from typing import Optional

# Try to load from .env file
try:
    from dotenv import load_dotenv
    
    # Look for .env in current directory or parent directories
    env_path = Path('.env')
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # Try parent directory
        parent_env = Path('..') / '.env'
        if parent_env.exists():
            load_dotenv(parent_env)
except ImportError:
    pass  # python-dotenv not installed


class Config:
    """Configuration settings for the PDF to QTI pipeline."""
    
    # AI Provider API Keys
    GEMINI_API_KEY: Optional[str] = os.environ.get("GEMINI_API_KEY")
    OPENAI_API_KEY: Optional[str] = os.environ.get("OPENAI_API_KEY")
    
    # AWS Bedrock (for Anthropic Claude)
    AWS_ACCESS_KEY_ID: Optional[str] = os.environ.get("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.environ.get("AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str = os.environ.get("AWS_REGION", "us-east-1")
    
    # Extend.ai API
    EXTEND_API_KEY: Optional[str] = os.environ.get("EXTEND_API_KEY")
    
    # Default settings
    DEFAULT_PROVIDER: str = os.environ.get("DEFAULT_PROVIDER", "gemini")
    DEFAULT_OUTPUT_DIR: str = os.environ.get("DEFAULT_OUTPUT_DIR", "./output")
    
    @classmethod
    def validate_provider(cls, provider: str) -> bool:
        """Check if the specified provider has required credentials."""
        if provider == "gemini":
            return bool(cls.GEMINI_API_KEY)
        elif provider == "gpt":
            return bool(cls.OPENAI_API_KEY)
        elif provider == "opus":
            return bool(cls.AWS_ACCESS_KEY_ID and cls.AWS_SECRET_ACCESS_KEY)
        return False
    
    @classmethod
    def get_available_providers(cls) -> list:
        """Get list of providers with valid credentials."""
        providers = []
        if cls.GEMINI_API_KEY:
            providers.append("gemini")
        if cls.OPENAI_API_KEY:
            providers.append("gpt")
        if cls.AWS_ACCESS_KEY_ID and cls.AWS_SECRET_ACCESS_KEY:
            providers.append("opus")
        return providers
    
    @classmethod
    def can_parse_pdf(cls) -> bool:
        """Check if Extend.ai API key is available for PDF parsing."""
        return bool(cls.EXTEND_API_KEY)

