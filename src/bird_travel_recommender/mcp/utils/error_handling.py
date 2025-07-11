#!/usr/bin/env python3
"""
Enhanced Error Handling Framework for MCP Tools

Provides comprehensive error handling, recovery strategies, and validation
for all 30 MCP tools across 6 categories.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Dict, Optional, Callable
from functools import wraps

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Categories of errors that can occur in MCP tools"""

    API_ERROR = "api_error"
    VALIDATION_ERROR = "validation_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    TIMEOUT_ERROR = "timeout_error"
    DATA_ERROR = "data_error"
    NETWORK_ERROR = "network_error"
    UNKNOWN_ERROR = "unknown_error"


class MCPError(Exception):
    """Base exception class for MCP tool errors"""

    def __init__(
        self, message: str, category: ErrorCategory, details: Optional[Dict] = None
    ):
        self.message = message
        self.category = category
        self.details = details or {}
        super().__init__(message)


class ValidationError(MCPError):
    """Raised when input validation fails"""

    def __init__(self, message: str, field: str, value: Any):
        super().__init__(
            message, ErrorCategory.VALIDATION_ERROR, {"field": field, "value": value}
        )
        self.field = field
        self.value = value


class APIError(MCPError):
    """Raised when eBird API calls fail"""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        endpoint: Optional[str] = None,
    ):
        super().__init__(
            message,
            ErrorCategory.API_ERROR,
            {"status_code": status_code, "endpoint": endpoint},
        )
        self.status_code = status_code
        self.endpoint = endpoint


class RateLimitError(MCPError):
    """Raised when API rate limits are exceeded"""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(
            message, ErrorCategory.RATE_LIMIT_ERROR, {"retry_after": retry_after}
        )
        self.retry_after = retry_after


def validate_parameters(schema: Dict[str, Dict]) -> Callable:
    """
    Decorator to validate input parameters against a schema.

    Args:
        schema: Dict mapping parameter names to validation rules
                e.g., {"lat": {"type": float, "range": (-90, 90)}}
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Validate each parameter
            for param_name, rules in schema.items():
                if param_name in kwargs:
                    value = kwargs[param_name]

                    # Type validation
                    if "type" in rules and not isinstance(value, rules["type"]):
                        # Handle tuple of types (e.g., (int, float))
                        if isinstance(rules["type"], tuple):
                            type_names = " or ".join(t.__name__ for t in rules["type"])
                        else:
                            type_names = rules["type"].__name__

                        raise ValidationError(
                            f"Parameter '{param_name}' must be of type {type_names}",
                            param_name,
                            value,
                        )

                    # Range validation
                    if "range" in rules and isinstance(value, (int, float)):
                        min_val, max_val = rules["range"]
                        if not (min_val <= value <= max_val):
                            raise ValidationError(
                                f"Parameter '{param_name}' must be between {min_val} and {max_val}",
                                param_name,
                                value,
                            )

                    # Length validation for strings/lists
                    if "max_length" in rules and hasattr(value, "__len__"):
                        if len(value) > rules["max_length"]:
                            raise ValidationError(
                                f"Parameter '{param_name}' length exceeds maximum of {rules['max_length']}",
                                param_name,
                                value,
                            )

                # Required parameter validation
                elif rules.get("required", False):
                    raise ValidationError(
                        f"Required parameter '{param_name}' is missing",
                        param_name,
                        None,
                    )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def with_timeout(timeout_seconds: int = 30) -> Callable:
    """Decorator to add timeout handling to async functions"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs), timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                raise MCPError(
                    f"Operation timed out after {timeout_seconds} seconds",
                    ErrorCategory.TIMEOUT_ERROR,
                    {
                        "timeout_seconds": timeout_seconds,
                        "function": getattr(func, "__name__", str(func)),
                    },
                )

        return wrapper

    return decorator


