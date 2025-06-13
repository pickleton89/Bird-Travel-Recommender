#!/usr/bin/env python3
"""
Location-related MCP handler methods for the Bird Travel Recommender.

These handlers provide location-specific eBird API functionality including:
- Region details and metadata
- Hotspot information  
- Species location finding
- Notable observations near coordinates
- Species-specific observations near coordinates
"""

import logging
from typing import Dict, List, Optional

from ...utils.ebird_api import EBirdClient

# Configure logging
logger = logging.getLogger(__name__)

class LocationHandlers:
    """Location-related MCP tool handlers"""
    
    def __init__(self):
        self.ebird_api = EBirdClient()
    
    async def handle_get_region_details(self, region_code: str, name_format: str = "detailed"):
        """Handle get_region_details tool"""
        try:
            logger.info(f"Getting region details for {region_code}")
            
            region_info = self.ebird_api.get_region_info(
                region_code=region_code,
                name_format=name_format
            )
            
            return {
                "success": True,
                "region_code": region_code,
                "name_format": name_format,
                "region_info": region_info
            }
            
        except Exception as e:
            logger.error(f"Error in get_region_details: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "region_code": region_code,
                "region_info": {}
            }
    
    async def handle_get_hotspot_details(self, location_id: str):
        """Handle get_hotspot_details tool"""
        try:
            logger.info(f"Getting hotspot details for {location_id}")
            
            hotspot_info = self.ebird_api.get_hotspot_info(location_id=location_id)
            
            return {
                "success": True,
                "location_id": location_id,
                "hotspot_info": hotspot_info
            }
            
        except Exception as e:
            logger.error(f"Error in get_hotspot_details: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "location_id": location_id,
                "hotspot_info": {}
            }
    
    async def handle_find_nearest_species(
        self, 
        species_code: str, 
        lat: float, 
        lng: float, 
        days_back: int = 14,
        distance_km: int = 50,
        hotspot_only: bool = False
    ):
        """Handle find_nearest_species tool"""
        try:
            logger.info(f"Finding nearest observations for {species_code} at {lat},{lng}")
            
            observations = self.ebird_api.get_nearest_observations(
                species_code=species_code,
                lat=lat,
                lng=lng,
                days_back=days_back,
                distance_km=distance_km,
                hotspot_only=hotspot_only
            )
            
            return {
                "success": True,
                "species_code": species_code,
                "search_location": {"lat": lat, "lng": lng},
                "parameters": {
                    "days_back": days_back,
                    "distance_km": distance_km,
                    "hotspot_only": hotspot_only
                },
                "observations": observations,
                "count": len(observations)
            }
            
        except Exception as e:
            logger.error(f"Error in find_nearest_species: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "species_code": species_code,
                "observations": []
            }
    
    async def handle_get_nearby_notable_observations(
        self,
        lat: float,
        lng: float,
        distance_km: int = 25,
        days_back: int = 7,
        detail: str = "simple",
        hotspot_only: bool = False,
        include_provisional: bool = False,
        max_results: int = 200
    ):
        """Handle get_nearby_notable_observations tool"""
        try:
            logger.info(f"Getting nearby notable observations at {lat},{lng}")
            
            observations = self.ebird_api.get_nearby_notable_observations(
                lat=lat,
                lng=lng,
                distance_km=distance_km,
                days_back=days_back,
                detail=detail,
                hotspot_only=hotspot_only,
                include_provisional=include_provisional,
                max_results=max_results
            )
            
            return {
                "success": True,
                "coordinates": {"lat": lat, "lng": lng},
                "search_parameters": {
                    "distance_km": distance_km,
                    "days_back": days_back,
                    "detail": detail,
                    "hotspot_only": hotspot_only,
                    "include_provisional": include_provisional,
                    "max_results": max_results
                },
                "notable_observations": observations,
                "observation_count": len(observations)
            }
            
        except Exception as e:
            logger.error(f"Error in get_nearby_notable_observations: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "coordinates": {"lat": lat, "lng": lng},
                "notable_observations": []
            }
    
    async def handle_get_nearby_species_observations(
        self,
        species_code: str,
        lat: float,
        lng: float,
        distance_km: int = 25,
        days_back: int = 7,
        detail: str = "simple",
        hotspot_only: bool = False,
        include_provisional: bool = False,
        max_results: int = 200
    ):
        """Handle get_nearby_species_observations tool"""
        try:
            logger.info(f"Getting nearby observations for species {species_code} at {lat},{lng}")
            
            observations = self.ebird_api.get_nearby_species_observations(
                species_code=species_code,
                lat=lat,
                lng=lng,
                distance_km=distance_km,
                days_back=days_back,
                detail=detail,
                hotspot_only=hotspot_only,
                include_provisional=include_provisional,
                max_results=max_results
            )
            
            return {
                "success": True,
                "species_code": species_code,
                "coordinates": {"lat": lat, "lng": lng},
                "search_parameters": {
                    "distance_km": distance_km,
                    "days_back": days_back,
                    "detail": detail,
                    "hotspot_only": hotspot_only,
                    "include_provisional": include_provisional,
                    "max_results": max_results
                },
                "species_observations": observations,
                "observation_count": len(observations)
            }
            
        except Exception as e:
            logger.error(f"Error in get_nearby_species_observations: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "species_code": species_code,
                "coordinates": {"lat": lat, "lng": lng},
                "species_observations": []
            }
    
    async def handle_get_top_locations(
        self,
        region: str,
        days_back: int = 7,
        max_results: int = 100,
        locale: str = "en"
    ):
        """Handle get_top_locations tool"""
        try:
            logger.info(f"Getting top active locations in region {region}")
            
            locations = self.ebird_api.get_top_locations(
                region=region,
                days_back=days_back,
                max_results=max_results,
                locale=locale
            )
            
            return {
                "success": True,
                "region": region,
                "search_parameters": {
                    "days_back": days_back,
                    "max_results": max_results,
                    "locale": locale
                },
                "top_locations": locations,
                "location_count": len(locations)
            }
            
        except Exception as e:
            logger.error(f"Error in get_top_locations: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "region": region,
                "top_locations": []
            }
    
    async def handle_get_regional_statistics(
        self,
        region: str,
        days_back: int = 30,
        locale: str = "en"
    ):
        """Handle get_regional_statistics tool"""
        try:
            logger.info(f"Getting regional statistics for {region}")
            
            statistics = self.ebird_api.get_regional_statistics(
                region=region,
                days_back=days_back,
                locale=locale
            )
            
            return {
                "success": True,
                "region": region,
                "search_parameters": {
                    "days_back": days_back,
                    "locale": locale
                },
                "statistics": statistics
            }
            
        except Exception as e:
            logger.error(f"Error in get_regional_statistics: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "region": region,
                "statistics": {}
            }
    
    async def handle_get_location_species_list(
        self,
        location_id: str,
        locale: str = "en"
    ):
        """Handle get_location_species_list tool"""
        try:
            logger.info(f"Getting species list for location {location_id}")
            
            species_list = self.ebird_api.get_location_species_list(
                location_id=location_id,
                locale=locale
            )
            
            return {
                "success": True,
                "location_id": location_id,
                "search_parameters": {
                    "locale": locale
                },
                "species_list": species_list,
                "species_count": len(species_list)
            }
            
        except Exception as e:
            logger.error(f"Error in get_location_species_list: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "location_id": location_id,
                "species_list": []
            }
    
    async def handle_get_subregions(
        self,
        region_code: str,
        region_type: str = "subnational1"
    ):
        """Handle get_subregions tool"""
        try:
            logger.info(f"Getting {region_type} subregions for {region_code}")
            
            subregions = self.ebird_api.get_subregions(
                region_code=region_code,
                region_type=region_type
            )
            
            return {
                "success": True,
                "parent_region": region_code,
                "region_type": region_type,
                "subregions": subregions,
                "subregion_count": len(subregions)
            }
            
        except Exception as e:
            logger.error(f"Error in get_subregions: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "parent_region": region_code,
                "subregions": []
            }
    
    async def handle_get_adjacent_regions(
        self,
        region_code: str
    ):
        """Handle get_adjacent_regions tool"""
        try:
            logger.info(f"Getting adjacent regions for {region_code}")
            
            adjacent_regions = self.ebird_api.get_adjacent_regions(
                region_code=region_code
            )
            
            return {
                "success": True,
                "center_region": region_code,
                "adjacent_regions": adjacent_regions,
                "adjacent_count": len(adjacent_regions)
            }
            
        except Exception as e:
            logger.error(f"Error in get_adjacent_regions: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "center_region": region_code,
                "adjacent_regions": []
            }
    
    async def handle_get_elevation_data(
        self,
        latitude: float,
        longitude: float,
        radius_km: int = 25
    ):
        """Handle get_elevation_data tool"""
        try:
            logger.info(f"Getting elevation data for ({latitude}, {longitude}) within {radius_km}km")
            
            elevation_data = self.ebird_api.get_elevation_data(
                lat=latitude,
                lng=longitude,
                radius_km=radius_km
            )
            
            return {
                "success": True,
                "coordinates": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "search_radius": radius_km,
                "elevation_analysis": elevation_data
            }
            
        except Exception as e:
            logger.error(f"Error in get_elevation_data: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "coordinates": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "elevation_analysis": None
            }