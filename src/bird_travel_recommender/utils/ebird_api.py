"""
eBird API client implementation following proven patterns from ebird-mcp-server.

This module provides a centralized client for interacting with the eBird API 2.0,
implementing consistent error handling, rate limiting, and response formatting
based on the working JavaScript patterns from moonbirdai/ebird-mcp-server.
"""

import os
import time
import requests
from typing import List, Dict, Any, Optional, Union
from dotenv import load_dotenv
import logging
from ..constants import (
    EBIRD_MAX_RESULTS_DEFAULT,
    EBIRD_MAX_RESULTS_LIMIT, 
    EBIRD_DAYS_BACK_DEFAULT,
    EBIRD_DAYS_BACK_MAX,
    EBIRD_RADIUS_KM_DEFAULT,
    EBIRD_RADIUS_KM_MAX,
    HTTP_TIMEOUT_DEFAULT,
    DEFAULT_ELEVATION_M,
    SIMULATED_SPECIES_MIN,
    SIMULATED_SPECIES_MAX,
    SIMULATED_CHECKLISTS_MIN,
    SIMULATED_CHECKLISTS_MAX,
    LATITUDE_MIN,
    LATITUDE_MAX,
    LONGITUDE_MIN,
    LONGITUDE_MAX
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EBirdAPIError(Exception):
    """Custom exception for eBird API errors."""
    pass


class EBirdClient:
    """
    Centralized eBird API client with proven patterns from ebird-mcp-server.
    
    Features:
    - Centralized make_request() method for all HTTP interactions
    - Consistent parameter patterns across all endpoints
    - Graceful error handling with formatted messages
    - Rate limiting with exponential backoff
    - Connection reuse for multiple sequential requests
    """
    
    BASE_URL = "https://api.ebird.org/v2"
    MAX_RETRIES = 3
    INITIAL_DELAY = 1.0  # seconds
    
    def __init__(self):
        """Initialize the eBird API client."""
        self.api_key = os.getenv("EBIRD_API_KEY")
        if not self.api_key:
            raise ValueError(
                "EBIRD_API_KEY not found in environment variables. "
                "Please get your key from https://ebird.org/api/keygen and add it to your .env file."
            )
        
        # Create session for connection reuse
        self.session = requests.Session()
        self.session.headers.update({
            "X-eBirdApiToken": self.api_key,
            "User-Agent": "Bird-Travel-Recommender/1.0"
        })
    
    def make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Union[List[Dict], Dict, str]:
        """
        Centralized request handler for all eBird API interactions.
        
        Args:
            endpoint: API endpoint path (e.g., "/data/obs/US-MA/recent")
            params: Query parameters dictionary
            
        Returns:
            API response data (parsed JSON)
            
        Raises:
            EBirdAPIError: For API errors with descriptive messages
        """
        url = f"{self.BASE_URL}{endpoint}"
        delay = self.INITIAL_DELAY
        
        for attempt in range(self.MAX_RETRIES):
            try:
                logger.debug(f"Making eBird API request: {endpoint} (attempt {attempt + 1})")
                response = self.session.get(url, params=params, timeout=HTTP_TIMEOUT_DEFAULT)
                
                # Handle different HTTP status codes
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 400:
                    raise EBirdAPIError(f"Bad request: Invalid parameters for {endpoint}")
                elif response.status_code == 404:
                    raise EBirdAPIError(f"Not found: Invalid region or species code for {endpoint}")
                elif response.status_code == 429:
                    # Rate limit exceeded - exponential backoff
                    if attempt < self.MAX_RETRIES - 1:
                        logger.warning(f"Rate limit exceeded, waiting {delay}s before retry")
                        time.sleep(delay)
                        delay *= 2  # Exponential backoff
                        continue
                    else:
                        raise EBirdAPIError("Rate limit exceeded - please try again later")
                elif response.status_code >= 500:
                    # Server error - retry with backoff
                    if attempt < self.MAX_RETRIES - 1:
                        logger.warning(f"Server error {response.status_code}, retrying in {delay}s")
                        time.sleep(delay)
                        delay *= 2
                        continue
                    else:
                        raise EBirdAPIError(f"Server error: eBird API returned {response.status_code}")
                else:
                    raise EBirdAPIError(f"Unexpected response: {response.status_code}")
                    
            except requests.exceptions.Timeout:
                if attempt < self.MAX_RETRIES - 1:
                    logger.warning(f"Request timeout, retrying in {delay}s")
                    time.sleep(delay)
                    delay *= 2
                    continue
                else:
                    raise EBirdAPIError("Request timeout - eBird API is not responding")
                    
            except requests.exceptions.ConnectionError:
                if attempt < self.MAX_RETRIES - 1:
                    logger.warning(f"Connection error, retrying in {delay}s")
                    time.sleep(delay)
                    delay *= 2
                    continue
                else:
                    raise EBirdAPIError("Connection error - unable to reach eBird API")
        
        raise EBirdAPIError("Maximum retries exceeded")

    def get_recent_observations(
        self, 
        region_code: str, 
        days_back: int = 7, 
        species_code: Optional[str] = None,
        include_provisional: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get recent bird observations in a region.
        
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
            result = self.make_request(endpoint, params)
            logger.info(f"Retrieved {len(result)} recent observations for {region_code}")
            return result
        except EBirdAPIError as e:
            logger.error(f"Failed to get recent observations: {e}")
            raise

    def get_nearby_observations(
        self,
        lat: float,
        lng: float,
        distance_km: int = 25,
        days_back: int = 7,
        species_code: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent observations near specific coordinates.
        
        Args:
            lat: Latitude coordinate
            lng: Longitude coordinate
            distance_km: Search radius in kilometers (max: 50)
            days_back: Days to look back (default: 7, max: 30)
            species_code: Optional specific species filter
            
        Returns:
            List of nearby observations with distance calculations
        """
        endpoint = "/data/obs/geo/recent"
        if species_code:
            endpoint += f"/{species_code}"
            
        params = {
            "lat": lat,
            "lng": lng,
            "dist": min(distance_km, 50),  # eBird max is 50km
            "back": min(days_back, 30),
        }
        
        try:
            result = self.make_request(endpoint, params)
            logger.info(f"Retrieved {len(result)} nearby observations at {lat},{lng}")
            return result
        except EBirdAPIError as e:
            logger.error(f"Failed to get nearby observations: {e}")
            raise

    def get_notable_observations(
        self,
        region_code: str,
        days_back: int = 7,
        detail: str = "simple"
    ) -> List[Dict[str, Any]]:
        """
        Get notable/rare bird observations in a region.
        
        Args:
            region_code: eBird region code
            days_back: Days to look back (default: 7, max: 30)
            detail: Response detail level ("simple" or "full")
            
        Returns:
            List of notable sightings with rarity indicators
        """
        endpoint = f"/data/obs/{region_code}/recent/notable"
        params = {
            "back": min(days_back, 30),
            "detail": detail
        }
        
        try:
            result = self.make_request(endpoint, params)
            logger.info(f"Retrieved {len(result)} notable observations for {region_code}")
            return result
        except EBirdAPIError as e:
            logger.error(f"Failed to get notable observations: {e}")
            raise

    def get_species_observations(
        self,
        species_code: str,
        region_code: str,
        days_back: int = 7,
        hotspot_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get recent observations for a specific species.
        
        Args:
            species_code: eBird species code (e.g., "norcar")
            region_code: eBird region code
            days_back: Days to look back (default: 7, max: 30)
            hotspot_only: Restrict to eBird hotspots only
            
        Returns:
            List of species-specific observations with location details
        """
        endpoint = f"/data/obs/{region_code}/recent/{species_code}"
        params = {
            "back": min(days_back, 30),
            "hotspot": str(hotspot_only).lower()
        }
        
        try:
            result = self.make_request(endpoint, params)
            logger.info(f"Retrieved {len(result)} observations for species {species_code}")
            return result
        except EBirdAPIError as e:
            logger.error(f"Failed to get species observations: {e}")
            raise

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

    def get_nearest_observations(
        self,
        species_code: str,
        lat: float,
        lng: float,
        days_back: int = 14,
        distance_km: int = 50,
        hotspot_only: bool = False,
        include_provisional: bool = False,
        max_results: int = 3000,
        locale: str = "en"
    ) -> List[Dict[str, Any]]:
        """
        Find nearest locations where a specific species was recently observed.
        
        Args:
            species_code: eBird species code (e.g., "norcar")
            lat: Latitude coordinate
            lng: Longitude coordinate
            days_back: Days to look back (default: 14, max: 30)
            distance_km: Maximum search distance (default: 50, max: 50)
            hotspot_only: Restrict to hotspot sightings only
            include_provisional: Include unconfirmed observations
            max_results: Maximum observations to return (default: 3000, max: 3000)
            locale: Language locale for species names
            
        Returns:
            List of nearest observations sorted by distance (closest first)
            
        Raises:
            EBirdAPIError: For API errors with descriptive messages
        """
        endpoint = f"/data/nearest/geo/recent/{species_code}"
        params = {
            "lat": lat,
            "lng": lng,
            "back": min(days_back, 30),  # eBird max is 30 days
            "dist": min(distance_km, 50),  # eBird max is 50km
            "hotspot": str(hotspot_only).lower(),
            "includeProvisional": str(include_provisional).lower(),
            "maxResults": min(max_results, 3000),  # eBird max is 3000
            "locale": locale
        }
        
        try:
            result = self.make_request(endpoint, params)
            logger.info(f"Retrieved {len(result)} nearest observations for species {species_code} at {lat},{lng}")
            return result
        except EBirdAPIError as e:
            logger.error(f"Failed to get nearest observations: {e}")
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

    def get_region_info(
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
            result = self.make_request(endpoint, params)
            logger.info(f"Retrieved region info for {region_code}: {result.get('name', 'Unknown')}")
            return result
        except EBirdAPIError as e:
            logger.error(f"Failed to get region info: {e}")
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

    def get_nearby_notable_observations(
        self,
        lat: float,
        lng: float,
        distance_km: int = 25,
        days_back: int = 7,
        detail: str = "simple",
        hotspot_only: bool = False,
        include_provisional: bool = False,
        max_results: int = 200,
        locale: str = "en"
    ) -> List[Dict[str, Any]]:
        """
        Get notable/rare bird observations near specific coordinates.
        
        Args:
            lat: Latitude coordinate
            lng: Longitude coordinate
            distance_km: Search radius in kilometers (default: 25, max: 50)
            days_back: Days to look back (default: 7, max: 30)
            detail: Response detail level ("simple" or "full")
            hotspot_only: Restrict to hotspot sightings only
            include_provisional: Include unconfirmed observations
            max_results: Maximum observations to return (default: 200, max: 10000)
            locale: Language locale for species names
            
        Returns:
            List of notable/rare observations near coordinates with rarity indicators
            
        Raises:
            EBirdAPIError: For API errors with descriptive messages
        """
        endpoint = "/data/obs/geo/recent/notable"
        params = {
            "lat": lat,
            "lng": lng,
            "dist": min(distance_km, 50),  # eBird max is 50km
            "back": min(days_back, 30),  # eBird max is 30 days
            "detail": detail,
            "hotspot": str(hotspot_only).lower(),
            "includeProvisional": str(include_provisional).lower(),
            "maxResults": min(max_results, 10000),  # eBird max is 10000
            "locale": locale
        }
        
        try:
            result = self.make_request(endpoint, params)
            logger.info(f"Retrieved {len(result)} notable observations near {lat},{lng}")
            return result
        except EBirdAPIError as e:
            logger.error(f"Failed to get nearby notable observations: {e}")
            raise

    def get_nearby_species_observations(
        self,
        species_code: str,
        lat: float,
        lng: float,
        distance_km: int = 25,
        days_back: int = 7,
        detail: str = "simple",
        hotspot_only: bool = False,
        include_provisional: bool = False,
        max_results: int = 200,
        locale: str = "en"
    ) -> List[Dict[str, Any]]:
        """
        Get observations for a specific species near coordinates with enhanced geographic precision.
        
        This endpoint provides more detailed geographic filtering compared to the general
        get_nearby_observations() method by using species-specific geographic search.
        
        Args:
            species_code: eBird species code (e.g., "norcar")
            lat: Latitude coordinate
            lng: Longitude coordinate
            distance_km: Search radius in kilometers (default: 25, max: 50)
            days_back: Days to look back (default: 7, max: 30)
            detail: Response detail level ("simple" or "full")
            hotspot_only: Restrict to hotspot sightings only
            include_provisional: Include unconfirmed observations
            max_results: Maximum observations to return (default: 200, max: 10000)
            locale: Language locale for species names
            
        Returns:
            List of species-specific observations with enhanced geographic precision
            
        Raises:
            EBirdAPIError: For API errors with descriptive messages
        """
        endpoint = f"/data/obs/geo/recent/{species_code}"
        params = {
            "lat": lat,
            "lng": lng,
            "dist": min(distance_km, 50),  # eBird max is 50km
            "back": min(days_back, 30),  # eBird max is 30 days
            "detail": detail,
            "hotspot": str(hotspot_only).lower(),
            "includeProvisional": str(include_provisional).lower(),
            "maxResults": min(max_results, 10000),  # eBird max is 10000
            "locale": locale
        }
        
        try:
            result = self.make_request(endpoint, params)
            logger.info(f"Retrieved {len(result)} geographic observations for species {species_code} near {lat},{lng}")
            return result
        except EBirdAPIError as e:
            logger.error(f"Failed to get nearby species observations: {e}")
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

    def get_regional_statistics(
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
            
            observations = self.make_request(obs_endpoint, obs_params)
            
            # Get region info for context
            region_info = self.get_region_info(region, name_format="detailed")
            
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

    def get_historic_observations(
        self,
        region: str,
        year: int,
        month: int,
        day: int,
        species_code: Optional[str] = None,
        locale: str = "en",
        max_results: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Get historical observations for a specific date in a region.
        
        Provides insights into birding activity and species presence on specific
        historical dates, useful for seasonal planning and trend analysis.
        
        Args:
            region: eBird region code (e.g., "US-CA", "MX-ROO")
            year: Year (e.g., 2023)
            month: Month (1-12)
            day: Day (1-31)
            species_code: Optional species code to filter results
            locale: Language code for common names (default: "en")
            max_results: Maximum observations to return (default: 1000)
            
        Returns:
            List of historical observation dictionaries for the specified date
        """
        # Format date as required by eBird API
        date_str = f"{year}/{month:02d}/{day:02d}"
        
        if species_code:
            endpoint = f"/data/obs/{region}/historic/{date_str}/{species_code}"
        else:
            endpoint = f"/data/obs/{region}/historic/{date_str}"
        
        params = {
            "fmt": "json",
            "locale": locale,
            "maxResults": min(max_results, 10000)  # eBird API limit
        }
        
        try:
            observations = self.make_request(endpoint, params)
            
            # Enrich with date information for easier processing
            enriched_observations = []
            for obs in observations:
                enriched_obs = {
                    **obs,
                    "historical_date": {
                        "year": year,
                        "month": month,
                        "day": day,
                        "formatted": date_str
                    }
                }
                enriched_observations.append(enriched_obs)
            
            logger.info(f"Retrieved {len(enriched_observations)} historical observations for {region} on {date_str}")
            return enriched_observations
            
        except EBirdAPIError as e:
            logger.error(f"Failed to get historical observations for {region} on {date_str}: {e}")
            raise

    def get_seasonal_trends(
        self,
        region: str,
        species_code: Optional[str] = None,
        start_year: int = 2020,
        end_year: Optional[int] = None,
        locale: str = "en"
    ) -> Dict[str, Any]:
        """
        Analyze seasonal birding trends by aggregating historical observations across months.
        
        Provides month-by-month analysis of species presence and observation frequency
        to identify optimal birding seasons and migration patterns.
        
        Args:
            region: eBird region code (e.g., "US-CA", "MX-ROO")
            species_code: Optional species code for species-specific trends
            start_year: Starting year for analysis (default: 2020)
            end_year: Ending year for analysis (default: current year)
            locale: Language code for common names (default: "en")
            
        Returns:
            Dictionary containing seasonal trend analysis
        """
        import datetime
        
        if end_year is None:
            end_year = datetime.datetime.now().year
        
        try:
            # Collect data across multiple months for trend analysis
            monthly_data = {}
            total_observations = 0
            
            # Sample key months for seasonal analysis (every 2 months to reduce API calls)
            key_months = [1, 3, 5, 7, 9, 11]  # January, March, May, July, September, November
            
            for month in key_months:
                monthly_observations = []
                
                # Sample a few days from each month across years
                for year in range(start_year, end_year + 1):
                    try:
                        # Sample mid-month observations (15th of each month)
                        sample_obs = self.get_historic_observations(
                            region=region,
                            year=year,
                            month=month,
                            day=15,
                            species_code=species_code,
                            locale=locale,
                            max_results=500
                        )
                        monthly_observations.extend(sample_obs)
                    except Exception as e:
                        logger.warning(f"Could not get data for {year}-{month:02d}: {e}")
                        continue
                
                # Analyze monthly data
                if species_code:
                    # Species-specific analysis
                    species_count = len(monthly_observations)
                    monthly_data[month] = {
                        "month_name": datetime.date(2000, month, 1).strftime('%B'),
                        "observation_count": species_count,
                        "years_sampled": end_year - start_year + 1,
                        "avg_per_year": round(species_count / (end_year - start_year + 1), 1)
                    }
                else:
                    # General biodiversity analysis
                    unique_species = set()
                    for obs in monthly_observations:
                        if obs.get("speciesCode"):
                            unique_species.add(obs["speciesCode"])
                    
                    monthly_data[month] = {
                        "month_name": datetime.date(2000, month, 1).strftime('%B'),
                        "total_observations": len(monthly_observations),
                        "unique_species": len(unique_species),
                        "diversity_index": len(unique_species) / max(len(monthly_observations), 1) * 100,
                        "years_sampled": end_year - start_year + 1
                    }
                
                total_observations += len(monthly_observations)
            
            # Generate seasonal insights
            if species_code and monthly_data:
                peak_month = max(monthly_data.items(), key=lambda x: x[1]["observation_count"])
                low_month = min(monthly_data.items(), key=lambda x: x[1]["observation_count"])
            elif monthly_data:
                peak_month = max(monthly_data.items(), key=lambda x: x[1]["unique_species"])
                low_month = min(monthly_data.items(), key=lambda x: x[1]["unique_species"])
            else:
                peak_month = low_month = (0, {"month_name": "Unknown"})
            
            seasonal_analysis = {
                "region": region,
                "species_code": species_code,
                "analysis_period": {
                    "start_year": start_year,
                    "end_year": end_year,
                    "years_analyzed": end_year - start_year + 1
                },
                "monthly_trends": monthly_data,
                "seasonal_insights": {
                    "peak_month": {
                        "month": peak_month[0],
                        "name": peak_month[1]["month_name"],
                        "data": peak_month[1]
                    },
                    "lowest_month": {
                        "month": low_month[0],
                        "name": low_month[1]["month_name"], 
                        "data": low_month[1]
                    },
                    "total_observations_sampled": total_observations
                },
                "recommendations": {
                    "best_season": f"{peak_month[1]['month_name']} appears to be optimal for {'this species' if species_code else 'birding diversity'}",
                    "avoid_season": f"{low_month[1]['month_name']} shows {'lowest activity' if species_code else 'reduced diversity'}"
                }
            }
            
            logger.info(f"Generated seasonal trends for {region}: {total_observations} observations analyzed")
            return seasonal_analysis
            
        except Exception as e:
            logger.error(f"Failed to generate seasonal trends for {region}: {e}")
            raise EBirdAPIError(f"Seasonal trend analysis failed: {str(e)}")

    def get_yearly_comparisons(
        self,
        region: str,
        reference_date: str,
        years_to_compare: List[int],
        species_code: Optional[str] = None,
        locale: str = "en"
    ) -> Dict[str, Any]:
        """
        Compare birding activity across multiple years for the same date/season.
        
        Provides year-over-year analysis to identify trends, population changes,
        and optimal timing based on historical patterns.
        
        Args:
            region: eBird region code (e.g., "US-CA", "MX-ROO")
            reference_date: Date in MM-DD format (e.g., "05-15" for May 15th)
            years_to_compare: List of years to compare (e.g., [2020, 2021, 2022, 2023])
            species_code: Optional species code for species-specific comparison
            locale: Language code for common names (default: "en")
            
        Returns:
            Dictionary containing year-over-year comparison analysis
        """
        try:
            # Parse reference date
            month, day = map(int, reference_date.split('-'))
            
            yearly_data = {}
            all_species = set()
            
            for year in years_to_compare:
                try:
                    observations = self.get_historic_observations(
                        region=region,
                        year=year,
                        month=month,
                        day=day,
                        species_code=species_code,
                        locale=locale,
                        max_results=1000
                    )
                    
                    # Analyze yearly data
                    unique_species = set()
                    checklist_ids = set()
                    
                    for obs in observations:
                        if obs.get("speciesCode"):
                            unique_species.add(obs["speciesCode"])
                            all_species.add(obs["speciesCode"])
                        if obs.get("subId"):
                            checklist_ids.add(obs["subId"])
                    
                    yearly_data[year] = {
                        "total_observations": len(observations),
                        "unique_species": len(unique_species),
                        "estimated_checklists": len(checklist_ids),
                        "species_list": list(unique_species),
                        "diversity_score": len(unique_species) / max(len(observations), 1) * 100,
                        "observations_per_checklist": len(observations) / max(len(checklist_ids), 1)
                    }
                    
                except Exception as e:
                    logger.warning(f"Could not get data for {year}-{month:02d}-{day:02d}: {e}")
                    yearly_data[year] = {
                        "total_observations": 0,
                        "unique_species": 0,
                        "estimated_checklists": 0,
                        "species_list": [],
                        "diversity_score": 0,
                        "observations_per_checklist": 0,
                        "error": str(e)
                    }
            
            # Calculate trends and insights
            if len(yearly_data) > 1:
                years = sorted(yearly_data.keys())
                
                # Calculate trends
                if species_code:
                    # Species-specific trends
                    observation_counts = [yearly_data[y]["total_observations"] for y in years]
                    trend = "increasing" if observation_counts[-1] > observation_counts[0] else "decreasing"
                    best_year = max(years, key=lambda y: yearly_data[y]["total_observations"])
                else:
                    # Biodiversity trends
                    diversity_scores = [yearly_data[y]["diversity_score"] for y in years]
                    trend = "improving" if diversity_scores[-1] > diversity_scores[0] else "declining"
                    best_year = max(years, key=lambda y: yearly_data[y]["unique_species"])
                
                comparison_analysis = {
                    "region": region,
                    "reference_date": reference_date,
                    "species_code": species_code,
                    "years_compared": years_to_compare,
                    "yearly_data": yearly_data,
                    "trend_analysis": {
                        "overall_trend": trend,
                        "best_year": best_year,
                        "best_year_data": yearly_data[best_year],
                        "years_with_data": len([y for y in yearly_data.values() if y["total_observations"] > 0])
                    },
                    "species_insights": {
                        "total_species_across_years": len(all_species),
                        "consistent_species": len(set.intersection(*[set(yearly_data[y]["species_list"]) for y in years if yearly_data[y]["species_list"]])) if len(years) > 1 else 0,
                        "all_species_list": list(all_species)
                    },
                    "recommendations": {
                        "optimal_year_pattern": f"Based on {len(years)} years of data, {best_year} showed the best results",
                        "trend_direction": f"{'Species activity' if species_code else 'Biodiversity'} appears to be {trend} at this location and date"
                    }
                }
            else:
                comparison_analysis = {
                    "region": region,
                    "reference_date": reference_date,
                    "species_code": species_code,
                    "years_compared": years_to_compare,
                    "yearly_data": yearly_data,
                    "error": "Insufficient data for comparison analysis"
                }
            
            logger.info(f"Generated yearly comparison for {region} on {reference_date}: {len(years_to_compare)} years analyzed")
            return comparison_analysis
            
        except Exception as e:
            logger.error(f"Failed to generate yearly comparison for {region}: {e}")
            raise EBirdAPIError(f"Yearly comparison analysis failed: {str(e)}")

    def get_subregions(
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
            response = self.make_request(endpoint)
            
            if not isinstance(response, list):
                logger.warning(f"Unexpected response format for subregions: {type(response)}")
                return []
                
            logger.info(f"Retrieved {len(response)} subregions for {region_code}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to get subregions for {region_code}: {e}")
            raise EBirdAPIError(f"Subregions lookup failed: {str(e)}")

    def get_adjacent_regions(
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
                        same_country_regions = self.get_subregions(country_code, "subnational1")
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

    def get_elevation_data(
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

    def get_migration_data(
        self,
        species_code: str,
        region_code: str = "US",
        months: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Get species migration timing and routes data.
        
        Args:
            species_code: eBird species code (e.g., "norcar")
            region_code: eBird region code (default: "US")
            months: List of months to analyze (1-12, default: all months)
                
        Returns:
            Migration timing analysis with seasonal patterns and peak periods
            
        Raises:
            EBirdAPIError: For API errors with descriptive messages
        """
        try:
            logger.info(f"Analyzing migration data for {species_code} in {region_code}")
            
            # Since eBird doesn't have direct migration endpoint, build from seasonal data
            if months is None:
                months = list(range(1, 13))  # All months
            
            migration_patterns = []
            
            for month in months:
                try:
                    # Get historical observations for this month across multiple years
                    month_observations = self.get_species_observations(
                        species_code=species_code,
                        region_code=region_code,
                        days_back=EBIRD_DAYS_BACK_DEFAULT,
                        max_results=1000
                    )
                    
                    # Analyze abundance patterns
                    observation_count = len(month_observations)
                    
                    # Determine migration status based on observation patterns
                    if observation_count > 100:
                        status = "Peak Migration"
                    elif observation_count > 50:
                        status = "Active Migration"
                    elif observation_count > 10:
                        status = "Present"
                    else:
                        status = "Rare/Absent"
                    
                    migration_patterns.append({
                        "month": month,
                        "month_name": ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][month-1],
                        "observation_count": observation_count,
                        "migration_status": status
                    })
                    
                except Exception:
                    # Fallback for months with no data
                    migration_patterns.append({
                        "month": month,
                        "month_name": ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][month-1],
                        "observation_count": 0,
                        "migration_status": "No Data"
                    })
            
            # Identify peak migration periods
            peak_months = [p for p in migration_patterns if p["migration_status"] == "Peak Migration"]
            
            result = {
                "species_code": species_code,
                "region": region_code,
                "analysis_months": months,
                "migration_patterns": migration_patterns,
                "peak_migration_months": [p["month_name"] for p in peak_months],
                "total_peak_months": len(peak_months),
                "analysis_note": f"Migration analysis based on seasonal observation patterns for {species_code}"
            }
            
            logger.info(f"Generated migration analysis for {species_code}: {len(peak_months)} peak months identified")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get migration data for {species_code}: {e}")
            raise EBirdAPIError(f"Migration data analysis failed: {str(e)}")

    def get_peak_times(
        self,
        species_code: str,
        lat: float,
        lng: float,
        radius_km: int = 25
    ) -> Dict[str, Any]:
        """
        Get best times to see specific species at a location.
        
        Args:
            species_code: eBird species code (e.g., "norcar")
            lat: Latitude coordinate
            lng: Longitude coordinate
            radius_km: Search radius in kilometers (default: 25)
                
        Returns:
            Optimal timing recommendations for species observation
            
        Raises:
            EBirdAPIError: For API errors with descriptive messages
        """
        try:
            logger.info(f"Analyzing peak times for {species_code} at ({lat}, {lng})")
            
            # Get recent observations to understand current patterns
            recent_observations = self.get_nearby_species_observations(
                species_codes=[species_code],
                latitude=lat,
                longitude=lng,
                radius=radius_km,
                days=30
            )
            
            # Analyze time patterns from recent observations
            hourly_counts = {}
            daily_counts = {}
            
            for obs in recent_observations.get("species_observations", []):
                # Extract timing information (if available in observation data)
                obs_date = obs.get("obsDt", "")
                if obs_date:
                    try:
                        # Simple hour extraction (assuming ISO format)
                        if "T" in obs_date and ":" in obs_date:
                            hour = int(obs_date.split("T")[1].split(":")[0])
                            hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
                    except:
                        pass
            
            # Determine optimal times based on bird behavior patterns
            # Most songbirds are active in early morning and late afternoon
            recommended_times = {
                "best_hours": ["6:00-9:00 AM", "4:00-7:00 PM"],
                "peak_season": "Spring and Fall migration periods",
                "daily_pattern": "Most active during dawn and dusk",
                "weather_factors": "Clear, calm mornings are optimal"
            }
            
            # Generate time-based recommendations
            time_recommendations = {
                "morning": {
                    "start_time": "6:00 AM",
                    "end_time": "9:00 AM",
                    "activity_level": "High",
                    "notes": "Peak singing and foraging activity"
                },
                "midday": {
                    "start_time": "10:00 AM", 
                    "end_time": "3:00 PM",
                    "activity_level": "Moderate",
                    "notes": "Birds often rest during heat of day"
                },
                "evening": {
                    "start_time": "4:00 PM",
                    "end_time": "7:00 PM", 
                    "activity_level": "High",
                    "notes": "Evening feeding and territorial activity"
                }
            }
            
            result = {
                "species_code": species_code,
                "location": {"latitude": lat, "longitude": lng},
                "search_radius": radius_km,
                "recent_observations": len(recent_observations.get("species_observations", [])),
                "recommended_times": recommended_times,
                "time_recommendations": time_recommendations,
                "analysis_note": f"Peak timing analysis for {species_code} based on typical behavior patterns"
            }
            
            logger.info(f"Generated peak times analysis for {species_code} at ({lat}, {lng})")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get peak times for {species_code}: {e}")
            raise EBirdAPIError(f"Peak times analysis failed: {str(e)}")

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

    def get_recent_checklists(
        self,
        region_code: str,
        days_back: int = 7,
        max_results: int = 50
    ) -> Dict[str, Any]:
        """
        Get most recent checklists in a region.
        
        Args:
            region_code: eBird region code (e.g., "US-CA")
            days_back: Days back to search (1-30, default: 7)
            max_results: Maximum checklists to return (default: 50)
                
        Returns:
            Recent checklist activity with observer and location information
            
        Raises:
            EBirdAPIError: For API errors with descriptive messages
        """
        try:
            days_back = min(days_back, EBIRD_DAYS_BACK_MAX)  # API limit
            endpoint = f"/data/obs/{region_code}/recent"
            
            params = {
                "back": days_back,
                "maxResults": min(max_results, 10000),
                "detail": "full",
                "includeProvisional": "true"
            }
            
            logger.info(f"Fetching recent checklists for {region_code} (last {days_back} days)")
            response = self.make_request(endpoint, params)
            
            if not isinstance(response, list):
                logger.warning(f"Unexpected response format for recent checklists: {type(response)}")
                return {
                    "region": region_code,
                    "days_back": days_back,
                    "checklists": [],
                    "checklist_count": 0
                }
            
            # Process observations into checklist format
            checklist_map = {}
            
            for obs in response:
                # Group by submission ID to create checklists
                sub_id = obs.get("subId", "unknown")
                
                if sub_id not in checklist_map:
                    checklist_map[sub_id] = {
                        "checklist_id": sub_id,
                        "location_name": obs.get("locName", "Unknown"),
                        "location_id": obs.get("locId", ""),
                        "observer": obs.get("userDisplayName", "Anonymous"),
                        "observation_date": obs.get("obsDt", ""),
                        "coordinates": {
                            "latitude": obs.get("lat", 0),
                            "longitude": obs.get("lng", 0)
                        },
                        "species_list": [],
                        "species_count": 0
                    }
                
                # Add species to checklist
                species_info = {
                    "species_code": obs.get("speciesCode", ""),
                    "common_name": obs.get("comName", ""),
                    "scientific_name": obs.get("sciName", ""),
                    "count": obs.get("howMany", 1)
                }
                checklist_map[sub_id]["species_list"].append(species_info)
            
            # Convert to list and add species counts
            checklists = []
            for checklist in checklist_map.values():
                checklist["species_count"] = len(checklist["species_list"])
                checklists.append(checklist)
            
            # Sort by date (most recent first)
            checklists.sort(key=lambda x: x["observation_date"], reverse=True)
            checklists = checklists[:max_results]
            
            result = {
                "region": region_code,
                "days_back": days_back,
                "search_parameters": {
                    "max_results": max_results,
                    "include_provisional": True
                },
                "checklists": checklists,
                "checklist_count": len(checklists),
                "total_observations": len(response)
            }
            
            logger.info(f"Retrieved {len(checklists)} recent checklists for {region_code}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get recent checklists for {region_code}: {e}")
            raise EBirdAPIError(f"Recent checklists lookup failed: {str(e)}")

    def get_checklist_details(
        self,
        checklist_id: str
    ) -> Dict[str, Any]:
        """
        Get detailed information about a specific checklist.
        
        Args:
            checklist_id: eBird checklist ID (e.g., "S123456789")
                
        Returns:
            Detailed checklist information including all species and metadata
            
        Raises:
            EBirdAPIError: For API errors with descriptive messages
        """
        try:
            endpoint = f"/data/obs/{checklist_id}"
            
            logger.info(f"Fetching checklist details for {checklist_id}")
            response = self.make_request(endpoint)
            
            if not isinstance(response, list):
                logger.warning(f"Unexpected response format for checklist details: {type(response)}")
                return {
                    "checklist_id": checklist_id,
                    "error": "Invalid checklist format",
                    "species_list": []
                }
            
            if not response:
                return {
                    "checklist_id": checklist_id,
                    "error": "Checklist not found or empty",
                    "species_list": []
                }
            
            # Extract checklist metadata from first observation
            first_obs = response[0]
            
            # Process all species in checklist
            species_list = []
            for obs in response:
                species_info = {
                    "species_code": obs.get("speciesCode", ""),
                    "common_name": obs.get("comName", ""),
                    "scientific_name": obs.get("sciName", ""),
                    "count": obs.get("howMany", "X"),  # X means present but not counted
                    "breeding_code": obs.get("breedingCode", ""),
                    "behavior_notes": obs.get("comments", "")
                }
                species_list.append(species_info)
            
            result = {
                "checklist_id": checklist_id,
                "location_name": first_obs.get("locName", "Unknown"),
                "location_id": first_obs.get("locId", ""),
                "coordinates": {
                    "latitude": first_obs.get("lat", 0),
                    "longitude": first_obs.get("lng", 0)
                },
                "observer": first_obs.get("userDisplayName", "Anonymous"),
                "observation_date": first_obs.get("obsDt", ""),
                "duration_minutes": first_obs.get("durationHrs", 0) * 60 if first_obs.get("durationHrs") else None,
                "distance_km": first_obs.get("effortDistanceKm", None),
                "number_observers": first_obs.get("numObservers", 1),
                "species_list": species_list,
                "species_count": len(species_list),
                "checklist_complete": first_obs.get("obsReviewed", False)
            }
            
            logger.info(f"Retrieved checklist details for {checklist_id}: {len(species_list)} species")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get checklist details for {checklist_id}: {e}")
            raise EBirdAPIError(f"Checklist details lookup failed: {str(e)}")

    def get_user_stats(
        self,
        username: str,
        region_code: str = "world",
        year: int = 2024
    ) -> Dict[str, Any]:
        """
        Get birder profile and statistics.
        
        ⚠️ IMPORTANT: This method returns SIMULATED DATA for demonstration purposes.
        Real eBird user statistics require special API permissions that are not 
        available through the standard eBird API.
        
        Args:
            username: eBird username or identifier
            region_code: Region for statistics (default: "world")  
            year: Year for statistics (default: 2024)
                
        Returns:
            Simulated user birding statistics and profile information
            
        Raises:
            EBirdAPIError: For API errors with descriptive messages
        """
        try:
            logger.info(f"Generating SIMULATED user statistics for {username} in {region_code}")
            
            # ⚠️ SIMULATED DATA - NOT FROM REAL EBIRD API
            # The eBird API does not provide public access to user statistics.
            # In a production system, this would either:
            # 1. Query user's public checklists if available
            # 2. Require OAuth authentication for private data
            # 3. Be removed entirely if not needed
            
            import random
            random.seed(hash(username) % 1000)  # Consistent results for same username
            
            base_species = random.randint(SIMULATED_SPECIES_MIN, SIMULATED_SPECIES_MAX)
            base_checklists = random.randint(SIMULATED_CHECKLISTS_MIN, SIMULATED_CHECKLISTS_MAX)
            
            user_stats = {
                "username": username,
                "region": region_code,
                "year": year,
                "species_count": base_species,
                "checklist_count": base_checklists,
                "observation_count": base_checklists * random.randint(8, 25),
                "countries_visited": random.randint(1, 15),
                "states_provinces_visited": random.randint(1, 25),
                "total_hours_birding": base_checklists * random.uniform(1.5, 4.0),
                "average_species_per_checklist": round(base_species / max(base_checklists, 1), 1),
                "most_active_month": random.choice(["May", "October", "April", "September"]),
                "birding_level": "Intermediate" if base_species < 200 else "Advanced",
                "data_source": "SIMULATED - NOT REAL USER DATA"
            }
            
            # Add some seasonal activity patterns
            monthly_activity = {}
            for month in range(1, 13):
                month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                activity_level = random.randint(0, 15)
                monthly_activity[month_names[month-1]] = activity_level
            
            result = {
                "user_profile": user_stats,
                "monthly_activity": monthly_activity,
                "warning": "⚠️ SIMULATED DATA - The eBird API does not provide public access to user statistics",
                "implementation_note": "In production, this would require OAuth authentication or be removed"
            }
            
            logger.info(f"Generated SIMULATED user statistics for {username}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate simulated user stats for {username}: {e}")
            raise EBirdAPIError(f"User statistics generation failed: {str(e)}")

    def close(self):
        """Close the HTTP session."""
        self.session.close()


# Global client instance for convenience
_client = None

def get_client() -> EBirdClient:
    """Get or create the global eBird client instance."""
    global _client
    if _client is None:
        _client = EBirdClient()
    return _client


# Convenience functions that use the global client
def get_recent_observations(*args, **kwargs):
    """Convenience function for getting recent observations."""
    return get_client().get_recent_observations(*args, **kwargs)

def get_nearby_observations(*args, **kwargs):
    """Convenience function for getting nearby observations."""
    return get_client().get_nearby_observations(*args, **kwargs)

def get_notable_observations(*args, **kwargs):
    """Convenience function for getting notable observations."""
    return get_client().get_notable_observations(*args, **kwargs)

def get_species_observations(*args, **kwargs):
    """Convenience function for getting species observations."""
    return get_client().get_species_observations(*args, **kwargs)

def get_hotspots(*args, **kwargs):
    """Convenience function for getting hotspots."""
    return get_client().get_hotspots(*args, **kwargs)

def get_nearby_hotspots(*args, **kwargs):
    """Convenience function for getting nearby hotspots."""
    return get_client().get_nearby_hotspots(*args, **kwargs)

def get_taxonomy(*args, **kwargs):
    """Convenience function for getting taxonomy."""
    return get_client().get_taxonomy(*args, **kwargs)

def get_nearest_observations(*args, **kwargs):
    """Convenience function for getting nearest observations."""
    return get_client().get_nearest_observations(*args, **kwargs)

def get_species_list(*args, **kwargs):
    """Convenience function for getting species list."""
    return get_client().get_species_list(*args, **kwargs)

def get_region_info(*args, **kwargs):
    """Convenience function for getting region info."""
    return get_client().get_region_info(*args, **kwargs)

def get_hotspot_info(*args, **kwargs):
    """Convenience function for getting hotspot info."""
    return get_client().get_hotspot_info(*args, **kwargs)

def get_nearby_notable_observations(*args, **kwargs):
    """Convenience function for getting nearby notable observations."""
    return get_client().get_nearby_notable_observations(*args, **kwargs)

def get_nearby_species_observations(*args, **kwargs):
    """Convenience function for getting nearby species observations."""
    return get_client().get_nearby_species_observations(*args, **kwargs)

def get_top_locations(*args, **kwargs):
    """Convenience function for getting most active birding locations."""
    return get_client().get_top_locations(*args, **kwargs)

def get_regional_statistics(*args, **kwargs):
    """Convenience function for getting regional birding statistics."""
    return get_client().get_regional_statistics(*args, **kwargs)

def get_location_species_list(*args, **kwargs):
    """Convenience function for getting species list for a location."""
    return get_client().get_location_species_list(*args, **kwargs)

def get_historic_observations(*args, **kwargs):
    """Convenience function for getting historical observations."""
    return get_client().get_historic_observations(*args, **kwargs)

def get_seasonal_trends(*args, **kwargs):
    """Convenience function for getting seasonal birding trends."""
    return get_client().get_seasonal_trends(*args, **kwargs)

def get_yearly_comparisons(*args, **kwargs):
    """Convenience function for getting yearly birding comparisons."""
    return get_client().get_yearly_comparisons(*args, **kwargs)

def get_subregions(*args, **kwargs):
    """Convenience function for getting subregions."""
    return get_client().get_subregions(*args, **kwargs)

def get_adjacent_regions(*args, **kwargs):
    """Convenience function for getting adjacent regions."""
    return get_client().get_adjacent_regions(*args, **kwargs)

def get_elevation_data(*args, **kwargs):
    """Convenience function for getting elevation data."""
    return get_client().get_elevation_data(*args, **kwargs)

def get_migration_data(*args, **kwargs):
    """Convenience function for getting migration data."""
    return get_client().get_migration_data(*args, **kwargs)

def get_peak_times(*args, **kwargs):
    """Convenience function for getting peak times."""
    return get_client().get_peak_times(*args, **kwargs)

def get_seasonal_hotspots(*args, **kwargs):
    """Convenience function for getting seasonal hotspots."""
    return get_client().get_seasonal_hotspots(*args, **kwargs)

def get_recent_checklists(*args, **kwargs):
    """Convenience function for getting recent checklists."""
    return get_client().get_recent_checklists(*args, **kwargs)

def get_checklist_details(*args, **kwargs):
    """Convenience function for getting checklist details."""
    return get_client().get_checklist_details(*args, **kwargs)

def get_user_stats(*args, **kwargs):
    """Convenience function for getting user stats."""
    return get_client().get_user_stats(*args, **kwargs)


if __name__ == "__main__":
    # Basic test of the API client
    try:
        client = EBirdClient()
        
        # Test taxonomy lookup
        logger.info("Testing taxonomy lookup...")
        taxonomy = client.get_taxonomy(species_codes=["norcar", "blujay"])
        for species in taxonomy:
            logger.info(f"  {species['comName']} ({species['speciesCode']})")
        
        # Test recent observations
        logger.info("Testing recent observations in Massachusetts...")
        observations = client.get_recent_observations("US-MA", days_back=3)
        logger.info(f"  Found {len(observations)} recent observations")
        
        client.close()
        logger.info("eBird API client test completed successfully!")
        
    except Exception as e:
        logger.error(f"Error testing eBird API: {e}")