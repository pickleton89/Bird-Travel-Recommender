from pocketflow import Flow
from nodes import (
    ValidateSpeciesNode, 
    FetchSightingsNode, 
    FilterConstraintsNode,
    ClusterHotspotsNode,
    ScoreLocationsNode,
    OptimizeRouteNode,
    GenerateItineraryNode
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
    fetch_sightings = FetchSightingsNode(max_workers=5)  # BatchNode with 5 parallel workers
    filter_constraints = FilterConstraintsNode()
    cluster_hotspots = ClusterHotspotsNode(cluster_radius_km=15.0)
    score_locations = ScoreLocationsNode()
    optimize_route = OptimizeRouteNode(max_locations_for_optimization=12)
    generate_itinerary = GenerateItineraryNode(max_retries=3)  # AsyncNode with retry logic
    
    # Connect nodes in pipeline sequence
    # Each node reads from shared store and writes results back to shared store
    validate_species >> fetch_sightings >> filter_constraints >> cluster_hotspots >> score_locations >> optimize_route >> generate_itinerary
    
    # Create flow starting with species validation
    flow = Flow(start=validate_species)
    
    logger.info("Birding flow created successfully: 7 nodes connected in pipeline")
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
                "max_days": 3,
                "max_daily_distance_km": 200,
                "date_range": {"start": "2024-09-01", "end": "2024-09-30"},
                "region": "US-MA",
                "max_locations_per_day": 8,
                "min_location_score": 0.3
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
        # Execute the flow
        result = birding_flow.run(input_data)
        
        logger.info("Birding pipeline completed successfully")
        logger.info(f"Final result keys: {list(result.keys())}")
        
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
                "location_scoring_stats": result.get("location_scoring_stats", {}),
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