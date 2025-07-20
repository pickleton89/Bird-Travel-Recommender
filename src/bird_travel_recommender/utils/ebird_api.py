"""
eBird API client implementation following proven patterns from ebird-mcp-server.

This module provides a unified interface to the eBird API 2.0, combining all specialized
modules into a single client class while maintaining consistent error handling, rate limiting,
and response formatting based on the working JavaScript patterns from moonbirdai/ebird-mcp-server.

This is the main entry point for all eBird API functionality in the Bird Travel Recommender.
"""

import logging
from typing import Optional
from dotenv import load_dotenv

# Import all specialized modules (sync)
from .ebird_base import EBirdBaseClient, EBirdAPIError
from .ebird_observations import EBirdObservationsMixin
from .ebird_locations import EBirdLocationsMixin
from .ebird_taxonomy import EBirdTaxonomyMixin
from .ebird_regions import EBirdRegionsMixin
from .ebird_analysis import EBirdAnalysisMixin
from .ebird_checklists import EBirdChecklistsMixin

# Export the main classes and functions
__all__ = ["EBirdClient", "EBirdAPIError", "get_client"]

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EBirdClient(
    EBirdBaseClient,
    EBirdObservationsMixin,
    EBirdLocationsMixin,
    EBirdTaxonomyMixin,
    EBirdRegionsMixin,
    EBirdAnalysisMixin,
    EBirdChecklistsMixin,
):
    """
    Unified eBird API client with comprehensive functionality.

    This client combines all eBird API capabilities into a single interface,
    providing access to observations, locations, taxonomy, regional data,
    historical analysis, and checklist information.

    Features:
    - Centralized make_request() method for all HTTP interactions
    - Consistent parameter patterns across all endpoints
    - Graceful error handling with formatted messages
    - Rate limiting with exponential backoff
    - Connection reuse for multiple sequential requests
    - Comprehensive coverage of eBird API 2.0 endpoints

    Examples:
        # Initialize client
        client = EBirdClient()

        # Get recent observations
        observations = client.get_recent_observations("US-MA", days_back=7)

        # Get nearby hotspots
        hotspots = client.get_nearby_hotspots(42.3601, -71.0589, distance_km=25)

        # Get species taxonomy
        taxonomy = client.get_taxonomy(species_codes=["norcar", "blujay"])

        # Analyze seasonal trends
        trends = client.get_seasonal_trends("US-CA", species_code="norcar")

        # Clean up when done
        client.close()
    """

    def __init__(self):
        """
        Initialize the unified eBird API client.

        Inherits initialization from EBirdBaseClient which handles:
        - API key validation and loading from environment
        - Session setup with proper headers and authentication
        - Connection pooling for efficient request handling
        """
        super().__init__()
        logger.info("Initialized unified eBird API client with all modules")


# Global client instance for convenience
_client: Optional["EBirdClient"] = None
_async_client: Optional["EBirdClient"] = None


def get_client() -> EBirdClient:
    """Get or create the global eBird client instance."""
    global _client
    if _client is None:
        _client = EBirdClient()
    return _client


async def get_async_client() -> EBirdClient:
    """Get or create the global async eBird client instance."""
    global _async_client
    if _async_client is None:
        _async_client = EBirdClient()
    return _async_client


# Convenience functions that use the global client
# These maintain backward compatibility with existing code


def get_recent_observations(*args, **kwargs):
    """Convenience function for getting recent observations."""
    return get_client().get_recent_observations(*args, **kwargs)


def get_nearby_observations(*args, **kwargs):
    """Convenience function for getting nearby observations."""
    return get_client().get_nearby_observations(*args, **kwargs)


def get_notable_observations(*args, **kwargs):
    """Convenience function for getting notable observations."""
    return get_client().get_notable_observations(*args, **kwargs)


def get_species_observations(*args, **kwargs):
    """Convenience function for getting species observations."""
    return get_client().get_species_observations(*args, **kwargs)


def get_hotspots(*args, **kwargs):
    """Convenience function for getting hotspots."""
    return get_client().get_hotspots(*args, **kwargs)


def get_nearby_hotspots(*args, **kwargs):
    """Convenience function for getting nearby hotspots."""
    return get_client().get_nearby_hotspots(*args, **kwargs)


def get_taxonomy(*args, **kwargs):
    """Convenience function for getting taxonomy."""
    return get_client().get_taxonomy(*args, **kwargs)


def get_nearest_observations(*args, **kwargs):
    """Convenience function for getting nearest observations."""
    return get_client().get_nearest_observations(*args, **kwargs)


def get_species_list(*args, **kwargs):
    """Convenience function for getting species list."""
    return get_client().get_species_list(*args, **kwargs)


def get_region_info(*args, **kwargs):
    """Convenience function for getting region info."""
    return get_client().get_region_info(*args, **kwargs)


def get_hotspot_info(*args, **kwargs):
    """Convenience function for getting hotspot info."""
    return get_client().get_hotspot_info(*args, **kwargs)


