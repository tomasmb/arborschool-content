"""
Retry handler with exponential backoff for API calls and operations.

Provides robust retry logic for:
- API rate limits (429)
- API quota errors
- Network errors
- Empty responses
- Transient failures
"""

from __future__ import annotations

import logging
import random
import time
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

T = TypeVar("T")

_logger = logging.getLogger(__name__)


def is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error is retryable.

    Args:
        error: The exception to check

    Returns:
        True if the error is retryable, False otherwise
    """
    error_str = str(error).lower()
    error_type = type(error).__name__.lower()

    # Rate limiting and quota errors
    if any(code in error_str for code in ["429", "rate limit", "quota", "insufficient_quota"]):
        return True

    # Server errors (5xx)
    if any(code in error_str for code in ["500", "502", "503", "504"]):
        return True

    # Network and connection errors
    retryable_keywords = [
        "timeout",
        "connection",
        "network",
        "unavailable",
        "bad gateway",
        "service unavailable",
        "gateway timeout",
        "internal server error",
        "connection reset",
        "connection refused",
    ]
    if any(keyword in error_str for keyword in retryable_keywords):
        return True

    # Empty response errors
    if "empty" in error_str or "no content" in error_str:
        return True

    # Specific exception types that are retryable
    retryable_types = [
        "timeouterror",
        "connectionerror",
        "httperror",
        "requestexception",
    ]
    if error_type in retryable_types:
        return True

    return False


def extract_retry_after(error: Exception) -> Optional[float]:
    """
    Extract retry-after delay from error message if available.

    Args:
        error: The exception to extract delay from

    Returns:
        Delay in seconds, or None if not found
    """
    error_str = str(error)

    # Look for "retry after" or "retry in" patterns
    import re

    patterns = [
        r"retry[_\s]+after[:\s]+(\d+(?:\.\d+)?)",
        r"retry[_\s]+in[:\s]+(\d+(?:\.\d+)?)",
        r"retryafter[:\s]+(\d+(?:\.\d+)?)",
        r'"retryafter":\s*"?(\d+(?:\.\d+)?)"?',
        r'"retry_after":\s*"?(\d+(?:\.\d+)?)"?',
    ]

    for pattern in patterns:
        match = re.search(pattern, error_str, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except (ValueError, IndexError):
                continue

    return None


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_check: Optional[Callable[[Exception], bool]] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        exponential_base: Base for exponential backoff (default: 2.0)
        jitter: Add random jitter to delays (default: True)
        retryable_check: Custom function to check if error is retryable

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Optional[Exception] = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    # Check if error is retryable
                    is_retryable = (
                        retryable_check(e) if retryable_check
                        else is_retryable_error(e)
                    )

                    if not is_retryable:
                        _logger.error(
                            f"Non-retryable error in {func.__name__}: {e}"
                        )
                        raise

                    # Don't retry on last attempt
                    if attempt == max_retries - 1:
                        _logger.error(
                            f"Max retries ({max_retries}) reached for "
                            f"{func.__name__}: {e}"
                        )
                        raise

                    # Calculate delay
                    delay = extract_retry_after(e)
                    if delay is None:
                        # Exponential backoff
                        delay = min(
                            base_delay * (exponential_base ** attempt),
                            max_delay
                        )

                    # Add jitter to avoid thundering herd
                    if jitter:
                        jitter_amount = random.uniform(0, delay * 0.1)
                        delay += jitter_amount

                    _logger.warning(
                        f"Retryable error in {func.__name__} "
                        f"(attempt {attempt + 1}/{max_retries}): {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    time.sleep(delay)

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError(f"Unexpected error in {func.__name__}")

        return wrapper
    return decorator


def retry_on_empty_response(
    max_retries: int = 3,
    base_delay: float = 2.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Specialized retry decorator for functions that may return empty responses.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds

    Returns:
        Decorated function with retry logic for empty responses
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            for attempt in range(max_retries):
                result = func(*args, **kwargs)

                # Check if result is empty
                is_empty = False
                if result is None:
                    is_empty = True
                elif isinstance(result, str):
                    is_empty = not result.strip()
                elif isinstance(result, dict):
                    is_empty = not result or (
                        result.get("success") is False and
                        "empty" in str(result.get("error", "")).lower()
                    )

                if not is_empty:
                    return result

                if attempt == max_retries - 1:
                    _logger.error(
                        f"Max retries ({max_retries}) reached for "
                        f"{func.__name__}: empty response"
                    )
                    if isinstance(result, dict):
                        return result
                    raise ValueError(f"Empty response from {func.__name__}")

                delay = base_delay * (2 ** attempt)
                _logger.warning(
                    f"Empty response from {func.__name__} "
                    f"(attempt {attempt + 1}/{max_retries}). "
                    f"Retrying in {delay:.2f}s..."
                )
                time.sleep(delay)

            raise RuntimeError(f"Unexpected error in {func.__name__}")

        return wrapper
    return decorator
