"""
Unified Sightings Node - Replaces both sync and async sightings implementations.

This node eliminates the duplication between FetchSightingsNode and AsyncFetchSightingsNode
by providing a single implementation that works in both sync and async modes.
"""

from typing import Dict, Any, List, Optional
import time
import asyncio
from pydantic import BaseModel, Field

from ..base import BaseNode, NodeInput, NodeOutput, BatchProcessingMixin
from ..factory import register_node
from ..mixins import LoggingMixin, ValidationMixin, CachingMixin, MetricsMixin, ErrorHandlingMixin
from ...ebird.client import EBirdClient
from ...exceptions.ebird import EBirdAPIError


class SightingsInput(NodeInput):
    """Input validation for sightings node."""
    
    species_code: Optional[str] = Field(None, description="Specific species code to fetch")
    region_code: str = Field("US-MA", description="eBird region code")
    days_back: int = Field(7, ge=1, le=30, description="Days to look back (1-30)")
    max_results: int = Field(100, ge=1, le=10000, description="Maximum number of results")
    start_location: Optional[Dict[str, float]] = Field(None, description="Starting location with lat/lng")
    max_distance_km: int = Field(200, ge=1, le=1000, description="Maximum distance for nearby searches")


class SightingsOutput(NodeOutput):
    """Output model for sightings node."""
    
    sightings_count: Optional[int] = Field(None, description="Number of sightings found")
    locations_found: Optional[int] = Field(None, description="Number of unique locations")
    species_processed: Optional[int] = Field(None, description="Number of species processed")
    fetch_method_stats: Optional[Dict[str, int]] = Field(None, description="Statistics by fetch method")


