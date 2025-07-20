"""
Regions functionality mixin for eBird API.

This module provides a single regions implementation that eliminates
the duplication between sync and async clients.
"""

from typing import List, Dict, Any
from ..models import RegionModel
from ...config.logging import get_logger


class RegionsMixin:
    """
    Mixin providing regions functionality.
    
    This single implementation replaces both the sync and async
    regions modules, eliminating ~400 lines of duplication.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
    async def get_region_info(
        self, 
        region_code: str,
        region_name_format: str = "en",
        fmt: str = "json"
    ) -> RegionModel:
        """
        Get information about a specific region.
        
        Args:
            region_code: eBird region code (e.g., 'US-CA')
            region_name_format: Language format for region names
            fmt: Response format (default: json)
            
        Returns:
            Region information
            
        Raises:
            EBirdAPIError: For API-related errors
            ValidationError: For invalid region code
        """
        if not region_code or not region_code.strip():
            from ...exceptions import ValidationError
            raise ValidationError("Region code is required", field="region_code")
            
        endpoint = f"/ref/region/info/{region_code}"
        params = {
            "regionNameFormat": region_name_format,
            "fmt": fmt
        }
        
        self.logger.debug(f"Fetching region info for: {region_code}")
        
        try:
            response = await self.request(endpoint, params)
            
            # Convert to Pydantic model
            region = RegionModel(**response)
            
            self.logger.info(f"Retrieved region info for {region_code}")
            return region
            
        except Exception as e:
            self.logger.error(f"Failed to fetch region info for {region_code}: {e}")
            raise
            
    async def get_regional_statistics(
        self, 
        region_code: str,
        year: int,
        month: int,
        fmt: str = "json"
    ) -> Dict[str, Any]:
        """
        Get regional birding statistics for a specific month.
        
        Args:
            region_code: eBird region code
            year: Year (4-digit)
            month: Month (1-12)
            fmt: Response format (default: json)
            
        Returns:
            Regional statistics including species counts and checklist metrics
            
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
            
        endpoint = f"/product/stats/{region_code}/{year}/{month}"
        params = {"fmt": fmt}
        
        self.logger.debug(f"Fetching regional stats for {region_code} in {year}-{month:02d}")
        
        try:
            response = await self.request(endpoint, params)
            
            self.logger.info(f"Retrieved regional statistics for {region_code}")
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to fetch regional statistics: {e}")
            raise
            
    async def get_subregions(
        self, 
        region_code: str,
        region_type: str = "subnational1",
        fmt: str = "json"
    ) -> List[RegionModel]:
        """
        Get subregions within a region.
        
        Args:
            region_code: Parent region code
            region_type: Type of subregions ('subnational1' or 'subnational2')
            fmt: Response format (default: json)
            
        Returns:
            List of subregions
            
        Raises:
            EBirdAPIError: For API-related errors
            ValidationError: For invalid parameters
        """
        if not region_code or not region_code.strip():
            from ...exceptions import ValidationError
            raise ValidationError("Region code is required", field="region_code")
            
        if region_type not in ["subnational1", "subnational2"]:
            from ...exceptions import ValidationError
            raise ValidationError(
                "Region type must be 'subnational1' or 'subnational2'", 
                field="region_type"
            )
            
        endpoint = f"/ref/region/list/{region_type}/{region_code}"
        params = {"fmt": fmt}
        
        self.logger.debug(f"Fetching {region_type} subregions for {region_code}")
        
        try:
            response = await self.request(endpoint, params)
            
            # Convert to Pydantic models
            subregions = [RegionModel(**item) for item in response]
            
            self.logger.info(f"Retrieved {len(subregions)} subregions for {region_code}")
            return subregions
            
        except Exception as e:
            self.logger.error(f"Failed to fetch subregions for {region_code}: {e}")
            raise
            
    async def get_adjacent_regions(
        self, 
        region_code: str,
        fmt: str = "json"
    ) -> List[RegionModel]:
        """
        Get regions adjacent to the specified region.
        
        Args:
            region_code: eBird region code
            fmt: Response format (default: json)
            
        Returns:
            List of adjacent regions
            
        Raises:
            EBirdAPIError: For API-related errors
            ValidationError: For invalid region code
        """
        if not region_code or not region_code.strip():
            from ...exceptions import ValidationError
            raise ValidationError("Region code is required", field="region_code")
            
        endpoint = f"/ref/region/adjacent/{region_code}"
        params = {"fmt": fmt}
        
        self.logger.debug(f"Fetching adjacent regions for: {region_code}")
        
        try:
            response = await self.request(endpoint, params)
            
            # Convert to Pydantic models
            adjacent_regions = [RegionModel(**item) for item in response]
            
            self.logger.info(f"Retrieved {len(adjacent_regions)} adjacent regions")
            return adjacent_regions
            
        except Exception as e:
            self.logger.error(f"Failed to fetch adjacent regions for {region_code}: {e}")
            raise
            
    async def get_countries(self, fmt: str = "json") -> List[RegionModel]:
        """
        Get list of all countries with eBird data.
        
        Args:
            fmt: Response format (default: json)
            
        Returns:
            List of countries
            
        Raises:
            EBirdAPIError: For API-related errors
        """
        endpoint = "/ref/region/list/country/world"
        params = {"fmt": fmt}
        
        self.logger.debug("Fetching list of countries")
        
        try:
            response = await self.request(endpoint, params)
            
            # Convert to Pydantic models
            countries = [RegionModel(**item) for item in response]
            
            self.logger.info(f"Retrieved {len(countries)} countries")
            return countries
            
        except Exception as e:
            self.logger.error(f"Failed to fetch countries list: {e}")
            raise
            
    async def get_subnational1_regions(
        self, 
        country_code: str,
        fmt: str = "json"
    ) -> List[RegionModel]:
        """
        Get subnational1 regions (states/provinces) for a country.
        
        Args:
            country_code: Country code (e.g., 'US')
            fmt: Response format (default: json)
            
        Returns:
            List of subnational1 regions
            
        Raises:
            EBirdAPIError: For API-related errors
            ValidationError: For invalid country code
        """
        if not country_code or not country_code.strip():
            from ...exceptions import ValidationError
            raise ValidationError("Country code is required", field="country_code")
            
        endpoint = f"/ref/region/list/subnational1/{country_code}"
        params = {"fmt": fmt}
        
        self.logger.debug(f"Fetching subnational1 regions for: {country_code}")
        
        try:
            response = await self.request(endpoint, params)
            
            # Convert to Pydantic models
            regions = [RegionModel(**item) for item in response]
            
            self.logger.info(f"Retrieved {len(regions)} subnational1 regions")
            return regions
            
        except Exception as e:
            self.logger.error(f"Failed to fetch subnational1 regions for {country_code}: {e}")
            raise
            
    async def get_subnational2_regions(
        self, 
        subnational1_code: str,
        fmt: str = "json"
    ) -> List[RegionModel]:
        """
        Get subnational2 regions (counties) for a subnational1 region.
        
        Args:
            subnational1_code: Subnational1 region code (e.g., 'US-CA')
            fmt: Response format (default: json)
            
        Returns:
            List of subnational2 regions
            
        Raises:
            EBirdAPIError: For API-related errors
            ValidationError: For invalid region code
        """
        if not subnational1_code or not subnational1_code.strip():
            from ...exceptions import ValidationError
            raise ValidationError("Subnational1 code is required", field="subnational1_code")
            
        endpoint = f"/ref/region/list/subnational2/{subnational1_code}"
        params = {"fmt": fmt}
        
        self.logger.debug(f"Fetching subnational2 regions for: {subnational1_code}")
        
        try:
            response = await self.request(endpoint, params)
            
            # Convert to Pydantic models
            regions = [RegionModel(**item) for item in response]
            
            self.logger.info(f"Retrieved {len(regions)} subnational2 regions")
            return regions
            
        except Exception as e:
            self.logger.error(f"Failed to fetch subnational2 regions for {subnational1_code}: {e}")
            raise