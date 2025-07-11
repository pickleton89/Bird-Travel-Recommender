"""
Async eBird API client for location and hotspot-related endpoints.

This module provides async methods for retrieving location data from the eBird API,
including hotspots, top birding locations, and seasonal location analysis.
"""

from typing import List, Dict, Any, Optional
import logging
from .ebird_async_base import EBirdAPIError

logger = logging.getLogger(__name__)


class EBirdAsyncLocationsMixin:
    """Async mixin class providing location and hotspot-related eBird API methods."""

    async def get_hotspots(
        self, region_code: str, format: str = "json"
    ) -> List[Dict[str, Any]]:
        """
        Get birding hotspots in a region (async).

        Args:
            region_code: eBird region code
            format: Response format ("json" or "csv")

        Returns:
            List of hotspots with coordinates and metadata
        """
        endpoint = f"/ref/hotspot/{region_code}"
        params = {"fmt": format}

        try:
            result = await self.make_request(endpoint, params)
            logger.info(f"Retrieved {len(result)} hotspots for {region_code}")
            return result
        except EBirdAPIError as e:
            logger.error(f"Failed to get hotspots: {e}")
            raise

    async def get_nearby_hotspots(
        self, lat: float, lng: float, distance_km: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Get birding hotspots near a location (async).

        Args:
            lat: Latitude (-90 to 90)
            lng: Longitude (-180 to 180)
            distance_km: Search radius in kilometers (max: 50)

        Returns:
            List of nearby hotspots with coordinates and metadata
        """
        endpoint = "/ref/hotspot/geo"
        params = {
            "lat": lat,
            "lng": lng,
            "dist": min(distance_km, 50),  # eBird max is 50km
            "fmt": "json",
        }

        try:
            result = await self.make_request(endpoint, params)
            logger.info(
                f"Retrieved {len(result)} hotspots within {distance_km}km of ({lat}, {lng})"
            )
            return result
        except EBirdAPIError as e:
            logger.error(f"Failed to get nearby hotspots: {e}")
            raise

    async def get_hotspot_info(self, location_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific hotspot (async).

        Args:
            location_id: eBird location identifier (e.g., "L99381")

        Returns:
            Hotspot details including coordinates, name, and metadata
        """
        endpoint = f"/ref/hotspot/info/{location_id}"

        try:
            result = await self.make_request(endpoint)
            logger.info(f"Retrieved hotspot info for {location_id}")
            return result
        except EBirdAPIError as e:
            logger.error(f"Failed to get hotspot info for {location_id}: {e}")
            raise

    async def get_top_locations(
        self, region_code: str, days_back: int = 7, max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get the most active birding locations in a region (async).

        Args:
            region_code: eBird region code
            days_back: Days to look back (default: 7, max: 30)
            max_results: Maximum number of locations to return

        Returns:
            List of top locations with activity metrics
        """
        endpoint = f"/product/top100/{region_code}/{days_back}"
        params = {"maxResults": max_results}

        try:
            result = await self.make_request(endpoint, params)
            logger.info(f"Retrieved top {len(result)} locations for {region_code}")
            return result
        except EBirdAPIError as e:
            logger.error(f"Failed to get top locations for {region_code}: {e}")
            raise

    async def get_location_species_list(
        self,
        location_id: str,
        days_back: Optional[int] = None,
        include_provisional: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get the species list for a specific location (async).

        Args:
            location_id: eBird location identifier
            days_back: Days to look back (optional, for recent species only)
            include_provisional: Include unreviewed observations

        Returns:
            List of species observed at the location
        """
        if days_back is not None:
            endpoint = f"/data/obs/{location_id}/recent"
            params = {
                "back": min(days_back, 30),
                "includeProvisional": str(include_provisional).lower(),
            }
        else:
            endpoint = f"/product/spplist/{location_id}"
            params = {"includeProvisional": str(include_provisional).lower()}

        try:
            result = await self.make_request(endpoint, params)
            logger.info(f"Retrieved species list for location {location_id}")
            return result
        except EBirdAPIError as e:
            logger.error(f"Failed to get species list for {location_id}: {e}")
            raise

    async def get_seasonal_hotspots(
        self,
        lat: float,
        lng: float,
        distance_km: int = 25,
        season: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get seasonal hotspot recommendations near a location (async).

        Args:
            lat: Latitude (-90 to 90)
            lng: Longitude (-180 to 180)
            distance_km: Search radius in kilometers (max: 50)
            season: Optional season filter ("spring", "summer", "fall", "winter")

        Returns:
            List of seasonal hotspots with activity patterns
        """
        # This is a synthetic method that combines nearby hotspots with seasonal analysis
        hotspots = await self.get_nearby_hotspots(lat, lng, distance_km)

        # For now, return all hotspots - in a full implementation,
        # this would analyze seasonal bird activity patterns
        logger.info(f"Retrieved {len(hotspots)} seasonal hotspots near ({lat}, {lng})")
        return hotspots
