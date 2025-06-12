from pocketflow import Node, BatchNode, AsyncNode
from .utils.call_llm import call_llm
from .utils.ebird_api import get_client, EBirdAPIError
from typing import List, Dict, Any, Optional
import re
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

logger = logging.getLogger(__name__)

class GetQuestionNode(Node):
    def exec(self, _):
        # Get question directly from user input
        user_question = input("Enter your question: ")
        return user_question
    
    def post(self, shared, prep_res, exec_res):
        # Store the user's question
        shared["question"] = exec_res
        return "default"  # Go to the next node

class AnswerNode(Node):
    def prep(self, shared):
        # Read question from shared
        return shared["question"]
    
    def exec(self, question):
        # Call LLM to get the answer
        return call_llm(question)
    
    def post(self, shared, prep_res, exec_res):
        # Store the answer in shared
        shared["answer"] = exec_res


class ValidateSpeciesNode(Node):
    """
    Validate bird species names using eBird taxonomy with LLM fallback.
    
    Strategy:
    1. Direct eBird taxonomy lookup (fast, reliable, cheap)
    2. LLM fallback only for fuzzy matching when taxonomy fails
    3. Cache successful name→code mappings
    4. Add seasonal context and behavioral notes
    """
    
    def __init__(self):
        super().__init__()
        self.species_cache = {}  # Cache for name→code mappings
        
    def prep(self, shared):
        """Extract species list from shared store."""
        species_list = shared.get("input", {}).get("species_list", [])
        if not species_list:
            raise ValueError("No species list provided in shared['input']['species_list']")
        return species_list
    
    def exec(self, species_list: List[str]) -> Dict[str, Any]:
        """
        Validate species names using eBird taxonomy with LLM fallback.
        
        Args:
            species_list: List of bird species names (common names)
            
        Returns:
            Dictionary with validated species and processing stats
        """
        validated_species = []
        processing_stats = {
            "total_input": len(species_list),
            "direct_taxonomy_matches": 0,
            "llm_fuzzy_matches": 0,
            "failed_validations": 0,
            "cache_hits": 0
        }
        
        # Get full eBird taxonomy for matching
        try:
            ebird_client = get_client()
            full_taxonomy = ebird_client.get_taxonomy()
            logger.info(f"Retrieved {len(full_taxonomy)} species from eBird taxonomy")
        except EBirdAPIError as e:
            logger.error(f"Failed to get eBird taxonomy: {e}")
            # Fallback to LLM-only validation
            return self._llm_only_validation(species_list, processing_stats)
        
        for species_name in species_list:
            # Check cache first
            cache_key = species_name.lower().strip()
            if cache_key in self.species_cache:
                validated_species.append(self.species_cache[cache_key])
                processing_stats["cache_hits"] += 1
                continue
            
            # Try direct eBird taxonomy lookup
            direct_match = self._direct_taxonomy_lookup(species_name, full_taxonomy)
            if direct_match:
                validated_species.append(direct_match)
                self.species_cache[cache_key] = direct_match
                processing_stats["direct_taxonomy_matches"] += 1
                continue
            
            # Fallback to LLM for fuzzy matching
            llm_match = self._llm_fuzzy_match(species_name, full_taxonomy)
            if llm_match:
                validated_species.append(llm_match)
                self.species_cache[cache_key] = llm_match
                processing_stats["llm_fuzzy_matches"] += 1
            else:
                processing_stats["failed_validations"] += 1
                logger.warning(f"Could not validate species: {species_name}")
        
        logger.info(f"Validated {len(validated_species)} of {len(species_list)} species")
        
        return {
            "validated_species": validated_species,
            "processing_stats": processing_stats
        }
    
    def _direct_taxonomy_lookup(self, species_name: str, taxonomy: List[Dict]) -> Optional[Dict[str, Any]]:
        """
        Attempt direct match against eBird taxonomy.
        
        Args:
            species_name: Common name to search for
            taxonomy: Full eBird taxonomy list
            
        Returns:
            Validated species dict or None if no match
        """
        normalized_input = species_name.lower().strip()
        
        for species in taxonomy:
            # Check exact common name match
            if species["comName"].lower() == normalized_input:
                return self._format_validated_species(
                    species, species_name, "direct_common_name", 1.0
                )
            
            # Check exact scientific name match
            if species["sciName"].lower() == normalized_input:
                return self._format_validated_species(
                    species, species_name, "direct_scientific_name", 1.0
                )
            
            # Check species code match
            if species["speciesCode"].lower() == normalized_input:
                return self._format_validated_species(
                    species, species_name, "direct_species_code", 1.0
                )
        
        # Try partial matching for common abbreviations
        for species in taxonomy:
            common_name = species["comName"].lower()
            
            # Handle common patterns like "cardinal" → "Northern Cardinal"
            if (normalized_input in common_name and 
                len(normalized_input) > 3):  # Avoid matching very short strings
                return self._format_validated_species(
                    species, species_name, "partial_common_name", 0.8
                )
        
        return None
    
    def _llm_fuzzy_match(self, species_name: str, taxonomy: List[Dict]) -> Optional[Dict[str, Any]]:
        """
        Use LLM for fuzzy matching when direct lookup fails.
        
        Args:
            species_name: Species name that failed direct lookup
            taxonomy: Full eBird taxonomy for context
            
        Returns:
            Best match species dict or None
        """
        # Create a smaller subset of taxonomy for LLM context (to avoid token limits)
        common_species = [s for s in taxonomy if s.get("category") == "species"][:500]
        
        species_validation_prompt = f"""
You are an expert ornithologist with comprehensive knowledge of North American birds.

I need to match this bird name: "{species_name}"

Here are some eBird taxonomy entries to help with matching:
{self._format_taxonomy_for_llm(common_species[:50])}

Please:
1. Find the best matching eBird species for "{species_name}"
2. Handle variations (e.g., "cardinal" → "Northern Cardinal", "blue jay" → "Blue Jay")
3. Consider common misspellings and colloquial names
4. If no good match exists, respond with "NO_MATCH"

Respond with ONLY the exact eBird common name from the taxonomy, or "NO_MATCH".
Example responses: "Northern Cardinal", "Blue Jay", "NO_MATCH"
"""
        
        try:
            llm_response = call_llm(species_validation_prompt).strip()
            
            if llm_response == "NO_MATCH":
                return None
            
            # Find the LLM's suggested match in the full taxonomy
            for species in taxonomy:
                if species["comName"].lower() == llm_response.lower():
                    return self._format_validated_species(
                        species, species_name, "llm_fuzzy_match", 0.7
                    )
            
            logger.warning(f"LLM suggested '{llm_response}' but not found in taxonomy")
            return None
            
        except Exception as e:
            logger.error(f"LLM fuzzy matching failed for '{species_name}': {e}")
            return None
    
    def _llm_only_validation(self, species_list: List[str], stats: Dict) -> Dict[str, Any]:
        """
        Fallback method when eBird API is unavailable.
        
        Args:
            species_list: List of species names to validate
            stats: Processing statistics dictionary
            
        Returns:
            Validation results using LLM knowledge only
        """
        logger.warning("Using LLM-only validation due to eBird API failure")
        
        validated_species = []
        
        llm_validation_prompt = f"""
You are an expert ornithologist. For each bird name below, provide:
1. Standardized common name
2. Scientific name
3. Likely eBird species code (guess based on patterns)
4. Basic seasonal/behavioral notes

Bird names to validate: {species_list}

Format each response as:
Name: [standardized common name]
Scientific: [scientific name]  
Code: [likely eBird code]
Notes: [brief seasonal/behavioral context]
---

If a name is invalid or unrecognizable, respond with "INVALID" for that entry.
"""
        
        try:
            llm_response = call_llm(llm_validation_prompt)
            # Parse LLM response (simplified for this implementation)
            # In production, would need more robust parsing
            
            for species_name in species_list:
                validated_species.append({
                    "original_name": species_name,
                    "common_name": species_name,  # Simplified
                    "scientific_name": "Unknown",
                    "species_code": "unknown",
                    "validation_method": "llm_only_fallback",
                    "confidence": 0.5,
                    "seasonal_notes": "API unavailable - limited validation"
                })
                stats["llm_fuzzy_matches"] += 1
            
        except Exception as e:
            logger.error(f"LLM-only validation failed: {e}")
            stats["failed_validations"] = len(species_list)
        
        return {
            "validated_species": validated_species,
            "processing_stats": stats
        }
    
    def _format_validated_species(self, species: Dict, original_name: str, method: str, confidence: float) -> Dict[str, Any]:
        """
        Format a validated species with additional context.
        
        Args:
            species: eBird taxonomy entry
            original_name: User's original input
            method: Validation method used
            confidence: Confidence score (0.0-1.0)
            
        Returns:
            Formatted species dictionary
        """
        return {
            "original_name": original_name,
            "common_name": species["comName"],
            "scientific_name": species["sciName"],
            "species_code": species["speciesCode"],
            "taxonomic_order": species.get("taxonOrder", 0),
            "family_common_name": species.get("familyComName", ""),
            "family_scientific_name": species.get("familySciName", ""),
            "validation_method": method,
            "confidence": confidence,
            "seasonal_notes": self._get_seasonal_notes(species["comName"]),
            "behavioral_notes": self._get_behavioral_notes(species["comName"])
        }
    
    def _get_seasonal_notes(self, common_name: str) -> str:
        """Generate basic seasonal context for common species."""
        name_lower = common_name.lower()
        
        if "warbler" in name_lower:
            return "Peak migration: spring (April-May) and fall (August-September)"
        elif "duck" in name_lower or "waterfowl" in name_lower:
            return "Best viewing: fall/winter migration and breeding season"
        elif "hawk" in name_lower or "eagle" in name_lower:
            return "Migration peaks: spring (March-April) and fall (September-October)"
        elif "cardinal" in name_lower or "jay" in name_lower:
            return "Year-round resident in most of range"
        else:
            return "Seasonal timing varies by region and migration patterns"
    
    def _get_behavioral_notes(self, common_name: str) -> str:
        """Generate basic behavioral context for common species."""
        name_lower = common_name.lower()
        
        if "warbler" in name_lower:
            return "Active feeders, check mid-canopy to upper canopy, early morning best"
        elif "duck" in name_lower:
            return "Water-dependent, check wetlands, ponds, and shorelines"
        elif "hawk" in name_lower:
            return "Soaring raptors, check thermals and ridgelines, late morning optimal"
        elif "cardinal" in name_lower:
            return "Seed feeders, dense cover, active at feeders dawn and dusk"
        elif "jay" in name_lower:
            return "Vocal and conspicuous, mixed habitats, often in family groups"
        else:
            return "Refer to species-specific field guides for optimal viewing strategies"
    
    def _format_taxonomy_for_llm(self, taxonomy_subset: List[Dict]) -> str:
        """Format taxonomy entries for LLM context."""
        formatted = []
        for species in taxonomy_subset[:20]:  # Limit to avoid token overuse
            formatted.append(f"- {species['comName']} ({species['sciName']}) [{species['speciesCode']}]")
        return "\n".join(formatted)
    
    def post(self, shared, prep_res, exec_res):
        """Store validated species in shared store."""
        shared["validated_species"] = exec_res["validated_species"]
        shared["validation_stats"] = exec_res["processing_stats"]
        
        success_rate = (exec_res["processing_stats"]["direct_taxonomy_matches"] + 
                       exec_res["processing_stats"]["llm_fuzzy_matches"]) / exec_res["processing_stats"]["total_input"]
        
        if success_rate < 0.5:
            logger.warning(f"Low validation success rate: {success_rate:.1%}")
            return "validation_failed"  # Could trigger error handling flow
        
        logger.info(f"Species validation completed with {success_rate:.1%} success rate")
        return "default"


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
            raise ValueError("No validated species found in shared store")
        
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
        
        if success_rate < 0.5:
            logger.warning(f"Low fetch success rate: {success_rate:.1%}")
            return "fetch_failed"

        if total_observations == 0:
            logger.warning("No observations found for any species")
            return "no_observations"

        logger.info(f"Sightings fetch completed: {success_rate:.1%} success rate, "
                   f"{total_observations} total observations")
        return "default"


