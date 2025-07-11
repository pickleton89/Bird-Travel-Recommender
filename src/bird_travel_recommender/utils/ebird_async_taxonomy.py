"""
Async eBird API client for taxonomy and species-related endpoints.

This module provides async methods for retrieving bird species and taxonomy data from the eBird API,
including species lists, taxonomic information, and location-specific species data.
"""

from typing import List, Dict, Any, Optional
import logging
from .ebird_async_base import EBirdAPIError

logger = logging.getLogger(__name__)


class EBirdAsyncTaxonomyMixin:
    """Async mixin class providing taxonomy and species-related eBird API methods."""
    
    async def get_taxonomy(
        self,
        species_codes: Optional[List[str]] = None,
        format: str = "json",
        locale: str = "en"
    ) -> List[Dict[str, Any]]:
        """
        Get eBird taxonomy information (async).
        
        Args:
            species_codes: Optional list of species codes to filter
            format: Response format ("json" or "csv")
            locale: Language locale (default: "en")
            
        Returns:
            Taxonomy data with species codes, common names, scientific names
        """
        endpoint = "/ref/taxonomy/ebird"
        params = {
            "fmt": format,
            "locale": locale
        }
        
        if species_codes:
            params["species"] = ",".join(species_codes)
        
        try:
            result = await self.make_request(endpoint, params)
            if species_codes:
                logger.info(f"Retrieved taxonomy for {len(species_codes)} species codes")
            else:
                logger.info(f"Retrieved complete eBird taxonomy ({len(result)} entries)")
            return result
        except EBirdAPIError as e:
            logger.error(f"Failed to get taxonomy: {e}")
            raise

    async def get_species_list(
        self, 
        region_code: str,
        include_provisional: bool = False
    ) -> List[str]:
        """
        Get complete species list for a region (async).
        
        Args:
            region_code: eBird region code
            include_provisional: Include species from unreviewed observations
            
        Returns:
            List of species codes found in the region
        """
        endpoint = f"/product/spplist/{region_code}"
        params = {"includeProvisional": str(include_provisional).lower()}
        
        try:
            result = await self.make_request(endpoint, params)
            logger.info(f"Retrieved species list for {region_code}: {len(result)} species")
            return result
        except EBirdAPIError as e:
            logger.error(f"Failed to get species list for {region_code}: {e}")
            raise

    async def validate_species_codes(
        self,
        species_codes: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Validate species codes against eBird taxonomy (async).
        
        Args:
            species_codes: List of species codes to validate
            
        Returns:
            Dictionary mapping species codes to taxonomy information
        """
        try:
            taxonomy_data = await self.get_taxonomy(species_codes=species_codes)
            
            # Create mapping from species codes to full taxonomy info
            validated = {}
            for species in taxonomy_data:
                code = species.get('speciesCode', '')
                if code:
                    validated[code] = species
            
            logger.info(f"Validated {len(validated)} of {len(species_codes)} species codes")
            return validated
            
        except EBirdAPIError as e:
            logger.error(f"Failed to validate species codes: {e}")
            raise

    async def search_species_by_name(
        self,
        common_name: str,
        region_code: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for species by common name (async).
        
        This is a helper method that searches through taxonomy data
        to find species matching a common name pattern.
        
        Args:
            common_name: Common name to search for (case-insensitive)
            region_code: Optional region to filter results
            
        Returns:
            List of matching species with taxonomy information
        """
        try:
            # Get full taxonomy or region-specific species list
            if region_code:
                # Get species list for region, then get taxonomy for those species
                species_codes = await self.get_species_list(region_code)
                if not species_codes:
                    return []
                taxonomy_data = await self.get_taxonomy(species_codes=species_codes)
            else:
                # Search full taxonomy (this could be large)
                taxonomy_data = await self.get_taxonomy()
            
            # Filter by common name
            search_term = common_name.lower()
            matches = []
            
            for species in taxonomy_data:
                common_name_field = species.get('comName', '').lower()
                if search_term in common_name_field:
                    matches.append(species)
            
            logger.info(f"Found {len(matches)} species matching '{common_name}'")
            return matches
            
        except EBirdAPIError as e:
            logger.error(f"Failed to search species by name '{common_name}': {e}")
            raise

    async def get_regional_species_stats(
        self,
        region_code: str
    ) -> Dict[str, Any]:
        """
        Get species statistics for a region (async).
        
        Args:
            region_code: eBird region code
            
        Returns:
            Dictionary with species count and related statistics
        """
        try:
            species_list = await self.get_species_list(region_code)
            
            stats = {
                "region_code": region_code,
                "total_species": len(species_list),
                "species_codes": species_list
            }
            
            logger.info(f"Generated species stats for {region_code}: {stats['total_species']} species")
            return stats
            
        except EBirdAPIError as e:
            logger.error(f"Failed to get species stats for {region_code}: {e}")
            raise