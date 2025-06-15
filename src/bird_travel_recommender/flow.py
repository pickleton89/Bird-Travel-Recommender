from pocketflow import Flow
# Import migrated nodes from new locations
from .nodes.validation.species import ValidateSpeciesNode
from .nodes.fetching.sightings import FetchSightingsNode
from .nodes.fetching.async_sightings import AsyncFetchSightingsNode

# Import remaining nodes from original nodes.py file using importlib
import importlib.util
import os
_nodes_file_path = os.path.join(os.path.dirname(__file__), 'nodes.py')
_spec = importlib.util.spec_from_file_location("original_nodes_module", _nodes_file_path)
_original_nodes = importlib.util.module_from_spec(_spec)

# Set up the module's globals to match the original context
import sys
_original_nodes.__dict__.update({
    '__package__': 'bird_travel_recommender',
    '__spec__': _spec,
})

# Execute the module
_spec.loader.exec_module(_original_nodes)

# Import the remaining non-migrated classes
FilterConstraintsNode = _original_nodes.FilterConstraintsNode
ClusterHotspotsNode = _original_nodes.ClusterHotspotsNode
ScoreLocationsNode = _original_nodes.ScoreLocationsNode
OptimizeRouteNode = _original_nodes.OptimizeRouteNode
GenerateItineraryNode = _original_nodes.GenerateItineraryNode
from .constants import (
    MAX_WORKERS_DEFAULT,
    CLUSTER_RADIUS_KM_DEFAULT,
    MAX_LOCATIONS_FOR_OPTIMIZATION,
    MAX_RETRIES_DEFAULT,
    MAX_DAYS_DEFAULT,
    MAX_DAILY_DISTANCE_KM_DEFAULT,
    MAX_LOCATIONS_PER_DAY,
    MIN_LOCATION_SCORE
)
import logging

logger = logging.getLogger(__name__)


def create_birding_flow():
    """
    Create and return the complete 7-node birding travel recommendation flow.
    
    This flow implements the comprehensive birding pipeline as specified in the design document:
    1. ValidateSpeciesNode - Convert species names to eBird codes with LLM fallback
    2. FetchSightingsNode - Parallel API calls to get recent observations (BatchNode)
    3. FilterConstraintsNode - Apply geographic/temporal constraints with enrichment-in-place
    4. ClusterHotspotsNode - Group nearby locations with hotspot integration
    5. ScoreLocationsNode - Rank locations with LLM-enhanced habitat evaluation
    6. OptimizeRouteNode - TSP-style route optimization with fallbacks
    7. GenerateItineraryNode - LLM-enhanced markdown itinerary generation (AsyncNode)
    
    Returns:
        Flow: Configured PocketFlow with all nodes connected
    """
    logger.info("Creating birding travel recommendation flow with 7 pipeline nodes")
    
    # Create all pipeline nodes
    validate_species = ValidateSpeciesNode()
    fetch_sightings = FetchSightingsNode(max_workers=MAX_WORKERS_DEFAULT)  # BatchNode with parallel workers
    filter_constraints = FilterConstraintsNode()
    cluster_hotspots = ClusterHotspotsNode(cluster_radius_km=CLUSTER_RADIUS_KM_DEFAULT)
    score_locations = ScoreLocationsNode()
    optimize_route = OptimizeRouteNode(max_locations_for_optimization=MAX_LOCATIONS_FOR_OPTIMIZATION)
    generate_itinerary = GenerateItineraryNode(max_retries=MAX_RETRIES_DEFAULT)  # AsyncNode with retry logic
    
    # Connect nodes in pipeline sequence
    # Each node reads from shared store and writes results back to shared store
    # Error conditions are handled gracefully within the normal flow
    validate_species >> fetch_sightings >> filter_constraints >> cluster_hotspots >> score_locations >> optimize_route >> generate_itinerary
    
    # Create flow starting with species validation
    flow = Flow(start=validate_species)
    
    logger.info("Birding flow created successfully: 7 nodes connected in pipeline")
    return flow


