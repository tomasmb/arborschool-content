"""Semantic Validator - Validates XML fidelity using AI."""

from typing import Dict, Any

# Import from parent package
try:
    from models import SemanticValidationResult, SourceFormat
    from prompts.semantic_validation import create_semantic_validation_prompt
except ImportError:
    from ..models import SemanticValidationResult, SourceFormat
    from ..prompts.semantic_validation import create_semantic_validation_prompt

from .ai_client_factory import AIClient


class SemanticValidator:
    """Validates semantic fidelity of QTI XML against original source content."""

    FIDELITY_THRESHOLD = 90

    def __init__(self, ai_client: AIClient):
        """Initialize with AI client."""
        self.client = ai_client

    def validate(
        self,
        source_content: str,
        xml: str,
        source_format: SourceFormat = "markdown",
    ) -> SemanticValidationResult:
        """
        Validate XML semantic fidelity against original source content.

        Returns:
            SemanticValidationResult with fidelity score and errors
        """
        prompt = create_semantic_validation_prompt(source_content, xml, source_format)

        try:
            response_data = self.client.generate_json(prompt, thinking_level="high")
            return self._parse_response(response_data)
        except ValueError as e:
            raise ValueError(f"Semantic validation failed - invalid response format: {e}")
        except Exception as e:
            raise Exception(f"Semantic validation failed - API error: {e}")

    def _parse_response(self, data: Dict[str, Any]) -> SemanticValidationResult:
        """Parse and validate response."""
        if "is_valid" not in data or "fidelity_score" not in data:
            raise ValueError("Invalid semantic validation response structure")

        fidelity_score = data["fidelity_score"]
        is_valid = data["is_valid"] and fidelity_score >= self.FIDELITY_THRESHOLD

        return SemanticValidationResult(
            is_valid=is_valid,
            fidelity_score=fidelity_score,
            errors=data.get("errors", []),
            warnings=data.get("warnings", []),
        )

