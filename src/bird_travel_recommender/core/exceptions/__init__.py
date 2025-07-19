"""Centralized exception hierarchy."""

from .base import (
    ErrorContext,
    BirdTravelRecommenderError,
    ValidationError,
    ConfigurationError,
)
from .ebird import (
    EBirdAPIError,
    EBirdAuthenticationError,
    EBirdRateLimitError,
    EBirdTimeoutError,
    EBirdServerError,
    EBirdDataError,
)
from .mcp import (
    MCPError,
    MCPToolNotFoundError,
    MCPToolExecutionError,
    MCPSchemaValidationError,
    MCPRegistrationError,
)

__all__ = [
    # Base exceptions
    "ErrorContext",
    "BirdTravelRecommenderError",
    "ValidationError",
    "ConfigurationError",
    # eBird exceptions
    "EBirdAPIError",
    "EBirdAuthenticationError",
    "EBirdRateLimitError",
    "EBirdTimeoutError",
    "EBirdServerError",
    "EBirdDataError",
    # MCP exceptions
    "MCPError",
    "MCPToolNotFoundError",
    "MCPToolExecutionError",
    "MCPSchemaValidationError",
    "MCPRegistrationError",
]