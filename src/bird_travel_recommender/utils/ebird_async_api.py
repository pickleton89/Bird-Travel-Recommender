"""
Async eBird API client implementation following proven patterns from ebird-mcp-server.

This module provides a unified async interface to the eBird API 2.0, combining all specialized
modules into a single async client class while maintaining consistent error handling, rate limiting,
and response formatting based on the working JavaScript patterns from moonbirdai/ebird-mcp-server.

This is the main entry point for all async eBird API functionality in the Bird Travel Recommender.
"""

import os
import logging
import asyncio
from typing import List, Dict, Any, Optional, Union
from dotenv import load_dotenv

# Import all specialized async modules
from .ebird_async_base import EBirdAsyncBaseClient, EBirdAPIError
from .ebird_async_observations import EBirdAsyncObservationsMixin
from .ebird_async_locations import EBirdAsyncLocationsMixin
from .ebird_async_taxonomy import EBirdAsyncTaxonomyMixin
from .ebird_async_regions import EBirdAsyncRegionsMixin
from .ebird_async_analysis import EBirdAsyncAnalysisMixin
from .ebird_async_checklists import EBirdAsyncChecklistsMixin

from ..constants import (
    EBIRD_MAX_RESULTS_DEFAULT,
    EBIRD_MAX_RESULTS_LIMIT, 
    EBIRD_DAYS_BACK_DEFAULT,
    EBIRD_DAYS_BACK_MAX,
    EBIRD_RADIUS_KM_DEFAULT,
    EBIRD_RADIUS_KM_MAX,
    HTTP_TIMEOUT_DEFAULT,
    DEFAULT_ELEVATION_M,
    SIMULATED_SPECIES_MIN,
    SIMULATED_SPECIES_MAX,
    SIMULATED_CHECKLISTS_MIN,
    SIMULATED_CHECKLISTS_MAX,
    LATITUDE_MIN,
    LATITUDE_MAX,
    LONGITUDE_MIN,
    LONGITUDE_MAX
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EBirdAsyncClient(
    EBirdAsyncBaseClient,
    EBirdAsyncObservationsMixin,
    EBirdAsyncLocationsMixin,
    EBirdAsyncTaxonomyMixin,
    EBirdAsyncRegionsMixin,
    EBirdAsyncAnalysisMixin,
    EBirdAsyncChecklistsMixin
):
    """
    Unified async eBird API client with comprehensive functionality.
    
    This client combines all eBird API capabilities into a single async interface,
    providing access to observations, locations, taxonomy, regional data,
    historical analysis, and checklist information with concurrent request support.
    
    Features:
    - Centralized async make_request() method for all HTTP interactions
    - Consistent parameter patterns across all endpoints
    - Graceful error handling with formatted messages
    - Rate limiting with exponential backoff
    - Connection reuse for multiple concurrent requests
    - Context manager support for proper session lifecycle
    - Comprehensive coverage of eBird API 2.0 endpoints
    - Batch operation methods for performance optimization
    
    Examples:
        # Using as async context manager (recommended)
        async with EBirdAsyncClient() as client:
            observations = await client.get_recent_observations("US-MA", days_back=7)
            hotspots = await client.get_nearby_hotspots(42.3601, -71.0589, distance_km=25)
            taxonomy = await client.get_taxonomy(species_codes=["norcar", "blujay"])
        
        # Concurrent requests for better performance
        async with EBirdAsyncClient() as client:
            obs1, obs2, obs3 = await asyncio.gather(
                client.get_recent_observations("US-MA"),
                client.get_recent_observations("US-NY"),
                client.get_recent_observations("US-CT")
            )
        
        # Manual session management
        client = EBirdAsyncClient()
        try:
            observations = await client.get_recent_observations("US-MA")
        finally:
            await client.close()
    """
    
    def __init__(self):
        """
        Initialize the unified async eBird API client.
        
        Inherits initialization from EBirdAsyncBaseClient which handles:
        - API key validation and loading from environment
        - Session setup preparation (created on first request)
        - Connection pooling configuration for efficient concurrent requests
        """
        super().__init__()
        logger.info("Initialized unified async eBird API client with all modules")

    async def batch_recent_observations(
        self,
        region_codes: List[str],
        days_back: int = 7,
        species_code: Optional[str] = None,
        include_provisional: bool = False
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get recent observations for multiple regions concurrently.
        
        This method demonstrates the performance benefits of async by making
        multiple API requests simultaneously instead of sequentially.
        
        Args:
            region_codes: List of eBird region codes
            days_back: Days to look back for all regions
            species_code: Optional species filter for all regions
            include_provisional: Include unreviewed observations
            
        Returns:
            Dictionary mapping region codes to their observation lists
        """
        logger.info(f"Fetching recent observations for {len(region_codes)} regions concurrently")
        
        # Create tasks for concurrent execution
        tasks = []
        for region_code in region_codes:
            task = self.get_recent_observations(
                region_code=region_code,
                days_back=days_back,
                species_code=species_code,
                include_provisional=include_provisional
            )
            tasks.append(task)
        
        # Execute all requests concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle exceptions
        batch_results = {}
        for i, result in enumerate(results):
            region_code = region_codes[i]
            if isinstance(result, Exception):
                logger.error(f"Error fetching observations for {region_code}: {result}")
                batch_results[region_code] = []
            else:
                batch_results[region_code] = result
        
        total_observations = sum(len(obs) for obs in batch_results.values())
        logger.info(f"Batch operation completed: {total_observations} total observations from {len(region_codes)} regions")
        
        return batch_results

    async def batch_nearby_hotspots(
        self,
        coordinates: List[tuple],
        distance_km: int = 25
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get nearby hotspots for multiple coordinates concurrently.
        
        Args:
            coordinates: List of (lat, lng) tuples
            distance_km: Search radius for all locations
            
        Returns:
            Dictionary mapping coordinate strings to hotspot lists
        """
        logger.info(f"Fetching nearby hotspots for {len(coordinates)} locations concurrently")
        
        # Create tasks for concurrent execution
        tasks = []
        for lat, lng in coordinates:
            task = self.get_nearby_hotspots(lat=lat, lng=lng, distance_km=distance_km)
            tasks.append(task)
        
        # Execute all requests concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        batch_results = {}
        for i, result in enumerate(results):
            lat, lng = coordinates[i]
            coord_key = f"{lat},{lng}"
            if isinstance(result, Exception):
                logger.error(f"Error fetching hotspots for {coord_key}: {result}")
                batch_results[coord_key] = []
            else:
                batch_results[coord_key] = result
        
        total_hotspots = sum(len(hotspots) for hotspots in batch_results.values())
        logger.info(f"Batch hotspot operation completed: {total_hotspots} total hotspots from {len(coordinates)} locations")
        
        return batch_results

    async def batch_species_validation(
        self,
        species_codes: List[str],
        batch_size: int = 50
    ) -> Dict[str, Dict[str, Any]]:
        """
        Validate species codes in batches to avoid overwhelming the API.
        
        Args:
            species_codes: List of species codes to validate
            batch_size: Number of species codes per batch request
            
        Returns:
            Dictionary mapping species codes to validation results
        """
        logger.info(f"Validating {len(species_codes)} species codes in batches of {batch_size}")
        
        # Split into batches
        batches = [species_codes[i:i + batch_size] for i in range(0, len(species_codes), batch_size)]
        
        # Create tasks for concurrent batch processing
        tasks = [self.validate_species_codes(batch) for batch in batches]
        
        # Execute all batch requests concurrently
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results from all batches
        all_validated = {}
        for i, result in enumerate(batch_results):
            if isinstance(result, Exception):
                logger.error(f"Error validating batch {i}: {result}")
            else:
                all_validated.update(result)
        
        logger.info(f"Species validation completed: {len(all_validated)} species validated")
        return all_validated


# Global async client instance for convenience (optional)
_async_client = None

async def get_async_client() -> EBirdAsyncClient:
    """Get or create the global async eBird client instance."""
    global _async_client
    if _async_client is None:
        _async_client = EBirdAsyncClient()
    return _async_client


# Async convenience functions that use the global client
# These provide async alternatives to the sync convenience functions

async def async_get_recent_observations(*args, **kwargs):
    """Async convenience function for getting recent observations."""
    client = await get_async_client()
    return await client.get_recent_observations(*args, **kwargs)

async def async_get_nearby_observations(*args, **kwargs):
    """Async convenience function for getting nearby observations."""
    client = await get_async_client()
    return await client.get_nearby_observations(*args, **kwargs)

async def async_get_notable_observations(*args, **kwargs):
    """Async convenience function for getting notable observations."""
    client = await get_async_client()
    return await client.get_notable_observations(*args, **kwargs)

async def async_get_species_observations(*args, **kwargs):
    """Async convenience function for getting species observations."""
    client = await get_async_client()
    return await client.get_species_observations(*args, **kwargs)

async def async_get_hotspots(*args, **kwargs):
    """Async convenience function for getting hotspots."""
    client = await get_async_client()
    return await client.get_hotspots(*args, **kwargs)

async def async_get_nearby_hotspots(*args, **kwargs):
    """Async convenience function for getting nearby hotspots."""
    client = await get_async_client()
    return await client.get_nearby_hotspots(*args, **kwargs)

async def async_get_taxonomy(*args, **kwargs):
    """Async convenience function for getting taxonomy."""
    client = await get_async_client()
    return await client.get_taxonomy(*args, **kwargs)

async def async_batch_recent_observations(*args, **kwargs):
    """Async convenience function for batch recent observations."""
    client = await get_async_client()
    return await client.batch_recent_observations(*args, **kwargs)

async def async_batch_nearby_hotspots(*args, **kwargs):
    """Async convenience function for batch nearby hotspots."""
    client = await get_async_client()
    return await client.batch_nearby_hotspots(*args, **kwargs)


if __name__ == "__main__":
    # Basic test of the async API client
    async def test_async_client():
        try:
            async with EBirdAsyncClient() as client:
                # Test taxonomy lookup
                logger.info("Testing async taxonomy lookup...")
                taxonomy = await client.get_taxonomy(species_codes=["norcar", "blujay"])
                for species in taxonomy:
                    logger.info(f"  {species['comName']} ({species['speciesCode']})")
                
                # Test concurrent recent observations
                logger.info("Testing concurrent recent observations...")
                region_codes = ["US-MA", "US-NY", "US-CT"]
                batch_results = await client.batch_recent_observations(region_codes, days_back=3)
                
                for region, observations in batch_results.items():
                    logger.info(f"  {region}: {len(observations)} recent observations")
                
                logger.info("Async eBird API client test completed successfully!")
                
        except Exception as e:
            logger.error(f"Error testing async eBird API: {e}")

    # Run the async test
    asyncio.run(test_async_client())