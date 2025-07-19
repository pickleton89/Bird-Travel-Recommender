"""
Locations functionality mixin for eBird API.

This module provides a single locations implementation that eliminates
the duplication between sync and async clients.
"""

from typing import List, Optional, Dict, Any
from ..models import HotspotModel, LocationModel
from ..protocols import EBirdClientProtocol
from ...config.logging import get_logger
from ...config.constants import EBIRD_MAX_RESULTS_DEFAULT


class LocationsMixin:
    """
    Mixin providing locations and hotspots functionality.
    
    This single implementation replaces both the sync and async
    locations modules, eliminating ~300 lines of duplication.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
    async def get_hotspots(
        self, 
        region_code: str,
        fmt: str = "json",
        back: Optional[int] = None
    ) -> List[HotspotModel]:
        """
        Get birding hotspots in a region.
        
        Args:
            region_code: eBird region code (e.g., 'US-CA')
            fmt: Response format (default: json)
            back: Number of days back to check for activity
            
        Returns:
            List of hotspots with coordinates and metadata
            
        Raises:
            EBirdAPIError: For API-related errors
            ValidationError: For invalid parameters
        """
        if not region_code or not region_code.strip():
            from ...exceptions import ValidationError
            raise ValidationError("Region code is required", field="region_code")
            
        endpoint = f"/ref/hotspot/{region_code}"
        params = {"fmt": fmt}
        
        if back is not None:
            params["back"] = back
            
        self.logger.debug(f"Fetching hotspots for region: {region_code}")
        
        try:
            response = await self.request(endpoint, params)
            
            # Convert to Pydantic models for type safety
            hotspots = [HotspotModel(**item) for item in response]
            
            self.logger.info(f"Retrieved {len(hotspots)} hotspots for {region_code}")
            return hotspots
            
        except Exception as e:
            self.logger.error(f"Failed to fetch hotspots for {region_code}: {e}")
            raise
            
    async def get_nearby_hotspots(
        self, 
        lat: float, 
        lng: float,
        distance_km: int = 25,
        fmt: str = "json",
        back: Optional[int] = None
    ) -> List[HotspotModel]:
        """
        Get birding hotspots near specific coordinates.
        
        Args:
            lat: Latitude coordinate
            lng: Longitude coordinate  
            distance_km: Search radius in kilometers
            fmt: Response format (default: json)
            back: Number of days back to check for activity
            
        Returns:
            List of nearby hotspots
            
        Raises:
            EBirdAPIError: For API-related errors
            ValidationError: For invalid coordinates
        """
        # Validate coordinates
        if not (-90 <= lat <= 90):
            from ...exceptions import ValidationError
            raise ValidationError("Latitude must be between -90 and 90", field="lat")
            
        if not (-180 <= lng <= 180):
            from ...exceptions import ValidationError
            raise ValidationError("Longitude must be between -180 and 180", field="lng")
            
        if distance_km <= 0 or distance_km > 50:
            from ...exceptions import ValidationError
            raise ValidationError("Distance must be between 1 and 50 km", field="distance_km")
            
        endpoint = "/ref/hotspot/geo"
        params = {
            "lat": lat,
            "lng": lng,
            "dist": distance_km,
            "fmt": fmt
        }
        
        if back is not None:
            params["back"] = back
            
        self.logger.debug(f"Fetching nearby hotspots at {lat},{lng} within {distance_km}km")
        
        try:
            response = await self.request(endpoint, params)
            
            # Convert to Pydantic models
            hotspots = [HotspotModel(**item) for item in response]
            
            self.logger.info(f"Retrieved {len(hotspots)} nearby hotspots")
            return hotspots
            
        except Exception as e:
            self.logger.error(f"Failed to fetch nearby hotspots: {e}")
            raise
            
    async def get_hotspot_info(
        self, 
        location_id: str,
        fmt: str = "json"
    ) -> HotspotModel:
        """
        Get detailed information about a specific hotspot.
        
        Args:
            location_id: eBird location ID
            fmt: Response format (default: json)
            
        Returns:
            Detailed hotspot information
            
        Raises:
            EBirdAPIError: For API-related errors
            ValidationError: For invalid location ID
        """
        if not location_id or not location_id.strip():
            from ...exceptions import ValidationError
            raise ValidationError("Location ID is required", field="location_id")
            
        endpoint = f"/ref/hotspot/info/{location_id}"
        params = {"fmt": fmt}
        
        self.logger.debug(f"Fetching hotspot info for: {location_id}")
        
        try:
            response = await self.request(endpoint, params)
            
            # Convert to Pydantic model
            hotspot = HotspotModel(**response)
            
            self.logger.info(f"Retrieved hotspot info for {location_id}")
            return hotspot
            
        except Exception as e:
            self.logger.error(f"Failed to fetch hotspot info for {location_id}: {e}")
            raise
            
    async def get_top_locations(
        self, 
        region_code: str,
        year: int,
        month: int,
        max_results: int = EBIRD_MAX_RESULTS_DEFAULT
    ) -> List[Dict[str, Any]]:
        """
        Get top birding locations for a region in a specific month.
        
        Args:
            region_code: eBird region code
            year: Year (4-digit)
            month: Month (1-12)
            max_results: Maximum number of results
            
        Returns:
            List of top locations with species counts
            
        Raises:
            EBirdAPIError: For API-related errors
            ValidationError: For invalid parameters
        """
        if not region_code or not region_code.strip():
            from ...exceptions import ValidationError
            raise ValidationError("Region code is required", field="region_code")
            
        # Validate date
        if not (1900 <= year <= 2100):
            from ...exceptions import ValidationError
            raise ValidationError("Year must be between 1900 and 2100", field="year")
            
        if not (1 <= month <= 12):
            from ...exceptions import ValidationError
            raise ValidationError("Month must be between 1 and 12", field="month")
            
        endpoint = f"/product/top100/{region_code}/{year}/{month}"
        params = {"maxResults": max_results}
        
        self.logger.debug(f"Fetching top locations for {region_code} in {year}-{month:02d}")
        
        try:
            response = await self.request(endpoint, params)
            
            self.logger.info(f"Retrieved {len(response)} top locations")
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to fetch top locations: {e}")
            raise
            
    async def get_seasonal_hotspots(
        self, 
        region_code: str,
        species_code: str,
        year: int,
        month: int
    ) -> List[HotspotModel]:
        """
        Get seasonal hotspots for a specific species.
        
        Args:
            region_code: eBird region code
            species_code: Species code
            year: Year (4-digit)
            month: Month (1-12)
            
        Returns:
            List of seasonal hotspots for the species
            
        Raises:
            EBirdAPIError: For API-related errors
            ValidationError: For invalid parameters
        """
        if not region_code or not region_code.strip():
            from ...exceptions import ValidationError
            raise ValidationError("Region code is required", field="region_code")
            
        if not species_code or not species_code.strip():
            from ...exceptions import ValidationError
            raise ValidationError("Species code is required", field="species_code")
            
        # Validate date
        if not (1900 <= year <= 2100):
            from ...exceptions import ValidationError
            raise ValidationError("Year must be between 1900 and 2100", field="year")
            
        if not (1 <= month <= 12):
            from ...exceptions import ValidationError
            raise ValidationError("Month must be between 1 and 12", field="month")
            
        endpoint = f"/data/obs/{region_code}/historic/{year}/{month}/{species_code}"
        params = {}
        
        self.logger.debug(f"Fetching seasonal hotspots for {species_code} in {region_code}")
        
        try:
            response = await self.request(endpoint, params)
            
            # Extract unique locations and convert to hotspot models
            locations = {}
            for obs in response:
                loc_id = obs.get("locId")
                if loc_id and loc_id not in locations:
                    locations[loc_id] = {
                        "locId": loc_id,
                        "locName": obs.get("locName"),
                        "lat": obs.get("lat"),
                        "lng": obs.get("lng"),
                        "countryCode": obs.get("countryCode"),
                        "subnational1Code": obs.get("subnational1Code"),
                        "latestObsDt": obs.get("obsDt"),
                        "numSpeciesAllTime": None  # Not available in this endpoint
                    }
                    
            hotspots = [HotspotModel(**loc_data) for loc_data in locations.values()]
            
            self.logger.info(f"Retrieved {len(hotspots)} seasonal hotspots")
            return hotspots
            
        except Exception as e:
            self.logger.error(f"Failed to fetch seasonal hotspots: {e}")
            raise