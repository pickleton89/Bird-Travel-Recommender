#!/usr/bin/env python3
"""
Input Validation Framework for Bird Travel Recommender MCP Server

Provides comprehensive input validation, sanitization, and security controls
to prevent injection attacks, DoS attacks, and data corruption.
"""

import re
import logging
from datetime import datetime
from functools import wraps
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Security Constants
MAX_SPECIES_LIST_SIZE = 100
MAX_RESULTS_LIMIT = 1000
MAX_STRING_LENGTH = 500
MAX_DAYS_BACK = 30
MAX_DISTANCE_KM = 50
MIN_DISTANCE_KM = 1

# Regex patterns for validation
REGION_CODE_PATTERN = re.compile(r"^[A-Z]{2}(-[A-Z0-9]{1,3})?$")
SPECIES_CODE_PATTERN = re.compile(r"^[a-z]{3,6}\d{0,2}$")
LOCATION_ID_PATTERN = re.compile(r"^L\d+$")
SAFE_STRING_PATTERN = re.compile(r"^[a-zA-Z0-9\s\-_.,()]+$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Control characters to remove
CONTROL_CHARS = "".join(chr(i) for i in range(32) if i not in [9, 10, 13])
CONTROL_CHAR_PATTERN = re.compile(f"[{re.escape(CONTROL_CHARS)}]")


@dataclass
class ValidationError(Exception):
    """Custom exception for validation errors"""

    field: str
    value: Any
    message: str
    error_code: str = "VALIDATION_ERROR"


class InputValidator:
    """Comprehensive input validation and sanitization"""

    @staticmethod
    def validate_coordinates(lat: float, lng: float) -> None:
        """Validate geographic coordinates"""
        if not isinstance(lat, (int, float)):
            raise ValidationError(
                "lat", lat, "Latitude must be a number", "INVALID_TYPE"
            )
        if not isinstance(lng, (int, float)):
            raise ValidationError(
                "lng", lng, "Longitude must be a number", "INVALID_TYPE"
            )

        if not -90 <= lat <= 90:
            raise ValidationError(
                "lat",
                lat,
                f"Latitude must be between -90 and 90, got {lat}",
                "OUT_OF_RANGE",
            )
        if not -180 <= lng <= 180:
            raise ValidationError(
                "lng",
                lng,
                f"Longitude must be between -180 and 180, got {lng}",
                "OUT_OF_RANGE",
            )

    @staticmethod
    def validate_region_code(code: str) -> str:
        """Validate and sanitize region code"""
        if not isinstance(code, str):
            raise ValidationError(
                "region_code", code, "Region code must be a string", "INVALID_TYPE"
            )

        original_code = code
        code = code.strip().upper()

        # Check if the original was lowercase (which might be suspicious)
        if original_code != original_code.upper() and len(original_code) > 0:
            # Allow case conversion but log it
            pass

        if not REGION_CODE_PATTERN.match(code):
            raise ValidationError(
                "region_code",
                code,
                f"Invalid region code format. Expected format: 'US' or 'US-CA', got '{code}'",
                "INVALID_FORMAT",
            )
        return code

    @staticmethod
    def validate_species_code(code: str) -> str:
        """Validate and sanitize species code"""
        if not isinstance(code, str):
            raise ValidationError(
                "species_code", code, "Species code must be a string", "INVALID_TYPE"
            )

        code = code.strip().lower()
        if not SPECIES_CODE_PATTERN.match(code):
            raise ValidationError(
                "species_code",
                code,
                f"Invalid species code format. Expected format: 'norcar', 'amecro1', got '{code}'",
                "INVALID_FORMAT",
            )
        return code

    @staticmethod
    def validate_location_id(location_id: str) -> str:
        """Validate and sanitize location ID"""
        if not isinstance(location_id, str):
            raise ValidationError(
                "location_id",
                location_id,
                "Location ID must be a string",
                "INVALID_TYPE",
            )

        location_id = location_id.strip()
        if not LOCATION_ID_PATTERN.match(location_id):
            raise ValidationError(
                "location_id",
                location_id,
                f"Invalid location ID format. Expected format: 'L123456', got '{location_id}'",
                "INVALID_FORMAT",
            )
        return location_id

    @staticmethod
    def validate_string_length(
        value: str, field_name: str, max_length: int = MAX_STRING_LENGTH
    ) -> str:
        """Validate string length and sanitize"""
        if not isinstance(value, str):
            raise ValidationError(
                field_name, value, f"{field_name} must be a string", "INVALID_TYPE"
            )

        if len(value) > max_length:
            raise ValidationError(
                field_name,
                value,
                f"{field_name} exceeds maximum length of {max_length} characters",
                "TOO_LONG",
            )

        return value.strip()

    @staticmethod
    def validate_array_size(
        arr: List[Any], field_name: str, max_size: int
    ) -> List[Any]:
        """Validate array size to prevent DoS attacks"""
        if not isinstance(arr, list):
            raise ValidationError(
                field_name, arr, f"{field_name} must be a list", "INVALID_TYPE"
            )

        if len(arr) > max_size:
            raise ValidationError(
                field_name,
                arr,
                f"{field_name} exceeds maximum size of {max_size} items",
                "TOO_MANY_ITEMS",
            )

        if len(arr) == 0:
            raise ValidationError(
                field_name, arr, f"{field_name} cannot be empty", "EMPTY_LIST"
            )

        return arr

    @staticmethod
    def validate_numeric_range(
        value: Union[int, float],
        field_name: str,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
    ) -> Union[int, float]:
        """Validate numeric values within specified range"""
        if not isinstance(value, (int, float)):
            raise ValidationError(
                field_name, value, f"{field_name} must be a number", "INVALID_TYPE"
            )

        if min_val is not None and value < min_val:
            raise ValidationError(
                field_name,
                value,
                f"{field_name} must be >= {min_val}, got {value}",
                "TOO_SMALL",
            )

        if max_val is not None and value > max_val:
            raise ValidationError(
                field_name,
                value,
                f"{field_name} must be <= {max_val}, got {value}",
                "TOO_LARGE",
            )

        return value

    @staticmethod
    def validate_date_string(date_str: str, field_name: str) -> str:
        """Validate date string format and ensure it's not in the future"""
        if not isinstance(date_str, str):
            raise ValidationError(
                field_name, date_str, f"{field_name} must be a string", "INVALID_TYPE"
            )

        if not DATE_PATTERN.match(date_str):
            raise ValidationError(
                field_name,
                date_str,
                f"Invalid date format. Expected YYYY-MM-DD, got '{date_str}'",
                "INVALID_FORMAT",
            )

        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            if date_obj > datetime.now():
                raise ValidationError(
                    field_name, date_str, "Date cannot be in the future", "FUTURE_DATE"
                )
        except ValueError:
            raise ValidationError(
                field_name,
                date_str,
                f"Invalid date value: '{date_str}'",
                "INVALID_DATE",
            )

        return date_str

    @staticmethod
    def sanitize_string(value: str) -> str:
        """Sanitize string by removing control characters and dangerous patterns"""
        if not isinstance(value, str):
            return str(value)

        # Remove control characters
        value = CONTROL_CHAR_PATTERN.sub("", value)

        # Remove potential prompt injection patterns
        dangerous_patterns = [
            r"ignore\s+previous\s+instructions",
            r"system\s*:",
            r"assistant\s*:",
            r"user\s*:",
            r"<\s*script\s*>",
            r"javascript\s*:",
            r"data\s*:",
            r"vbscript\s*:",
        ]

        for pattern in dangerous_patterns:
            value = re.sub(pattern, "", value, flags=re.IGNORECASE)

        return value.strip()

    @staticmethod
    def sanitize_for_llm(text: str) -> str:
        """Sanitize text specifically for LLM prompts to prevent injection"""
        if not isinstance(text, str):
            text = str(text)

        # First apply general sanitization
        text = InputValidator.sanitize_string(text)

        # Remove or escape characters that could be used for prompt injection
        text = text.replace('"', '\\"')  # Escape quotes
        text = text.replace("'", "\\'")  # Escape single quotes
        text = re.sub(r"\n+", " ", text)  # Replace newlines with spaces
        text = re.sub(r"\s+", " ", text)  # Normalize whitespace

        # Limit length for LLM context
        if len(text) > 1000:
            text = text[:997] + "..."

        return text


def validate_inputs(schema: Dict[str, Any]):
    """Decorator for comprehensive input validation"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Validate each parameter according to schema
                for param_name, validation_rules in schema.items():
                    if param_name in kwargs:
                        value = kwargs[param_name]

                        # Apply validation rules
                        if "type" in validation_rules:
                            expected_type = validation_rules["type"]
                            if not isinstance(value, expected_type):
                                raise ValidationError(
                                    param_name,
                                    value,
                                    f"Expected {expected_type.__name__}, got {type(value).__name__}",
                                    "INVALID_TYPE",
                                )

                        if "validator" in validation_rules:
                            validator_func = validation_rules["validator"]
                            kwargs[param_name] = validator_func(value)

                        if "sanitizer" in validation_rules:
                            sanitizer_func = validation_rules["sanitizer"]
                            kwargs[param_name] = sanitizer_func(value)

                # Call the original function
                return await func(*args, **kwargs)

            except ValidationError as e:
                logger.warning(
                    f"Validation error in {getattr(func, '__name__', str(func))}: {e.message}"
                )
                return {
                    "success": False,
                    "error": e.message,
                    "error_code": e.error_code,
                    "field": e.field,
                    "value": str(e.value),
                }
            except Exception as e:
                logger.error(
                    f"Unexpected error in {getattr(func, '__name__', str(func))}: {str(e)}"
                )
                return {
                    "success": False,
                    "error": "Internal validation error",
                    "error_code": "INTERNAL_ERROR",
                }

        return wrapper

    return decorator


# Predefined validation schemas for common use cases
COORDINATE_SCHEMA = {
    "lat": {
        "type": float,
        "validator": lambda x: InputValidator.validate_numeric_range(x, "lat", -90, 90),
    },
    "lng": {
        "type": float,
        "validator": lambda x: InputValidator.validate_numeric_range(
            x, "lng", -180, 180
        ),
    },
}

REGION_SCHEMA = {
    "region_code": {
        "type": str,
        "validator": InputValidator.validate_region_code,
        "sanitizer": InputValidator.sanitize_string,
    }
}

SPECIES_LIST_SCHEMA = {
    "species_names": {
        "type": list,
        "validator": lambda x: InputValidator.validate_array_size(
            x, "species_names", MAX_SPECIES_LIST_SIZE
        ),
    }
}

DISTANCE_SCHEMA = {
    "distance_km": {
        "type": (int, float),
        "validator": lambda x: InputValidator.validate_numeric_range(
            x, "distance_km", MIN_DISTANCE_KM, MAX_DISTANCE_KM
        ),
    }
}

DAYS_BACK_SCHEMA = {
    "days_back": {
        "type": int,
        "validator": lambda x: InputValidator.validate_numeric_range(
            x, "days_back", 1, MAX_DAYS_BACK
        ),
    }
}
