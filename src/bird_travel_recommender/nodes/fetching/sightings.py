"""
FetchSightingsNode: Fetch recent bird sightings using eBird API with parallel processing.

This node implements a BatchNode for parallel species queries with:
- Smart endpoint selection (region-wide vs species-specific)
- Response aggregation and normalization
- Rate limiting with exponential backoff
- Handle empty results for rare species gracefully
"""

from pocketflow import BatchNode
from ...utils.ebird_api import get_client, EBirdAPIError
from typing import Dict, Any, Optional
import threading
import time
import logging

logger = logging.getLogger(__name__)


class FetchSightingsNode(BatchNode):
    """
    Fetch recent bird sightings using eBird API with parallel processing.
    
    Features:
    - BatchNode for parallel species queries
    - Smart endpoint selection (region-wide vs species-specific)
    - Response aggregation and normalization
    - Rate limiting with exponential backoff
    - Handle empty results for rare species gracefully
    """
    
    def __init__(self, max_workers: int = 5):
        super().__init__()
        self.max_workers = max_workers
        self.rate_limit_lock = threading.Lock()
        self.last_request_time = 0
        self.min_request_interval = 0.2  # 200ms between requests for rate limiting
        
    def prep(self, shared):
        """
        Extract validated species as individual items for BatchNode processing.
        
        BatchNode expects prep() to return a list of items to process in parallel.
        Each item will be passed to exec() individually.
        """
        validated_species = shared.get("validated_species", [])
        constraints = shared.get("input", {}).get("constraints", {})
        
        if not validated_species:
            logger.warning("No validated species found in shared store")
            # Return empty list so BatchNode can handle gracefully
            return []
        
        # Store constraints for access during exec
        self._constraints = constraints
        
        # Return list of species for BatchNode to process in parallel
        return validated_species
    
    def exec(self, species: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch sightings for a single species (called by BatchNode for each species).
        
        Args:
            species: Single validated species dictionary
            
        Returns:
            Dictionary with sightings for this species
        """
        constraints = self._constraints
        
        # Extract constraint parameters
        region_code = constraints.get("region", "US-MA")  # Default to Massachusetts
        days_back = min(constraints.get("days_back", 7), 30)  # eBird max is 30
        start_location = constraints.get("start_location")
        max_distance_km = constraints.get("max_daily_distance_km", 200)
        
        logger.debug(f"Fetching sightings for {species['common_name']}")
        
        # Create fetch task for this species
        task = self._create_fetch_task(species, region_code, days_back, start_location, max_distance_km)
        
        # Fetch sightings for this species
        try:
            result = self._fetch_species_sightings(task)
            return result
        except Exception as e:
            logger.error(f"Unexpected error fetching sightings for {species['common_name']}: {e}")
            return {
                "success": False,
                "error": str(e),
                "sightings": [],
                "species_code": species["species_code"]
            }
    
    def _create_fetch_task(self, species: Dict, region_code: str, days_back: int, 
                          start_location: Optional[Dict], max_distance_km: int) -> Dict[str, Any]:
        """
        Create a fetch task with optimal strategy selection.
        
        Args:
            species: Validated species dictionary
            region_code: eBird region code
            days_back: Days to look back
            start_location: Optional starting location for nearby searches
            max_distance_km: Maximum distance for nearby searches
            
        Returns:
            Fetch task dictionary with strategy and parameters
        """
        task = {
            "species": species,
            "region_code": region_code,
            "days_back": days_back
        }
        
        # Smart endpoint selection based on query type and location
        if start_location and start_location.get("lat") and start_location.get("lng"):
            # Use nearby observations if we have coordinates
            task["method"] = "nearby_observations"
            task["lat"] = start_location["lat"]
            task["lng"] = start_location["lng"]
            task["distance_km"] = min(max_distance_km // 2, 50)  # Half max distance, capped at eBird limit
        else:
            # Use species-specific observations for region
            task["method"] = "species_observations"
        
        return task
    
    def _fetch_species_sightings(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch sightings for a single species with rate limiting.
        
        Args:
            task: Fetch task dictionary
            
        Returns:
            Result dictionary with sightings and metadata
        """
        # Apply rate limiting
        with self.rate_limit_lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.min_request_interval:
                sleep_time = self.min_request_interval - time_since_last
                time.sleep(sleep_time)
            self.last_request_time = time.time()
        
        species = task["species"]
        method = task["method"]
        
        try:
            ebird_client = get_client()
            
            if method == "nearby_observations":
                sightings = ebird_client.get_nearby_observations(
                    lat=task["lat"],
                    lng=task["lng"],
                    distance_km=task["distance_km"],
                    days_back=task["days_back"],
                    species_code=species["species_code"]
                )
            elif method == "species_observations":
                sightings = ebird_client.get_species_observations(
                    species_code=species["species_code"],
                    region_code=task["region_code"],
                    days_back=task["days_back"]
                )
            else:
                raise ValueError(f"Unknown fetch method: {method}")
            
            # Enrich sightings with species validation metadata
            enriched_sightings = []
            for sighting in sightings:
                enriched_sighting = dict(sighting)  # Copy original sighting
                enriched_sighting.update({
                    "fetch_method": method,
                    "fetch_timestamp": time.time(),
                    "validation_confidence": species["confidence"],
                    "validation_method": species["validation_method"],
                    "original_species_name": species["original_name"],
                    "seasonal_notes": species.get("seasonal_notes", ""),
                    "behavioral_notes": species.get("behavioral_notes", "")
                })
                enriched_sightings.append(enriched_sighting)
            
            logger.debug(f"Fetched {len(enriched_sightings)} sightings for {species['common_name']} using {method}")
            
            return {
                "success": True,
                "sightings": enriched_sightings,
                "method": method,
                "species_code": species["species_code"]
            }
            
        except EBirdAPIError as e:
            logger.error(f"eBird API error for {species['common_name']}: {e}")
            return {
                "success": False,
                "error": str(e),
                "method": method,
                "species_code": species["species_code"]
            }
        except Exception as e:
            logger.error(f"Unexpected error for {species['common_name']}: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "method": method,
                "species_code": species["species_code"]
            }
    
    def post(self, shared, prep_res, exec_res):
        """
        Aggregate results from BatchNode execution.
        
        Args:
            shared: Shared store
            prep_res: List of species (from prep)
            exec_res: List of results from each exec call
        """
        # Aggregate results from all species
        all_sightings = []
        successful_fetches = 0
        total_observations = 0
        unique_locations = set()
        fetch_method_stats = {}
        api_errors = 0
        empty_results = 0
        
        for result in exec_res:
            if result.get("success", False):
                all_sightings.extend(result.get("sightings", []))
                successful_fetches += 1
                total_observations += len(result.get("sightings", []))
                
                # Track unique locations
                for sighting in result.get("sightings", []):
                    if sighting.get("locId"):
                        unique_locations.add(sighting["locId"])
                
                # Track fetch method statistics
                method = result.get("method", "unknown")
                fetch_method_stats[method] = fetch_method_stats.get(method, 0) + 1
                
                if len(result.get("sightings", [])) == 0:
                    empty_results += 1
            else:
                api_errors += 1
        
        # Create processing statistics
        processing_stats = {
            "total_species": len(prep_res),
            "successful_fetches": successful_fetches,
            "empty_results": empty_results,
            "api_errors": api_errors,
            "total_observations": total_observations,
            "unique_locations": len(unique_locations),
            "fetch_method_stats": fetch_method_stats
        }
        
        # Store results in shared store
        shared["all_sightings"] = all_sightings
        shared["fetch_stats"] = processing_stats

        # Check if we got sufficient data
        success_rate = successful_fetches / len(prep_res) if prep_res else 0
        
        # Handle case where no species were provided
        if len(prep_res) == 0:
            logger.warning("No species provided for fetching")
            shared["fetch_warning"] = "No species provided for fetching"
        elif success_rate < 0.5:
            logger.warning(f"Low fetch success rate: {success_rate:.1%}")
            shared["fetch_warning"] = f"Low fetch success rate: {success_rate:.1%}"
        elif total_observations == 0:
            logger.warning("No observations found for any species")
            shared["fetch_warning"] = "No observations found for any species"
        else:
            logger.info(f"Sightings fetch completed: {success_rate:.1%} success rate, "
                       f"{total_observations} total observations")

        return "default"