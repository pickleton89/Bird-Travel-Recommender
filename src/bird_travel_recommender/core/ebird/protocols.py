"""
Type protocols and interfaces for the unified eBird API client.

This module defines the contracts that eliminate the need for
separate sync and async client implementations.
"""

from typing import Protocol, Dict, Any, runtime_checkable
from abc import abstractmethod


@runtime_checkable
class EBirdTransportProtocol(Protocol):
    """
    Protocol defining the transport layer interface.
    
    This allows the unified client to work with both sync and async
    transport implementations without code duplication.
    """
    
    @abstractmethod
    async def request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make an HTTP request to the eBird API.
        
        Args:
            endpoint: API endpoint (e.g., "/ref/taxonomy/ebird")
            params: Query parameters
            
        Returns:
            JSON response data
            
        Raises:
            EBirdAPIError: For API-related errors
        """
        ...
        
    @abstractmethod
    def close(self) -> None:
        """Close the transport and clean up resources."""
        ...


@runtime_checkable
class EBirdClientProtocol(Protocol):
    """
    Protocol defining the eBird client interface.
    
    This ensures consistent interfaces across all client implementations
    while allowing for different execution modes.
    """
    
    @abstractmethod
    async def request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a request through the middleware pipeline.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            Processed response data
        """
        ...
        
    @abstractmethod
    def close(self) -> None:
        """Close the client and clean up resources."""
        ...


@runtime_checkable
class MiddlewareProtocol(Protocol):
    """
    Protocol for middleware components.
    
    Middleware can modify requests before they are sent and
    responses after they are received.
    """
    
    async def before_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process parameters before making the request.
        
        Args:
            endpoint: API endpoint
            params: Original parameters
            
        Returns:
            Modified parameters
        """
        return params
        
    async def after_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process response after receiving it.
        
        Args:
            response: Original response
            
        Returns:
            Modified response
        """
        return response


@runtime_checkable
class CacheProtocol(Protocol):
    """
    Protocol for cache implementations.
    
    Allows different caching strategies (memory, Redis, etc.)
    without changing client code.
    """
    
    async def get(self, key: str) -> Any:
        """Get value from cache."""
        ...
        
    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Set value in cache with TTL."""
        ...
        
    async def delete(self, key: str) -> None:
        """Delete value from cache."""
        ...
        
    async def clear(self) -> None:
        """Clear all cache entries."""
        ...