@register_node("sightings", aliases=["fetch_sightings", "sightings_fetch"])
class UnifiedSightingsNode(
    BaseNode, 
    BatchProcessingMixin, 
    LoggingMixin, 
    ValidationMixin, 
    CachingMixin, 
    MetricsMixin,
    ErrorHandlingMixin
):
    """
    Unified sightings node that replaces both sync and async versions.
    
    This node fetches recent bird sightings using the eBird API with:
    - Unified sync/async execution through dependency injection
    - Smart endpoint selection (region-wide vs species-specific vs nearby)
    - Batch processing with controlled concurrency
    - Response aggregation and normalization
    - Built-in rate limiting and error recovery
    - Comprehensive metrics and caching
    """
    
    def __init__(self, dependencies, max_workers: int = 5):
        """
        Initialize the unified sightings node.
        
        Args:
            dependencies: Injected dependencies
            max_workers: Maximum concurrent workers for batch processing
        """
        super().__init__(dependencies)
        self.max_workers = max_workers
    
    def validate_input(self, data: Dict[str, Any]) -> SightingsInput:
        """Validate sightings-specific input."""
        
        # Extract constraints from shared store structure
        constraints = data.get("input", {}).get("constraints", {})
        if not constraints:
            constraints = data.get("constraints", {})
        
        # Validate required fields for sightings operations
        self.validate_required_fields(constraints, ["region"])
        
        # Map constraint fields to input model fields
        input_data = {
            "region_code": constraints.get("region", "US-MA"),
            "days_back": min(constraints.get("days_back", 7), 30),
            "start_location": constraints.get("start_location"),
            "max_distance_km": constraints.get("max_daily_distance_km", 200),
        }
        
        return SightingsInput(**input_data)
    
    async def process(self, shared_store: Dict[str, Any]) -> SightingsOutput:
        """
        Core sightings processing logic - unified for both sync/async.
        
        Args:
            shared_store: Shared data store containing validated species and constraints
            
        Returns:
            SightingsOutput with processing results
        """
        self.log_execution_start("sightings_fetch")
        start_time = time.time()
        
        try:
            # Get validated input
            input_data = self.validate_input(shared_store)
            
            # Get validated species from shared store
            validated_species = shared_store.get("validated_species", [])
            if not validated_species:
                return SightingsOutput(
                    success=False,
                    error="No validated species found in shared store",
                    metadata={"warning": "Empty species list provided"}
                )
            
            self.increment_counter("sightings_requests_total", {"species_count": str(len(validated_species))})
            
            # Check cache for this request
            cache_key_params = {
                "species_codes": [s.get("species_code") for s in validated_species],
                "region_code": input_data.region_code,
                "days_back": input_data.days_back,
                "start_location": input_data.start_location
            }
            
            cached_result = await self.get_cached_result("sightings_fetch", **cache_key_params)
            if cached_result:
                self.increment_counter("sightings_cache_hits_total")
                return SightingsOutput(**cached_result)
            
            # Process species in batch with controlled concurrency
            with self.time_operation("sightings_batch_processing"):
                batch_results = await self.process_batch(
                    validated_species,
                    lambda species: self._fetch_species_sightings(species, input_data),
                    max_concurrency=self.max_workers
                )
            
            # Aggregate results
            aggregated_results = self._aggregate_sightings_results(batch_results, validated_species)
            
            # Create output
            output = SightingsOutput(
                success=True,
                data={
                    "all_sightings": aggregated_results["all_sightings"],
                    "fetch_stats": aggregated_results["processing_stats"]
                },
                sightings_count=aggregated_results["processing_stats"]["total_observations"],
                locations_found=aggregated_results["processing_stats"]["unique_locations"],
                species_processed=len(validated_species),
                fetch_method_stats=aggregated_results["processing_stats"]["fetch_method_stats"],
                execution_time_ms=(time.time() - start_time) * 1000
            )
            
            # Cache the result
            await self.set_cached_result(
                "sightings_fetch", 
                output.dict(), 
                ttl=300,  # 5 minutes
                **cache_key_params
            )
            
            # Record metrics
            self.record_gauge("sightings_found_total", aggregated_results["processing_stats"]["total_observations"])
            self.record_gauge("sightings_success_rate", aggregated_results["processing_stats"]["success_rate"])
            
            self.log_execution_end("sightings_fetch", True, output.execution_time_ms, 
                                 sightings_count=output.sightings_count)
            
            return output
            
        except Exception as e:
            error_response = self.handle_api_error(e, "sightings_fetch", 
                                                 species_count=len(shared_store.get("validated_species", [])))
            
            execution_time = (time.time() - start_time) * 1000
            self.log_execution_end("sightings_fetch", False, execution_time)
            
            return SightingsOutput(
                success=False,
                error=str(e),
                execution_time_ms=execution_time,
                metadata={"error_type": type(e).__name__}
            )
    
    async def _fetch_species_sightings(self, species: Dict[str, Any], input_data: SightingsInput) -> Dict[str, Any]:
        """
        Fetch sightings for a single species.
        
        Args:
            species: Validated species dictionary
            input_data: Validated input parameters
            
        Returns:
            Result dictionary for this species
        """
        try:
            # Create fetch task with optimal strategy selection
            task = self._create_fetch_task(species, input_data)
            
            # Execute the API call through the injected eBird client
            sightings = await self._execute_fetch_task(task)
            
            # Enrich sightings with species validation metadata
            enriched_sightings = self._enrich_sightings(sightings, species, task)
            
            self.logger.debug(
                f"Fetched {len(enriched_sightings)} sightings for {species['common_name']} using {task['method']}"
            )
            
            return {
                "success": True,
                "sightings": enriched_sightings,
                "method": task["method"],
                "species_code": species["species_code"],
                "species_name": species["common_name"],
            }
            
        except EBirdAPIError as e:
            return self.handle_api_error(e, "fetch_species_sightings", 
                                       species_code=species["species_code"],
                                       species_name=species["common_name"])
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "sightings": [],
                "species_code": species["species_code"],
                "species_name": species["common_name"],
                "method": "error",
            }
    
    def _create_fetch_task(self, species: Dict[str, Any], input_data: SightingsInput) -> Dict[str, Any]:
        """
        Create a fetch task with optimal strategy selection.
        
        Args:
            species: Validated species dictionary
            input_data: Validated input parameters
            
        Returns:
            Fetch task dictionary with strategy and parameters
        """
        task = {
            "species": species,
            "region_code": input_data.region_code,
            "days_back": input_data.days_back
        }
        
        # Smart endpoint selection based on query type and location
        if (input_data.start_location and 
            input_data.start_location.get("lat") and 
            input_data.start_location.get("lng")):
            # Use nearby observations if we have coordinates
            task["method"] = "nearby_observations"
            task["lat"] = input_data.start_location["lat"]
            task["lng"] = input_data.start_location["lng"]
            task["distance_km"] = min(input_data.max_distance_km // 2, 50)
        else:
            # Use species-specific observations for region
            task["method"] = "species_observations"
        
        return task
    
    async def _execute_fetch_task(self, task: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute the fetch task using the appropriate eBird client method.
        
        Args:
            task: Fetch task configuration
            
        Returns:
            List of sightings from eBird API
        """
        species = task["species"]
        method = task["method"]
        
        # Use the injected eBird client (handles sync/async automatically)
        client = self.deps.ebird_client
        
        if method == "nearby_observations":
            sightings = await client.get_nearby_observations(
                lat=task["lat"],
                lng=task["lng"],
                distance_km=task["distance_km"],
                days_back=task["days_back"],
                species_code=species["species_code"],
            )
        elif method == "species_observations":
            sightings = await client.get_species_observations(
                species_code=species["species_code"],
                region_code=task["region_code"],
                days_back=task["days_back"],
            )
        else:
            raise ValueError(f"Unknown fetch method: {method}")
        
        return sightings
    
    def _enrich_sightings(self, sightings: List[Dict[str, Any]], species: Dict[str, Any], 
                         task: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Enrich sightings with species validation metadata.
        
        Args:
            sightings: Raw sightings from eBird API
            species: Validated species information
            task: Fetch task configuration
            
        Returns:
            Enriched sightings with additional metadata
        """
        enriched_sightings = []
        
        for sighting in sightings:
            enriched_sighting = dict(sighting)  # Copy original sighting
            enriched_sighting.update({
                "fetch_method": task["method"],
                "fetch_timestamp": time.time(),
                "validation_confidence": species.get("confidence", 1.0),
                "validation_method": species.get("validation_method", "unknown"),
                "original_species_name": species.get("original_name", species.get("common_name")),
                "seasonal_notes": species.get("seasonal_notes", ""),
                "behavioral_notes": species.get("behavioral_notes", ""),
            })
            enriched_sightings.append(enriched_sighting)
        
        return enriched_sightings
    
    def _aggregate_sightings_results(self, results: List, species_list: List[Dict]) -> Dict[str, Any]:
        """
        Aggregate results from batch processing.
        
        Args:
            results: List of results from batch processing
            species_list: Original species list for statistics
            
        Returns:
            Aggregated results with statistics
        """
        # Use the mixin method for basic aggregation
        basic_stats = self.aggregate_batch_results(results, len(species_list))
        
        # Additional sightings-specific aggregation
        all_sightings = []
        unique_locations = set()
        fetch_method_stats = {}
        total_observations = 0
        
        for result in basic_stats["successful_results"]:
            sightings = result.get("sightings", [])
            all_sightings.extend(sightings)
            total_observations += len(sightings)
            
            # Track unique locations
            for sighting in sightings:
                if sighting.get("locId"):
                    unique_locations.add(sighting["locId"])
            
            # Track fetch method statistics
            method = result.get("method", "unknown")
            fetch_method_stats[method] = fetch_method_stats.get(method, 0) + 1
        
        # Enhanced processing statistics
        processing_stats = {
            **basic_stats,
            "total_observations": total_observations,
            "unique_locations": len(unique_locations),
            "fetch_method_stats": fetch_method_stats,
            "execution_mode": self.deps.execution_mode.value,
        }
        
        return {
            "all_sightings": all_sightings,
            "processing_stats": processing_stats
        }