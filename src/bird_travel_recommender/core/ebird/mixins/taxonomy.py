"""
Taxonomy functionality mixin for eBird API.

This module provides a single taxonomy implementation that eliminates
the duplication between sync and async clients.
"""

from typing import List, Optional
from ..models import TaxonomyModel
from ..protocols import EBirdClientProtocol
from ...config.logging import get_logger


class TaxonomyMixin:
    """
    Mixin providing taxonomy functionality.
    
    This single implementation replaces both the sync and async
    taxonomy modules, eliminating ~200 lines of duplication.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
    async def get_taxonomy(
        self, 
        fmt: str = "json",
        locale: str = "en",
        version: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[TaxonomyModel]:
        """
        Get eBird taxonomy data.
        
        Args:
            fmt: Response format (default: json)
            locale: Language locale (default: en)
            version: Taxonomy version (default: latest)
            category: Species category filter
            
        Returns:
            List of taxonomy entries
            
        Raises:
            EBirdAPIError: For API-related errors
            ValidationError: For invalid parameters
        """
        params = {
            "fmt": fmt,
            "locale": locale
        }
        
        if version:
            params["version"] = version
            
        if category:
            params["cat"] = category
            
        self.logger.debug(f"Fetching taxonomy with params: {params}")
        
        try:
            response = await self.request("/ref/taxonomy/ebird", params)
            
            # Convert to Pydantic models for type safety
            taxonomy_entries = [TaxonomyModel(**item) for item in response]
            
            self.logger.info(f"Retrieved {len(taxonomy_entries)} taxonomy entries")
            return taxonomy_entries
            
        except Exception as e:
            self.logger.error(f"Failed to fetch taxonomy: {e}")
            raise
            
    async def get_taxonomic_forms(
        self, 
        species_code: str,
        fmt: str = "json"
    ) -> List[TaxonomyModel]:
        """
        Get taxonomic forms for a species.
        
        Args:
            species_code: Species code to get forms for
            fmt: Response format (default: json)
            
        Returns:
            List of taxonomic forms
            
        Raises:
            EBirdAPIError: For API-related errors
            ValidationError: For invalid species code
        """
        if not species_code or not species_code.strip():
            from ...exceptions import ValidationError
            raise ValidationError("Species code is required", field="species_code")
            
        params = {"fmt": fmt}
        endpoint = f"/ref/taxonomy/forms/{species_code}"
        
        self.logger.debug(f"Fetching taxonomic forms for {species_code}")
        
        try:
            response = await self.request(endpoint, params)
            
            # Convert to Pydantic models
            forms = [TaxonomyModel(**item) for item in response]
            
            self.logger.info(f"Retrieved {len(forms)} taxonomic forms for {species_code}")
            return forms
            
        except Exception as e:
            self.logger.error(f"Failed to fetch taxonomic forms for {species_code}: {e}")
            raise
            
    async def get_taxonomic_groups(
        self,
        group_name_locale: str = "en",
        fmt: str = "json"
    ) -> List[dict]:
        """
        Get eBird taxonomic groups.
        
        Args:
            group_name_locale: Language for group names (default: en)
            fmt: Response format (default: json)
            
        Returns:
            List of taxonomic groups
            
        Raises:
            EBirdAPIError: For API-related errors
        """
        params = {
            "groupNameLocale": group_name_locale,
            "fmt": fmt
        }
        
        self.logger.debug(f"Fetching taxonomic groups with locale: {group_name_locale}")
        
        try:
            response = await self.request("/ref/taxonomy/groups", params)
            
            self.logger.info(f"Retrieved {len(response)} taxonomic groups")
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to fetch taxonomic groups: {e}")
            raise
            
    async def get_species_list(
        self, 
        region_code: str,
        fmt: str = "json"
    ) -> List[str]:
        """
        Get species list for a region.
        
        Args:
            region_code: Region code (e.g., 'US-CA')
            fmt: Response format (default: json)
            
        Returns:
            List of species codes
            
        Raises:
            EBirdAPIError: For API-related errors
            ValidationError: For invalid region code
        """
        if not region_code or not region_code.strip():
            from ...exceptions import ValidationError
            raise ValidationError("Region code is required", field="region_code")
            
        params = {"fmt": fmt}
        endpoint = f"/product/spplist/{region_code}"
        
        self.logger.debug(f"Fetching species list for region: {region_code}")
        
        try:
            response = await self.request(endpoint, params)
            
            self.logger.info(f"Retrieved {len(response)} species for region {region_code}")
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to fetch species list for {region_code}: {e}")
            raise