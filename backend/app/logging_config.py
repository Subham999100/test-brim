"""Centralized logging configuration for SAP BRIM AI backend."""

import os
import sys
import logging
from backend.app.security.log_safety import PrivacyLogFilter

VERBOSE_LOGGERS = (
    "uvicorn.access",
    "sqlalchemy.engine",
    "sqlalchemy.pool",
    "sqlalchemy.dialects",
    "httpx",
    "httpcore",
    "urllib3",
    "watchfiles",
    "passlib",
    "huggingface_hub",
    "transformers",
    "torch",
    "sentence_transformers",
    "google",
    "google.generativeai",
    "google.auth",
    "groq",
    "openai",
    "asyncio",
    "multipart",
)


class AppLogFormatter(logging.Formatter):
    """Clean, consistent formatting for terminal logs."""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


def setup_logging(log_level: str | None = None) -> None:
    """Initialize and configure centralized application logging."""
    log_level_name = (log_level or os.getenv("LOG_LEVEL", "INFO")).upper().strip()
    resolved_level = getattr(logging, log_level_name, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(resolved_level)

    # Avoid duplicate handlers on re-initialization or module reload
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(resolved_level)
    console_handler.setFormatter(AppLogFormatter())
    console_handler.addFilter(PrivacyLogFilter())
    root_logger.addHandler(console_handler)

    # Silence noisy third-party and internal query loggers
    target_noise_level = logging.WARNING if resolved_level > logging.DEBUG else logging.DEBUG
    for name in VERBOSE_LOGGERS:
        noisy_logger = logging.getLogger(name)
        noisy_logger.setLevel(target_noise_level)
        noisy_logger.propagate = False
