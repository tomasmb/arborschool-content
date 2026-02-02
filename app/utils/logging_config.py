"""Centralized logging configuration for CLI scripts.

This module provides a consistent logging setup used across all CLI scripts
to avoid duplicating the same basicConfig pattern everywhere.
"""

from __future__ import annotations

import logging

# Default format used across all scripts
DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def setup_logging(verbose: bool = False, level: int | None = None) -> None:
    """Configure logging with consistent format.

    Args:
        verbose: If True, sets level to DEBUG. Overrides `level` parameter.
        level: Explicit logging level. Defaults to INFO if not specified.

    Example:
        >>> setup_logging()  # INFO level
        >>> setup_logging(verbose=True)  # DEBUG level
        >>> setup_logging(level=logging.WARNING)  # WARNING level
    """
    if verbose:
        effective_level = logging.DEBUG
    elif level is not None:
        effective_level = level
    else:
        effective_level = logging.INFO

    logging.basicConfig(
        level=effective_level,
        format=DEFAULT_LOG_FORMAT,
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name.

    This is a convenience wrapper around logging.getLogger() that ensures
    consistent usage patterns.

    Args:
        name: The logger name, typically __name__ of the calling module.

    Returns:
        A Logger instance.
    """
    return logging.getLogger(name)
