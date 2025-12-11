"""Factory for creating AI clients based on provider.

Supports:
- gemini: Uses GeminiClient (default)
- gpt: Uses OpenAIClient
- opus: Uses AnthropicClient (Claude Opus 4.5 via AWS Bedrock)
"""

import logging
from typing import Literal, Protocol, Dict, Any, List

logger = logging.getLogger(__name__)

# Type alias for model provider selection
ModelProvider = Literal["gemini", "gpt", "opus"]


class AIClient(Protocol):
    """Protocol for AI clients - defines the interface all clients must implement."""
    
    def generate_json(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 8192,
        thinking_level: str = "high",
    ) -> Dict[str, Any]:
        """Generate JSON response from the AI model."""
        ...

    def generate_text(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 8192,
        thinking_level: str = "high",
    ) -> str:
        """Generate text response from the AI model."""
        ...

    def generate_json_with_images(
        self,
        prompt: str,
        images: List[Dict[str, Any]],
        max_tokens: int = 8192,
        thinking_level: str = "high",
    ) -> Dict[str, Any]:
        """Generate JSON response with image context."""
        ...


def create_ai_client(model_provider: ModelProvider = "gemini") -> AIClient:
    """
    Create an AI client based on the specified provider.

    Args:
        model_provider: The AI provider to use ("gemini", "gpt", or "opus")

    Returns:
        AIClient instance

    Raises:
        ValueError: If unknown provider specified
    """
    if model_provider == "gemini":
        from .gemini_client import GeminiClient
        logger.info("Using Gemini (gemini-3-pro-preview) as AI provider")
        return GeminiClient()
    elif model_provider == "gpt":
        from .openai_client import OpenAIClient
        logger.info("Using OpenAI GPT-5.1 as AI provider")
        return OpenAIClient()
    elif model_provider == "opus":
        from .anthropic_client import AnthropicClient
        logger.info("Using Anthropic Claude Opus 4.5 via Bedrock as AI provider")
        return AnthropicClient()
    else:
        raise ValueError(
            f"Unknown model provider: {model_provider}. "
            "Supported providers: 'gemini', 'gpt', 'opus'"
        )

