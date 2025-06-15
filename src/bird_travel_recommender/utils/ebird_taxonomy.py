"""
eBird API client for taxonomy and species-related endpoints.

This module provides methods for retrieving bird species and taxonomy data from the eBird API,
including species lists, taxonomic information, and location-specific species data.
"""

from typing import List, Dict, Any, Optional
import logging
from .ebird_base import EBirdBaseClient, EBirdAPIError

logger = logging.getLogger(__name__)


class EBirdTaxonomyMixin:
    """Mixin class providing taxonomy and species-related eBird API methods."""
    
    def get_taxonomy(
        self,
        species_codes: Optional[List[str]] = None,
        format: str = "json",
        locale: str = "en"
    ) -> List[Dict[str, Any]]:
        """
        Get eBird taxonomy information.
        
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
            result = self.make_request(endpoint, params)
            if species_codes:
                logger.info(f"Retrieved taxonomy for {len(species_codes)} species codes")
            else:
                logger.info(f"Retrieved complete eBird taxonomy ({len(result)} entries)")
            return result
        except EBirdAPIError as e:
            logger.error(f"Failed to get taxonomy: {e}")
            raise

    def get_species_list(
        self,
        region_code: str
    ) -> List[str]:
        """
        Get complete list of species ever reported in a region.
        
        Args:
            region_code: eBird region code (e.g., "US-MA", "CA-ON")
            
        Returns:
            List of eBird species codes for all species in region
            
        Raises:
            EBirdAPIError: For API errors with descriptive messages
        """
        endpoint = f"/product/spplist/{region_code}"
        
        try:
            result = self.make_request(endpoint)
            logger.info(f"Retrieved species list for {region_code}: {len(result)} species")
            return result
        except EBirdAPIError as e:
            logger.error(f"Failed to get species list: {e}")
            raise

    def get_location_species_list(
        self,
        location_id: str,
        locale: str = "en"
    ) -> List[Dict[str, Any]]:
        """
        Get complete list of all bird species ever reported at a specific location.
        
        This endpoint provides the historical species list for a location,
        useful for understanding the full birding potential and biodiversity
        of a specific hotspot or coordinate.
        
        Args:
            location_id: eBird location ID (e.g., "L99381") or coordinates as "lat,lng"
            locale: Language code for common names (default: "en")
            
        Returns:
            List of species dictionaries with names and codes
        """
        # Handle both location IDs and coordinates
        if location_id.startswith("L"):
            # Standard location ID
            endpoint = f"/product/spplist/{location_id}"
        else:
            # Assume coordinates format "lat,lng"
            try:
                lat, lng = location_id.split(",")
                endpoint = f"/product/spplist/geo"
                # For coordinates, we need to use different parameters
            except ValueError:
                raise EBirdAPIError(f"Invalid location format: {location_id}. Use location ID (L12345) or coordinates (lat,lng)")
        
        params = {
            "fmt": "json",
            "locale": locale
        }
        
        # Add coordinates to params if using geographic endpoint
        if not location_id.startswith("L"):
            lat, lng = location_id.split(",")
            params.update({
                "lat": float(lat),
                "lng": float(lng)
            })
        
        try:
            species_codes = self.make_request(endpoint, params)
            
            # Get detailed taxonomy information for the species
            if species_codes:
                taxonomy_info = self.get_taxonomy(species_codes=species_codes[:200], locale=locale)  # Limit to avoid API overload
                
                # Create enriched species list
                species_list = []
                taxonomy_dict = {t["speciesCode"]: t for t in taxonomy_info}
                
                for species_code in species_codes:
                    if species_code in taxonomy_dict:
                        species_list.append(taxonomy_dict[species_code])
                    else:
                        # Fallback for species not in taxonomy response
                        species_list.append({
                            "speciesCode": species_code,
                            "comName": f"Species {species_code}",
                            "sciName": "Unknown",
                            "category": "species"
                        })
                
                logger.info(f"Retrieved {len(species_list)} species for location {location_id}")
                return species_list
            else:
                logger.info(f"No species found for location {location_id}")
                return []
                
        except EBirdAPIError as e:
            logger.error(f"Failed to get species list for location {location_id}: {e}")
            raise


class EBirdTaxonomyClient(EBirdBaseClient, EBirdTaxonomyMixin):
    """Complete eBird API client for taxonomy and species-related endpoints."""
    pass