def get_nearby_notable_observations(*args, **kwargs):
    """Convenience function for getting nearby notable observations."""
    return get_client().get_nearby_notable_observations(*args, **kwargs)


def get_nearby_species_observations(*args, **kwargs):
    """Convenience function for getting nearby species observations."""
    return get_client().get_nearby_species_observations(*args, **kwargs)


def get_top_locations(*args, **kwargs):
    """Convenience function for getting most active birding locations."""
    return get_client().get_top_locations(*args, **kwargs)


def get_regional_statistics(*args, **kwargs):
    """Convenience function for getting regional birding statistics."""
    return get_client().get_regional_statistics(*args, **kwargs)


def get_location_species_list(*args, **kwargs):
    """Convenience function for getting species list for a location."""
    return get_client().get_location_species_list(*args, **kwargs)


def get_historic_observations(*args, **kwargs):
    """Convenience function for getting historical observations."""
    return get_client().get_historic_observations(*args, **kwargs)


def get_seasonal_trends(*args, **kwargs):
    """Convenience function for getting seasonal birding trends."""
    return get_client().get_seasonal_trends(*args, **kwargs)


def get_yearly_comparisons(*args, **kwargs):
    """Convenience function for getting yearly birding comparisons."""
    return get_client().get_yearly_comparisons(*args, **kwargs)


def get_subregions(*args, **kwargs):
    """Convenience function for getting subregions."""
    return get_client().get_subregions(*args, **kwargs)


def get_adjacent_regions(*args, **kwargs):
    """Convenience function for getting adjacent regions."""
    return get_client().get_adjacent_regions(*args, **kwargs)


def get_elevation_data(*args, **kwargs):
    """Convenience function for getting elevation data."""
    return get_client().get_elevation_data(*args, **kwargs)


def get_migration_data(*args, **kwargs):
    """Convenience function for getting migration data."""
    return get_client().get_migration_data(*args, **kwargs)


def get_peak_times(*args, **kwargs):
    """Convenience function for getting peak times."""
    return get_client().get_peak_times(*args, **kwargs)


def get_seasonal_hotspots(*args, **kwargs):
    """Convenience function for getting seasonal hotspots."""
    return get_client().get_seasonal_hotspots(*args, **kwargs)


def get_recent_checklists(*args, **kwargs):
    """Convenience function for getting recent checklists."""
    return get_client().get_recent_checklists(*args, **kwargs)


def get_checklist_details(*args, **kwargs):
    """Convenience function for getting checklist details."""
    return get_client().get_checklist_details(*args, **kwargs)


def get_user_stats(*args, **kwargs):
    """Convenience function for getting user stats."""
    return get_client().get_user_stats(*args, **kwargs)


# ========================================
# ASYNC CONVENIENCE FUNCTIONS
# ========================================
# These provide async alternatives to the sync convenience functions above
# for better performance with concurrent requests


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


async def async_get_nearest_observations(*args, **kwargs):
    """Async convenience function for getting nearest observations."""
    client = await get_async_client()
    return await client.get_nearest_observations(*args, **kwargs)


async def async_get_species_list(*args, **kwargs):
    """Async convenience function for getting species list."""
    client = await get_async_client()
    return await client.get_species_list(*args, **kwargs)


async def async_get_region_info(*args, **kwargs):
    """Async convenience function for getting region info."""
    client = await get_async_client()
    return await client.get_region_info(*args, **kwargs)


async def async_get_hotspot_info(*args, **kwargs):
    """Async convenience function for getting hotspot info."""
    client = await get_async_client()
    return await client.get_hotspot_info(*args, **kwargs)


# Batch operations for performance
async def async_batch_recent_observations(*args, **kwargs):
    """Async convenience function for batch recent observations."""
    client = await get_async_client()
    return await client.batch_recent_observations(*args, **kwargs)


async def async_batch_nearby_hotspots(*args, **kwargs):
    """Async convenience function for batch nearby hotspots."""
    client = await get_async_client()
    return await client.batch_nearby_hotspots(*args, **kwargs)


async def async_batch_species_validation(*args, **kwargs):
    """Async convenience function for batch species validation."""
    client = await get_async_client()
    return await client.batch_species_validation(*args, **kwargs)


if __name__ == "__main__":
    # Basic test of the refactored API client
    try:
        client = EBirdClient()

        # Test taxonomy lookup
        logger.info("Testing taxonomy lookup...")
        taxonomy = client.get_taxonomy(species_codes=["norcar", "blujay"])
        for species in taxonomy:
            logger.info(f"  {species['comName']} ({species['speciesCode']})")

        # Test recent observations
        logger.info("Testing recent observations in Massachusetts...")
        observations = client.get_recent_observations("US-MA", days_back=3)
        logger.info(f"  Found {len(observations)} recent observations")

        client.close()
        logger.info("eBird API client test completed successfully!")

    except Exception as e:
        logger.error(f"Error testing eBird API: {e}")