def create_async_birding_flow():
    """
    Create and return the async version of the birding travel recommendation flow.
    
    This flow uses AsyncFetchSightingsNode for significant performance improvements
    through concurrent API requests instead of sequential processing.
    
    Performance Benefits:
    - Concurrent species fetching: 5+ species fetched simultaneously vs sequentially
    - Reduced total pipeline time: ~70-80% faster for multi-species queries
    - Better resource utilization: non-blocking I/O operations
    - Maintained reliability: same error handling and retry logic
    
    Returns:
        Flow: Configured PocketFlow with async sightings fetch node
    """
    logger.info("Creating async birding travel recommendation flow with concurrent API fetching")
    
    # Create all pipeline nodes (same as sync version except fetch node)
    validate_species = ValidateSpeciesNode()
    fetch_sightings = AsyncFetchSightingsNode()  # AsyncNode for concurrent requests
    filter_constraints = FilterConstraintsNode()
    cluster_hotspots = ClusterHotspotsNode(cluster_radius_km=CLUSTER_RADIUS_KM_DEFAULT)
    score_locations = ScoreLocationsNode()
    optimize_route = OptimizeRouteNode(max_locations_for_optimization=MAX_LOCATIONS_FOR_OPTIMIZATION)
    generate_itinerary = GenerateItineraryNode(max_retries=MAX_RETRIES_DEFAULT)  # AsyncNode with retry logic
    
    # Connect nodes in pipeline sequence
    # Each node reads from shared store and writes results back to shared store
    # Error conditions are handled gracefully within the normal flow
    validate_species >> fetch_sightings >> filter_constraints >> cluster_hotspots >> score_locations >> optimize_route >> generate_itinerary
    
    # Create flow starting with species validation
    flow = Flow(start=validate_species)
    
    logger.info("Async birding flow created successfully: 7 nodes with concurrent fetch processing")
    return flow


def create_test_input():
    """
    Create test input data for the birding flow.
    
    Returns:
        Dict: Test input data matching the expected shared store format
    """
    return {
        "input": {
            "species_list": [
                "Northern Cardinal",
                "Blue Jay", 
                "American Robin",
                "Yellow Warbler",
                "Red-tailed Hawk"
            ],
            "constraints": {
                "start_location": {"lat": 42.3601, "lng": -71.0589},  # Boston, MA
                "max_days": MAX_DAYS_DEFAULT,
                "max_daily_distance_km": MAX_DAILY_DISTANCE_KM_DEFAULT,
                "date_range": {"start": "2024-09-01", "end": "2024-09-30"},
                "region": "US-MA",
                "max_locations_per_day": MAX_LOCATIONS_PER_DAY,
                "min_location_score": MIN_LOCATION_SCORE
            }
        }
    }


# Create the main birding flow
birding_flow = create_birding_flow()


def run_birding_pipeline(input_data=None, debug=False):
    """
    Run the complete birding pipeline with input data.
    
    Args:
        input_data: Optional input data dictionary. If None, uses test data.
        debug: Enable debug logging
        
    Returns:
        Dict: Complete pipeline results including itinerary and statistics
    """
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    if input_data is None:
        input_data = create_test_input()
        logger.info("Using test input data")
    
    logger.info("Starting birding pipeline execution")
    logger.info(f"Target species: {input_data['input']['species_list']}")
    logger.info(f"Start location: {input_data['input']['constraints']['start_location']}")
    logger.info(f"Region: {input_data['input']['constraints']['region']}")
    
    try:
        # Create a shared store to track state
        shared_store = input_data.copy()
        
        # Execute the flow
        flow_result = birding_flow.run(shared_store)
        
        logger.info("Birding pipeline completed successfully")
        logger.info(f"Flow result: {flow_result}")
        
        # Access the final shared store
        result = shared_store
        
        # Return comprehensive results
        return {
            "success": True,
            "itinerary_markdown": result.get("itinerary_markdown", ""),
            "optimized_route": result.get("optimized_route", []),
            "route_segments": result.get("route_segments", []),
            "validated_species": result.get("validated_species", []),
            "hotspot_clusters": result.get("hotspot_clusters", []),
            "scored_locations": result.get("scored_locations", []),
            "pipeline_statistics": {
                "validation_stats": result.get("validation_stats", {}),
                "fetch_stats": result.get("fetch_stats", {}),
                "filtering_stats": result.get("filtering_stats", {}),
                "clustering_stats": result.get("clustering_stats", {}),
                "scoring_stats": result.get("scoring_stats", {}),
                "route_optimization_stats": result.get("route_optimization_stats", {}),
                "itinerary_generation_stats": result.get("itinerary_generation_stats", {})
            },
            "execution_mode": "local"
        }
        
    except Exception as e:
        logger.error(f"Birding pipeline failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "itinerary_markdown": "# Pipeline Execution Failed\n\nAn error occurred during pipeline execution. Please check the logs for details.",
            "pipeline_statistics": {},
            "execution_mode": "local"
        }