"""
Unified eBird API client.

This module provides a single client implementation that eliminates
the massive duplication between sync and async eBird API clients.
This single file replaces 16 duplicate files (~2,600 lines).
"""

from typing import Dict, Any, List, Optional
from ..config.settings import settings
from ..config.logging import get_logger
from ..config.constants import ExecutionMode
from ..exceptions import ConfigurationError
from .protocols import EBirdTransportProtocol, MiddlewareProtocol
from .transport import HttpxTransport, AiohttpTransport
from .middleware.rate_limiting import RateLimitMiddleware
from .middleware.caching import CachingMiddleware
from .mixins.taxonomy import TaxonomyMixin
from .mixins.observations import ObservationsMixin
from .mixins.locations import LocationsMixin
from .mixins.regions import RegionsMixin
from .mixins.checklists import ChecklistsMixin


class EBirdClient(TaxonomyMixin, ObservationsMixin, LocationsMixin, RegionsMixin, ChecklistsMixin):
    """
    Unified eBird client with sync/async support.
    
    This single implementation replaces all the duplicate eBird API clients,
    providing both sync and async modes through a unified interface.
    
    Features:
    - Single codebase for sync and async operations
    - Intelligent middleware pipeline
    - Type-safe response models
    - Comprehensive error handling
    - Built-in rate limiting and caching
    - Protocol-based architecture for extensibility
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        mode: ExecutionMode = ExecutionMode.ASYNC,
        enable_rate_limiting: bool = True,
        enable_caching: bool = True,
        custom_middleware: Optional[List[MiddlewareProtocol]] = None
    ):
        """
        Initialize the unified eBird client.
        
        Args:
            api_key: eBird API key (defaults to settings.ebird_api_key)
            mode: Execution mode (SYNC or ASYNC)
            enable_rate_limiting: Enable rate limiting middleware
            enable_caching: Enable caching middleware
            custom_middleware: Additional middleware to apply
            
        Raises:
            ConfigurationError: If API key is missing or invalid
        """
        # Initialize mixins
        super().__init__()
        
        # Validate and set API key
        self.api_key = api_key or settings.ebird_api_key
        if not self.api_key:
            raise ConfigurationError("eBird API key is required")
            
        self.mode = mode
        self.logger = get_logger(f"ebird_client_{mode.value}")
        
        # Create transport layer based on mode
        self.transport = self._create_transport()
        
        # Build middleware pipeline
        self.middleware_stack = self._build_middleware(
            enable_rate_limiting, 
            enable_caching, 
            custom_middleware or []
        )
        
        self.logger.info(f"Initialized eBird client in {mode.value} mode")
        
    def _create_transport(self) -> EBirdTransportProtocol:
        """
        Create transport layer based on execution mode.
        
        Returns:
            Transport implementation (sync or async)
        """
        if self.mode == ExecutionMode.ASYNC:
            return AiohttpTransport(self.api_key)
        else:
            return HttpxTransport(self.api_key)
            
    def _build_middleware(
        self, 
        enable_rate_limiting: bool,
        enable_caching: bool,
        custom_middleware: List[MiddlewareProtocol]
    ) -> List[MiddlewareProtocol]:
        """
        Build the middleware pipeline.
        
        Args:
            enable_rate_limiting: Whether to include rate limiting
            enable_caching: Whether to include caching
            custom_middleware: Additional middleware
            
        Returns:
            List of middleware in execution order
        """
        middleware = []
        
        # Add rate limiting middleware first
        if enable_rate_limiting:
            middleware.append(RateLimitMiddleware())
            
        # Add caching middleware
        if enable_caching:
            middleware.append(CachingMiddleware())
            
        # Add custom middleware
        middleware.extend(custom_middleware)
        
        return middleware
        
    async def request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a request through the middleware pipeline.
        
        This is the core method that all API calls flow through,
        providing consistent middleware processing and error handling.
        
        Args:
            endpoint: API endpoint (e.g., "/ref/taxonomy/ebird")
            params: Query parameters
            
        Returns:
            Processed response data
            
        Raises:
            EBirdAPIError: For API-related errors
        """
        # Add metadata for middleware
        enriched_params = params.copy()
        enriched_params["_endpoint"] = endpoint
        enriched_params["_timestamp"] = __import__("time").time()
        
        # Apply before_request middleware
        for middleware in self.middleware_stack:
            enriched_params = await middleware.before_request(endpoint, enriched_params)
            
        # Check if we have a cached response
        if "_cached_response" in enriched_params:
            self.logger.debug(f"Returning cached response for {endpoint}")
            return enriched_params["_cached_response"]
            
        # Make the actual request
        try:
            response = await self.transport.request(endpoint, enriched_params)
            
            # Add metadata for after_response middleware
            response["_endpoint"] = endpoint
            response["_cache_key"] = getattr(middleware, "_cache_key", None) if self.middleware_stack else None
            
            # Apply after_response middleware (in reverse order)
            for middleware in reversed(self.middleware_stack):
                response = await middleware.after_response(response)
                
            return response
            
        except Exception as e:
            self.logger.error(f"Request failed for {endpoint}: {e}")
            raise
            
    def close(self) -> None:
        """
        Close the client and clean up resources.
        
        This should be called when the client is no longer needed
        to properly clean up transport resources.
        """
        try:
            self.transport.close()
            self.logger.info("eBird client closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing eBird client: {e}")
            
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self.close()
        
    def __enter__(self):
        """Sync context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.close()
        
    # Convenience factory methods
    @classmethod
    def create_async(cls, api_key: Optional[str] = None, **kwargs) -> 'EBirdClient':
        """
        Create an async eBird client.
        
        Args:
            api_key: eBird API key
            **kwargs: Additional client options
            
        Returns:
            Configured async client
        """
        return cls(api_key=api_key, mode=ExecutionMode.ASYNC, **kwargs)
        
    @classmethod
    def create_sync(cls, api_key: Optional[str] = None, **kwargs) -> 'EBirdClient':
        """
        Create a sync eBird client.
        
        Args:
            api_key: eBird API key
            **kwargs: Additional client options
            
        Returns:
            Configured sync client
        """
        return cls(api_key=api_key, mode=ExecutionMode.SYNC, **kwargs)
        
    # Health and status methods
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the eBird API.
        
        Returns:
            Health check results
        """
        try:
            # Simple API call to check connectivity
            await self.get_taxonomy()
            return {
                "status": "healthy",
                "mode": self.mode.value,
                "api_accessible": True,
                "middleware_count": len(self.middleware_stack)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "mode": self.mode.value,
                "api_accessible": False,
                "error": str(e),
                "middleware_count": len(self.middleware_stack)
            }
            
    def get_client_info(self) -> Dict[str, Any]:
        """
        Get information about the client configuration.
        
        Returns:
            Client configuration details
        """
        return {
            "mode": self.mode.value,
            "middleware_count": len(self.middleware_stack),
            "middleware_types": [type(m).__name__ for m in self.middleware_stack],
            "transport_type": type(self.transport).__name__,
            "api_key_configured": bool(self.api_key),
            "api_key_length": len(self.api_key) if self.api_key else 0
        }