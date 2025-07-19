"""
MCP-specific exceptions.

This module provides exceptions for MCP tool and handler operations,
consolidating error handling for the MCP subsystem.
"""

from typing import Optional
from .base import BirdTravelRecommenderError, ErrorContext, ErrorSeverity


class MCPError(BirdTravelRecommenderError):
    """
    Base exception for MCP-related errors.
    """
    
    def __init__(self, message: str, tool_name: Optional[str] = None, **kwargs):
        context = kwargs.get('context', ErrorContext())
        if tool_name:
            context.add_context("tool_name", tool_name)
            
        super().__init__(
            message, 
            context=context,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class MCPToolNotFoundError(MCPError):
    """
    Raised when a requested MCP tool is not found in the registry.
    """
    
    def __init__(self, tool_name: str, **kwargs):
        super().__init__(
            f"MCP tool '{tool_name}' not found in registry",
            tool_name=tool_name,
            severity=ErrorSeverity.LOW,
            recoverable=False,
            **kwargs
        )


class MCPToolExecutionError(MCPError):
    """
    Raised when an MCP tool fails during execution.
    """
    
    def __init__(self, message: str, tool_name: str, **kwargs):
        super().__init__(
            f"MCP tool '{tool_name}' execution failed: {message}",
            tool_name=tool_name,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class MCPSchemaValidationError(MCPError):
    """
    Raised when MCP tool input fails schema validation.
    """
    
    def __init__(self, message: str, tool_name: str, **kwargs):
        super().__init__(
            f"MCP tool '{tool_name}' schema validation failed: {message}",
            tool_name=tool_name,
            severity=ErrorSeverity.LOW,
            **kwargs
        )


class MCPRegistrationError(MCPError):
    """
    Raised when MCP tool registration fails.
    """
    
    def __init__(self, message: str, tool_name: str, **kwargs):
        super().__init__(
            f"MCP tool '{tool_name}' registration failed: {message}",
            tool_name=tool_name,
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            **kwargs
        )