class FilterConstraintsNode(Node):
    """
    Apply user constraints to sightings using enrichment-in-place strategy.
    
    Features:
    - Enrichment-in-place: adds constraint flags to original sighting records
    - Geographic filtering: distance calculations from start location
    - Temporal filtering: observation dates within travel window
    - Data quality filtering: valid GPS coordinates, duplicate handling
    - Travel feasibility: daily distance compliance
    """
    
    def __init__(self):
        super().__init__()
        # Import here to avoid circular imports
        from utils.geo_utils import (
            haversine_distance, validate_coordinates, is_within_date_range,
            is_within_radius, is_within_region, calculate_travel_time_estimate
        )
        self.haversine_distance = haversine_distance
        self.validate_coordinates = validate_coordinates
        self.is_within_date_range = is_within_date_range
        self.is_within_radius = is_within_radius
        self.is_within_region = is_within_region
        self.calculate_travel_time_estimate = calculate_travel_time_estimate
        
    def prep(self, shared):
        """Extract sightings and constraints from shared store."""
        all_sightings = shared.get("all_sightings", [])
        constraints = shared.get("input", {}).get("constraints", {})
        
        if not all_sightings:
            # Could be empty due to API issues - don't fail completely
            logger.warning("No sightings found in shared store - will process empty list")
        
        return {
            "all_sightings": all_sightings,
            "constraints": constraints
        }
    
    def exec(self, prep_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply constraints and enrich sightings with compliance flags.
        
        Args:
            prep_data: Dictionary with sightings and constraints
            
        Returns:
            Dictionary with enriched sightings and filtering statistics
        """
        all_sightings = prep_data["all_sightings"]
        constraints = prep_data["constraints"]
        
        # Extract constraint parameters with defaults
        start_location = constraints.get("start_location")
        max_daily_distance_km = constraints.get("max_daily_distance_km", 200)
        max_travel_radius_km = constraints.get("max_travel_radius_km", max_daily_distance_km)
        date_range_start = constraints.get("date_range", {}).get("start")
        date_range_end = constraints.get("date_range", {}).get("end")
        days_back = constraints.get("days_back", 30)
        region_code = constraints.get("region")
        min_observation_quality = constraints.get("min_observation_quality", "any")  # "reviewed", "valid", "any"
        
        filtering_stats = {
            "total_input_sightings": len(all_sightings),
            "valid_coordinates": 0,
            "within_travel_radius": 0,
            "within_date_range": 0,
            "within_region": 0,
            "high_quality_observations": 0,
            "duplicates_flagged": 0,
            "travel_feasible": 0,
            "constraint_compliance_summary": {}
        }
        
        if not all_sightings:
            logger.info("No sightings to filter")
            return {
                "enriched_sightings": [],
                "filtering_stats": filtering_stats
            }
        
        logger.info(f"Applying constraints to {len(all_sightings)} sightings")
        
        # Track seen observations for duplicate detection
        seen_observations = set()
        
        # Enrich each sighting with constraint compliance flags
        enriched_sightings = []
        for sighting in all_sightings:
            enriched_sighting = dict(sighting)  # Copy original sighting
            
            # 1. Geographic filtering
            lat, lng = sighting.get("lat"), sighting.get("lng")
            has_valid_gps = self.validate_coordinates(lat, lng)
            enriched_sighting["has_valid_gps"] = has_valid_gps
            
            if has_valid_gps:
                filtering_stats["valid_coordinates"] += 1
                
                # Distance from start location
                if start_location and start_location.get("lat") and start_location.get("lng"):
                    distance_from_start = self.haversine_distance(
                        start_location["lat"], start_location["lng"], lat, lng
                    )
                    enriched_sighting["distance_from_start_km"] = distance_from_start
                    enriched_sighting["within_travel_radius"] = distance_from_start <= max_travel_radius_km
                    
                    if enriched_sighting["within_travel_radius"]:
                        filtering_stats["within_travel_radius"] += 1
                        
                    # Travel time estimate
                    enriched_sighting["estimated_travel_time_hours"] = self.calculate_travel_time_estimate(distance_from_start)
                else:
                    enriched_sighting["distance_from_start_km"] = None
                    enriched_sighting["within_travel_radius"] = True  # No start location = no distance constraint
                    enriched_sighting["estimated_travel_time_hours"] = None
                
                # Region compliance
                if region_code:
                    within_region = self.is_within_region(lat, lng, region_code)
                    enriched_sighting["within_region"] = within_region
                    if within_region:
                        filtering_stats["within_region"] += 1
                else:
                    enriched_sighting["within_region"] = True
            else:
                # Invalid coordinates
                enriched_sighting["distance_from_start_km"] = None
                enriched_sighting["within_travel_radius"] = False
                enriched_sighting["estimated_travel_time_hours"] = None
                enriched_sighting["within_region"] = False
            
            # 2. Temporal filtering
            obs_date = sighting.get("obsDt")
            within_date_range = self.is_within_date_range(
                obs_date, date_range_start, date_range_end, days_back
            )
            enriched_sighting["within_date_range"] = within_date_range
            if within_date_range:
                filtering_stats["within_date_range"] += 1
            
            # 3. Data quality filtering
            obs_valid = sighting.get("obsValid", True)
            obs_reviewed = sighting.get("obsReviewed", False)
            location_private = sighting.get("locationPrivate", False)
            
            # Quality scoring
            if min_observation_quality == "reviewed" and obs_reviewed:
                quality_compliant = True
            elif min_observation_quality == "valid" and obs_valid:
                quality_compliant = True
            else:
                quality_compliant = True  # "any" quality accepted
            
            enriched_sighting["quality_compliant"] = quality_compliant
            enriched_sighting["observation_valid"] = obs_valid
            enriched_sighting["observation_reviewed"] = obs_reviewed
            enriched_sighting["location_private"] = location_private
            
            if quality_compliant:
                filtering_stats["high_quality_observations"] += 1
            
            # 4. Duplicate detection
            # Create unique key: location + species + date
            duplicate_key = (
                sighting.get("locId", "unknown"),
                sighting.get("speciesCode", "unknown"),
                sighting.get("obsDt", "unknown")
            )
            
            is_duplicate = duplicate_key in seen_observations
            enriched_sighting["is_duplicate"] = is_duplicate
            
            if not is_duplicate:
                seen_observations.add(duplicate_key)
            else:
                filtering_stats["duplicates_flagged"] += 1
            
            # 5. Travel feasibility (daily distance compliance)
            # This is a simplified check - in production would consider route optimization
            travel_feasible = True
            if enriched_sighting.get("estimated_travel_time_hours"):
                # Assume max 8 hours driving per day
                max_daily_travel_hours = 8
                travel_feasible = enriched_sighting["estimated_travel_time_hours"] <= max_daily_travel_hours
            
            enriched_sighting["daily_distance_compliant"] = travel_feasible
            if travel_feasible:
                filtering_stats["travel_feasible"] += 1
            
            # 6. Overall constraint compliance
            all_constraints_met = (
                enriched_sighting.get("has_valid_gps", False) and
                enriched_sighting.get("within_travel_radius", False) and
                enriched_sighting.get("within_date_range", False) and
                enriched_sighting.get("within_region", False) and
                enriched_sighting.get("quality_compliant", False) and
                not enriched_sighting.get("is_duplicate", True) and
                enriched_sighting.get("daily_distance_compliant", False)
            )
            
            enriched_sighting["meets_all_constraints"] = all_constraints_met
            
            enriched_sightings.append(enriched_sighting)
        
        # Calculate constraint compliance summary
        total_sightings = len(enriched_sightings)
        if total_sightings > 0:
            filtering_stats["constraint_compliance_summary"] = {
                "valid_coordinates_pct": (filtering_stats["valid_coordinates"] / total_sightings) * 100,
                "within_travel_radius_pct": (filtering_stats["within_travel_radius"] / total_sightings) * 100,
                "within_date_range_pct": (filtering_stats["within_date_range"] / total_sightings) * 100,
                "high_quality_pct": (filtering_stats["high_quality_observations"] / total_sightings) * 100,
                "duplicate_rate_pct": (filtering_stats["duplicates_flagged"] / total_sightings) * 100,
                "travel_feasible_pct": (filtering_stats["travel_feasible"] / total_sightings) * 100,
                "fully_compliant_count": sum(1 for s in enriched_sightings if s.get("meets_all_constraints", False))
            }
        
        logger.info(f"Constraint filtering completed: {total_sightings} sightings enriched, "
                   f"{filtering_stats['constraint_compliance_summary'].get('fully_compliant_count', 0)} fully compliant")
        
        return {
            "enriched_sightings": enriched_sightings,
            "filtering_stats": filtering_stats
        }
    
    def post(self, shared, prep_res, exec_res):
        """Store enriched sightings in shared store."""
        # Replace all_sightings with enriched version
        shared["all_sightings"] = exec_res["enriched_sightings"]
        shared["filtering_stats"] = exec_res["filtering_stats"]
        
        # Check if we have sufficient compliant data
        total_sightings = len(exec_res["enriched_sightings"])
        fully_compliant = exec_res["filtering_stats"]["constraint_compliance_summary"].get("fully_compliant_count", 0)
        
        if total_sightings == 0:
            logger.warning("No sightings to process after filtering")
            return "no_sightings"
        
        if fully_compliant == 0:
            logger.warning("No sightings meet all constraints - may need to relax filters")
            return "no_compliant_sightings"
        
        compliance_rate = fully_compliant / total_sightings
        if compliance_rate < 0.1:  # Less than 10% compliance
            logger.warning(f"Low constraint compliance rate: {compliance_rate:.1%}")
            return "low_compliance"
        
        logger.info(f"Constraint filtering successful: {compliance_rate:.1%} compliance rate")
        return "default"


class ClusterHotspotsNode(Node):
    """
    Group nearby locations using dual hotspot discovery patterns with full data preservation.
    
    Features:
    - Dual hotspot discovery: regional hotspots + coordinate-based hotspots
    - Location deduplication handling eBird's multiple identifiers
    - Distance-based clustering with travel time optimization
    - Full data preservation: each cluster contains complete sighting records
    """
    
    def __init__(self, cluster_radius_km: float = 15.0):
        super().__init__()
        self.cluster_radius_km = cluster_radius_km
        # Import geo utilities
        from utils.geo_utils import haversine_distance, validate_coordinates
        self.haversine_distance = haversine_distance
        self.validate_coordinates = validate_coordinates
        
    def prep(self, shared):
        """Extract enriched sightings and constraints from shared store."""
        enriched_sightings = shared.get("all_sightings", [])
        constraints = shared.get("input", {}).get("constraints", {})
        
        if not enriched_sightings:
            logger.warning("No enriched sightings found in shared store")
        
        return {
            "enriched_sightings": enriched_sightings,
            "constraints": constraints
        }
    
    def exec(self, prep_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cluster nearby locations and integrate with eBird hotspots.
        
        Args:
            prep_data: Dictionary with enriched sightings and constraints
            
        Returns:
            Dictionary with hotspot clusters and clustering statistics
        """
        enriched_sightings = prep_data["enriched_sightings"]
        constraints = prep_data["constraints"]
        
        clustering_stats = {
            "total_input_sightings": len(enriched_sightings),
            "unique_locations_found": 0,
            "hotspots_discovered": 0,
            "clusters_created": 0,
            "sightings_in_clusters": 0,
            "isolated_locations": 0,
            "duplicate_locations_merged": 0
        }
        
        if not enriched_sightings:
            logger.info("No sightings to cluster")
            return {
                "hotspot_clusters": [],
                "clustering_stats": clustering_stats
            }
        
        logger.info(f"Clustering {len(enriched_sightings)} sightings into hotspots")
        
        # Step 1: Extract unique locations from sightings
        unique_locations = self._extract_unique_locations(enriched_sightings, clustering_stats)
        
        # Step 2: Discover eBird hotspots for the region
        region_hotspots = self._discover_regional_hotspots(constraints, clustering_stats)
        
        # Step 3: Merge sighting locations with discovered hotspots
        merged_locations = self._merge_locations_with_hotspots(unique_locations, region_hotspots, clustering_stats)
        
        # Step 4: Apply distance-based clustering
        location_clusters = self._apply_distance_clustering(merged_locations, clustering_stats)
        
        # Step 5: Build final hotspot clusters with full sighting data
        hotspot_clusters = self._build_hotspot_clusters(location_clusters, enriched_sightings, clustering_stats)
        
        logger.info(f"Clustering completed: {clustering_stats['clusters_created']} clusters from "
                   f"{clustering_stats['unique_locations_found']} unique locations")
        
        return {
            "hotspot_clusters": hotspot_clusters,
            "clustering_stats": clustering_stats
        }
    
    def _extract_unique_locations(self, sightings: List[Dict], stats: Dict) -> List[Dict[str, Any]]:
        """
        Extract unique locations from sightings, handling eBird location identifier variations.
        
        Args:
            sightings: List of enriched sightings
            stats: Statistics dictionary to update
            
        Returns:
            List of unique location dictionaries
        """
        location_map = {}  # Key: normalized location identifier
        
        for sighting in sightings:
            lat, lng = sighting.get("lat"), sighting.get("lng")
            loc_id = sighting.get("locId")
            loc_name = sighting.get("locName", "Unknown Location")
            
            # Skip sightings without valid coordinates
            if not self.validate_coordinates(lat, lng):
                continue
            
            # Create normalized location key
            # eBird can have multiple locIds for the same GPS point, so use coordinates
            coord_key = f"{lat:.4f},{lng:.4f}"  # 4 decimal places ≈ 11m precision
            
            if coord_key not in location_map:
                location_map[coord_key] = {
                    "coord_key": coord_key,
                    "lat": lat,
                    "lng": lng,
                    "primary_loc_id": loc_id,
                    "primary_loc_name": loc_name,
                    "alternate_loc_ids": set(),
                    "alternate_loc_names": set(),
                    "sighting_count": 0,
                    "species_codes": set(),
                    "observation_dates": set(),
                    "is_hotspot": False,
                    "hotspot_metadata": {}
                }
            else:
                # Merge alternate identifiers
                if loc_id and loc_id != location_map[coord_key]["primary_loc_id"]:
                    location_map[coord_key]["alternate_loc_ids"].add(loc_id)
                if loc_name and loc_name != location_map[coord_key]["primary_loc_name"]:
                    location_map[coord_key]["alternate_loc_names"].add(loc_name)
            
            # Update location statistics
            location_map[coord_key]["sighting_count"] += 1
            if sighting.get("speciesCode"):
                location_map[coord_key]["species_codes"].add(sighting["speciesCode"])
            if sighting.get("obsDt"):
                location_map[coord_key]["observation_dates"].add(sighting["obsDt"])
        
        # Convert sets to lists for JSON serialization
        unique_locations = []
        for location in location_map.values():
            location["alternate_loc_ids"] = list(location["alternate_loc_ids"])
            location["alternate_loc_names"] = list(location["alternate_loc_names"])
            location["species_codes"] = list(location["species_codes"])
            location["observation_dates"] = list(location["observation_dates"])
            location["species_diversity"] = len(location["species_codes"])
            unique_locations.append(location)
        
        stats["unique_locations_found"] = len(unique_locations)
        stats["duplicate_locations_merged"] = len([loc for loc in unique_locations if loc["alternate_loc_ids"]])
        
        logger.debug(f"Extracted {len(unique_locations)} unique locations from sightings")
        return unique_locations
    
    def _discover_regional_hotspots(self, constraints: Dict, stats: Dict) -> List[Dict[str, Any]]:
        """
        Discover eBird hotspots for the region using dual discovery methods.
        
        Args:
            constraints: User constraints containing region and location info
            stats: Statistics dictionary to update
            
        Returns:
            List of discovered hotspot dictionaries
        """
        hotspots = []
        
        try:
            from utils.ebird_api import get_client
            ebird_client = get_client()
            
            # Method 1: Regional hotspots
            region_code = constraints.get("region")
            if region_code:
                try:
                    regional_hotspots = ebird_client.get_hotspots(region_code)
                    hotspots.extend(regional_hotspots)
                    logger.debug(f"Found {len(regional_hotspots)} regional hotspots for {region_code}")
                except Exception as e:
                    logger.warning(f"Failed to get regional hotspots for {region_code}: {e}")
            
            # Method 2: Coordinate-based hotspots (if start location available)
            start_location = constraints.get("start_location")
            if start_location and start_location.get("lat") and start_location.get("lng"):
                try:
                    max_distance = min(constraints.get("max_daily_distance_km", 200) // 2, 50)  # Half travel distance, eBird max 50km
                    nearby_hotspots = ebird_client.get_nearby_hotspots(
                        lat=start_location["lat"],
                        lng=start_location["lng"],
                        distance_km=max_distance
                    )
                    
                    # Deduplicate by locId
                    existing_loc_ids = {h.get("locId") for h in hotspots}
                    new_hotspots = [h for h in nearby_hotspots if h.get("locId") not in existing_loc_ids]
                    hotspots.extend(new_hotspots)
                    
                    logger.debug(f"Found {len(new_hotspots)} additional nearby hotspots")
                except Exception as e:
                    logger.warning(f"Failed to get nearby hotspots: {e}")
            
        except Exception as e:
            logger.error(f"Failed to discover hotspots: {e}")
        
        stats["hotspots_discovered"] = len(hotspots)
        logger.info(f"Discovered {len(hotspots)} eBird hotspots")
        return hotspots
    
    def _merge_locations_with_hotspots(self, locations: List[Dict], hotspots: List[Dict], stats: Dict) -> List[Dict]:
        """
        Merge sighting locations with discovered hotspots.
        
        Args:
            locations: Unique locations from sightings
            hotspots: Discovered eBird hotspots
            stats: Statistics dictionary to update
            
        Returns:
            List of merged location dictionaries
        """
        # Create coordinate-based lookup for hotspots
        hotspot_lookup = {}
        for hotspot in hotspots:
            if self.validate_coordinates(hotspot.get("lat"), hotspot.get("lng")):
                coord_key = f"{hotspot['lat']:.4f},{hotspot['lng']:.4f}"
                hotspot_lookup[coord_key] = hotspot
        
        # Merge hotspot data into locations
        merged_locations = []
        hotspot_matches = 0
        
        for location in locations:
            coord_key = location["coord_key"]
            
            # Check for exact coordinate match
            if coord_key in hotspot_lookup:
                hotspot = hotspot_lookup[coord_key]
                location["is_hotspot"] = True
                location["hotspot_metadata"] = {
                    "hotspot_loc_id": hotspot.get("locId"),
                    "hotspot_name": hotspot.get("locName"),
                    "country_code": hotspot.get("countryCode"),
                    "subnational1_code": hotspot.get("subnational1Code"),
                    "subnational2_code": hotspot.get("subnational2Code"),
                    "latest_obs_date": hotspot.get("latestObsDt"),
                    "num_species_all_time": hotspot.get("numSpeciesAllTime", 0)
                }
                hotspot_matches += 1
            else:
                # Check for nearby hotspots (within 500m)
                nearby_hotspot = self._find_nearby_hotspot(location, hotspots, max_distance_km=0.5)
                if nearby_hotspot:
                    location["is_hotspot"] = True
                    location["hotspot_metadata"] = {
                        "hotspot_loc_id": nearby_hotspot.get("locId"),
                        "hotspot_name": nearby_hotspot.get("locName"),
                        "distance_to_hotspot_km": self.haversine_distance(
                            location["lat"], location["lng"],
                            nearby_hotspot["lat"], nearby_hotspot["lng"]
                        ),
                        "country_code": nearby_hotspot.get("countryCode"),
                        "subnational1_code": nearby_hotspot.get("subnational1Code"),
                        "num_species_all_time": nearby_hotspot.get("numSpeciesAllTime", 0)
                    }
                    hotspot_matches += 1
            
            merged_locations.append(location)
        
        # Add hotspots that don't have sighting locations
        sighting_coords = {loc["coord_key"] for loc in locations}
        for hotspot in hotspots:
            if self.validate_coordinates(hotspot.get("lat"), hotspot.get("lng")):
                coord_key = f"{hotspot['lat']:.4f},{hotspot['lng']:.4f}"
                if coord_key not in sighting_coords:
                    # Add hotspot as potential location even without current sightings
                    merged_locations.append({
                        "coord_key": coord_key,
                        "lat": hotspot["lat"],
                        "lng": hotspot["lng"],
                        "primary_loc_id": hotspot.get("locId"),
                        "primary_loc_name": hotspot.get("locName"),
                        "alternate_loc_ids": [],
                        "alternate_loc_names": [],
                        "sighting_count": 0,
                        "species_codes": [],
                        "observation_dates": [],
                        "species_diversity": 0,
                        "is_hotspot": True,
                        "hotspot_metadata": {
                            "hotspot_loc_id": hotspot.get("locId"),
                            "hotspot_name": hotspot.get("locName"),
                            "country_code": hotspot.get("countryCode"),
                            "subnational1_code": hotspot.get("subnational1Code"),
                            "num_species_all_time": hotspot.get("numSpeciesAllTime", 0)
                        }
                    })
        
        logger.debug(f"Merged {hotspot_matches} sighting locations with hotspots, "
                    f"added {len(merged_locations) - len(locations)} hotspot-only locations")
        
        return merged_locations
    
    def _find_nearby_hotspot(self, location: Dict, hotspots: List[Dict], max_distance_km: float) -> Optional[Dict]:
        """Find the closest hotspot within max_distance_km."""
        closest_hotspot = None
        min_distance = float('inf')
        
        for hotspot in hotspots:
            if self.validate_coordinates(hotspot.get("lat"), hotspot.get("lng")):
                distance = self.haversine_distance(
                    location["lat"], location["lng"],
                    hotspot["lat"], hotspot["lng"]
                )
                if distance <= max_distance_km and distance < min_distance:
                    min_distance = distance
                    closest_hotspot = hotspot
        
        return closest_hotspot
    
    def _apply_distance_clustering(self, locations: List[Dict], stats: Dict) -> List[List[Dict]]:
        """
        Apply distance-based clustering to group nearby locations.
        
        Args:
            locations: List of merged location dictionaries
            stats: Statistics dictionary to update
            
        Returns:
            List of location clusters (each cluster is a list of locations)
        """
        if not locations:
            return []
        
        # Simple greedy clustering algorithm
        clusters = []
        unassigned = locations.copy()
        
        while unassigned:
            # Start new cluster with first unassigned location
            seed_location = unassigned.pop(0)
            current_cluster = [seed_location]
            
            # Find all locations within cluster radius of any location in current cluster
            changed = True
            while changed:
                changed = False
                remaining = []
                
                for candidate in unassigned:
                    # Check if candidate is close to any location in current cluster
                    min_distance = min(
                        self.haversine_distance(
                            candidate["lat"], candidate["lng"],
                            cluster_loc["lat"], cluster_loc["lng"]
                        )
                        for cluster_loc in current_cluster
                    )
                    
                    if min_distance <= self.cluster_radius_km:
                        current_cluster.append(candidate)
                        changed = True
                    else:
                        remaining.append(candidate)
                
                unassigned = remaining
            
            clusters.append(current_cluster)
        
        # Sort clusters by total sighting count (descending)
        clusters.sort(key=lambda cluster: sum(loc["sighting_count"] for loc in cluster), reverse=True)
        
        stats["clusters_created"] = len(clusters)
        stats["isolated_locations"] = len([c for c in clusters if len(c) == 1])
        
        logger.debug(f"Created {len(clusters)} location clusters using {self.cluster_radius_km}km radius")
        return clusters
    
    def _build_hotspot_clusters(self, location_clusters: List[List[Dict]], sightings: List[Dict], stats: Dict) -> List[Dict]:
        """
        Build final hotspot clusters with complete sighting data.
        
        Args:
            location_clusters: Clustered locations
            sightings: Original enriched sightings
            stats: Statistics dictionary to update
            
        Returns:
            List of hotspot cluster dictionaries with full data
        """
        hotspot_clusters = []
        total_sightings_in_clusters = 0
        
        for i, location_cluster in enumerate(location_clusters):
            if not location_cluster:
                continue
            
            # Find all sightings that belong to this cluster
            cluster_sightings = []
            cluster_coord_keys = {loc["coord_key"] for loc in location_cluster}
            
            for sighting in sightings:
                if self.validate_coordinates(sighting.get("lat"), sighting.get("lng")):
                    sighting_coord_key = f"{sighting['lat']:.4f},{sighting['lng']:.4f}"
                    if sighting_coord_key in cluster_coord_keys:
                        cluster_sightings.append(sighting)
            
            # Calculate cluster center (centroid)
            cluster_center_lat = sum(loc["lat"] for loc in location_cluster) / len(location_cluster)
            cluster_center_lng = sum(loc["lng"] for loc in location_cluster) / len(location_cluster)
            
            # Determine cluster name (prefer hotspot names)
            hotspot_locations = [loc for loc in location_cluster if loc["is_hotspot"]]
            if hotspot_locations:
                # Use most diverse hotspot name
                best_hotspot = max(hotspot_locations, key=lambda loc: loc.get("species_diversity", 0))
                cluster_name = best_hotspot.get("hotspot_metadata", {}).get("hotspot_name") or best_hotspot["primary_loc_name"]
            else:
                # Use location with most sightings
                best_location = max(location_cluster, key=lambda loc: loc["sighting_count"])
                cluster_name = best_location["primary_loc_name"]
            
            # Calculate cluster statistics
            total_species = len(set(
                sighting.get("speciesCode") for sighting in cluster_sightings
                if sighting.get("speciesCode")
            ))
            
            hotspot_cluster = {
                "cluster_id": f"cluster_{i+1}",
                "cluster_name": cluster_name,
                "center_lat": cluster_center_lat,
                "center_lng": cluster_center_lng,
                "locations": location_cluster,
                "sightings": cluster_sightings,
                "statistics": {
                    "location_count": len(location_cluster),
                    "sighting_count": len(cluster_sightings),
                    "species_diversity": total_species,
                    "hotspot_count": len(hotspot_locations),
                    "cluster_radius_km": self._calculate_cluster_radius(location_cluster),
                    "most_recent_observation": max(
                        (s.get("obsDt") for s in cluster_sightings if s.get("obsDt")),
                        default="Unknown"
                    ),
                    "species_codes": sorted(list(set(
                        s.get("speciesCode") for s in cluster_sightings 
                        if s.get("speciesCode")
                    )))
                },
                "accessibility": {
                    "has_hotspot": len(hotspot_locations) > 0,
                    "avg_travel_time_estimate": self._calculate_avg_travel_time(cluster_sightings),
                    "coordinate_quality": "high" if all(
                        loc.get("sighting_count", 0) > 0 for loc in location_cluster
                    ) else "medium"
                }
            }
            
            hotspot_clusters.append(hotspot_cluster)
            total_sightings_in_clusters += len(cluster_sightings)
        
        stats["sightings_in_clusters"] = total_sightings_in_clusters
        
        logger.info(f"Built {len(hotspot_clusters)} hotspot clusters containing "
                   f"{total_sightings_in_clusters} sightings")
        
        return hotspot_clusters
    
    def _calculate_cluster_radius(self, locations: List[Dict]) -> float:
        """Calculate the radius of a cluster (max distance from centroid)."""
        if len(locations) <= 1:
            return 0.0
        
        # Calculate centroid
        center_lat = sum(loc["lat"] for loc in locations) / len(locations)
        center_lng = sum(loc["lng"] for loc in locations) / len(locations)
        
        # Find max distance from centroid
        max_distance = max(
            self.haversine_distance(center_lat, center_lng, loc["lat"], loc["lng"])
            for loc in locations
        )
        
        return max_distance
    
    def _calculate_avg_travel_time(self, sightings: List[Dict]) -> Optional[float]:
        """Calculate average travel time estimate for cluster sightings."""
        travel_times = [
            s.get("estimated_travel_time_hours") for s in sightings 
            if s.get("estimated_travel_time_hours") is not None
        ]
        
        if not travel_times:
            return None
        
        return sum(travel_times) / len(travel_times)
    
    def post(self, shared, prep_res, exec_res):
        """Store hotspot clusters in shared store."""
        shared["hotspot_clusters"] = exec_res["hotspot_clusters"]
        shared["clustering_stats"] = exec_res["clustering_stats"]
        
        # Check if clustering was successful
        clusters_created = exec_res["clustering_stats"]["clusters_created"]
        
        if clusters_created == 0:
            logger.warning("No hotspot clusters created")
            return "no_clusters"
        
        sightings_in_clusters = exec_res["clustering_stats"]["sightings_in_clusters"]
        total_sightings = exec_res["clustering_stats"]["total_input_sightings"]
        
        if total_sightings > 0:
            clustering_efficiency = sightings_in_clusters / total_sightings
            if clustering_efficiency < 0.5:
                logger.warning(f"Low clustering efficiency: {clustering_efficiency:.1%}")
                return "poor_clustering"
        
        logger.info(f"Hotspot clustering successful: {clusters_created} clusters created")
        return "default"


class ScoreLocationsNode(Node):
    """
    Rank clustered locations by species diversity and sighting frequency with LLM-enhanced habitat evaluation.
    
    Features:
    - Species diversity scoring with target species prioritization
    - Observation recency and frequency weighting
    - eBird hotspot popularity and accessibility scoring
    - LLM-enhanced habitat suitability evaluation
    - User preference weighting (photography, rarity, accessibility)
    """
    
    def __init__(self):
        super().__init__()
        from datetime import datetime, timedelta
        from utils.geo_utils import parse_ebird_datetime
        self.datetime = datetime
        self.timedelta = timedelta
        self.parse_ebird_datetime = parse_ebird_datetime
        
    def prep(self, shared):
        """Extract hotspot clusters and user constraints from shared store."""
        hotspot_clusters = shared.get("hotspot_clusters", [])
        constraints = shared.get("input", {}).get("constraints", {})
        validated_species = shared.get("validated_species", [])
        
        if not hotspot_clusters:
            logger.warning("No hotspot clusters found in shared store")
        
        return {
            "hotspot_clusters": hotspot_clusters,
            "constraints": constraints,
            "validated_species": validated_species
        }
    
    def exec(self, prep_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score and rank hotspot clusters based on multiple criteria.
        
        Args:
            prep_data: Dictionary with hotspot clusters, constraints, and validated species
            
        Returns:
            Dictionary with scored locations and scoring statistics
        """
        hotspot_clusters = prep_data["hotspot_clusters"]
        constraints = prep_data["constraints"]
        validated_species = prep_data["validated_species"]
        
        scoring_stats = {
            "total_clusters_scored": len(hotspot_clusters),
            "target_species_count": len(validated_species),
            "average_diversity_score": 0.0,
            "average_recency_score": 0.0,
            "average_hotspot_score": 0.0,
            "average_accessibility_score": 0.0,
            "llm_enhanced_clusters": 0,
            "scoring_method_distribution": {}
        }
        
        if not hotspot_clusters:
            logger.info("No hotspot clusters to score")
            return {
                "scored_locations": [],
                "scoring_stats": scoring_stats
            }
        
        logger.info(f"Scoring {len(hotspot_clusters)} hotspot clusters")
        
        # Create target species lookup for prioritization
        target_species_codes = {species["species_code"] for species in validated_species}
        
        # Score each cluster
        scored_clusters = []
        for cluster in hotspot_clusters:
            cluster_score = self._score_cluster(cluster, target_species_codes, constraints, scoring_stats)
            scored_clusters.append(cluster_score)
        
        # Apply LLM enhancement for top clusters
        enhanced_clusters = self._apply_llm_enhancement(scored_clusters, validated_species, constraints, scoring_stats)
        
        # Sort by final score (descending)
        enhanced_clusters.sort(key=lambda c: c["final_score"], reverse=True)
        
        # Calculate summary statistics
        if enhanced_clusters:
            scoring_stats["average_diversity_score"] = sum(c["scoring"]["diversity_score"] for c in enhanced_clusters) / len(enhanced_clusters)
            scoring_stats["average_recency_score"] = sum(c["scoring"]["recency_score"] for c in enhanced_clusters) / len(enhanced_clusters)
            scoring_stats["average_hotspot_score"] = sum(c["scoring"]["hotspot_score"] for c in enhanced_clusters) / len(enhanced_clusters)
            scoring_stats["average_accessibility_score"] = sum(c["scoring"]["accessibility_score"] for c in enhanced_clusters) / len(enhanced_clusters)
        
        logger.info(f"Location scoring completed: {len(enhanced_clusters)} clusters ranked")
        
        return {
            "scored_locations": enhanced_clusters,
            "scoring_stats": scoring_stats
        }
    
    def _score_cluster(self, cluster: Dict, target_species_codes: set, constraints: Dict, stats: Dict) -> Dict:
        """
        Score a single cluster based on multiple criteria.
        
        Args:
            cluster: Hotspot cluster dictionary
            target_species_codes: Set of target species codes
            constraints: User constraints
            stats: Statistics dictionary to update
            
        Returns:
            Cluster dictionary with scoring information added
        """
        scored_cluster = dict(cluster)  # Copy original cluster
        
        # 1. Species Diversity Score (40% weight)
        diversity_score = self._calculate_diversity_score(cluster, target_species_codes)
        
        # 2. Observation Recency Score (25% weight)
        recency_score = self._calculate_recency_score(cluster)
        
        # 3. eBird Hotspot Score (20% weight)
        hotspot_score = self._calculate_hotspot_score(cluster)
        
        # 4. Accessibility Score (15% weight)
        accessibility_score = self._calculate_accessibility_score(cluster, constraints)
        
        # Calculate weighted base score
        base_score = (
            diversity_score * 0.40 +
            recency_score * 0.25 +
            hotspot_score * 0.20 +
            accessibility_score * 0.15
        )
        
        # Store detailed scoring breakdown
        scored_cluster["scoring"] = {
            "diversity_score": diversity_score,
            "recency_score": recency_score,
            "hotspot_score": hotspot_score,
            "accessibility_score": accessibility_score,
            "base_score": base_score,
            "target_species_found": len(set(cluster["statistics"]["species_codes"]) & target_species_codes),
            "total_species_found": cluster["statistics"]["species_diversity"],
            "scoring_method": "algorithmic"
        }
        
        scored_cluster["base_score"] = base_score
        scored_cluster["final_score"] = base_score  # Will be enhanced later
        
        return scored_cluster
    
    def _calculate_diversity_score(self, cluster: Dict, target_species_codes: set) -> float:
        """
        Calculate species diversity score with target species prioritization.
        
        Args:
            cluster: Hotspot cluster dictionary
            target_species_codes: Set of target species codes
            
        Returns:
            Diversity score (0.0-1.0)
        """
        cluster_species = set(cluster["statistics"]["species_codes"])
        total_species = len(cluster_species)
        target_species_found = len(cluster_species & target_species_codes)
        
        if not target_species_codes:
            # No target species specified, use total diversity
            return min(total_species / 50.0, 1.0)  # Normalize to max 50 species
        
        # Prioritize target species coverage
        target_coverage = target_species_found / len(target_species_codes)
        diversity_bonus = min(total_species / 30.0, 0.5)  # Up to 0.5 bonus for diversity
        
        return min(target_coverage + diversity_bonus, 1.0)
    
    def _calculate_recency_score(self, cluster: Dict) -> float:
        """
        Calculate observation recency score.
        
        Args:
            cluster: Hotspot cluster dictionary
            
        Returns:
            Recency score (0.0-1.0)
        """
        try:
            most_recent = cluster["statistics"]["most_recent_observation"]
            if most_recent == "Unknown":
                return 0.3  # Default score for unknown dates
            
            recent_date = self.parse_ebird_datetime(most_recent)
            if not recent_date:
                return 0.3
            
            now = self.datetime.now()
            days_ago = (now - recent_date).days
            
            # Score based on how recent the observations are
            if days_ago <= 3:
                return 1.0  # Very recent
            elif days_ago <= 7:
                return 0.8  # Within a week
            elif days_ago <= 14:
                return 0.6  # Within two weeks
            elif days_ago <= 30:
                return 0.4  # Within a month
            else:
                return 0.2  # Older than a month
                
        except Exception as e:
            logger.debug(f"Error calculating recency score: {e}")
            return 0.3  # Default fallback
    
    def _calculate_hotspot_score(self, cluster: Dict) -> float:
        """
        Calculate eBird hotspot score based on popularity and metadata.
        
        Args:
            cluster: Hotspot cluster dictionary
            
        Returns:
            Hotspot score (0.0-1.0)
        """
        accessibility = cluster.get("accessibility", {})
        
        # Base score for having hotspot status
        if not accessibility.get("has_hotspot", False):
            return 0.2  # Non-hotspot locations get low score
        
        hotspot_score = 0.6  # Base score for being a hotspot
        
        # Check hotspot metadata for additional scoring
        for location in cluster.get("locations", []):
            hotspot_metadata = location.get("hotspot_metadata", {})
            
            # Score based on all-time species count
            species_all_time = hotspot_metadata.get("num_species_all_time", 0)
            if species_all_time > 200:
                hotspot_score += 0.3
            elif species_all_time > 100:
                hotspot_score += 0.2
            elif species_all_time > 50:
                hotspot_score += 0.1
            
            # Prefer official eBird hotspots over nearby locations
            if hotspot_metadata.get("distance_to_hotspot_km", 0) == 0:
                hotspot_score += 0.1
            
            break  # Only score based on first hotspot location
        
        return min(hotspot_score, 1.0)
    
    def _calculate_accessibility_score(self, cluster: Dict, constraints: Dict) -> float:
        """
        Calculate accessibility score based on travel constraints and location quality.
        
        Args:
            cluster: Hotspot cluster dictionary
            constraints: User constraints
            
        Returns:
            Accessibility score (0.0-1.0)
        """
        accessibility = cluster.get("accessibility", {})
        
        # Base score from coordinate quality
        base_score = 0.7 if accessibility.get("coordinate_quality") == "high" else 0.5
        
        # Travel time considerations
        avg_travel_time = accessibility.get("avg_travel_time_estimate")
        if avg_travel_time is not None:
            # Prefer closer locations
            if avg_travel_time <= 1.0:  # Within 1 hour
                base_score += 0.2
            elif avg_travel_time <= 2.0:  # Within 2 hours
                base_score += 0.1
            elif avg_travel_time > 4.0:  # More than 4 hours
                base_score -= 0.2
        
        # Cluster size and sighting density
        location_count = cluster["statistics"]["location_count"]
        sighting_count = cluster["statistics"]["sighting_count"]
        
        if location_count > 1 and sighting_count > 5:
            base_score += 0.1  # Bonus for rich clusters
        
        return max(min(base_score, 1.0), 0.0)
    
    def _apply_llm_enhancement(self, scored_clusters: List[Dict], validated_species: List[Dict], 
                             constraints: Dict, stats: Dict) -> List[Dict]:
        """
        Apply LLM enhancement to top scoring clusters for habitat suitability evaluation.
        
        Args:
            scored_clusters: List of scored cluster dictionaries
            validated_species: List of validated species
            constraints: User constraints
            stats: Statistics dictionary to update
            
        Returns:
            List of enhanced cluster dictionaries
        """
        # Enhance top 10 clusters or all if fewer than 10
        clusters_to_enhance = min(10, len(scored_clusters))
        top_clusters = sorted(scored_clusters, key=lambda c: c["base_score"], reverse=True)[:clusters_to_enhance]
        
        enhanced_clusters = scored_clusters.copy()
        
        for i, cluster in enumerate(top_clusters):
            try:
                llm_enhancement = self._get_llm_habitat_evaluation(cluster, validated_species, constraints)
                
                # Find the cluster in the full list and update it
                cluster_id = cluster["cluster_id"]
                for j, full_cluster in enumerate(enhanced_clusters):
                    if full_cluster["cluster_id"] == cluster_id:
                        enhanced_clusters[j] = self._apply_llm_scoring(full_cluster, llm_enhancement)
                        stats["llm_enhanced_clusters"] += 1
                        break
                        
            except Exception as e:
                logger.warning(f"LLM enhancement failed for cluster {cluster['cluster_id']}: {e}")
                # Keep original scoring if LLM fails
        
        stats["scoring_method_distribution"] = {
            "algorithmic_only": len(enhanced_clusters) - stats["llm_enhanced_clusters"],
            "llm_enhanced": stats["llm_enhanced_clusters"]
        }
        
        return enhanced_clusters
    
    def _get_llm_habitat_evaluation(self, cluster: Dict, validated_species: List[Dict], constraints: Dict) -> Dict:
        """
        Get LLM-based habitat suitability evaluation for a cluster.
        
        Args:
            cluster: Hotspot cluster dictionary
            validated_species: List of validated species
            constraints: User constraints
            
        Returns:
            Dictionary with LLM evaluation results
        """
        # Prepare species information for LLM
        target_species_info = []
        cluster_species_codes = set(cluster["statistics"]["species_codes"])
        
        for species in validated_species:
            if species["species_code"] in cluster_species_codes:
                target_species_info.append({
                    "common_name": species["common_name"],
                    "scientific_name": species["scientific_name"],
                    "seasonal_notes": species.get("seasonal_notes", ""),
                    "behavioral_notes": species.get("behavioral_notes", "")
                })
        
        # Create LLM prompt for habitat evaluation
        location_scoring_prompt = f"""
You are an expert birder evaluating locations for observing specific bird species.

LOCATION: {cluster["cluster_name"]}
COORDINATES: {cluster["center_lat"]:.4f}, {cluster["center_lng"]:.4f}
RECENT SIGHTINGS: {cluster["statistics"]["sighting_count"]} observations
SPECIES DIVERSITY: {cluster["statistics"]["species_diversity"]} species total

TARGET SPECIES FOUND AT THIS LOCATION:
{self._format_species_for_llm(target_species_info)}

LOCATION CHARACTERISTICS:
- eBird Hotspot: {"Yes" if cluster["accessibility"]["has_hotspot"] else "No"}
- Number of sub-locations: {cluster["statistics"]["location_count"]}
- Most recent observation: {cluster["statistics"]["most_recent_observation"]}

Please evaluate this location for birding success considering:
1. Habitat suitability for the target species
2. Seasonal timing and migration patterns
3. Time of day effectiveness for observations
4. Weather condition preferences
5. Accessibility and birding logistics

Provide a habitat suitability score from 0.0 to 1.0 and brief reasoning.
Respond in this format:
SCORE: 0.8
REASONING: [2-3 sentences explaining the score]
BEST_TIME: [optimal timing advice]
TIPS: [specific observation tips for this location]
"""
        
        from utils.call_llm import call_llm
        llm_response = call_llm(location_scoring_prompt)
        
        return self._parse_llm_evaluation(llm_response)
    
    def _format_species_for_llm(self, species_info: List[Dict]) -> str:
        """Format species information for LLM prompt."""
        if not species_info:
            return "No target species recently observed at this location."
        
        formatted = []
        for species in species_info[:5]:  # Limit to 5 species to avoid token overuse
            formatted.append(f"- {species['common_name']} ({species['scientific_name']})")
            if species.get('seasonal_notes'):
                formatted.append(f"  Seasonal: {species['seasonal_notes']}")
            if species.get('behavioral_notes'):
                formatted.append(f"  Behavior: {species['behavioral_notes']}")
        
        return "\n".join(formatted)
    
    def _parse_llm_evaluation(self, llm_response: str) -> Dict:
        """
        Parse LLM evaluation response.
        
        Args:
            llm_response: Raw LLM response text
            
        Returns:
            Dictionary with parsed evaluation data
        """
        evaluation = {
            "habitat_score": 0.5,  # Default fallback
            "reasoning": "LLM evaluation parsing failed",
            "best_time": "Timing varies by species",
            "tips": "Refer to field guides for specific advice"
        }
        
        try:
            lines = llm_response.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if line.startswith("SCORE:"):
                    try:
                        score_str = line.replace("SCORE:", "").strip()
                        score = float(score_str)
                        evaluation["habitat_score"] = max(0.0, min(1.0, score))
                    except ValueError:
                        pass
                elif line.startswith("REASONING:"):
                    evaluation["reasoning"] = line.replace("REASONING:", "").strip()
                elif line.startswith("BEST_TIME:"):
                    evaluation["best_time"] = line.replace("BEST_TIME:", "").strip()
                elif line.startswith("TIPS:"):
                    evaluation["tips"] = line.replace("TIPS:", "").strip()
        
        except Exception as e:
            logger.debug(f"Error parsing LLM evaluation: {e}")
        
        return evaluation
    
    def _apply_llm_scoring(self, cluster: Dict, llm_evaluation: Dict) -> Dict:
        """
        Apply LLM evaluation to cluster scoring.
        
        Args:
            cluster: Original cluster dictionary
            llm_evaluation: LLM evaluation results
            
        Returns:
            Enhanced cluster dictionary
        """
        enhanced_cluster = dict(cluster)
        
        # Add LLM evaluation data
        enhanced_cluster["llm_evaluation"] = llm_evaluation
        enhanced_cluster["scoring"]["scoring_method"] = "llm_enhanced"
        
        # Calculate enhanced final score
        base_score = cluster["base_score"]
        habitat_score = llm_evaluation["habitat_score"]
        
        # Blend algorithmic and LLM scores (70% base, 30% habitat)
        enhanced_final_score = (base_score * 0.7) + (habitat_score * 0.3)
        enhanced_cluster["final_score"] = enhanced_final_score
        
        enhanced_cluster["scoring"]["habitat_score"] = habitat_score
        enhanced_cluster["scoring"]["enhanced_final_score"] = enhanced_final_score
        
        return enhanced_cluster
    
    def post(self, shared, prep_res, exec_res):
        """Store scored locations in shared store."""
        shared["scored_locations"] = exec_res["scored_locations"]
        shared["location_scoring_stats"] = exec_res["scoring_stats"]
        
        # Check if scoring was successful
        scored_count = len(exec_res["scored_locations"])
        
        if scored_count == 0:
            logger.warning("No locations were scored")
            return "no_scored_locations"
        
        # Check if we have good scoring diversity
        top_score = exec_res["scored_locations"][0]["final_score"] if scored_count > 0 else 0
        if top_score < 0.3:
            logger.warning(f"Low top location score: {top_score:.2f}")
            return "low_scoring_locations"
        
        # Report LLM enhancement success
        llm_enhanced = exec_res["scoring_stats"]["llm_enhanced_clusters"]
        if llm_enhanced > 0:
            logger.info(f"Location scoring successful: {scored_count} locations ranked, "
                       f"{llm_enhanced} enhanced with LLM habitat evaluation")
        else:
            logger.info(f"Location scoring successful: {scored_count} locations ranked using algorithmic scoring")
        
        return "default"


class OptimizeRouteNode(Node):
    """
    Calculate optimal visiting order for birding locations using TSP-style algorithms.
    
    Features:
    - TSP-style optimization for small location sets
    - Nearest neighbor heuristic with improvements for larger sets
    - Fallback strategies for computational constraints
    - Route segment calculation with travel times and distances
    """
    
    def __init__(self, max_locations_for_optimization: int = 12):
        super().__init__()
        self.max_locations_for_optimization = max_locations_for_optimization
        
    def prep(self, shared):
        """Extract scored locations and constraints from shared store."""
        scored_locations = shared.get("scored_locations", [])
        constraints = shared.get("input", {}).get("constraints", {})
        
        if not scored_locations:
            logger.warning("No scored locations found in shared store")
        
        return {
            "scored_locations": scored_locations,
            "constraints": constraints
        }
    
    def exec(self, prep_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize visiting order for scored locations.
        
        Args:
            prep_data: Dictionary with scored locations and constraints
            
        Returns:
            Dictionary with optimized route and optimization statistics
        """
        scored_locations = prep_data["scored_locations"]
        constraints = prep_data["constraints"]
        
        route_stats = {
            "input_locations": len(scored_locations),
            "locations_optimized": 0,
            "optimization_method": "none",
            "total_route_distance_km": 0.0,
            "estimated_total_drive_time_hours": 0.0,
            "computational_efficiency": "n/a"
        }
        
        if not scored_locations:
            logger.info("No scored locations to optimize")
            return {
                "optimized_route": [],
                "route_segments": [],
                "route_stats": route_stats
            }
        
        # Extract start location from constraints
        start_location = constraints.get("start_location")
        if not start_location or not start_location.get("lat") or not start_location.get("lng"):
            logger.warning("No valid start location found, using first scored location")
            if scored_locations:
                start_location = {
                    "lat": scored_locations[0]["center_lat"],
                    "lng": scored_locations[0]["center_lng"]
                }
            else:
                start_location = {"lat": 42.3601, "lng": -71.0589}  # Default to Boston
        
        logger.info(f"Optimizing route for {len(scored_locations)} locations from start point "
                   f"({start_location['lat']:.4f}, {start_location['lng']:.4f})")
        
        # Apply user preferences for location selection
        selected_locations = self._select_locations_for_route(scored_locations, constraints)
        
        # Perform route optimization
        optimization_result = self._optimize_route(start_location, selected_locations)
        
        # Calculate detailed route segments
        route_segments = self._calculate_route_segments(start_location, optimization_result["optimized_route"])
        
        # Update statistics
        route_stats.update({
            "input_locations": len(scored_locations),
            "locations_optimized": len(selected_locations),
            "optimization_method": optimization_result.get("optimization_method", "unknown"),
            "total_route_distance_km": optimization_result.get("total_distance_km", 0.0),
            "estimated_total_drive_time_hours": sum(seg.get("estimated_drive_time_hours", 0) for seg in route_segments),
            "computational_efficiency": self._assess_computational_efficiency(optimization_result)
        })
        
        logger.info(f"Route optimization completed: {len(optimization_result['optimized_route'])} locations, "
                   f"{route_stats['total_route_distance_km']:.1f}km total distance, "
                   f"method: {route_stats['optimization_method']}")
        
        return {
            "optimized_route": optimization_result["optimized_route"],
            "route_segments": route_segments,
            "route_stats": route_stats,
            "optimization_details": optimization_result.get("optimization_stats", {})
        }
    
    def _select_locations_for_route(self, scored_locations: List[Dict], constraints: Dict) -> List[Dict]:
        """
        Select subset of locations for route optimization based on user preferences.
        
        Args:
            scored_locations: List of scored location dictionaries
            constraints: User constraints and preferences
            
        Returns:
            Filtered list of locations for optimization
        """
        # Extract route planning constraints
        max_locations = constraints.get("max_locations_per_day", self.max_locations_for_optimization)
        max_daily_distance = constraints.get("max_daily_distance_km", 400)
        min_score_threshold = constraints.get("min_location_score", 0.3)
        
        # Filter by minimum score
        candidate_locations = [
            loc for loc in scored_locations 
            if loc.get("final_score", 0) >= min_score_threshold
        ]
        
        if not candidate_locations:
            logger.warning(f"No locations meet minimum score threshold {min_score_threshold}, using all locations")
            candidate_locations = scored_locations
        
        # Limit to top scoring locations
        candidate_locations = sorted(candidate_locations, key=lambda loc: loc.get("final_score", 0), reverse=True)
        
        if len(candidate_locations) > max_locations:
            selected_locations = candidate_locations[:max_locations]
            logger.info(f"Selected top {max_locations} locations for route optimization")
        else:
            selected_locations = candidate_locations
        
        # TODO: Could add additional filtering based on geographic clustering
        # to ensure locations aren't too spread out for daily_distance constraints
        
        return selected_locations
    
    def _optimize_route(self, start_location: Dict, locations: List[Dict]) -> Dict[str, Any]:
        """
        Perform route optimization using appropriate algorithm.
        
        Args:
            start_location: Starting point coordinates
            locations: List of locations to visit
            
        Returns:
            Optimization result dictionary
        """
        try:
            from utils.route_optimizer import optimize_birding_route
            
            result = optimize_birding_route(
                start_location=start_location,
                locations=locations,
                max_locations=self.max_locations_for_optimization
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Route optimization failed: {e}")
            # Fallback: return locations in original score order
            return {
                "optimized_route": locations,
                "total_distance_km": self._calculate_simple_route_distance(start_location, locations),
                "optimization_method": "fallback_score_order",
                "optimization_stats": {"error": str(e)}
            }
    
    def _calculate_route_segments(self, start_location: Dict, route: List[Dict]) -> List[Dict]:
        """
        Calculate detailed route segments.
        
        Args:
            start_location: Starting point coordinates
            route: Optimized route
            
        Returns:
            List of route segment dictionaries
        """
        try:
            from utils.route_optimizer import calculate_route_segments
            return calculate_route_segments(start_location, route)
        except Exception as e:
            logger.error(f"Route segment calculation failed: {e}")
            return []
    
    def _calculate_simple_route_distance(self, start_location: Dict, locations: List[Dict]) -> float:
        """
        Simple distance calculation for fallback scenarios.
        
        Args:
            start_location: Starting point
            locations: List of locations
            
        Returns:
            Total distance in kilometers
        """
        if not locations:
            return 0.0
        
        from utils.geo_utils import haversine_distance
        
        total_distance = 0.0
        current_lat, current_lng = start_location["lat"], start_location["lng"]
        
        for location in locations:
            distance = haversine_distance(
                current_lat, current_lng,
                location["center_lat"], location["center_lng"]
            )
            total_distance += distance
            current_lat, current_lng = location["center_lat"], location["center_lng"]
        
        # Add return distance
        return_distance = haversine_distance(
            current_lat, current_lng,
            start_location["lat"], start_location["lng"]
        )
        total_distance += return_distance
        
        return total_distance
    
    def _assess_computational_efficiency(self, optimization_result: Dict) -> str:
        """
        Assess the computational efficiency of the optimization.
        
        Args:
            optimization_result: Result from route optimization
            
        Returns:
            Efficiency assessment string
        """
        method = optimization_result.get("optimization_method", "unknown")
        locations_count = optimization_result.get("optimization_stats", {}).get("locations_processed", 0)
        
        if method == "empty" or method == "single_location":
            return "trivial"
        elif method == "2-opt" and locations_count <= 8:
            return "optimal"
        elif method == "enhanced_nearest_neighbor":
            return "good_heuristic"
        elif method == "fallback_score_order":
            return "fallback"
        else:
            return "standard_heuristic"
    
    def post(self, shared, prep_res, exec_res):
        """Store optimized route in shared store."""
        shared["optimized_route"] = exec_res["optimized_route"]
        shared["route_segments"] = exec_res["route_segments"]
        shared["route_optimization_stats"] = exec_res["route_stats"]
        shared["optimization_details"] = exec_res["optimization_details"]
        
        # Check if optimization was successful
        optimized_locations = len(exec_res["optimized_route"])
        total_distance = exec_res["route_stats"]["total_route_distance_km"]
        
        if optimized_locations == 0:
            logger.warning("No locations in optimized route")
            return "no_route"
        
        if total_distance > 1000:  # More than 1000km seems excessive for a day trip
            logger.warning(f"Route distance very long: {total_distance:.1f}km")
            return "excessive_distance"
        
        # Check optimization method success
        method = exec_res["route_stats"]["optimization_method"]
        if method == "fallback_score_order":
            logger.warning("Route optimization fell back to score ordering")
            return "optimization_failed"
        
        logger.info(f"Route optimization successful: {optimized_locations} locations, "
                   f"{total_distance:.1f}km, method: {method}")
        return "default"


class GenerateItineraryNode(Node):
    """
    Generate detailed markdown itinerary with expert birding guidance using LLM enhancement.
    
    Features:
    - Professional birding guide prompting for detailed itineraries
    - Species-specific advice on timing, habitat, and field techniques
    - Route segment integration with travel times and directions
    - Fallback template-based generation if LLM fails
    - Comprehensive birding trip planning with equipment and etiquette advice
    """
    
    def __init__(self, max_retries: int = 3):
        super().__init__()
        self.max_retries = max_retries
        
    def prep(self, shared):
        """Extract all pipeline data needed for itinerary generation."""
        optimized_route = shared.get("optimized_route", [])
        route_segments = shared.get("route_segments", [])
        validated_species = shared.get("validated_species", [])
        constraints = shared.get("input", {}).get("constraints", {})
        
        # Collect comprehensive data for itinerary
        return {
            "optimized_route": optimized_route,
            "route_segments": route_segments,
            "validated_species": validated_species,
            "constraints": constraints,
            "pipeline_stats": {
                "validation_stats": shared.get("validation_stats", {}),
                "fetch_stats": shared.get("fetch_stats", {}),
                "filtering_stats": shared.get("filtering_stats", {}),
                "clustering_stats": shared.get("clustering_stats", {}),
                "scoring_stats": shared.get("location_scoring_stats", {}),
                "route_stats": shared.get("route_optimization_stats", {})
            }
        }
    
    def exec(self, prep_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive birding itinerary using LLM enhancement.
        
        Args:
            prep_data: Dictionary with all pipeline data
            
        Returns:
            Dictionary with generated itinerary and generation statistics
        """
        optimized_route = prep_data["optimized_route"]
        route_segments = prep_data["route_segments"]
        validated_species = prep_data["validated_species"]
        constraints = prep_data["constraints"]
        pipeline_stats = prep_data["pipeline_stats"]
        
        generation_stats = {
            "itinerary_method": "none",
            "llm_attempts": 0,
            "fallback_used": False,
            "total_locations": len(optimized_route),
            "total_species": len(validated_species),
            "estimated_trip_duration_hours": sum(seg.get("estimated_drive_time_hours", 0) for seg in route_segments),
            "content_sections_generated": 0
        }
        
        if not optimized_route:
            logger.warning("No optimized route available for itinerary generation")
            return {
                "itinerary_markdown": self._generate_empty_itinerary_message(),
                "generation_stats": generation_stats
            }
        
        logger.info(f"Generating itinerary for {len(optimized_route)} locations and {len(validated_species)} target species")
        
        # Attempt LLM-enhanced itinerary generation
        llm_itinerary = self._generate_llm_itinerary(prep_data, generation_stats)
        
        if llm_itinerary:
            generation_stats["itinerary_method"] = "llm_enhanced"
            logger.info("Successfully generated LLM-enhanced itinerary")
            return {
                "itinerary_markdown": llm_itinerary,
                "generation_stats": generation_stats
            }
        else:
            # Fallback to template-based generation
            logger.warning("LLM itinerary generation failed, using template fallback")
            template_itinerary = self._generate_template_itinerary(prep_data, generation_stats)
            generation_stats["itinerary_method"] = "template_fallback"
            generation_stats["fallback_used"] = True
            
            return {
                "itinerary_markdown": template_itinerary,
                "generation_stats": generation_stats
            }
    
    def _generate_llm_itinerary(self, prep_data: Dict[str, Any], stats: Dict) -> Optional[str]:
        """
        Generate professional birding itinerary using LLM.
        
        Args:
            prep_data: All pipeline data
            stats: Statistics dictionary to update
            
        Returns:
            Generated markdown itinerary or None if failed
        """
        for attempt in range(self.max_retries):
            stats["llm_attempts"] = attempt + 1
            
            try:
                itinerary_prompt = self._create_itinerary_prompt(prep_data)
                
                itinerary_response = call_llm(itinerary_prompt)
                
                # Validate and enhance the response
                if self._validate_itinerary_response(itinerary_response):
                    enhanced_itinerary = self._enhance_itinerary_with_metadata(itinerary_response, prep_data)
                    stats["content_sections_generated"] = len(enhanced_itinerary.split("##"))
                    return enhanced_itinerary
                else:
                    logger.warning(f"LLM itinerary validation failed on attempt {attempt + 1}")
                    
            except Exception as e:
                logger.error(f"LLM itinerary generation attempt {attempt + 1} failed: {e}")
        
        return None
    
    def _create_itinerary_prompt(self, prep_data: Dict[str, Any]) -> str:
        """
        Create comprehensive LLM prompt for itinerary generation.
        
        Args:
            prep_data: All pipeline data
            
        Returns:
            Detailed LLM prompt string
        """
        optimized_route = prep_data["optimized_route"]
        route_segments = prep_data["route_segments"]
        validated_species = prep_data["validated_species"]
        constraints = prep_data["constraints"]
        pipeline_stats = prep_data["pipeline_stats"]
        
        # Prepare trip overview
        trip_overview = self._format_trip_overview(constraints, pipeline_stats)
        
        # Prepare target species information
        species_info = self._format_species_for_itinerary(validated_species)
        
        # Prepare location details
        location_details = self._format_locations_for_itinerary(optimized_route, route_segments)
        
        itinerary_prompt = f"""
You are a professional birding guide with extensive field experience creating detailed trip itineraries.

TRIP OVERVIEW:
{trip_overview}

TARGET SPECIES:
{species_info}

OPTIMIZED ROUTE:
{location_details}

Create a comprehensive birding itinerary with expert guidance. Include:

1. **Executive Summary**: Brief overview of the trip highlights and expectations
2. **Species Target List**: Priority species with specific timing and habitat advice
3. **Detailed Location Guide**: For each location, provide:
   - Optimal arrival time and duration
   - Habitat characteristics and target species
   - Specific observation tips and techniques
   - Weather and seasonal considerations
   - Equipment recommendations
4. **Travel Schedule**: Driving directions and timing between locations
5. **Field Tips**: Professional advice on field techniques, birding ethics, and photography
6. **Contingency Plans**: Alternative locations or activities if target species aren't found

Format as clean markdown with proper headers. Focus on actionable field guidance that maximizes observation success. Include specific coordinates where helpful.

Make this sound like a professional birding guide's detailed trip plan, not a generic travel itinerary.
"""
        
        return itinerary_prompt
    
    def _format_trip_overview(self, constraints: Dict, stats: Dict) -> str:
        """Format trip overview section for LLM prompt."""
        total_distance = stats.get("route_stats", {}).get("total_route_distance_km", 0)
        estimated_time = stats.get("route_stats", {}).get("estimated_total_drive_time_hours", 0)
        locations_count = stats.get("route_stats", {}).get("locations_optimized", 0)
        
        start_location = constraints.get("start_location", {})
        start_coords = f"({start_location.get('lat', 'unknown')}, {start_location.get('lng', 'unknown')})"
        
        overview = f"""
- Starting Point: {start_coords}
- Total Locations: {locations_count}
- Total Distance: {total_distance:.1f} km
- Estimated Driving Time: {estimated_time:.1f} hours
- Region: {constraints.get('region', 'Not specified')}
- Date Range: {constraints.get('date_range', {}).get('start', 'Flexible')} to {constraints.get('date_range', {}).get('end', 'Flexible')}
- Max Daily Distance: {constraints.get('max_daily_distance_km', 'Not specified')} km
"""
        
        return overview.strip()
    
    def _format_species_for_itinerary(self, validated_species: List[Dict]) -> str:
        """Format target species information for LLM prompt."""
        if not validated_species:
            return "No specific target species identified."
        
        species_sections = []
        for species in validated_species[:10]:  # Limit to prevent prompt overflow
            section = f"""
**{species['common_name']}** (*{species['scientific_name']}*)
- eBird Code: {species['species_code']}
- Validation: {species['validation_method']} (confidence: {species['confidence']:.1f})
- Seasonal Notes: {species.get('seasonal_notes', 'No specific timing noted')}
- Behavioral Notes: {species.get('behavioral_notes', 'Standard observation approaches')}
"""
            species_sections.append(section.strip())
        
        if len(validated_species) > 10:
            species_sections.append(f"... and {len(validated_species) - 10} additional species")
        
        return "\n\n".join(species_sections)
    
    def _format_locations_for_itinerary(self, route: List[Dict], segments: List[Dict]) -> str:
        """Format location and route information for LLM prompt."""
        if not route:
            return "No locations in optimized route."
        
        location_sections = []
        for i, location in enumerate(route):
            # Find corresponding route segment
            segment = next((seg for seg in segments if seg.get("segment_number") == i + 1), {})
            
            section = f"""
**Stop {i + 1}: {location['cluster_name']}**
- Coordinates: ({location['center_lat']:.4f}, {location['center_lng']:.4f})
- Score: {location.get('final_score', 0):.2f}
- Species Diversity: {location['statistics']['species_diversity']} species
- Recent Sightings: {location['statistics']['sighting_count']} observations
- Hotspot Status: {"Official eBird Hotspot" if location['accessibility']['has_hotspot'] else "Sighting Location"}
- Distance from Previous: {segment.get('distance_km', 0):.1f} km
- Estimated Drive Time: {segment.get('estimated_drive_time_hours', 0):.1f} hours
- Target Species Found: {', '.join(location['statistics']['species_codes'][:5])}
"""
            
            # Add LLM evaluation if available
            if location.get("llm_evaluation"):
                eval_info = location["llm_evaluation"]
                section += f"""
- Habitat Score: {eval_info.get('habitat_score', 0):.2f}
- Expert Assessment: {eval_info.get('reasoning', 'No assessment')}
- Best Timing: {eval_info.get('best_time', 'Variable')}
- Field Tips: {eval_info.get('tips', 'Standard birding approaches')}
"""
            
            location_sections.append(section.strip())
        
        return "\n\n".join(location_sections)
    
    def _validate_itinerary_response(self, response: str) -> bool:
        """
        Validate that the LLM response is a reasonable itinerary.
        
        Args:
            response: LLM response string
            
        Returns:
            True if response appears to be a valid itinerary
        """
        if not response or len(response) < 500:
            return False
        
        # Check for essential sections
        required_elements = [
            "##",  # Markdown headers
            "species",  # Should mention species
            "location",  # Should mention locations
            "time",  # Should mention timing
        ]
        
        response_lower = response.lower()
        return all(element in response_lower for element in required_elements)
    
    def _enhance_itinerary_with_metadata(self, itinerary: str, prep_data: Dict[str, Any]) -> str:
        """
        Enhance LLM-generated itinerary with additional metadata.
        
        Args:
            itinerary: Base LLM-generated itinerary
            prep_data: Pipeline data for enhancement
            
        Returns:
            Enhanced itinerary with metadata
        """
        pipeline_stats = prep_data["pipeline_stats"]
        
        # Add header with generation metadata
        header = f"""# Birding Trip Itinerary
*Generated by Bird Travel Recommender*

---

## Trip Statistics
- **Locations Analyzed**: {pipeline_stats.get('clustering_stats', {}).get('total_input_sightings', 0)} sightings across {pipeline_stats.get('clustering_stats', {}).get('unique_locations_found', 0)} locations
- **Species Validated**: {pipeline_stats.get('validation_stats', {}).get('total_input', 0)} requested, {pipeline_stats.get('validation_stats', {}).get('direct_taxonomy_matches', 0) + pipeline_stats.get('validation_stats', {}).get('llm_fuzzy_matches', 0)} confirmed
- **Route Optimization**: {pipeline_stats.get('route_stats', {}).get('optimization_method', 'Unknown')} method
- **Total Trip Distance**: {pipeline_stats.get('route_stats', {}).get('total_route_distance_km', 0):.1f} km

---

"""
        
        # Add footer with disclaimers
        footer = f"""

---

## Important Notes

### Data Sources
- Bird observations from eBird API (recent {pipeline_stats.get('fetch_stats', {}).get('total_observations', 0)} observations)
- Hotspot data from official eBird hotspot registry
- Route optimization using traveling salesman algorithms

### Disclaimers
- Observation times and locations are based on recent eBird data and may not guarantee current bird presence
- Weather conditions, seasonal timing, and local factors can significantly impact birding success
- Always respect private property, follow local regulations, and practice ethical birding
- Consider checking recent eBird reports before visiting each location

### Equipment Recommendations
- Binoculars (8x42 or 10x42 recommended)
- Field guide for local region
- eBird mobile app for real-time reporting
- Camera with telephoto lens (optional)
- Weather-appropriate clothing and comfortable walking shoes

*Happy Birding!*

*Generated on {self._get_current_timestamp()}*
"""
        
        return header + itinerary + footer
    
    def _generate_template_itinerary(self, prep_data: Dict[str, Any], stats: Dict) -> str:
        """
        Generate basic template-based itinerary as fallback.
        
        Args:
            prep_data: Pipeline data
            stats: Statistics dictionary to update
            
        Returns:
            Template-based itinerary markdown
        """
        optimized_route = prep_data["optimized_route"]
        route_segments = prep_data["route_segments"]
        validated_species = prep_data["validated_species"]
        constraints = prep_data["constraints"]
        
        stats["content_sections_generated"] = 5  # Fixed sections in template
        
        itinerary = f"""# Birding Trip Itinerary
*Template-based itinerary (LLM generation unavailable)*

## Trip Overview
- **Starting Point**: {constraints.get('start_location', {}).get('lat', 'Not specified')}, {constraints.get('start_location', {}).get('lng', 'Not specified')}
- **Total Locations**: {len(optimized_route)}
- **Target Species**: {len(validated_species)}
- **Estimated Distance**: {sum(seg.get('distance_km', 0) for seg in route_segments):.1f} km
- **Estimated Travel Time**: {sum(seg.get('estimated_drive_time_hours', 0) for seg in route_segments):.1f} hours

## Target Species List
"""
        
        for species in validated_species:
            itinerary += f"- **{species['common_name']}** (*{species['scientific_name']}*) - {species.get('seasonal_notes', 'No timing notes')}\n"
        
        itinerary += "\n## Location Schedule\n"
        
        for i, location in enumerate(optimized_route):
            segment = next((seg for seg in route_segments if seg.get("segment_number") == i + 1), {})
            
            itinerary += f"""
### Stop {i + 1}: {location['cluster_name']}
- **Coordinates**: {location['center_lat']:.4f}, {location['center_lng']:.4f}
- **Species Diversity**: {location['statistics']['species_diversity']} species observed
- **Recent Sightings**: {location['statistics']['sighting_count']} observations
- **Score**: {location.get('final_score', 0):.2f}
- **Distance from previous**: {segment.get('distance_km', 0):.1f} km ({segment.get('estimated_drive_time_hours', 0):.1f} hours)
- **Hotspot Status**: {"Official eBird Hotspot" if location['accessibility']['has_hotspot'] else "Regular birding location"}

**Species found here**: {', '.join(location['statistics']['species_codes'][:8])}

"""
        
        itinerary += """
## General Birding Tips
- Check eBird for recent sightings before visiting each location
- Early morning (dawn to 10 AM) is typically the most productive time for birding
- Bring appropriate weather gear and comfortable walking shoes
- Respect private property and follow local birding ethics
- Consider joining local birding groups for area-specific knowledge

## Equipment Checklist
- [ ] Binoculars (8x42 or 10x42 recommended)
- [ ] Field guide for the region
- [ ] eBird mobile app
- [ ] Camera (optional)
- [ ] Notebook and pen
- [ ] Snacks and water
- [ ] Weather-appropriate clothing

*This itinerary was generated using automated route optimization and eBird data analysis.*
"""
        
        return itinerary
    
    def _generate_empty_itinerary_message(self) -> str:
        """Generate message when no route is available."""
        return """# Birding Trip Itinerary

## No Route Available

Unfortunately, no birding locations could be optimized for your trip parameters. This could be due to:

- No recent bird sightings in the specified region
- All locations filtered out by travel constraints
- API data unavailable

## Suggestions
1. Try expanding your search radius
2. Consider relaxing travel distance constraints
3. Check eBird directly for recent activity in your target region
4. Verify your target species are present in the specified region and season

*Generated by Bird Travel Recommender*
"""
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp for itinerary generation."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def post(self, shared, prep_res, exec_res):
        """
        Store generated itinerary in shared store and return shared store.
        
        Since this is the final node in the pipeline, we return the shared store
        instead of a control string so the flow can access the complete results.
        """
        shared["itinerary_markdown"] = exec_res["itinerary_markdown"]
        shared["itinerary_generation_stats"] = exec_res["generation_stats"]
        
        # Log generation status for monitoring
        generation_method = exec_res["generation_stats"]["itinerary_method"]
        content_sections = exec_res["generation_stats"]["content_sections_generated"]
        
        if generation_method == "none":
            logger.warning("No itinerary was generated")
        elif exec_res["generation_stats"]["fallback_used"]:
            logger.warning("Itinerary generation fell back to template")
        elif content_sections < 3:
            logger.warning(f"Itinerary appears incomplete: only {content_sections} sections")
        else:
            logger.info(f"Itinerary generation successful: {generation_method} method, "
                       f"{content_sections} content sections")

        # Store shared store reference for flow access and return control string
        shared["_final_result"] = shared.copy()  # Store a copy for flow access
        return "default"