"""
Async eBird API client for observation-related endpoints.

This module provides async methods for retrieving bird observation data from the eBird API,
including recent observations, nearby sightings, notable birds, and species-specific queries.
"""

from typing import List, Dict, Any, Optional
import logging
from .ebird_async_base import EBirdAsyncBaseClient, EBirdAPIError

logger = logging.getLogger(__name__)


class EBirdAsyncObservationsMixin:
    """Async mixin class providing observation-related eBird API methods."""
    
    async def get_recent_observations(
        self, 
        region_code: str, 
        days_back: int = 7, 
        species_code: Optional[str] = None,
        include_provisional: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get recent bird observations in a region (async).
        
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
            "includeProvisional": str(include_provisional).lower()
        }
        
        try:
            result = await self.make_request(endpoint, params)
            logger.info(f"Retrieved {len(result)} recent observations for {region_code}")
            return result
        except EBirdAPIError as e:
            logger.error(f"Error fetching recent observations for {region_code}: {e}")
            raise
    
    async def get_nearby_observations(
        self,
        lat: float,
        lng: float,
        distance_km: int = 25,
        days_back: int = 7,
        species_code: Optional[str] = None,
        include_provisional: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get recent bird observations near a location (async).
        
        Args:
            lat: Latitude (-90 to 90)
            lng: Longitude (-180 to 180)
            distance_km: Search radius in kilometers (max: 50)
            days_back: Days to look back (default: 7, max: 30)
            species_code: Optional specific species filter
            include_provisional: Include unreviewed observations
            
        Returns:
            List of nearby observations with species, location, date, count
        """
        endpoint = f"/data/obs/geo/recent"
        if species_code:
            endpoint += f"/{species_code}"
            
        params = {
            "lat": lat,
            "lng": lng,
            "dist": min(distance_km, 50),  # eBird max is 50km
            "back": min(days_back, 30),
            "includeProvisional": str(include_provisional).lower()
        }
        
        try:
            result = await self.make_request(endpoint, params)
            logger.info(f"Retrieved {len(result)} nearby observations within {distance_km}km of ({lat}, {lng})")
            return result
        except EBirdAPIError as e:
            logger.error(f"Error fetching nearby observations for ({lat}, {lng}): {e}")
            raise
    
    async def get_notable_observations(
        self,
        region_code: str,
        days_back: int = 7,
        include_provisional: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get notable (rare/unusual) bird observations in a region (async).
        
        Args:
            region_code: eBird region code (e.g., "US-MA", "CA-ON")
            days_back: Days to look back (default: 7, max: 30)
            include_provisional: Include unreviewed observations
            
        Returns:
            List of notable observations with species, location, date, count
        """
        endpoint = f"/data/obs/{region_code}/recent/notable"
        
        params = {
            "back": min(days_back, 30),
            "includeProvisional": str(include_provisional).lower()
        }
        
        try:
            result = await self.make_request(endpoint, params)
            logger.info(f"Retrieved {len(result)} notable observations for {region_code}")
            return result
        except EBirdAPIError as e:
            logger.error(f"Error fetching notable observations for {region_code}: {e}")
            raise
    
    async def get_species_observations(
        self,
        region_code: str,
        species_code: str,
        days_back: int = 7,
        include_provisional: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get observations for a specific species in a region (async).
        
        Args:
            region_code: eBird region code (e.g., "US-MA", "CA-ON")
            species_code: eBird species code (e.g., "norcar", "blujay")
            days_back: Days to look back (default: 7, max: 30)
            include_provisional: Include unreviewed observations
            
        Returns:
            List of species observations with location, date, count
        """
        return await self.get_recent_observations(
            region_code=region_code,
            days_back=days_back,
            species_code=species_code,
            include_provisional=include_provisional
        )
    
    async def get_nearest_observations(
        self,
        lat: float,
        lng: float,
        species_code: str,
        days_back: int = 7,
        distance_km: int = 25,
        include_provisional: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get nearest observations of a specific species (async).
        
        Args:
            lat: Latitude (-90 to 90)
            lng: Longitude (-180 to 180)
            species_code: eBird species code (e.g., "norcar", "blujay")
            days_back: Days to look back (default: 7, max: 30)
            distance_km: Search radius in kilometers (max: 50)
            include_provisional: Include unreviewed observations
            
        Returns:
            List of nearest species observations
        """
        endpoint = f"/data/nearest/geo/recent/{species_code}"
        
        params = {
            "lat": lat,
            "lng": lng,
            "dist": min(distance_km, 50),
            "back": min(days_back, 30),
            "includeProvisional": str(include_provisional).lower()
        }
        
        try:
            result = await self.make_request(endpoint, params)
            logger.info(f"Retrieved {len(result)} nearest {species_code} observations near ({lat}, {lng})")
            return result
        except EBirdAPIError as e:
            logger.error(f"Error fetching nearest {species_code} observations for ({lat}, {lng}): {e}")
            raise
    
    async def get_nearby_notable_observations(
        self,
        lat: float,
        lng: float,
        distance_km: int = 25,
        days_back: int = 7,
        include_provisional: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get notable bird observations near a location (async).
        
        Args:
            lat: Latitude (-90 to 90)
            lng: Longitude (-180 to 180)
            distance_km: Search radius in kilometers (max: 50)
            days_back: Days to look back (default: 7, max: 30)
            include_provisional: Include unreviewed observations
            
        Returns:
            List of nearby notable observations
        """
        endpoint = f"/data/obs/geo/recent/notable"
        
        params = {
            "lat": lat,
            "lng": lng,
            "dist": min(distance_km, 50),
            "back": min(days_back, 30),
            "includeProvisional": str(include_provisional).lower()
        }
        
        try:
            result = await self.make_request(endpoint, params)
            logger.info(f"Retrieved {len(result)} nearby notable observations within {distance_km}km of ({lat}, {lng})")
            return result
        except EBirdAPIError as e:
            logger.error(f"Error fetching nearby notable observations for ({lat}, {lng}): {e}")
            raise
    
    async def get_nearby_species_observations(
        self,
        lat: float,
        lng: float,
        species_code: str,
        distance_km: int = 25,
        days_back: int = 7,
        include_provisional: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get observations of a specific species near a location (async).
        
        Args:
            lat: Latitude (-90 to 90)
            lng: Longitude (-180 to 180)
            species_code: eBird species code (e.g., "norcar", "blujay")
            distance_km: Search radius in kilometers (max: 50)
            days_back: Days to look back (default: 7, max: 30)
            include_provisional: Include unreviewed observations
            
        Returns:
            List of nearby species observations
        """
        endpoint = f"/data/obs/geo/recent/{species_code}"
        
        params = {
            "lat": lat,
            "lng": lng,
            "dist": min(distance_km, 50),
            "back": min(days_back, 30),
            "includeProvisional": str(include_provisional).lower()
        }
        
        try:
            result = await self.make_request(endpoint, params)
            logger.info(f"Retrieved {len(result)} nearby {species_code} observations within {distance_km}km of ({lat}, {lng})")
            return result
        except EBirdAPIError as e:
            logger.error(f"Error fetching nearby {species_code} observations for ({lat}, {lng}): {e}")
            raise