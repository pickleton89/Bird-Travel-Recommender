"""
Backward compatibility adapters for eBird API clients.

This module provides adapters that wrap the new unified client with the
old interface, enabling gradual migration without breaking existing code.
"""

import asyncio
from typing import Dict, Any, List, Optional
from ..config.logging import get_logger
from ..config.constants import ExecutionMode
from .client import EBirdClient


class EBirdBaseAdapter:
    """
    Adapter that mimics the old EBirdBaseClient interface.
    
    This allows existing code to use the new unified client without
    any changes to the calling code.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with backward-compatible interface."""
        self.logger = get_logger(__name__)
        self._client = EBirdClient.create_sync(api_key=api_key)
        
    def make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a request using the old synchronous interface.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            JSON response data
        """
        # Run the async request in sync mode
        return asyncio.run(self._client.request(endpoint, params))
        
    def close(self) -> None:
        """Clean up resources."""
        self._client.close()


class EBirdAsyncBaseAdapter:
    """
    Adapter that mimics the old EBirdAsyncBaseClient interface.
    
    This allows existing async code to use the new unified client without
    any changes to the calling code.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with backward-compatible async interface."""
        self.logger = get_logger(__name__)
        self._client = EBirdClient.create_async(api_key=api_key)
        
    async def make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make an async request using the old interface.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            JSON response data
        """
        return await self._client.request(endpoint, params)
        
    def close(self) -> None:
        """Clean up resources."""
        self._client.close()
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self.close()


class EBirdTaxonomyAdapter(EBirdBaseAdapter):
    """
    Adapter for the old EBirdTaxonomyMixin interface.
    
    Maps old method signatures to new unified client methods.
    """
    
    def get_taxonomy(self, fmt: str = "json", locale: str = "en", 
                    version: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get eBird taxonomy using old interface."""
        result = asyncio.run(self._client.get_taxonomy(fmt=fmt, locale=locale, version=version))
        # Convert Pydantic models back to dicts for backward compatibility
        return [item.dict() for item in result]
        
    def get_species_list(self, region_code: str, fmt: str = "json") -> List[str]:
        """Get species list using old interface."""
        return asyncio.run(self._client.get_species_list(region_code, fmt=fmt))


class EBirdAsyncTaxonomyAdapter(EBirdAsyncBaseAdapter):
    """
    Adapter for the old async EBirdTaxonomyMixin interface.
    """
    
    async def get_taxonomy(self, fmt: str = "json", locale: str = "en", 
                          version: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get eBird taxonomy using old async interface."""
        result = await self._client.get_taxonomy(fmt=fmt, locale=locale, version=version)
        # Convert Pydantic models back to dicts for backward compatibility
        return [item.dict() for item in result]
        
    async def get_species_list(self, region_code: str, fmt: str = "json") -> List[str]:
        """Get species list using old async interface."""
        return await self._client.get_species_list(region_code, fmt=fmt)


class EBirdObservationsAdapter(EBirdBaseAdapter):
    """
    Adapter for the old EBirdObservationsMixin interface.
    """
    
    def get_recent_observations(self, region_code: str, species_code: Optional[str] = None,
                               back: int = 14, max_results: int = 100, **kwargs) -> List[Dict[str, Any]]:
        """Get recent observations using old interface."""
        result = asyncio.run(self._client.get_recent_observations(
            region_code=region_code,
            species_code=species_code,
            back=back,
            max_results=max_results,
            **kwargs
        ))
        # Convert Pydantic models back to dicts for backward compatibility
        return [item.dict() for item in result]


class EBirdAsyncObservationsAdapter(EBirdAsyncBaseAdapter):
    """
    Adapter for the old async EBirdObservationsMixin interface.
    """
    
    async def get_recent_observations(self, region_code: str, species_code: Optional[str] = None,
                                     back: int = 14, max_results: int = 100, **kwargs) -> List[Dict[str, Any]]:
        """Get recent observations using old async interface."""
        result = await self._client.get_recent_observations(
            region_code=region_code,
            species_code=species_code,
            back=back,
            max_results=max_results,
            **kwargs
        )
        # Convert Pydantic models back to dicts for backward compatibility
        return [item.dict() for item in result]


class EBirdLocationsAdapter(EBirdBaseAdapter):
    """
    Adapter for the old EBirdLocationsMixin interface.
    """
    
    def get_hotspots(self, region_code: str, format: str = "json") -> List[Dict[str, Any]]:
        """Get hotspots using old interface."""
        result = asyncio.run(self._client.get_hotspots(region_code, fmt=format))
        return [item.dict() for item in result]
        
    def get_nearby_hotspots(self, lat: float, lng: float, 
                           distance_km: int = 25) -> List[Dict[str, Any]]:
        """Get nearby hotspots using old interface."""
        result = asyncio.run(self._client.get_nearby_hotspots(lat, lng, distance_km))
        return [item.dict() for item in result]


class EBirdAsyncLocationsAdapter(EBirdAsyncBaseAdapter):
    """
    Adapter for the old async EBirdLocationsMixin interface.
    """
    
    async def get_hotspots(self, region_code: str, format: str = "json") -> List[Dict[str, Any]]:
        """Get hotspots using old async interface."""
        result = await self._client.get_hotspots(region_code, fmt=format)
        return [item.dict() for item in result]
        
    async def get_nearby_hotspots(self, lat: float, lng: float, 
                                 distance_km: int = 25) -> List[Dict[str, Any]]:
        """Get nearby hotspots using old async interface."""
        result = await self._client.get_nearby_hotspots(lat, lng, distance_km)
        return [item.dict() for item in result]


# Convenience factory functions for drop-in replacement
def create_legacy_ebird_client(api_key: Optional[str] = None) -> EBirdBaseAdapter:
    """
    Create a legacy-compatible eBird client.
    
    This is a drop-in replacement for the old EBirdBaseClient.
    """
    return EBirdBaseAdapter(api_key)


def create_legacy_async_ebird_client(api_key: Optional[str] = None) -> EBirdAsyncBaseAdapter:
    """
    Create a legacy-compatible async eBird client.
    
    This is a drop-in replacement for the old EBirdAsyncBaseClient.
    """
    return EBirdAsyncBaseAdapter(api_key)


# Legacy class aliases for minimal code changes
class EBirdAPIClient(EBirdObservationsAdapter, EBirdTaxonomyAdapter, EBirdLocationsAdapter):
    """
    Legacy API client that combines all functionality.
    
    This provides a single class that matches the old client interface
    while using the new unified implementation underneath.
    """
    pass


class EBirdAsyncAPIClient(EBirdAsyncObservationsAdapter, EBirdAsyncTaxonomyAdapter, 
                         EBirdAsyncLocationsAdapter):
    """
    Legacy async API client that combines all functionality.
    
    This provides a single async class that matches the old client interface
    while using the new unified implementation underneath.
    """
    pass