def with_retry(
    max_retries: int = 3, delay: float = 1.0, backoff_factor: float = 2.0
) -> Callable:
    """Decorator to add retry logic with exponential backoff"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except (APIError, RateLimitError, MCPError) as e:
                    last_exception = e

                    if attempt == max_retries:
                        break

                    # Special handling for rate limit errors
                    if isinstance(e, RateLimitError) and e.retry_after:
                        wait_time = e.retry_after
                    else:
                        wait_time = current_delay

                    logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                    current_delay *= backoff_factor
                except Exception as e:
                    # Don't retry for unexpected errors
                    last_exception = e
                    break

            if last_exception:
                raise last_exception
            else:
                raise MCPError("Maximum retries exceeded", ErrorCategory.API_ERROR)

        return wrapper

    return decorator


def handle_errors_gracefully(fallback_value: Any = None) -> Callable:
    """
    Decorator to provide graceful error handling with standardized responses.

    Args:
        fallback_value: Value to return in case of error (for data fields)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)

            except ValidationError as e:
                logger.error(
                    f"Validation error in {getattr(func, '__name__', str(func))}: {e.message}"
                )
                return {
                    "success": False,
                    "error": e.message,
                    "error_category": e.category.value,
                    "error_details": e.details,
                    "validation_failed": True,
                }

            except APIError as e:
                logger.error(
                    f"API error in {getattr(func, '__name__', str(func))}: {e.message}"
                )
                return {
                    "success": False,
                    "error": f"eBird API error: {e.message}",
                    "error_category": e.category.value,
                    "error_details": e.details,
                    "api_failed": True,
                    **({"data": fallback_value} if fallback_value is not None else {}),
                }

            except RateLimitError as e:
                logger.error(
                    f"Rate limit error in {getattr(func, '__name__', str(func))}: {e.message}"
                )
                return {
                    "success": False,
                    "error": f"Rate limit exceeded: {e.message}",
                    "error_category": e.category.value,
                    "error_details": e.details,
                    "rate_limited": True,
                    "retry_after": e.retry_after,
                }

            except MCPError as e:
                logger.error(
                    f"MCP error in {getattr(func, '__name__', str(func))}: {e.message}"
                )
                return {
                    "success": False,
                    "error": e.message,
                    "error_category": e.category.value,
                    "error_details": e.details,
                }

            except Exception as e:
                logger.error(
                    f"Unexpected error in {getattr(func, '__name__', str(func))}: {str(e)}",
                    exc_info=True,
                )
                return {
                    "success": False,
                    "error": f"Unexpected error: {str(e)}",
                    "error_category": ErrorCategory.UNKNOWN_ERROR.value,
                    "function": getattr(func, "__name__", str(func)),
                }

        return wrapper

    return decorator


class CircuitBreaker:
    """Circuit breaker pattern for API calls to prevent cascading failures"""

    def __init__(self, failure_threshold: int = 5, timeout_duration: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout_duration = timeout_duration
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def can_execute(self) -> bool:
        """Check if the circuit breaker allows execution"""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout_duration:
                self.state = "HALF_OPEN"
                return True
            return False
        else:  # HALF_OPEN
            return True

    def record_success(self):
        """Record a successful operation"""
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self):
        """Record a failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


# Global circuit breaker for eBird API
ebird_circuit_breaker = CircuitBreaker()


def with_circuit_breaker(
    circuit_breaker: CircuitBreaker = ebird_circuit_breaker,
) -> Callable:
    """Decorator to add circuit breaker pattern to API calls"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not circuit_breaker.can_execute():
                raise APIError(
                    "Service temporarily unavailable due to circuit breaker",
                    status_code=503,
                )

            try:
                result = await func(*args, **kwargs)
                circuit_breaker.record_success()
                return result
            except (APIError, Exception) as e:
                circuit_breaker.record_failure()
                raise e

        return wrapper

    return decorator


# Common validation schemas for different tool categories
SPECIES_VALIDATION_SCHEMAS = {
    "validate_species": {
        "species_names": {"type": list, "required": True, "max_length": 50}
    },
    "get_regional_species_list": {"region": {"type": str, "required": True}},
}

LOCATION_VALIDATION_SCHEMAS = {
    "find_nearest_species": {
        "species_code": {"type": str, "required": True},
        "latitude": {"type": (int, float), "required": True, "range": (-90, 90)},
        "longitude": {"type": (int, float), "required": True, "range": (-180, 180)},
        "days_back": {"type": int, "range": (1, 30)},
        "distance_km": {"type": int, "range": (1, 50)},
    },
    "get_region_details": {"region": {"type": str, "required": True}},
    "get_hotspot_details": {"location_id": {"type": str, "required": True}},
}

PIPELINE_VALIDATION_SCHEMAS = {
    "fetch_sightings": {
        "validated_species": {"type": list, "required": True},
        "region": {"type": str, "required": True},
        "days_back": {"type": int, "range": (1, 30)},
    },
    "filter_constraints": {
        "sightings": {"type": list, "required": True},
        "start_location": {"type": dict, "required": True},
        "max_distance_km": {"type": (int, float), "range": (1, 1000)},
    },
}


def get_validation_schema(tool_name: str) -> Dict:
    """Get validation schema for a specific tool"""
    all_schemas = {
        **SPECIES_VALIDATION_SCHEMAS,
        **LOCATION_VALIDATION_SCHEMAS,
        **PIPELINE_VALIDATION_SCHEMAS,
    }
    return all_schemas.get(tool_name, {})
