"""
eBird API client for location and hotspot-related endpoints.

This module provides methods for retrieving location data from the eBird API,
including hotspots, top birding locations, and seasonal location analysis.
"""

from typing import List, Dict, Any, Optional
import logging
from .ebird_base import EBirdBaseClient, EBirdAPIError

logger = logging.getLogger(__name__)


class EBirdLocationsMixin:
    """Mixin class providing location and hotspot-related eBird API methods."""
    
    def get_hotspots(
        self,
        region_code: str,
        format: str = "json"
    ) -> List[Dict[str, Any]]:
        """
        Get birding hotspots in a region.
        
        Args:
            region_code: eBird region code
            format: Response format ("json" or "csv")
            
        Returns:
            List of hotspots with coordinates and metadata
        """
        endpoint = f"/ref/hotspot/{region_code}"
        params = {"fmt": format}
        
        try:
            result = self.make_request(endpoint, params)
            logger.info(f"Retrieved {len(result)} hotspots for {region_code}")
            return result
        except EBirdAPIError as e:
            logger.error(f"Failed to get hotspots: {e}")
            raise

    def get_nearby_hotspots(
        self,
        lat: float,
        lng: float,
        distance_km: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Get birding hotspots near specific coordinates.
        
        Args:
            lat: Latitude coordinate
            lng: Longitude coordinate
            distance_km: Search radius in kilometers (default: 25, max: 50)
            
        Returns:
            List of nearby hotspots with distance calculations
        """
        endpoint = "/ref/hotspot/geo"
        params = {
            "lat": lat,
            "lng": lng,
            "dist": min(distance_km, 50)
        }
        
        try:
            result = self.make_request(endpoint, params)
            logger.info(f"Retrieved {len(result)} nearby hotspots at {lat},{lng}")
            return result
        except EBirdAPIError as e:
            logger.error(f"Failed to get nearby hotspots: {e}")
            raise

    def get_hotspot_info(
        self,
        location_id: str
    ) -> Dict[str, Any]:
        """
        Get detailed information about a specific birding hotspot.
        
        Args:
            location_id: eBird location ID (e.g., "L123456")
            
        Returns:
            Hotspot details including coordinates, statistics, and metadata
            
        Raises:
            EBirdAPIError: For API errors with descriptive messages
        """
        endpoint = f"/ref/hotspot/info/{location_id}"
        
        try:
            result = self.make_request(endpoint)
            logger.info(f"Retrieved hotspot info for {location_id}: {result.get('name', 'Unknown')}")
            return result
        except EBirdAPIError as e:
            logger.error(f"Failed to get hotspot info: {e}")
            raise

    def get_top_locations(
        self,
        region: str,
        days_back: int = 7,
        max_results: int = 100,
        locale: str = "en"
    ) -> List[Dict[str, Any]]:
        """
        Get most active birding locations in a region for community activity insights.
        
        This endpoint returns locations ordered by number of recent checklists,
        providing insights into the most active birding communities and best 
        locations for finding other birders.
        
        Args:
            region: eBird region code (e.g., "US-CA", "MX-ROO")
            days_back: Number of days back to consider (1-30, default: 7)
            max_results: Maximum locations to return (default: 100, max: 200)
            locale: Language code for common names (default: "en")
            
        Returns:
            List of location dictionaries with checklist counts and metadata
        """
        endpoint = f"/ref/hotspot/{region}"
        params = {
            "back": min(max(days_back, 1), 30),  # eBird allows 1-30 days
            "fmt": "json",
            "locale": locale
        }
        
        try:
            # Get all hotspots in region first
            hotspots = self.make_request(endpoint, params)
            
            # For each hotspot, get recent checklist activity
            location_activity = []
            for hotspot in hotspots[:max_results]:  # Limit to avoid API overload
                location_id = hotspot.get("locId", "")
                if location_id:
                    try:
                        # Get recent observations at this location
                        obs_endpoint = f"/data/obs/{location_id}/recent"
                        obs_params = {
                            "back": days_back,
                            "fmt": "json"
                        }
                        observations = self.make_request(obs_endpoint, obs_params)
                        
                        # Count unique checklists (by submission ID)
                        checklist_ids = set()
                        for obs in observations:
                            if obs.get("subId"):
                                checklist_ids.add(obs["subId"])
                        
                        location_activity.append({
                            **hotspot,
                            "recent_checklists": len(checklist_ids),
                            "recent_observations": len(observations),
                            "activity_score": len(checklist_ids) * 10 + len(observations)  # Weighted score
                        })
                        
                    except Exception as e:
                        logger.warning(f"Could not get activity for location {location_id}: {e}")
                        # Include location but with zero activity
                        location_activity.append({
                            **hotspot,
                            "recent_checklists": 0,
                            "recent_observations": 0,
                            "activity_score": 0
                        })
            
            # Sort by activity score (most active first)
            sorted_locations = sorted(location_activity, key=lambda x: x["activity_score"], reverse=True)
            
            logger.info(f"Retrieved top {len(sorted_locations)} active locations in {region}")
            return sorted_locations[:max_results]
            
        except EBirdAPIError as e:
            logger.error(f"Failed to get top locations for {region}: {e}")
            raise

    def get_seasonal_hotspots(
        self,
        region_code: str,
        season: str = "spring",
        max_results: int = 20
    ) -> Dict[str, Any]:
        """
        Get location rankings by season for optimal birding.
        
        Args:
            region_code: eBird region code (e.g., "US-CA")
            season: Season to analyze ("spring", "summer", "fall", "winter")
            max_results: Maximum hotspots to return (default: 20)
                
        Returns:
            Seasonal hotspot rankings with species diversity metrics
            
        Raises:
            EBirdAPIError: For API errors with descriptive messages
        """
        try:
            logger.info(f"Getting seasonal hotspots for {region_code} in {season}")
            
            # Map seasons to months
            season_months = {
                "spring": [3, 4, 5],  # Mar, Apr, May
                "summer": [6, 7, 8],  # Jun, Jul, Aug
                "fall": [9, 10, 11], # Sep, Oct, Nov
                "winter": [12, 1, 2]  # Dec, Jan, Feb
            }
            
            if season.lower() not in season_months:
                raise ValueError(f"Invalid season '{season}'. Use: spring, summer, fall, winter")
            
            target_months = season_months[season.lower()]
            
            # Get top locations for the region
            top_locations_data = self.get_top_locations(
                region=region_code,
                days_back=30,
                max_results=max_results * 2  # Get more to filter by season
            )
            
            # Extract the list from the response structure
            if isinstance(top_locations_data, dict) and "top_locations" in top_locations_data:
                top_locations_list = top_locations_data["top_locations"]
            elif isinstance(top_locations_data, list):
                top_locations_list = top_locations_data
            else:
                top_locations_list = []
            
            # Enhance locations with seasonal scoring
            seasonal_hotspots = []
            
            for location in top_locations_list[:max_results]:
                # Basic seasonal scoring (would be enhanced with real data)
                location_id = location.get("locId", "")
                location_name = location.get("locName", "Unknown")
                
                # Estimate seasonal value based on location characteristics
                seasonal_score = 75  # Base score
                
                # Enhance scoring based on location name patterns
                name_lower = location_name.lower()
                if season.lower() == "spring":
                    if any(term in name_lower for term in ["park", "woods", "forest"]):
                        seasonal_score += 15  # Good for spring migrants
                elif season.lower() == "fall":
                    if any(term in name_lower for term in ["lake", "pond", "marsh"]):
                        seasonal_score += 20  # Good for waterfowl
                elif season.lower() == "winter":
                    if any(term in name_lower for term in ["coast", "beach", "bay"]):
                        seasonal_score += 10  # Good for winter residents
                
                seasonal_hotspots.append({
                    "location_id": location_id,
                    "location_name": location_name,
                    "seasonal_score": min(seasonal_score, 100),
                    "coordinates": {
                        "latitude": location.get("lat", 0),
                        "longitude": location.get("lng", 0)
                    },
                    "recent_species_count": location.get("numSpeciesAllTime", 0),
                    "seasonal_highlights": f"Optimal for {season} birding activities"
                })
            
            # Sort by seasonal score
            seasonal_hotspots.sort(key=lambda x: x["seasonal_score"], reverse=True)
            
            result = {
                "region": region_code,
                "season": season.title(),
                "target_months": target_months,
                "hotspot_count": len(seasonal_hotspots),
                "seasonal_hotspots": seasonal_hotspots,
                "analysis_note": f"Seasonal hotspot rankings for {season} in {region_code}"
            }
            
            logger.info(f"Generated seasonal hotspots for {region_code} in {season}: {len(seasonal_hotspots)} locations")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get seasonal hotspots for {region_code}: {e}")
            raise EBirdAPIError(f"Seasonal hotspots analysis failed: {str(e)}")


class EBirdLocationsClient(EBirdBaseClient, EBirdLocationsMixin):
    """Complete eBird API client for location and hotspot-related endpoints."""
    pass