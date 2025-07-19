"""
Observations functionality mixin for eBird API.

This module provides a single observations implementation that eliminates
the duplication between sync and async clients.
"""

from typing import List, Optional
from ..models import ObservationModel
from ..protocols import EBirdClientProtocol
from ...config.logging import get_logger
from ...config.constants import EBIRD_MAX_RESULTS_DEFAULT, EBIRD_BACK_DAYS_DEFAULT


class ObservationsMixin:
    """
    Mixin providing observations functionality.
    
    This single implementation replaces both the sync and async
    observations modules, eliminating ~300 lines of duplication.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
    async def get_recent_observations(
        self, 
        region_code: str,
        species_code: Optional[str] = None,
        back: int = EBIRD_BACK_DAYS_DEFAULT,
        max_results: int = EBIRD_MAX_RESULTS_DEFAULT,
        cat: Optional[str] = None,
        hotspot: bool = False,
        include_provisional: bool = False,
        r: Optional[List[str]] = None
    ) -> List[ObservationModel]:
        """
        Get recent bird observations for a region.
        
        Args:
            region_code: Region code (e.g., 'US-CA')
            species_code: Optional species code filter
            back: Number of days back to search
            max_results: Maximum number of results
            cat: Species category filter
            hotspot: Only include hotspot observations
            include_provisional: Include provisional observations
            r: List of specific locations
            
        Returns:
            List of recent observations
            
        Raises:
            EBirdAPIError: For API-related errors
            ValidationError: For invalid parameters
        """
        if not region_code or not region_code.strip():
            from ...exceptions import ValidationError
            raise ValidationError("Region code is required", field="region_code")
            
        # Build endpoint based on whether species filter is provided
        if species_code:
            endpoint = f"/data/obs/{region_code}/recent/{species_code}"
        else:
            endpoint = f"/data/obs/{region_code}/recent"
            
        # Build parameters
        params = {
            "back": back,
            "maxResults": max_results
        }
        
        if cat:
            params["cat"] = cat
        if hotspot:
            params["hotspot"] = "true"
        if include_provisional:
            params["includeProvisional"] = "true"
        if r:
            params["r"] = ",".join(r)
            
        self.logger.debug(f"Fetching recent observations for {region_code}, species: {species_code}")
        
        try:
            response = await self.request(endpoint, params)
            
            # Convert to Pydantic models for type safety
            observations = [ObservationModel(**item) for item in response]
            
            self.logger.info(f"Retrieved {len(observations)} recent observations")
            return observations
            
        except Exception as e:
            self.logger.error(f"Failed to fetch recent observations: {e}")
            raise
            
    async def get_recent_notable_observations(
        self, 
        region_code: str,
        back: int = EBIRD_BACK_DAYS_DEFAULT,
        max_results: int = EBIRD_MAX_RESULTS_DEFAULT,
        hotspot: bool = False,
        r: Optional[List[str]] = None,
        detail: str = "simple"
    ) -> List[ObservationModel]:
        """
        Get recent notable bird observations for a region.
        
        Args:
            region_code: Region code (e.g., 'US-CA')
            back: Number of days back to search
            max_results: Maximum number of results
            hotspot: Only include hotspot observations
            r: List of specific locations
            detail: Detail level (simple or full)
            
        Returns:
            List of notable observations
            
        Raises:
            EBirdAPIError: For API-related errors
            ValidationError: For invalid parameters
        """
        if not region_code or not region_code.strip():
            from ...exceptions import ValidationError
            raise ValidationError("Region code is required", field="region_code")
            
        endpoint = f"/data/obs/{region_code}/recent/notable"
        
        params = {
            "back": back,
            "maxResults": max_results,
            "detail": detail
        }
        
        if hotspot:
            params["hotspot"] = "true"
        if r:
            params["r"] = ",".join(r)
            
        self.logger.debug(f"Fetching notable observations for {region_code}")
        
        try:
            response = await self.request(endpoint, params)
            
            # Convert to Pydantic models
            observations = [ObservationModel(**item) for item in response]
            
            self.logger.info(f"Retrieved {len(observations)} notable observations")
            return observations
            
        except Exception as e:
            self.logger.error(f"Failed to fetch notable observations: {e}")
            raise
            
    async def get_species_observations(
        self, 
        region_code: str,
        species_code: str,
        back: int = EBIRD_BACK_DAYS_DEFAULT,
        max_results: int = EBIRD_MAX_RESULTS_DEFAULT,
        hotspot: bool = False,
        r: Optional[List[str]] = None,
        include_provisional: bool = False
    ) -> List[ObservationModel]:
        """
        Get observations for a specific species in a region.
        
        Args:
            region_code: Region code (e.g., 'US-CA')
            species_code: Species code
            back: Number of days back to search
            max_results: Maximum number of results
            hotspot: Only include hotspot observations
            r: List of specific locations
            include_provisional: Include provisional observations
            
        Returns:
            List of species observations
            
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
            
        endpoint = f"/data/obs/{region_code}/recent/{species_code}"
        
        params = {
            "back": back,
            "maxResults": max_results
        }
        
        if hotspot:
            params["hotspot"] = "true"
        if include_provisional:
            params["includeProvisional"] = "true"
        if r:
            params["r"] = ",".join(r)
            
        self.logger.debug(f"Fetching observations for species {species_code} in {region_code}")
        
        try:
            response = await self.request(endpoint, params)
            
            # Convert to Pydantic models
            observations = [ObservationModel(**item) for item in response]
            
            self.logger.info(f"Retrieved {len(observations)} observations for {species_code}")
            return observations
            
        except Exception as e:
            self.logger.error(f"Failed to fetch species observations: {e}")
            raise
            
    async def get_historic_observations_on_date(
        self, 
        region_code: str,
        year: int,
        month: int,
        day: int,
        cat: Optional[str] = None,
        max_results: int = EBIRD_MAX_RESULTS_DEFAULT,
        hotspot: bool = False,
        include_provisional: bool = False,
        r: Optional[List[str]] = None
    ) -> List[ObservationModel]:
        """
        Get historic observations on a specific date.
        
        Args:
            region_code: Region code (e.g., 'US-CA')
            year: Year (4-digit)
            month: Month (1-12)
            day: Day (1-31)
            cat: Species category filter
            max_results: Maximum number of results
            hotspot: Only include hotspot observations
            include_provisional: Include provisional observations
            r: List of specific locations
            
        Returns:
            List of historic observations
            
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
            
        if not (1 <= day <= 31):
            from ...exceptions import ValidationError
            raise ValidationError("Day must be between 1 and 31", field="day")
            
        endpoint = f"/data/obs/{region_code}/historic/{year}/{month}/{day}"
        
        params = {
            "maxResults": max_results
        }
        
        if cat:
            params["cat"] = cat
        if hotspot:
            params["hotspot"] = "true"
        if include_provisional:
            params["includeProvisional"] = "true"
        if r:
            params["r"] = ",".join(r)
            
        self.logger.debug(f"Fetching historic observations for {year}-{month:02d}-{day:02d}")
        
        try:
            response = await self.request(endpoint, params)
            
            # Convert to Pydantic models
            observations = [ObservationModel(**item) for item in response]
            
            self.logger.info(f"Retrieved {len(observations)} historic observations")
            return observations
            
        except Exception as e:
            self.logger.error(f"Failed to fetch historic observations: {e}")
            raise