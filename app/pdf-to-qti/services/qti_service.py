"""QTI Service - Generates QTI XML using AI."""

import re
from typing import Optional, Dict

# Import from parent package
try:
    from models import QuestionChunk, SharedContext, QTIItem, SourceFormat
    from prompts.qti_generation import create_qti_generation_prompt
    from prompts.qti_configs import get_question_config
except ImportError:
    from ..models import QuestionChunk, SharedContext, QTIItem, SourceFormat
    from ..prompts.qti_generation import create_qti_generation_prompt
    from ..prompts.qti_configs import get_question_config

from .ai_client_factory import AIClient


class QTIService:
    """Generates QTI 3.0 XML from validated questions."""

    def __init__(self, ai_client: AIClient):
        """Initialize with AI client."""
        self.client = ai_client

    def generate(
        self,
        question: QuestionChunk,
        shared_contexts: Dict[str, SharedContext],
        question_type: str = "choice",
        source_format: SourceFormat = "markdown",
    ) -> QTIItem:
        """
        Generate QTI XML for a single question.

        Args:
            question: Validated question chunk
            shared_contexts: Map of context IDs to SharedContext objects
            question_type: Detected QTI question type
            source_format: Input format ('markdown' or 'html')

        Returns:
            QTIItem with generated XML
        """
        shared_context = None
        if question.shared_context_id:
            shared_context = shared_contexts.get(question.shared_context_id)

        config = get_question_config(question_type)

        prompt = create_qti_generation_prompt(
            question=question,
            shared_context=shared_context,
            question_type=question_type,
            type_instructions=config.prompt_instructions,
            example_xml=config.example_xml,
            source_format=source_format,
        )

        try:
            qti_xml = self.client.generate_text(prompt, thinking_level="high")
            qti_xml = self._clean_xml(qti_xml)

            if config.post_process:
                qti_xml = config.post_process(qti_xml)

            if not qti_xml.strip().startswith("<qti-assessment-item"):
                raise ValueError("Invalid QTI XML: doesn't start with <qti-assessment-item>")

            return QTIItem(
                question_id=question.id, qti_xml=qti_xml, question_type=question_type
            )

        except ValueError as e:
            raise ValueError(
                f"QTI generation failed for question {question.id} - validation error: {e}"
            )
        except Exception as e:
            raise Exception(
                f"QTI generation failed for question {question.id} - API error: {e}"
            )

    def _clean_xml(self, xml_content: str) -> str:
        """Clean and normalize QTI XML content."""
        if xml_content.strip().startswith("```xml"):
            xml_content = xml_content.strip()[6:-3].strip()
        elif xml_content.strip().startswith("```"):
            xml_content = xml_content.strip()[3:-3].strip()

        if xml_content.strip().startswith("<?xml"):
            xml_content = xml_content.split("?>", 1)[1].strip()

        xml_content = xml_content.replace("\x00", "")
        xml_content = self._fix_ncname_identifiers(xml_content)

        return xml_content.strip()

    def _fix_ncname_identifiers(self, xml_content: str) -> str:
        """Fix identifier attributes that start with numbers (invalid NCName)."""
        pattern = r'(identifier\s*=\s*["\'])(\d[^"\']*)(["\'"])'
        
        def prefix_identifier(match):
            prefix = match.group(1)
            value = match.group(2)
            suffix = match.group(3)
            return f'{prefix}Q_{value}{suffix}'
        
        return re.sub(pattern, prefix_identifier, xml_content, flags=re.IGNORECASE)

