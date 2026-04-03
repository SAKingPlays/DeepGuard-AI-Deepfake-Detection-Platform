"""Logging configuration."""
import logging
import os
from datetime import datetime
from src.config import LOGS_DIR


def setup_logger(name: str = "deepguard") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    fmt = logging.Formatter("[%(asctime)s] %(levelname)-8s %(name)s: %(message)s",
                            datefmt="%H:%M:%S")
    ch.setFormatter(fmt)

    # File handler
    log_file = os.path.join(LOGS_DIR,
                            f"deepguard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger


def get_logger(name: str = "deepguard") -> logging.Logger:
    return logging.getLogger(name)
