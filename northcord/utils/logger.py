from __future__ import annotations

import logging
import sys
from typing import Literal

_LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

_LOGGER_NAME = "northcord"


def setup_logging(
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO",
    log_file: str | None = None,
) -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(_LOG_LEVELS.get(level.upper(), logging.INFO))

    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stderr)
    # Console handler shows WARNING and above by default to keep terminal outputs neat and clean
    console_level = logging.WARNING if level.upper() != "DEBUG" else logging.DEBUG
    handler.setLevel(console_level)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if log_file:
        try:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except OSError as e:
            logger.warning("Could not set up log file %s: %s", log_file, e)

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    full_name = f"{_LOGGER_NAME}.{name}" if name else _LOGGER_NAME
    return logging.getLogger(full_name)
