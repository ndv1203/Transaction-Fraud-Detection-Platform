"""Structured logging utility for the Transaction Fraud Detection Platform."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(
    name: str = "fraud_detection",
    level: int | str = logging.INFO,
    log_file: str | Path | None = None,
) -> logging.Logger:
    """Create or retrieve a configured logger instance.

    Args:
        name: Logger namespace.
        level: Logging level (e.g., logging.INFO or "INFO").
        log_file: Optional file path to also write logs to disk.

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(name)
    resolved_level = (
        getattr(logging, level.upper(), logging.INFO)
        if isinstance(level, str)
        else level
    )
    logger.setLevel(resolved_level)
    logger.propagate = False

    formatter = logging.Formatter(fmt=DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)

    has_stream_handler = any(
        isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        for h in logger.handlers
    )
    if not has_stream_handler:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(resolved_level)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    if log_file is not None:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_path = str(log_path.resolve())
        has_file_handler = any(
            isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", None) == resolved_path
            for h in logger.handlers
        )
        if not has_file_handler:
            file_handler = logging.FileHandler(resolved_path, encoding="utf-8")
            file_handler.setLevel(resolved_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    return logger
