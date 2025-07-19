"""
eBird API specific exceptions.

This module consolidates all eBird API error handling into a single
location, eliminating duplicate exception classes.
"""

from typing import Optional
from .base import BirdTravelRecommenderError, ErrorContext, ErrorSeverity


class EBirdAPIError(BirdTravelRecommenderError):
    """
    Base exception for eBird API errors.
    
    Consolidates the duplicate EBirdAPIError classes found in both
    sync and async implementations.
    """
    
    def __init__(
        self, 
        message: str, 
        status_code: Optional[int] = None,
        endpoint: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', ErrorContext())
        if status_code:
            context.add_context("status_code", status_code)
        if endpoint:
            context.add_context("endpoint", endpoint)
            
        super().__init__(
            message, 
            context=context,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class EBirdAuthenticationError(EBirdAPIError):
    """
    eBird API authentication errors.
    
    Raised when API key is invalid or missing.
    """
    
    def __init__(self, message: str = "Invalid or missing eBird API key", **kwargs):
        super().__init__(
            message, 
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            **kwargs
        )


class EBirdRateLimitError(EBirdAPIError):
    """
    eBird API rate limit errors.
    
    Raised when API rate limits are exceeded.
    """
    
    def __init__(self, message: str = "eBird API rate limit exceeded", **kwargs):
        super().__init__(
            message, 
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            **kwargs
        )


class EBirdTimeoutError(EBirdAPIError):
    """
    eBird API timeout errors.
    
    Raised when API requests timeout.
    """
    
    def __init__(self, message: str = "eBird API request timeout", **kwargs):
        super().__init__(
            message, 
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            **kwargs
        )


class EBirdServerError(EBirdAPIError):
    """
    eBird API server errors.
    
    Raised when eBird API returns 5xx status codes.
    """
    
    def __init__(self, message: str = "eBird API server error", **kwargs):
        super().__init__(
            message, 
            severity=ErrorSeverity.HIGH,
            recoverable=True,
            **kwargs
        )


class EBirdDataError(EBirdAPIError):
    """
    eBird data processing errors.
    
    Raised when received data cannot be processed or is malformed.
    """
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, 
            severity=ErrorSeverity.MEDIUM,
            recoverable=False,
            **kwargs
        )