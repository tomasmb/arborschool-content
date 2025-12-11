"""Base AI client with shared retry, rate limiting, and error handling logic.

Provides common infrastructure for AI API clients:
- Exponential backoff with jitter
- Thread-safe rate limiting
- Retryable error detection
- Response parsing
"""

import json
import time
import random
import logging
import threading
import re
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, Callable
from collections import deque

logger = logging.getLogger(__name__)


class BaseAIClient(ABC):
    """
    Abstract base class for AI API clients.
    
    Provides:
    - Retry logic with exponential backoff
    - Thread-safe rate limiting
    - Error classification (retryable vs non-retryable)
    
    Subclasses must implement:
    - _make_json_request(): Provider-specific JSON generation
    - _make_text_request(): Provider-specific text generation
    - _parse_response(): Provider-specific response parsing
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        rate_limit_per_minute: int = 25,
    ):
        """
        Initialize base client with retry and rate limit configuration.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay between retries (seconds)
            max_delay: Maximum delay between retries (seconds)
            rate_limit_per_minute: Max requests per minute (for rate limiting)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.rate_limit_per_minute = rate_limit_per_minute
        self.rate_limit_window = 60.0
        
        # Thread-safe rate limiting
        self.request_timestamps: deque = deque()
        self._rate_limit_lock = threading.Lock()

    # =========================================================================
    # Public Interface
    # =========================================================================

    def generate_json(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 8192,
        thinking_level: str = "high",
    ) -> Dict[str, Any]:
        """
        Generate JSON response from the AI model.

        Args:
            prompt: The prompt to send
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum output tokens
            thinking_level: Reasoning depth ("low" or "high")

        Returns:
            Parsed JSON dict

        Raises:
            ValueError: If response is not valid JSON
            Exception: If API call fails after all retries
        """
        return self._generate_with_retry(
            lambda: self._make_json_request(prompt, temperature, max_tokens, thinking_level),
            parse_json=True,
        )

    def generate_text(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 8192,
        thinking_level: str = "high",
    ) -> str:
        """
        Generate text response from the AI model.

        Args:
            prompt: The prompt to send
            temperature: Sampling temperature
            max_tokens: Maximum output tokens
            thinking_level: Reasoning depth ("low" or "high")

        Returns:
            Generated text

        Raises:
            Exception: If API call fails after all retries
        """
        return self._generate_with_retry(
            lambda: self._make_text_request(prompt, temperature, max_tokens, thinking_level),
            parse_json=False,
        )

    # =========================================================================
    # Abstract Methods (Provider-Specific)
    # =========================================================================

    @abstractmethod
    def _make_json_request(
        self, prompt: str, temperature: float, max_tokens: int, thinking_level: str
    ) -> Any:
        """Make provider-specific API call for JSON generation."""
        pass

    @abstractmethod
    def _make_text_request(
        self, prompt: str, temperature: float, max_tokens: int, thinking_level: str
    ) -> Any:
        """Make provider-specific API call for text generation."""
        pass

    @abstractmethod
    def _parse_response(self, response: Any) -> str:
        """Parse provider-specific response to extract content string."""
        pass

    # =========================================================================
    # Retry Logic with Exponential Backoff
    # =========================================================================

    def _generate_with_retry(
        self,
        api_call: Callable,
        parse_json: bool = False,
        max_retries: Optional[int] = None,
    ) -> Any:
        """Execute API call with retry logic, exponential backoff, and rate limiting."""
        max_retries = max_retries or self.max_retries
        delay = self.base_delay

        for attempt in range(max_retries):
            try:
                self._wait_for_rate_limit()
                response = api_call()
                content = self._parse_response(response)

                if parse_json:
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError as e:
                        raise ValueError(f"Invalid JSON response: {e}")

                return content.strip() if isinstance(content, str) else content

            except ValueError:
                raise
            except Exception as e:
                is_retryable = self._is_retryable_error(e)
                is_last_attempt = attempt == max_retries - 1

                if not is_retryable or is_last_attempt:
                    error_type = "non-retryable" if not is_retryable else "max retries"
                    raise Exception(f"API call failed ({error_type}): {e}")

                sleep_time = self._calculate_retry_delay(e, delay)
                logger.warning(
                    f"Retryable error (attempt {attempt + 1}/{max_retries}): {e}. "
                    f"Retrying in {sleep_time:.2f}s..."
                )
                time.sleep(sleep_time)
                delay = min(delay * 2, self.max_delay)

        raise Exception("API call failed after all retries")

    def _calculate_retry_delay(self, error: Exception, current_delay: float) -> float:
        """Calculate retry delay, using API-specified delay for rate limits if available."""
        error_str = str(error).lower()
        if "429" in error_str or "rate limit" in error_str or "quota" in error_str:
            api_delay = self._extract_retry_delay(error)
            if api_delay:
                return min(api_delay + 1.0, self.max_delay)

        jitter = random.uniform(0, 0.3 * current_delay)
        return min(current_delay + jitter, self.max_delay)

    def _extract_retry_delay(self, error: Exception) -> Optional[float]:
        """Extract retry delay from error response if available."""
        error_str = str(error)

        match = re.search(r'Please retry in ([\d.]+)s', error_str, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass

        retry_match = re.search(r'"retryDelay":\s*"([\d.]+)s?"', error_str)
        if retry_match:
            try:
                return float(retry_match.group(1))
            except ValueError:
                pass

        return None

    # =========================================================================
    # Error Classification
    # =========================================================================

    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine if an error is retryable."""
        error_str = str(error).lower()

        if "429" in error_str or "rate limit" in error_str or "quota" in error_str:
            return True

        if any(code in error_str for code in ["500", "502", "503", "504"]):
            return True

        retryable_keywords = [
            "timeout", "connection", "network", "unavailable",
            "bad gateway", "service unavailable", "gateway timeout",
            "internal server error",
        ]
        if any(keyword in error_str for keyword in retryable_keywords):
            return True

        if isinstance(error, json.JSONDecodeError):
            return False

        return False

    # =========================================================================
    # Rate Limiting
    # =========================================================================

    def _wait_for_rate_limit(self) -> None:
        """Wait if necessary to respect rate limit. Thread-safe."""
        with self._rate_limit_lock:
            now = time.time()

            while (self.request_timestamps and 
                   (now - self.request_timestamps[0]) > self.rate_limit_window):
                self.request_timestamps.popleft()

            if len(self.request_timestamps) >= self.rate_limit_per_minute:
                oldest_timestamp = self.request_timestamps[0]
                wait_time = self.rate_limit_window - (now - oldest_timestamp) + 0.1

                if wait_time > 0:
                    logger.info(
                        f"Rate limit reached ({self.rate_limit_per_minute}/min). "
                        f"Waiting {wait_time:.2f}s..."
                    )
                    self._rate_limit_lock.release()
                    try:
                        time.sleep(wait_time)
                    finally:
                        self._rate_limit_lock.acquire()

                    now = time.time()
                    while (self.request_timestamps and 
                           (now - self.request_timestamps[0]) > self.rate_limit_window):
                        self.request_timestamps.popleft()

            self.request_timestamps.append(time.time())

