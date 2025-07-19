"""
Caching middleware for eBird API requests.

This module provides intelligent caching to reduce API calls
and improve response times for frequently requested data.
"""

import hashlib
import json
from typing import Dict, Any, Optional
from ...config.settings import settings
from ...config.logging import get_logger
from ..protocols import MiddlewareProtocol, CacheProtocol


class MemoryCache:
    """
    Simple in-memory cache implementation.
    
    Provides basic caching functionality for development
    and testing environments.
    """
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.logger = get_logger(__name__)
        
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        import time
        
        if key not in self._cache:
            return None
            
        entry = self._cache[key]
        
        # Check TTL
        if time.time() > entry["expires_at"]:
            del self._cache[key]
            return None
            
        return entry["value"]
        
    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Set value in cache with TTL."""
        import time
        
        self._cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl
        }
        
    async def delete(self, key: str) -> None:
        """Delete value from cache."""
        self._cache.pop(key, None)
        
    async def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()


class CachingMiddleware:
    """
    Caching middleware for eBird API requests.
    
    Automatically caches responses based on endpoint and parameters
    with intelligent TTL selection.
    """
    
    def __init__(self, cache: Optional[CacheProtocol] = None):
        self.cache = cache or MemoryCache()
        self.logger = get_logger(__name__)
        
        # TTL settings for different endpoints
        self.ttl_settings = {
            "/ref/taxonomy": 86400,  # 24 hours - taxonomy is stable
            "/product/spplist": 21600,  # 6 hours - species lists change slowly  
            "/data/obs": 300,  # 5 minutes - observations change frequently
            "/data/recent": 300,  # 5 minutes - recent data changes frequently
            "/ref/hotspot": 3600,  # 1 hour - hotspot info changes moderately
            "/ref/region": 86400,  # 24 hours - region info is stable
        }
        
    async def before_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check cache before making request.
        
        If cached data exists and is valid, the request will be skipped
        and cached data returned instead.
        
        Args:
            endpoint: API endpoint
            params: Request parameters
            
        Returns:
            Original parameters (caching is transparent to the client)
        """
        if not settings.cache_enabled:
            return params
            
        cache_key = self._generate_cache_key(endpoint, params)
        cached_response = await self.cache.get(cache_key)
        
        if cached_response is not None:
            self.logger.debug(f"Cache hit for {endpoint}")
            # Store cached response for after_response to return
            params["_cached_response"] = cached_response
        else:
            self.logger.debug(f"Cache miss for {endpoint}")
            
        return params
        
    async def after_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cache response after receiving it.
        
        Args:
            response: API response
            
        Returns:
            Response (possibly from cache)
        """
        # Check if we have a cached response to return instead
        if "_cached_response" in response:
            return response["_cached_response"]
            
        # Cache the new response
        if settings.cache_enabled and "_cache_key" in response:
            cache_key = response["_cache_key"]
            endpoint = response.get("_endpoint", "")
            ttl = self._get_ttl_for_endpoint(endpoint)
            
            # Remove metadata before caching
            clean_response = {k: v for k, v in response.items() 
                            if not k.startswith("_")}
            
            await self.cache.set(cache_key, clean_response, ttl)
            self.logger.debug(f"Cached response for {endpoint} with TTL {ttl}s")
            
            return clean_response
            
        return response
        
    def _generate_cache_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """
        Generate a unique cache key for the request.
        
        Args:
            endpoint: API endpoint
            params: Request parameters
            
        Returns:
            Unique cache key
        """
        # Create a normalized representation
        cache_data = {
            "endpoint": endpoint,
            "params": {k: v for k, v in sorted(params.items()) 
                     if not k.startswith("_")}
        }
        
        # Generate hash
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()
        
    def _get_ttl_for_endpoint(self, endpoint: str) -> int:
        """
        Get appropriate TTL for an endpoint.
        
        Args:
            endpoint: API endpoint
            
        Returns:
            TTL in seconds
        """
        # Find matching TTL setting
        for pattern, ttl in self.ttl_settings.items():
            if pattern in endpoint:
                return ttl
                
        # Default TTL
        return settings.cache_ttl
        
    async def invalidate_cache(self, pattern: Optional[str] = None) -> None:
        """
        Invalidate cache entries.
        
        Args:
            pattern: Optional pattern to match keys (None = clear all)
        """
        if pattern is None:
            await self.cache.clear()
            self.logger.info("Cleared entire cache")
        else:
            # For simple cache implementations, just clear all
            # More sophisticated implementations could pattern match
            await self.cache.clear()
            self.logger.info(f"Invalidated cache for pattern: {pattern}")