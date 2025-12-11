"""Split validation service."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

# Import from parent package
try:
    from models import QuestionChunk, SharedContext, SplitValidationResult, SplitValidationError
    from prompts.split_validation import create_split_validation_prompt
except ImportError:
    from ..models import QuestionChunk, SharedContext, SplitValidationResult, SplitValidationError
    from ..prompts.split_validation import create_split_validation_prompt

from .ai_client_factory import AIClient
from .openai_client import OpenAIClient

logger = logging.getLogger(__name__)

MAX_CONCURRENT_VALIDATIONS_GEMINI = 5
MAX_CONCURRENT_VALIDATIONS_OPENAI = 10


class SplitValidator:
    """
    Validates question splits using AI.
    
    Validates each question independently in parallel for speed and reliability.
    """

    def __init__(self, ai_client: AIClient):
        """Initialize with AI client."""
        self.client = ai_client
        self.max_concurrent = (
            MAX_CONCURRENT_VALIDATIONS_OPENAI 
            if isinstance(ai_client, OpenAIClient) 
            else MAX_CONCURRENT_VALIDATIONS_GEMINI
        )

    def validate(
        self, questions: list[QuestionChunk], shared_contexts: list[SharedContext] | None = None
    ) -> SplitValidationResult:
        """Validate that all questions are self-contained."""
        if not questions:
            return SplitValidationResult(is_valid=True, validation_results=[])
        
        logger.info(
            f"Validating {len(questions)} questions in parallel "
            f"(max {self.max_concurrent} concurrent)"
        )
        
        all_validation_results = []
        
        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            future_to_question = {
                executor.submit(
                    self._validate_single, question, questions, i, shared_contexts or []
                ): i
                for i, question in enumerate(questions)
            }
            
            for future in as_completed(future_to_question):
                question_idx = future_to_question[future]
                try:
                    result = future.result()
                    all_validation_results.append(result)
                    logger.debug(
                        f"Question {question_idx + 1}/{len(questions)} validated: "
                        f"{result.is_self_contained}"
                    )
                except Exception as e:
                    logger.error(f"Question {question_idx + 1} validation failed: {e}")
                    question_id = questions[question_idx].id
                    all_validation_results.append(
                        SplitValidationError(
                            question_id=question_id,
                            is_self_contained=False,
                            errors=[f"Validation failed: {str(e)}"],
                            warnings=[]
                        )
                    )
        
        question_id_to_index = {q.id: i for i, q in enumerate(questions)}
        all_validation_results.sort(key=lambda r: question_id_to_index.get(r.question_id, 999))
        
        is_valid = all(result.is_self_contained for result in all_validation_results)
        
        logger.info(
            f"Validation complete: "
            f"{sum(1 for r in all_validation_results if r.is_self_contained)}/{len(questions)} "
            f"questions valid"
        )
        
        self._log_failed_validations(questions, all_validation_results)
        
        return SplitValidationResult(is_valid=is_valid, validation_results=all_validation_results)

    def _log_failed_validations(
        self, questions: list[QuestionChunk], validation_results: list[SplitValidationError]
    ) -> None:
        """Log detailed info for questions that failed validation."""
        question_map = {q.id: q for q in questions}
        
        for result in validation_results:
            if result.is_self_contained:
                continue
            
            question = question_map.get(result.question_id)
            if not question:
                continue
            
            boundary_info = "No boundary info"
            if question.boundary:
                boundary_info = (
                    f"start_block_id={question.boundary.start_block_id}, "
                    f"end_block_id={question.boundary.end_block_id}"
                )
            
            logger.warning(
                f"❌ VALIDATION FAILED: {result.question_id}\n"
                f"   Boundaries: {boundary_info}\n"
                f"   Errors: {result.errors}\n"
                f"   Warnings: {result.warnings}\n"
                f"   Content ({len(question.content)} chars):\n"
                f"   {'='*60}\n"
                f"{question.content[:1500]}"
                f"{'... [truncated]' if len(question.content) > 1500 else ''}\n"
                f"   {'='*60}"
            )

    def _validate_single(
        self, 
        question: QuestionChunk, 
        all_questions: list[QuestionChunk], 
        question_index: int,
        all_shared_contexts: list[SharedContext] | None = None
    ) -> SplitValidationError:
        """Validate a single question with context from adjacent questions."""
        start_idx = max(0, question_index - 1)
        end_idx = min(len(all_questions), question_index + 2)
        context_questions = all_questions[start_idx:end_idx]
        
        relevant_contexts = []
        if all_shared_contexts:
            if question.shared_context_id:
                referenced_ctx = next(
                    (ctx for ctx in all_shared_contexts if ctx.id == question.shared_context_id),
                    None
                )
                if referenced_ctx:
                    relevant_contexts.append(referenced_ctx)
            for adj_q in context_questions:
                if adj_q.shared_context_id and adj_q.shared_context_id != question.shared_context_id:
                    adj_ctx = next(
                        (ctx for ctx in all_shared_contexts if ctx.id == adj_q.shared_context_id),
                        None
                    )
                    if adj_ctx and adj_ctx not in relevant_contexts:
                        relevant_contexts.append(adj_ctx)
        
        prompt = create_split_validation_prompt(context_questions, relevant_contexts)
        focus_instruction = (
            f"\n\n<focus>\nFocus validation on question {question.id} "
            f"(the middle question in the questions array above). "
            f"Verify it is self-contained and all referenced resources are present.\n</focus>"
        )

        try:
            response_data = self.client.generate_json(
                prompt + focus_instruction, thinking_level="high"
            )
            
            if "validation_results" not in response_data:
                raise ValueError("Missing validation_results in response")
            
            for result_data in response_data["validation_results"]:
                if result_data.get("question_id") == question.id:
                    return SplitValidationError(**result_data)
            
            raise ValueError(f"Validation result not found for question {question.id}")
            
        except ValueError as e:
            raise ValueError(f"Split validation failed - invalid response format: {e}")
        except Exception as e:
            raise Exception(f"Split validation failed - API error: {e}")

