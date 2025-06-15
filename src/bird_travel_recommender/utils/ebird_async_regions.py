"""
Async eBird API client for region and geographic-related endpoints.

This module provides async methods for retrieving regional information from the eBird API,
including region metadata, statistics, subregions, and geographic data.
"""

from typing import List, Dict, Any, Optional
import logging
from .ebird_async_base import EBirdAsyncBaseClient, EBirdAPIError
from ..constants import (
    EBIRD_DAYS_BACK_DEFAULT,
    EBIRD_RADIUS_KM_DEFAULT,
    EBIRD_RADIUS_KM_MAX,
    DEFAULT_ELEVATION_M,
    LATITUDE_MIN,
    LATITUDE_MAX,
    LONGITUDE_MIN,
    LONGITUDE_MAX
)

logger = logging.getLogger(__name__)


class EBirdAsyncRegionsMixin:
    """Async mixin class providing region and geographic-related eBird API methods."""
    
    async def get_region_info(
        self,
        region_code: str,
        name_format: str = "detailed"
    ) -> Dict[str, Any]:
        """
        Get metadata and human-readable information for a region.
        
        Args:
            region_code: eBird region code to get information about
            name_format: Name format ("detailed" or "short")
            
        Returns:
            Region information including name, type, and hierarchy
            
        Raises:
            EBirdAPIError: For API errors with descriptive messages
        """
        endpoint = f"/ref/region/info/{region_code}"
        params = {
            "nameFormat": name_format
        }
        
        try:
            result = await self.make_request(endpoint, params)
            logger.info(f"Retrieved region info for {region_code}: {result.get('name', 'Unknown')}")
            return result
        except EBirdAPIError as e:
            logger.error(f"Failed to get region info: {e}")
            raise

    async def get_regional_statistics(
        self,
        region: str,
        days_back: int = EBIRD_DAYS_BACK_DEFAULT,
        locale: str = "en"
    ) -> Dict[str, Any]:
        """
        Get comprehensive species counts and birding activity statistics for a region.
        
        Provides insights into regional birding activity including species diversity,
        observation counts, checklist activity, and temporal patterns.
        
        Args:
            region: eBird region code (e.g., "US-CA", "MX-ROO")  
            days_back: Number of days back to analyze (1-30, default: 30)
            locale: Language code for common names (default: "en")
            
        Returns:
            Dictionary containing comprehensive regional statistics
        """
        try:
            # Get recent observations for statistical analysis
            obs_endpoint = f"/data/obs/{region}/recent"
            obs_params = {
                "back": min(max(days_back, 1), 30),
                "includeProvisional": True,
                "maxResults": 10000,  # Get comprehensive data
                "fmt": "json",
                "locale": locale
            }
            
            observations = await self.make_request(obs_endpoint, obs_params)
            
            # Get region info for context
            region_info = await self.get_region_info(region, name_format="detailed")
            
            # Calculate comprehensive statistics
            unique_species = set()
            unique_locations = set()
            unique_checklists = set()
            unique_observers = set()
            daily_activity = {}
            species_frequency = {}
            location_activity = {}
            
            for obs in observations:
                # Species diversity
                species_code = obs.get("speciesCode", "")
                if species_code:
                    unique_species.add(species_code)
                    species_frequency[species_code] = species_frequency.get(species_code, 0) + 1
                
                # Location activity
                location_id = obs.get("locId", "")
                if location_id:
                    unique_locations.add(location_id)
                    location_activity[location_id] = location_activity.get(location_id, 0) + 1
                
                # Checklist and observer tracking
                checklist_id = obs.get("subId", "")
                if checklist_id:
                    unique_checklists.add(checklist_id)
                
                observer_id = obs.get("userDisplayName", obs.get("obsDt", ""))  # Fallback to date if no user
                if observer_id:
                    unique_observers.add(observer_id)
                
                # Daily activity pattern
                obs_date = obs.get("obsDt", "")[:10]  # Extract date part (YYYY-MM-DD)
                if obs_date:
                    daily_activity[obs_date] = daily_activity.get(obs_date, 0) + 1
            
            # Calculate derived statistics
            avg_daily_observations = sum(daily_activity.values()) / max(len(daily_activity), 1)
            most_active_location = max(location_activity.items(), key=lambda x: x[1]) if location_activity else ("", 0)
            most_common_species = max(species_frequency.items(), key=lambda x: x[1]) if species_frequency else ("", 0)
            
            statistics = {
                "region_info": region_info,
                "analysis_period": {
                    "days_back": days_back,
                    "total_days_with_activity": len(daily_activity)
                },
                "diversity_metrics": {
                    "total_species": len(unique_species),
                    "total_observations": len(observations),
                    "species_list": list(unique_species),
                    "most_common_species": {
                        "species_code": most_common_species[0],
                        "observation_count": most_common_species[1]
                    }
                },
                "activity_metrics": {
                    "unique_locations": len(unique_locations),
                    "unique_checklists": len(unique_checklists),
                    "estimated_observers": len(unique_observers),
                    "avg_daily_observations": round(avg_daily_observations, 1),
                    "most_active_location": {
                        "location_id": most_active_location[0],
                        "observation_count": most_active_location[1]
                    }
                },
                "temporal_patterns": {
                    "daily_activity": daily_activity,
                    "peak_activity_date": max(daily_activity.items(), key=lambda x: x[1])[0] if daily_activity else "",
                    "total_active_days": len(daily_activity)
                }
            }
            
            logger.info(f"Generated comprehensive statistics for {region}: {len(unique_species)} species, {len(observations)} observations")
            return statistics
            
        except EBirdAPIError as e:
            logger.error(f"Failed to get regional statistics for {region}: {e}")
            raise

    async def get_subregions(
        self,
        region_code: str,
        region_type: str = "subnational1"
    ) -> List[Dict[str, Any]]:
        """
        Get list of subregions (e.g., counties, states) within a region.
        
        Args:
            region_code: eBird region code (e.g., "US", "US-CA")
            region_type: Type of subregions to return:
                - "country" - Countries (for world)
                - "subnational1" - States/provinces (for countries)
                - "subnational2" - Counties/districts (for states)
                
        Returns:
            List of subregion objects with codes and names
            
        Raises:
            EBirdAPIError: For API errors with descriptive messages
        """
        try:
            endpoint = f"/ref/region/list/{region_type}/{region_code}"
            
            logger.info(f"Fetching {region_type} subregions for {region_code}")
            response = await self.make_request(endpoint)
            
            if not isinstance(response, list):
                logger.warning(f"Unexpected response format for subregions: {type(response)}")
                return []
                
            logger.info(f"Retrieved {len(response)} subregions for {region_code}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to get subregions for {region_code}: {e}")
            raise EBirdAPIError(f"Subregions lookup failed: {str(e)}")

    async def get_adjacent_regions(
        self,
        region_code: str
    ) -> List[Dict[str, Any]]:
        """
        Get adjacent/neighboring regions for cross-border planning.
        Since eBird doesn't have a direct adjacent regions endpoint,
        this method uses geographic logic and regional hierarchies.
        
        Args:
            region_code: eBird region code (e.g., "US-CA", "MX-BCN")
                
        Returns:
            List of adjacent region objects with codes and names
            
        Raises:
            EBirdAPIError: For API errors with descriptive messages
        """
        try:
            logger.info(f"Determining adjacent regions for {region_code}")
            
            # Define known adjacent regions for common areas
            adjacent_map = {
                # US States
                "US-CA": [{"code": "US-NV", "name": "Nevada"}, {"code": "US-OR", "name": "Oregon"}, {"code": "US-AZ", "name": "Arizona"}, {"code": "MX-BCN", "name": "Baja California Norte"}],
                "US-TX": [{"code": "US-NM", "name": "New Mexico"}, {"code": "US-OK", "name": "Oklahoma"}, {"code": "US-AR", "name": "Arkansas"}, {"code": "US-LA", "name": "Louisiana"}, {"code": "MX-COA", "name": "Coahuila"}, {"code": "MX-CHH", "name": "Chihuahua"}, {"code": "MX-TAM", "name": "Tamaulipas"}],
                "US-FL": [{"code": "US-GA", "name": "Georgia"}, {"code": "US-AL", "name": "Alabama"}],
                "US-NY": [{"code": "US-VT", "name": "Vermont"}, {"code": "US-MA", "name": "Massachusetts"}, {"code": "US-CT", "name": "Connecticut"}, {"code": "US-NJ", "name": "New Jersey"}, {"code": "US-PA", "name": "Pennsylvania"}, {"code": "CA-ON", "name": "Ontario"}],
                # Mexican States
                "MX-BCN": [{"code": "US-CA", "name": "California"}, {"code": "MX-SON", "name": "Sonora"}],
                "MX-SON": [{"code": "US-AZ", "name": "Arizona"}, {"code": "MX-BCN", "name": "Baja California Norte"}, {"code": "MX-CHH", "name": "Chihuahua"}],
                # Canadian Provinces
                "CA-ON": [{"code": "US-NY", "name": "New York"}, {"code": "US-MI", "name": "Michigan"}, {"code": "US-MN", "name": "Minnesota"}, {"code": "CA-QC", "name": "Quebec"}, {"code": "CA-MB", "name": "Manitoba"}],
                "CA-BC": [{"code": "US-WA", "name": "Washington"}, {"code": "US-AK", "name": "Alaska"}, {"code": "CA-AB", "name": "Alberta"}]
            }
            
            if region_code in adjacent_map:
                adjacent_regions = adjacent_map[region_code]
                logger.info(f"Found {len(adjacent_regions)} adjacent regions for {region_code}")
                return adjacent_regions
            else:
                # For regions not in our map, try to find parent region and suggest subregions
                parts = region_code.split('-')
                if len(parts) == 2:
                    country_code = parts[0]
                    try:
                        # Get all regions in the same country as potential neighbors
                        same_country_regions = await self.get_subregions(country_code, "subnational1")
                        # Filter out the current region and limit to reasonable number
                        potential_adjacent = [r for r in same_country_regions if r.get('code') != region_code][:5]
                        
                        logger.info(f"Generated {len(potential_adjacent)} potential adjacent regions for {region_code}")
                        return potential_adjacent
                    except:
                        pass
                
                logger.info(f"No adjacent regions data available for {region_code}")
                return [{"code": "unknown", "name": "Adjacent regions data not available for this region"}]
            
        except Exception as e:
            logger.error(f"Failed to get adjacent regions for {region_code}: {e}")
            raise EBirdAPIError(f"Adjacent regions lookup failed: {str(e)}")

    async def get_elevation_data(
        self,
        lat: float,
        lng: float,
        radius_km: int = EBIRD_RADIUS_KM_DEFAULT
    ) -> Dict[str, Any]:
        """
        Get elevation information for birding locations.
        
        Args:
            lat: Latitude coordinate
            lng: Longitude coordinate  
            radius_km: Search radius in kilometers (default: 25, max: 50)
                
        Returns:
            Elevation data including min/max/avg elevation and habitat zones
            
        Raises:
            EBirdAPIError: For API errors with descriptive messages
        """
        try:
            # Validate coordinates
            if not (LATITUDE_MIN <= lat <= LATITUDE_MAX):
                raise ValueError(f"Invalid latitude: {lat}")
            if not (LONGITUDE_MIN <= lng <= LONGITUDE_MAX):
                raise ValueError(f"Invalid longitude: {lng}")
                
            # Normalize radius
            radius_km = min(radius_km, EBIRD_RADIUS_KM_MAX)
            
            # ⚠️ IMPORTANT: eBird API does not provide elevation data
            # This method returns PLACEHOLDER DATA for demonstration purposes only
            # In production, you should integrate with a proper elevation API service
            # such as:
            # - Google Elevation API
            # - OpenTopoData API
            # - USGS Elevation Point Query Service
            # - Mapbox Terrain API
            
            logger.warning("Using PLACEHOLDER elevation data - integrate with real elevation API for production use")
            
            # PLACEHOLDER: Simple elevation estimation
            # Real implementation would query an elevation service
            estimated_elevation = DEFAULT_ELEVATION_M  # Default placeholder value
            habitat_zones = {'general', 'mixed'}
            
            # Add warning to output that this is not real data
            elevation_warning = "PLACEHOLDER DATA - Not from real elevation service"
            
            elevation_stats = {
                "min_elevation": estimated_elevation - 50 if estimated_elevation else None,
                "max_elevation": estimated_elevation + 100 if estimated_elevation else None,
                "avg_elevation": estimated_elevation,
                "elevation_range": 150 if estimated_elevation else None
            }
            
            result = {
                "latitude": lat,
                "longitude": lng,
                "radius_km": radius_km,
                "elevation_stats": elevation_stats,
                "habitat_zones": list(habitat_zones),
                "hotspot_count": 0,  # Not using actual hotspot data
                "warning": elevation_warning,
                "implementation_note": "Replace with real elevation API service for production use"
            }
            
            logger.info(f"Generated elevation analysis for ({lat}, {lng}): estimated elevation {estimated_elevation}m")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get elevation data for ({lat}, {lng}): {e}")
            raise EBirdAPIError(f"Elevation data lookup failed: {str(e)}")


class EBirdAsyncRegionsClient(EBirdAsyncBaseClient, EBirdAsyncRegionsMixin):
    """Complete async eBird API client for region and geographic-related endpoints."""
    pass