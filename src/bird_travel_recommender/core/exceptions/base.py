"""
Base exception hierarchy for the Bird Travel Recommender.

This module provides the foundational exception classes that eliminate
duplicate exception handling patterns across the codebase.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from ..config.constants import ErrorSeverity


class ErrorContext:
    """
    Rich error context for debugging and monitoring.
    
    Provides structured context information that can be used for
    debugging, monitoring, and automated error handling.
    """
    
    def __init__(self):
        self.correlation_id = str(uuid.uuid4())
        self.timestamp = datetime.utcnow()
        self.stack_trace: Optional[str] = None
        self.user_context: Dict[str, Any] = {}
        self.system_context: Dict[str, Any] = {}
        
    def add_context(self, key: str, value: Any) -> None:
        """Add contextual information."""
        self.user_context[key] = value
        
    def add_system_context(self, key: str, value: Any) -> None:
        """Add system-level contextual information."""
        self.system_context[key] = value
        
    def to_dict(self) -> Dict[str, Any]:
        """Serialize context for logging and monitoring."""
        return {
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "stack_trace": self.stack_trace,
            "user_context": self.user_context,
            "system_context": self.system_context
        }


class BirdTravelRecommenderError(Exception):
    """
    Base exception for all application errors.
    
    Provides rich context, error categorization, and structured
    error information for consistent error handling.
    """
    
    def __init__(
        self, 
        message: str, 
        code: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[ErrorContext] = None,
        recoverable: bool = True
    ):
        self.message = message
        self.code = code or self.__class__.__name__
        self.severity = severity
        self.context = context or ErrorContext()
        self.recoverable = recoverable
        super().__init__(message)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for serialization."""
        return {
            "error": self.message,
            "code": self.code,
            "severity": self.severity.value,
            "recoverable": self.recoverable,
            "context": self.context.to_dict(),
            "type": self.__class__.__name__
        }
        
    def add_context(self, key: str, value: Any) -> None:
        """Add contextual information to the error."""
        self.context.add_context(key, value)


class ValidationError(BirdTravelRecommenderError):
    """
    Input validation errors.
    
    Raised when user input fails validation checks.
    """
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        super().__init__(message, severity=ErrorSeverity.LOW, **kwargs)
        if field:
            self.add_context("field", field)


class ConfigurationError(BirdTravelRecommenderError):
    """
    Configuration-related errors.
    
    Raised when application configuration is invalid or missing.
    """
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, 
            severity=ErrorSeverity.HIGH, 
            recoverable=False,
            **kwargs
        )