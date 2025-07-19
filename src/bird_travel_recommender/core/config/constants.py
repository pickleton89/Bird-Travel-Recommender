"""
Application-wide constants.

This module centralizes all constants that were previously scattered
across multiple files, eliminating duplication.
"""

from enum import Enum

# HTTP Configuration
HTTP_TIMEOUT_DEFAULT = 30.0
HTTP_MAX_RETRIES = 3
HTTP_INITIAL_DELAY = 1.0

# eBird API Constants
EBIRD_BASE_URL = "https://api.ebird.org/v2"
EBIRD_MAX_RESULTS_DEFAULT = 100
EBIRD_BACK_DAYS_DEFAULT = 14

# Cache Constants
CACHE_TTL_DEFAULT = 3600  # 1 hour
CACHE_TTL_TAXONOMY = 86400  # 24 hours (taxonomy changes infrequently)
CACHE_TTL_OBSERVATIONS = 300  # 5 minutes (observations change frequently)

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_SECOND = 10
RATE_LIMIT_BURST_SIZE = 20

# Validation Constants
MIN_LATITUDE = -90.0
MAX_LATITUDE = 90.0
MIN_LONGITUDE = -180.0
MAX_LONGITUDE = 180.0
MAX_SPECIES_NAME_LENGTH = 100
MAX_LOCATION_NAME_LENGTH = 200


class ExecutionMode(Enum):
    """Execution mode for clients and nodes."""
    SYNC = "sync"
    ASYNC = "async"


class ErrorSeverity(Enum):
    """Error severity levels for structured error handling."""
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryStrategy(Enum):
    """Recovery strategies for error handling."""
    NONE = "none"
    RETRY = "retry"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    CIRCUIT_BREAKER = "circuit_breaker"
    FALLBACK = "fallback"