"""
AsyncFetchSightingsNode: Async fetch of recent bird sightings using eBird API with concurrent processing.

This node implements an AsyncNode for concurrent species queries with:
- AsyncNode for concurrent species queries using asyncio
- Smart endpoint selection (region-wide vs species-specific)
- Response aggregation and normalization
- Built-in rate limiting through aiohttp connection pooling
- Handle empty results for rare species gracefully
- Significant performance improvement over sync BatchNode
"""

from pocketflow import AsyncNode
from ...utils.ebird_async_api import EBirdAsyncClient
from typing import List, Dict, Any, Optional
import asyncio
import time
import logging

logger = logging.getLogger(__name__)


class AsyncFetchSightingsNode(AsyncNode):
    """
    Async fetch of recent bird sightings using eBird API with concurrent processing.

    Features:
    - AsyncNode for concurrent species queries using asyncio
    - Smart endpoint selection (region-wide vs species-specific)
    - Response aggregation and normalization
    - Built-in rate limiting through aiohttp connection pooling
    - Handle empty results for rare species gracefully
    - Significant performance improvement over sync BatchNode
    """

    def __init__(self):
        super().__init__()

    def prep(self, shared):
        """
        Extract validated species and constraints for async processing.

        AsyncNode expects prep() to return data that will be passed to exec().
        """
        validated_species = shared.get("validated_species", [])
        constraints = shared.get("input", {}).get("constraints", {})

        if not validated_species:
            raise ValueError("No validated species found in shared store")

        return {"species_list": validated_species, "constraints": constraints}

    async def exec(self, prep_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch sightings for all species concurrently using async eBird client.

        Args:
            prep_data: Dictionary containing species list and constraints

        Returns:
            Dictionary with aggregated sightings and processing stats
        """
        species_list = prep_data["species_list"]
        constraints = prep_data["constraints"]

        # Extract constraint parameters
        region_code = constraints.get("region", "US-MA")
        days_back = min(constraints.get("days_back", 7), 30)
        start_location = constraints.get("start_location")
        max_distance_km = constraints.get("max_daily_distance_km", 200)

        logger.info(f"Starting async fetch for {len(species_list)} species")

        # Use async context manager for proper session lifecycle
        async with EBirdAsyncClient() as client:
            # Create async tasks for all species
            tasks = []
            for species in species_list:
                task = self._create_species_task(
                    client,
                    species,
                    region_code,
                    days_back,
                    start_location,
                    max_distance_km,
                )
                tasks.append(task)

            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            return self._process_async_results(results, species_list)

    async def _create_species_task(
        self,
        client: EBirdAsyncClient,
        species: Dict[str, Any],
        region_code: str,
        days_back: int,
        start_location: Optional[Dict],
        max_distance_km: int,
    ):
        """
        Create async task for fetching sightings for a single species.

        Args:
            client: Async eBird client
            species: Validated species dictionary
            region_code: eBird region code
            days_back: Days to look back
            start_location: Optional starting location
            max_distance_km: Maximum distance for nearby searches

        Returns:
            Task result dictionary
        """
        try:
            # Smart endpoint selection
            if (
                start_location
                and start_location.get("lat")
                and start_location.get("lng")
            ):
                # Use nearby observations if we have coordinates
                sightings = await client.get_nearby_observations(
                    lat=start_location["lat"],
                    lng=start_location["lng"],
                    distance_km=min(max_distance_km // 2, 50),
                    days_back=days_back,
                    species_code=species["species_code"],
                )
                method = "nearby_observations"
            else:
                # Use species-specific observations for region
                sightings = await client.get_species_observations(
                    species_code=species["species_code"],
                    region_code=region_code,
                    days_back=days_back,
                )
                method = "species_observations"

            # Enrich sightings with species validation metadata
            enriched_sightings = []
            for sighting in sightings:
                enriched_sighting = dict(sighting)
                enriched_sighting.update(
                    {
                        "fetch_method": method,
                        "fetch_timestamp": time.time(),
                        "validation_confidence": species["confidence"],
                        "validation_method": species["validation_method"],
                        "original_species_name": species["original_name"],
                        "seasonal_notes": species.get("seasonal_notes", ""),
                        "behavioral_notes": species.get("behavioral_notes", ""),
                    }
                )
                enriched_sightings.append(enriched_sighting)

            logger.debug(
                f"Async fetched {len(enriched_sightings)} sightings for {species['common_name']}"
            )

            return {
                "success": True,
                "sightings": enriched_sightings,
                "method": method,
                "species_code": species["species_code"],
                "species_name": species["common_name"],
            }

        except Exception as e:
            logger.error(f"Async fetch error for {species['common_name']}: {e}")
            return {
                "success": False,
                "error": str(e),
                "sightings": [],
                "species_code": species["species_code"],
                "species_name": species["common_name"],
                "method": "error",
            }

    def _process_async_results(
        self, results: List, species_list: List[Dict]
    ) -> Dict[str, Any]:
        """
        Process and aggregate results from async fetch operations.

        Args:
            results: List of task results (may include exceptions)
            species_list: Original species list for stats

        Returns:
            Aggregated results dictionary
        """
        all_sightings = []
        successful_fetches = 0
        total_observations = 0
        unique_locations = set()
        fetch_method_stats = {}
        api_errors = 0
        empty_results = 0
        exception_count = 0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Exception in async task {i}: {result}")
                exception_count += 1
                continue

            if result.get("success", False):
                sightings = result.get("sightings", [])
                all_sightings.extend(sightings)
                successful_fetches += 1
                total_observations += len(sightings)

                # Track unique locations
                for sighting in sightings:
                    if sighting.get("locId"):
                        unique_locations.add(sighting["locId"])

                # Track fetch method statistics
                method = result.get("method", "unknown")
                fetch_method_stats[method] = fetch_method_stats.get(method, 0) + 1

                if len(sightings) == 0:
                    empty_results += 1
            else:
                api_errors += 1

        # Create processing statistics
        processing_stats = {
            "total_species": len(species_list),
            "successful_fetches": successful_fetches,
            "empty_results": empty_results,
            "api_errors": api_errors,
            "exception_count": exception_count,
            "total_observations": total_observations,
            "unique_locations": len(unique_locations),
            "fetch_method_stats": fetch_method_stats,
            "concurrent_execution": True,  # Flag to indicate async execution
        }

        return {"all_sightings": all_sightings, "processing_stats": processing_stats}

    def post(self, shared, prep_res, exec_res):
        """
        Store async fetch results in shared store.

        Args:
            shared: Shared store
            prep_res: Prep result (species and constraints)
            exec_res: Execution result (aggregated sightings and stats)
        """
        # Store results in shared store
        shared["all_sightings"] = exec_res["all_sightings"]
        shared["fetch_stats"] = exec_res["processing_stats"]

        # Check if we got sufficient data
        stats = exec_res["processing_stats"]
        success_rate = (
            stats["successful_fetches"] / stats["total_species"]
            if stats["total_species"] > 0
            else 0
        )

        if success_rate < 0.5:
            logger.warning(f"Low async fetch success rate: {success_rate:.1%}")
            return "fetch_failed"

        if stats["total_observations"] == 0:
            logger.warning("No observations found for any species")
            return "no_observations"

        logger.info(
            f"Async sightings fetch completed: {success_rate:.1%} success rate, "
            f"{stats['total_observations']} total observations from {stats['total_species']} species"
        )
        return "default"
