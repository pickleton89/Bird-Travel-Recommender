#!/usr/bin/env python3
"""
Rate Limiting Module for Bird Travel Recommender MCP Server

Provides advanced rate limiting capabilities including:
- Per-user rate limits
- Per-endpoint rate limits
- Circuit breaker pattern
- Adaptive rate limiting
- Rate limit monitoring and statistics
"""

import time
import logging
from collections import defaultdict, deque
from typing import Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
from functools import wraps

logger = logging.getLogger(__name__)


class RateLimitType(Enum):
    """Types of rate limits"""

    PER_USER = "per_user"
    PER_ENDPOINT = "per_endpoint"
    GLOBAL = "global"


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""

    max_requests: int
    window_seconds: int
    burst_allowance: int = 0  # Extra requests allowed in short bursts
    adaptive: bool = False  # Whether to adjust limits based on system load


@dataclass
class RateLimitStatus:
    """Current rate limit status"""

    requests_made: int
    max_requests: int
    window_seconds: int
    reset_time: float
    remaining: int
    is_exceeded: bool


class CircuitBreaker:
    """Circuit breaker for handling overloaded endpoints"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half-open

    def can_proceed(self) -> bool:
        """Check if request can proceed through circuit breaker"""
        now = time.time()

        if self.state == "closed":
            return True
        elif self.state == "open":
            if now - (self.last_failure_time or 0) > self.recovery_timeout:
                self.state = "half-open"
                return True
            return False
        elif self.state == "half-open":
            return True

        return False

    def record_success(self):
        """Record successful request"""
        if self.state == "half-open":
            self.state = "closed"
            self.failure_count = 0

    def record_failure(self):
        """Record failed request"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"


class RateLimiter:
    """Advanced rate limiting with multiple strategies"""

    def __init__(self):
        # Request tracking: {user_id: deque of timestamps}
        self.user_requests: Dict[str, deque] = defaultdict(deque)
        self.endpoint_requests: Dict[str, deque] = defaultdict(deque)
        self.global_requests: deque = deque()

        # Circuit breakers: {endpoint: CircuitBreaker}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

        # Rate limit configurations
        self.user_limits: Dict[str, RateLimitConfig] = {}
        self.endpoint_limits: Dict[str, RateLimitConfig] = {}
        self.global_limit: Optional[RateLimitConfig] = None

        # Default configurations
        self._setup_default_limits()

        # Statistics
        self.stats = {
            "total_requests": 0,
            "blocked_requests": 0,
            "circuit_breaker_trips": 0,
        }

    def _setup_default_limits(self):
        """Setup default rate limit configurations"""
        # Default user limits: 100 requests per hour
        self.default_user_limit = RateLimitConfig(
            max_requests=100, window_seconds=3600, burst_allowance=10
        )

        # Per-endpoint limits
        self.endpoint_limits = {
            "get_birding_advice": RateLimitConfig(
                max_requests=20,  # LLM calls are expensive
                window_seconds=3600,
                burst_allowance=2,
            ),
            "validate_species": RateLimitConfig(
                max_requests=50, window_seconds=3600, burst_allowance=5
            ),
            "fetch_sightings": RateLimitConfig(
                max_requests=100, window_seconds=3600, burst_allowance=10
            ),
            "plan_complete_trip": RateLimitConfig(
                max_requests=10,  # Complex orchestration
                window_seconds=3600,
                burst_allowance=1,
            ),
        }

        # Global system limit: 1000 requests per hour
        self.global_limit = RateLimitConfig(
            max_requests=1000, window_seconds=3600, adaptive=True
        )

        # Setup circuit breakers for endpoints
        for endpoint in self.endpoint_limits.keys():
            self.circuit_breakers[endpoint] = CircuitBreaker(
                failure_threshold=5,
                recovery_timeout=300,  # 5 minutes
            )

    def set_user_limit(self, user_id: str, config: RateLimitConfig):
        """Set custom rate limit for specific user"""
        self.user_limits[user_id] = config

    def _cleanup_old_requests(self, request_deque: deque, window_seconds: int) -> int:
        """Remove old requests outside the window and return current count"""
        now = time.time()
        cutoff = now - window_seconds

        while request_deque and request_deque[0] < cutoff:
            request_deque.popleft()

        return len(request_deque)

    def check_rate_limit(self, user_id: str, endpoint: str) -> RateLimitStatus:
        """Check if request is within rate limits"""
        now = time.time()

        # Check circuit breaker first
        circuit_breaker = self.circuit_breakers.get(endpoint)
        if circuit_breaker and not circuit_breaker.can_proceed():
            self.stats["circuit_breaker_trips"] += 1
            return RateLimitStatus(
                requests_made=0,
                max_requests=0,
                window_seconds=0,
                reset_time=now + circuit_breaker.recovery_timeout,
                remaining=0,
                is_exceeded=True,
            )

        # Check global limit
        if self.global_limit:
            global_count = self._cleanup_old_requests(
                self.global_requests, self.global_limit.window_seconds
            )

            if global_count >= self.global_limit.max_requests:
                return RateLimitStatus(
                    requests_made=global_count,
                    max_requests=self.global_limit.max_requests,
                    window_seconds=self.global_limit.window_seconds,
                    reset_time=now + self.global_limit.window_seconds,
                    remaining=0,
                    is_exceeded=True,
                )

        # Check endpoint limit
        endpoint_config = self.endpoint_limits.get(endpoint)
        if endpoint_config:
            endpoint_requests = self.endpoint_requests[endpoint]
            endpoint_count = self._cleanup_old_requests(
                endpoint_requests, endpoint_config.window_seconds
            )

            if endpoint_count >= endpoint_config.max_requests:
                return RateLimitStatus(
                    requests_made=endpoint_count,
                    max_requests=endpoint_config.max_requests,
                    window_seconds=endpoint_config.window_seconds,
                    reset_time=now + endpoint_config.window_seconds,
                    remaining=0,
                    is_exceeded=True,
                )

        # Check user limit
        user_config = self.user_limits.get(user_id, self.default_user_limit)
        user_requests = self.user_requests[user_id]
        user_count = self._cleanup_old_requests(
            user_requests, user_config.window_seconds
        )

        # Apply burst allowance
        effective_limit = user_config.max_requests + user_config.burst_allowance

        if user_count >= effective_limit:
            return RateLimitStatus(
                requests_made=user_count,
                max_requests=effective_limit,
                window_seconds=user_config.window_seconds,
                reset_time=now + user_config.window_seconds,
                remaining=0,
                is_exceeded=True,
            )

        # Request is allowed
        return RateLimitStatus(
            requests_made=user_count,
            max_requests=effective_limit,
            window_seconds=user_config.window_seconds,
            reset_time=now + user_config.window_seconds,
            remaining=effective_limit - user_count,
            is_exceeded=False,
        )

    def record_request(self, user_id: str, endpoint: str, success: bool = True):
        """Record a request for rate limiting purposes"""
        now = time.time()

        # Record in all tracking structures
        self.user_requests[user_id].append(now)
        self.endpoint_requests[endpoint].append(now)
        self.global_requests.append(now)

        # Update circuit breaker
        circuit_breaker = self.circuit_breakers.get(endpoint)
        if circuit_breaker:
            if success:
                circuit_breaker.record_success()
            else:
                circuit_breaker.record_failure()

        # Update statistics
        self.stats["total_requests"] += 1
        if not success:
            self.stats["blocked_requests"] += 1

    def get_user_status(self, user_id: str) -> Dict[str, Any]:
        """Get current rate limit status for a user"""
        user_config = self.user_limits.get(user_id, self.default_user_limit)
        user_requests = self.user_requests[user_id]
        user_count = self._cleanup_old_requests(
            user_requests, user_config.window_seconds
        )

        return {
            "user_id": user_id,
            "requests_made": user_count,
            "max_requests": user_config.max_requests,
            "burst_allowance": user_config.burst_allowance,
            "window_seconds": user_config.window_seconds,
            "remaining": max(
                0, user_config.max_requests + user_config.burst_allowance - user_count
            ),
            "reset_time": time.time() + user_config.window_seconds,
        }

    def get_system_stats(self) -> Dict[str, Any]:
        """Get system-wide rate limiting statistics"""
        now = time.time()

        # Current active users
        active_users = len(
            [
                user_id
                for user_id, requests in self.user_requests.items()
                if requests and requests[-1] > now - 3600  # Active in last hour
            ]
        )

        # Circuit breaker states
        circuit_states = {
            endpoint: breaker.state
            for endpoint, breaker in self.circuit_breakers.items()
        }

        return {
            "total_requests": self.stats["total_requests"],
            "blocked_requests": self.stats["blocked_requests"],
            "circuit_breaker_trips": self.stats["circuit_breaker_trips"],
            "active_users": active_users,
            "circuit_breaker_states": circuit_states,
            "global_requests_last_hour": len(self.global_requests),
        }


