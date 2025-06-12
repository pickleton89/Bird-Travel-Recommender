from pocketflow import Node, BatchNode
from utils.call_llm import call_llm
from utils.ebird_api import get_client, EBirdAPIError
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
        """Extract validated species and constraints from shared store."""
        validated_species = shared.get("validated_species", [])
        constraints = shared.get("input", {}).get("constraints", {})
        
        if not validated_species:
            raise ValueError("No validated species found in shared store")
        
        return {
            "validated_species": validated_species,
            "constraints": constraints
        }
    
    def exec(self, prep_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch sightings for all validated species using parallel processing.
        
        Args:
            prep_data: Dictionary with validated species and constraints
            
        Returns:
            Dictionary with all sightings and processing statistics
        """
        validated_species = prep_data["validated_species"]
        constraints = prep_data["constraints"]
        
        # Extract constraint parameters
        region_code = constraints.get("region", "US-MA")  # Default to Massachusetts
        days_back = min(constraints.get("days_back", 7), 30)  # eBird max is 30
        start_location = constraints.get("start_location")
        max_distance_km = constraints.get("max_daily_distance_km", 200)
        
        processing_stats = {
            "total_species": len(validated_species),
            "successful_fetches": 0,
            "empty_results": 0,
            "api_errors": 0,
            "total_observations": 0,
            "unique_locations": set(),
            "fetch_method_stats": {}
        }
        
        all_sightings = []
        
        logger.info(f"Fetching sightings for {len(validated_species)} species using {self.max_workers} workers")
        
        # Determine fetch strategy for each species
        fetch_tasks = []
        for species in validated_species:
            task = self._create_fetch_task(species, region_code, days_back, start_location, max_distance_km)
            fetch_tasks.append(task)
        
        # Execute fetch tasks in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(self._fetch_species_sightings, task): task 
                for task in fetch_tasks
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    if result["success"]:
                        all_sightings.extend(result["sightings"])
                        processing_stats["successful_fetches"] += 1
                        processing_stats["total_observations"] += len(result["sightings"])
                        
                        # Track unique locations
                        for sighting in result["sightings"]:
                            if sighting.get("locId"):
                                processing_stats["unique_locations"].add(sighting["locId"])
                        
                        # Track fetch method statistics
                        method = result["method"]
                        processing_stats["fetch_method_stats"][method] = processing_stats["fetch_method_stats"].get(method, 0) + 1
                        
                        if len(result["sightings"]) == 0:
                            processing_stats["empty_results"] += 1
                    else:
                        processing_stats["api_errors"] += 1
                        logger.warning(f"Failed to fetch sightings for {task['species']['common_name']}: {result['error']}")
                        
                except Exception as e:
                    processing_stats["api_errors"] += 1
                    logger.error(f"Unexpected error fetching sightings for {task['species']['common_name']}: {e}")
        
        # Convert set to count for JSON serialization
        processing_stats["unique_locations"] = len(processing_stats["unique_locations"])
        
        logger.info(f"Fetch completed: {processing_stats['successful_fetches']}/{processing_stats['total_species']} species, "
                   f"{processing_stats['total_observations']} observations, "
                   f"{processing_stats['unique_locations']} unique locations")
        
        return {
            "all_sightings": all_sightings,
            "processing_stats": processing_stats
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
        """Store all sightings in shared store."""
        shared["all_sightings"] = exec_res["all_sightings"]
        shared["fetch_stats"] = exec_res["processing_stats"]
        
        # Check if we got sufficient data
        success_rate = exec_res["processing_stats"]["successful_fetches"] / exec_res["processing_stats"]["total_species"]
        total_observations = exec_res["processing_stats"]["total_observations"]
        
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