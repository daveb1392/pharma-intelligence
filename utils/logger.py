"""Logging configuration for Pharma Intelligence scrapers."""

import sys
from loguru import logger
from utils.config import get_settings


def setup_logger() -> None:
    """Configure loguru logger with application settings."""
    settings = get_settings()

    # Remove default logger
    logger.remove()

    # Add console logger with configured level
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.log_level,
        colorize=True,
    )

    # Add file logger for persistent logs
    logger.add(
        "logs/pharma_intelligence_{time:YYYY-MM-DD}.log",
        rotation="00:00",  # Rotate at midnight
        retention="30 days",  # Keep logs for 30 days
        level="DEBUG",  # Log everything to file
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    logger.info(f"Logger initialized with level: {settings.log_level}")


def get_logger():
    """Get configured logger instance."""
    return logger
