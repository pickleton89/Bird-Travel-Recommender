"""
Centralized logging configuration.

This module provides consistent logging setup across the entire application,
eliminating scattered logging configuration.
"""

import logging
import sys
from typing import Optional
from .settings import settings


def setup_logging(level: Optional[str] = None, structured: bool = False) -> None:
    """
    Configure application-wide logging.
    
    Args:
        level: Log level override (defaults to settings.log_level)
        structured: Whether to use JSON structured logging
    """
    log_level = level or settings.log_level
    log_level_obj = getattr(logging, log_level.upper())
    
    # Create formatter
    if structured:
        # For production environments, structured logging is preferred
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "name": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        # For development, human-readable format
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level_obj)
    
    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    
    # Suppress noisy third-party loggers in non-debug mode
    if log_level != "DEBUG":
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("aiohttp").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str, correlation_id: Optional[str] = None) -> logging.Logger:
    """
    Get a logger with optional correlation ID.
    
    Args:
        name: Logger name (usually __name__)
        correlation_id: Optional correlation ID for request tracking
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if correlation_id:
        # Create adapter for correlation ID tracking
        logger = logging.LoggerAdapter(logger, {"correlation_id": correlation_id})
    
    return logger


# Initialize logging on import
setup_logging(structured=(settings.environment == "production"))