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
                response = self.session.get(url, params=params, timeout=30)
                
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


if __name__ == "__main__":
    # Basic test of the API client
    try:
        client = EBirdClient()
        
        # Test taxonomy lookup
        print("Testing taxonomy lookup...")
        taxonomy = client.get_taxonomy(species_codes=["norcar", "blujay"])
        for species in taxonomy:
            print(f"  {species['comName']} ({species['speciesCode']})")
        
        # Test recent observations
        print("\nTesting recent observations in Massachusetts...")
        observations = client.get_recent_observations("US-MA", days_back=3)
        print(f"  Found {len(observations)} recent observations")
        
        client.close()
        print("\neBird API client test completed successfully!")
        
    except Exception as e:
        print(f"Error testing eBird API: {e}")