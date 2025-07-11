"""
eBird API client for observation-related endpoints.

This module provides methods for retrieving bird observation data from the eBird API,
including recent observations, nearby sightings, notable birds, and species-specific queries.
"""

from typing import List, Dict, Any, Optional
import logging
from .ebird_base import EBirdBaseClient, EBirdAPIError

logger = logging.getLogger(__name__)


class EBirdObservationsMixin:
    """Mixin class providing observation-related eBird API methods."""

    def get_recent_observations(
        self,
        region_code: str,
        days_back: int = 7,
        species_code: Optional[str] = None,
        include_provisional: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get recent bird observations in a region.

        Args:
            region_code: eBird region code (e.g., "US-MA", "CA-ON")
            days_back: Days to look back (default: 7, max: 30)
            species_code: Optional specific species filter
            include_provisional: Include unreviewed observations

        Returns:
            List of recent observations with species, location, date, count
        """
        endpoint = f"/data/obs/{region_code}/recent"
        if species_code:
            endpoint += f"/{species_code}"

        params = {
            "back": min(days_back, 30),  # eBird max is 30 days
            "includeProvisional": str(include_provisional).lower(),
        }

        try:
            result = self.make_request(endpoint, params)
            logger.info(
                f"Retrieved {len(result)} recent observations for {region_code}"
            )
            return result
        except EBirdAPIError as e:
            logger.error(f"Failed to get recent observations: {e}")
            raise

    def get_nearby_observations(
        self,
        lat: float,
        lng: float,
        distance_km: int = 25,
        days_back: int = 7,
        species_code: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get recent observations near specific coordinates.

        Args:
            lat: Latitude coordinate
            lng: Longitude coordinate
            distance_km: Search radius in kilometers (max: 50)
            days_back: Days to look back (default: 7, max: 30)
            species_code: Optional specific species filter

        Returns:
            List of nearby observations with distance calculations
        """
        endpoint = "/data/obs/geo/recent"
        if species_code:
            endpoint += f"/{species_code}"

        params = {
            "lat": lat,
            "lng": lng,
            "dist": min(distance_km, 50),  # eBird max is 50km
            "back": min(days_back, 30),
        }

        try:
            result = self.make_request(endpoint, params)
            logger.info(f"Retrieved {len(result)} nearby observations at {lat},{lng}")
            return result
        except EBirdAPIError as e:
            logger.error(f"Failed to get nearby observations: {e}")
            raise

    def get_notable_observations(
        self, region_code: str, days_back: int = 7, detail: str = "simple"
    ) -> List[Dict[str, Any]]:
        """
        Get notable/rare bird observations in a region.

        Args:
            region_code: eBird region code
            days_back: Days to look back (default: 7, max: 30)
            detail: Response detail level ("simple" or "full")

        Returns:
            List of notable sightings with rarity indicators
        """
        endpoint = f"/data/obs/{region_code}/recent/notable"
        params = {"back": min(days_back, 30), "detail": detail}

        try:
            result = self.make_request(endpoint, params)
            logger.info(
                f"Retrieved {len(result)} notable observations for {region_code}"
            )
            return result
        except EBirdAPIError as e:
            logger.error(f"Failed to get notable observations: {e}")
            raise

    def get_species_observations(
        self,
        species_code: str,
        region_code: str,
        days_back: int = 7,
        hotspot_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get recent observations for a specific species.

        Args:
            species_code: eBird species code (e.g., "norcar")
            region_code: eBird region code
            days_back: Days to look back (default: 7, max: 30)
            hotspot_only: Restrict to eBird hotspots only

        Returns:
            List of species-specific observations with location details
        """
        endpoint = f"/data/obs/{region_code}/recent/{species_code}"
        params = {"back": min(days_back, 30), "hotspot": str(hotspot_only).lower()}

        try:
            result = self.make_request(endpoint, params)
            logger.info(
                f"Retrieved {len(result)} observations for species {species_code}"
            )
            return result
        except EBirdAPIError as e:
            logger.error(f"Failed to get species observations: {e}")
            raise

    def get_nearest_observations(
        self,
        species_code: str,
        lat: float,
        lng: float,
        days_back: int = 14,
        distance_km: int = 50,
        hotspot_only: bool = False,
        include_provisional: bool = False,
        max_results: int = 3000,
        locale: str = "en",
    ) -> List[Dict[str, Any]]:
        """
        Find nearest locations where a specific species was recently observed.

        Args:
            species_code: eBird species code (e.g., "norcar")
            lat: Latitude coordinate
            lng: Longitude coordinate
            days_back: Days to look back (default: 14, max: 30)
            distance_km: Maximum search distance (default: 50, max: 50)
            hotspot_only: Restrict to hotspot sightings only
            include_provisional: Include unconfirmed observations
            max_results: Maximum observations to return (default: 3000, max: 3000)
            locale: Language locale for species names

        Returns:
            List of nearest observations sorted by distance (closest first)

        Raises:
            EBirdAPIError: For API errors with descriptive messages
        """
        endpoint = f"/data/nearest/geo/recent/{species_code}"
        params = {
            "lat": lat,
            "lng": lng,
            "back": min(days_back, 30),  # eBird max is 30 days
            "dist": min(distance_km, 50),  # eBird max is 50km
            "hotspot": str(hotspot_only).lower(),
            "includeProvisional": str(include_provisional).lower(),
            "maxResults": min(max_results, 3000),  # eBird max is 3000
            "locale": locale,
        }

        try:
            result = self.make_request(endpoint, params)
            logger.info(
                f"Retrieved {len(result)} nearest observations for species {species_code} at {lat},{lng}"
            )
            return result
        except EBirdAPIError as e:
            logger.error(f"Failed to get nearest observations: {e}")
            raise

    def get_nearby_notable_observations(
        self,
        lat: float,
        lng: float,
        distance_km: int = 25,
        days_back: int = 7,
        detail: str = "simple",
        hotspot_only: bool = False,
        include_provisional: bool = False,
        max_results: int = 200,
        locale: str = "en",
    ) -> List[Dict[str, Any]]:
        """
        Get notable/rare bird observations near specific coordinates.

        Args:
            lat: Latitude coordinate
            lng: Longitude coordinate
            distance_km: Search radius in kilometers (default: 25, max: 50)
            days_back: Days to look back (default: 7, max: 30)
            detail: Response detail level ("simple" or "full")
            hotspot_only: Restrict to hotspot sightings only
            include_provisional: Include unconfirmed observations
            max_results: Maximum observations to return (default: 200, max: 10000)
            locale: Language locale for species names

        Returns:
            List of notable/rare observations near coordinates with rarity indicators

        Raises:
            EBirdAPIError: For API errors with descriptive messages
        """
        endpoint = "/data/obs/geo/recent/notable"
        params = {
            "lat": lat,
            "lng": lng,
            "dist": min(distance_km, 50),  # eBird max is 50km
            "back": min(days_back, 30),  # eBird max is 30 days
            "detail": detail,
            "hotspot": str(hotspot_only).lower(),
            "includeProvisional": str(include_provisional).lower(),
            "maxResults": min(max_results, 10000),  # eBird max is 10000
            "locale": locale,
        }

        try:
            result = self.make_request(endpoint, params)
            logger.info(
                f"Retrieved {len(result)} notable observations near {lat},{lng}"
            )
            return result
        except EBirdAPIError as e:
            logger.error(f"Failed to get nearby notable observations: {e}")
            raise

    def get_nearby_species_observations(
        self,
        species_code: str,
        lat: float,
        lng: float,
        distance_km: int = 25,
        days_back: int = 7,
        detail: str = "simple",
        hotspot_only: bool = False,
        include_provisional: bool = False,
        max_results: int = 200,
        locale: str = "en",
    ) -> List[Dict[str, Any]]:
        """
        Get observations for a specific species near coordinates with enhanced geographic precision.

        This endpoint provides more detailed geographic filtering compared to the general
        get_nearby_observations() method by using species-specific geographic search.

        Args:
            species_code: eBird species code (e.g., "norcar")
            lat: Latitude coordinate
            lng: Longitude coordinate
            distance_km: Search radius in kilometers (default: 25, max: 50)
            days_back: Days to look back (default: 7, max: 30)
            detail: Response detail level ("simple" or "full")
            hotspot_only: Restrict to hotspot sightings only
            include_provisional: Include unconfirmed observations
            max_results: Maximum observations to return (default: 200, max: 10000)
            locale: Language locale for species names

        Returns:
            List of species-specific observations with enhanced geographic precision

        Raises:
            EBirdAPIError: For API errors with descriptive messages
        """
        endpoint = f"/data/obs/geo/recent/{species_code}"
        params = {
            "lat": lat,
            "lng": lng,
            "dist": min(distance_km, 50),  # eBird max is 50km
            "back": min(days_back, 30),  # eBird max is 30 days
            "detail": detail,
            "hotspot": str(hotspot_only).lower(),
            "includeProvisional": str(include_provisional).lower(),
            "maxResults": min(max_results, 10000),  # eBird max is 10000
            "locale": locale,
        }

        try:
            result = self.make_request(endpoint, params)
            logger.info(
                f"Retrieved {len(result)} geographic observations for species {species_code} near {lat},{lng}"
            )
            return result
        except EBirdAPIError as e:
            logger.error(f"Failed to get nearby species observations: {e}")
            raise


class EBirdObservationsClient(EBirdBaseClient, EBirdObservationsMixin):
    """Complete eBird API client for observation-related endpoints."""

    pass
