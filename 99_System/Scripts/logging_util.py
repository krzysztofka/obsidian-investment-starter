"""Unified structured logging configuration with RichHandler support."""

import logging
import os
import sys

try:
    from rich.logging import RichHandler

    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False

_DEFAULT_FORMAT = "%(message)s"
_FILE_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def setup_logging(
    level: int = logging.INFO,
    log_file: str | None = None,
    use_rich: bool = True,
) -> logging.Logger:
    """Configure root logger with RichHandler for console and FileHandler if log_file is specified."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Avoid duplicate handlers on re-initialization
    root_logger.handlers.clear()

    console_handler: logging.Handler
    if use_rich and _HAS_RICH:
        console_handler = RichHandler(
            rich_tracebacks=True,
            show_time=False,
            show_path=False,
            markup=True,
        )
        console_handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT))
    else:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

    console_handler.setLevel(level)
    root_logger.addHandler(console_handler)

    if log_file:
        os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(_FILE_FORMAT))
        root_logger.addHandler(file_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Retrieve named logger."""
    return logging.getLogger(name)
