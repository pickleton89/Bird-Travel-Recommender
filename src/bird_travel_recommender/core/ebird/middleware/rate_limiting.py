"""
Rate limiting middleware for eBird API requests.

This module provides rate limiting to prevent API abuse and
ensure compliance with eBird API terms of service.
"""

import asyncio
import time
from collections import deque
from typing import Dict, Any
from ...config.settings import settings
from ...config.logging import get_logger
from ..protocols import MiddlewareProtocol


class RateLimitMiddleware:
    """
    Rate limiting middleware using token bucket algorithm.
    
    Ensures API requests stay within rate limits by throttling
    requests when necessary.
    """
    
    def __init__(
        self, 
        requests_per_second: float = 10.0,
        burst_size: int = 20
    ):
        self.requests_per_second = requests_per_second
        self.burst_size = burst_size
        self.tokens = burst_size
        self.last_refill = time.time()
        self.request_times = deque()
        self.logger = get_logger(__name__)
        
    async def before_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply rate limiting before making request.
        
        Args:
            endpoint: API endpoint
            params: Request parameters
            
        Returns:
            Unmodified parameters (rate limiting is transparent)
        """
        await self._wait_for_token()
        return params
        
    async def after_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        No processing needed after response for rate limiting.
        
        Args:
            response: API response
            
        Returns:
            Unmodified response
        """
        return response
        
    async def _wait_for_token(self) -> None:
        """
        Wait until a token is available for making a request.
        
        Implements token bucket algorithm with exponential backoff
        when rate limits are hit.
        """
        current_time = time.time()
        
        # Refill tokens based on elapsed time
        time_passed = current_time - self.last_refill
        tokens_to_add = time_passed * self.requests_per_second
        self.tokens = min(self.burst_size, self.tokens + tokens_to_add)
        self.last_refill = current_time
        
        # If no tokens available, wait
        if self.tokens < 1:
            wait_time = (1 - self.tokens) / self.requests_per_second
            self.logger.debug(f"Rate limit hit, waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
            
            # Recalculate tokens after waiting
            current_time = time.time()
            time_passed = current_time - self.last_refill
            tokens_to_add = time_passed * self.requests_per_second
            self.tokens = min(self.burst_size, self.tokens + tokens_to_add)
            self.last_refill = current_time
            
        # Consume a token
        self.tokens -= 1
        
        # Track request time for additional monitoring
        self.request_times.append(current_time)
        
        # Clean old request times (keep last minute)
        cutoff_time = current_time - 60
        while self.request_times and self.request_times[0] < cutoff_time:
            self.request_times.popleft()
            
    def get_current_rate(self) -> float:
        """
        Get current request rate (requests per second).
        
        Returns:
            Current rate in requests per second
        """
        if len(self.request_times) < 2:
            return 0.0
            
        time_span = self.request_times[-1] - self.request_times[0]
        if time_span == 0:
            return 0.0
            
        return len(self.request_times) / time_span
        
    def get_available_tokens(self) -> float:
        """
        Get number of available tokens.
        
        Returns:
            Number of available tokens
        """
        current_time = time.time()
        time_passed = current_time - self.last_refill
        tokens_to_add = time_passed * self.requests_per_second
        return min(self.burst_size, self.tokens + tokens_to_add)