def rate_limit(endpoint: str):
    """Decorator to apply rate limiting to MCP handlers"""

    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Get rate limiter from server instance
            if not hasattr(self, "rate_limiter"):
                logger.warning("No rate limiter configured")
                return await func(self, *args, **kwargs)

            # Get user session (should be set by auth decorator)
            session = kwargs.get("session")
            if not session:
                # Fallback to anonymous user
                user_id = "anonymous"
            else:
                user_id = session.user_id

            # Check rate limit
            rate_status = self.rate_limiter.check_rate_limit(user_id, endpoint)

            if rate_status.is_exceeded:
                # Record blocked request
                self.rate_limiter.record_request(user_id, endpoint, success=False)

                return {
                    "success": False,
                    "error": "Rate limit exceeded",
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "rate_limit": {
                        "requests_made": rate_status.requests_made,
                        "max_requests": rate_status.max_requests,
                        "window_seconds": rate_status.window_seconds,
                        "reset_time": rate_status.reset_time,
                        "remaining": rate_status.remaining,
                    },
                }

            # Execute the function
            try:
                result = await func(self, *args, **kwargs)
                success = (
                    result.get("success", True) if isinstance(result, dict) else True
                )

                # Record successful request
                self.rate_limiter.record_request(user_id, endpoint, success=success)

                # Add rate limit headers to response
                if isinstance(result, dict):
                    result["rate_limit"] = {
                        "requests_made": rate_status.requests_made + 1,
                        "max_requests": rate_status.max_requests,
                        "remaining": rate_status.remaining - 1,
                        "reset_time": rate_status.reset_time,
                    }

                return result

            except Exception:
                # Record failed request
                self.rate_limiter.record_request(user_id, endpoint, success=False)
                raise

        return wrapper

    return decorator
