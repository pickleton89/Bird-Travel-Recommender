from pocketflow import Flow

# Import unified nodes from the new architecture
from .core.nodes.factory import NodeFactory, NodeDependencies, ExecutionMode
from .core.nodes.pocketflow_adapters import (
    create_sightings_node,
    create_species_validation_node,
    create_cluster_hotspots_node,
    create_filter_constraints_node,
    create_score_locations_node,
    create_optimize_route_node,
    create_generate_itinerary_node,
)

# Legacy imports for backward compatibility (deprecated)
from .nodes.validation.species import ValidateSpeciesNode
from .nodes.fetching.sightings import FetchSightingsNode
from .nodes.fetching.async_sightings import AsyncFetchSightingsNode
from .nodes.processing.constraints import FilterConstraintsNode
from .nodes.processing.clustering import ClusterHotspotsNode
from .nodes.processing.scoring import ScoreLocationsNode
from .nodes.processing.routing import OptimizeRouteNode
from .nodes.processing.itinerary import GenerateItineraryNode
from .constants import (
    MAX_WORKERS_DEFAULT,
    CLUSTER_RADIUS_KM_DEFAULT,
    MAX_LOCATIONS_FOR_OPTIMIZATION,
    MAX_RETRIES_DEFAULT,
    MAX_DAYS_DEFAULT,
    MAX_DAILY_DISTANCE_KM_DEFAULT,
    MAX_LOCATIONS_PER_DAY,
    MIN_LOCATION_SCORE,
)
import logging

logger = logging.getLogger(__name__)


def create_unified_birding_flow(execution_mode: ExecutionMode = ExecutionMode.ASYNC):
    """
    Create and return the unified birding travel recommendation flow.
    
    This flow uses the new unified architecture that eliminates code duplication
    by providing nodes that work in both sync and async modes through dependency injection.
    
    Features:
    - Single implementation for all nodes (no sync/async duplication)
    - Runtime execution mode selection (sync/async)
    - Professional dependency injection and error handling
    - Built-in metrics, caching, and logging
    - Type-safe configuration with Pydantic models
    
    Args:
        execution_mode: Whether to run in sync or async mode
        
    Returns:
        Flow: Configured PocketFlow with unified architecture nodes
    """
    logger.info(f"Creating unified birding flow with {execution_mode.value} execution mode")
    
    # Create all nodes using PocketFlow-compatible adapters
    validate_species = create_species_validation_node(execution_mode)
    fetch_sightings = create_sightings_node(execution_mode, max_workers=MAX_WORKERS_DEFAULT)
    filter_constraints = create_filter_constraints_node(execution_mode)
    cluster_hotspots = create_cluster_hotspots_node(execution_mode, cluster_radius_km=CLUSTER_RADIUS_KM_DEFAULT)
    score_locations = create_score_locations_node(execution_mode)
    optimize_route = create_optimize_route_node(execution_mode, max_locations_for_optimization=MAX_LOCATIONS_FOR_OPTIMIZATION)
    generate_itinerary = create_generate_itinerary_node(execution_mode, max_retries=MAX_RETRIES_DEFAULT)
    
    # Connect nodes in pipeline sequence
    (
        validate_species
        >> fetch_sightings
        >> filter_constraints
        >> cluster_hotspots
        >> score_locations
        >> optimize_route
        >> generate_itinerary
    )
    
    # Create flow starting with species validation
    flow = Flow(start=validate_species)
    
    logger.info(f"Unified birding flow created successfully: 7 nodes with {execution_mode.value} execution")
    return flow


def create_birding_flow():
    """
    Create and return the complete 7-node birding travel recommendation flow.
    
    DEPRECATED: Use create_unified_birding_flow() instead.
    This function is maintained for backward compatibility but will be removed in a future version.
    
    The new unified architecture provides the same functionality with:
    - Eliminated code duplication
    - Professional dependency injection
    - Built-in metrics and caching
    - Type-safe configuration
    
    Returns:
        Flow: Configured PocketFlow with all nodes connected
    """
    import warnings
    warnings.warn(
        "create_birding_flow() is deprecated. Use create_unified_birding_flow(ExecutionMode.SYNC) instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    logger.info("Creating legacy birding travel recommendation flow (DEPRECATED)")

    # Create all pipeline nodes
    validate_species = ValidateSpeciesNode()
    fetch_sightings = FetchSightingsNode(
        max_workers=MAX_WORKERS_DEFAULT
    )  # BatchNode with parallel workers
    filter_constraints = FilterConstraintsNode()
    cluster_hotspots = ClusterHotspotsNode(cluster_radius_km=CLUSTER_RADIUS_KM_DEFAULT)
    score_locations = ScoreLocationsNode()
    optimize_route = OptimizeRouteNode(
        max_locations_for_optimization=MAX_LOCATIONS_FOR_OPTIMIZATION
    )
    generate_itinerary = GenerateItineraryNode(
        max_retries=MAX_RETRIES_DEFAULT
    )  # AsyncNode with retry logic

    # Connect nodes in pipeline sequence
    # Each node reads from shared store and writes results back to shared store
    # Error conditions are handled gracefully within the normal flow
    (
        validate_species
        >> fetch_sightings
        >> filter_constraints
        >> cluster_hotspots
        >> score_locations
        >> optimize_route
        >> generate_itinerary
    )

    # Create flow starting with species validation
    flow = Flow(start=validate_species)

    logger.info("Birding flow created successfully: 7 nodes connected in pipeline")
    return flow


def create_async_birding_flow():
    """
    Create and return the async version of the birding travel recommendation flow.
    
    DEPRECATED: Use create_unified_birding_flow(ExecutionMode.ASYNC) instead.
    This function is maintained for backward compatibility but will be removed in a future version.
    
    The new unified architecture provides the same functionality with:
    - Eliminated code duplication between sync/async versions
    - Professional dependency injection and error handling
    - Built-in metrics, caching, and logging
    - Type-safe configuration with Pydantic models

    Returns:
        Flow: Configured PocketFlow with async sightings fetch node
    """
    import warnings
    warnings.warn(
        "create_async_birding_flow() is deprecated. Use create_unified_birding_flow(ExecutionMode.ASYNC) instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    logger.info("Creating legacy async birding travel recommendation flow (DEPRECATED)")

    # Create all pipeline nodes (same as sync version except fetch node)
    validate_species = ValidateSpeciesNode()
    fetch_sightings = AsyncFetchSightingsNode()  # AsyncNode for concurrent requests
    filter_constraints = FilterConstraintsNode()
    cluster_hotspots = ClusterHotspotsNode(cluster_radius_km=CLUSTER_RADIUS_KM_DEFAULT)
    score_locations = ScoreLocationsNode()
    optimize_route = OptimizeRouteNode(
        max_locations_for_optimization=MAX_LOCATIONS_FOR_OPTIMIZATION
    )
    generate_itinerary = GenerateItineraryNode(
        max_retries=MAX_RETRIES_DEFAULT
    )  # AsyncNode with retry logic

    # Connect nodes in pipeline sequence
    # Each node reads from shared store and writes results back to shared store
    # Error conditions are handled gracefully within the normal flow
    (
        validate_species
        >> fetch_sightings
        >> filter_constraints
        >> cluster_hotspots
        >> score_locations
        >> optimize_route
        >> generate_itinerary
    )

    # Create flow starting with species validation
    flow = Flow(start=validate_species)

    logger.info(
        "Async birding flow created successfully: 7 nodes with concurrent fetch processing"
    )
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
                "Red-tailed Hawk",
            ],
            "constraints": {
                "start_location": {"lat": 42.3601, "lng": -71.0589},  # Boston, MA
                "max_days": MAX_DAYS_DEFAULT,
                "max_daily_distance_km": MAX_DAILY_DISTANCE_KM_DEFAULT,
                "date_range": {"start": "2024-09-01", "end": "2024-09-30"},
                "region": "US-MA",
                "max_locations_per_day": MAX_LOCATIONS_PER_DAY,
                "min_location_score": MIN_LOCATION_SCORE,
            },
        }
    }


# Create the main birding flow using unified architecture (PocketFlow compatible!)
# This now provides both sync and async capabilities through the same interface
birding_flow = create_unified_birding_flow(ExecutionMode.ASYNC)

# Legacy flows for backward compatibility (deprecated)
legacy_sync_flow = None  # Lazy-loaded to avoid deprecation warnings at module import
legacy_async_flow = None  # Lazy-loaded to avoid deprecation warnings at module import


def get_legacy_sync_flow():
    """Get the legacy sync flow (deprecated). Use create_unified_birding_flow(ExecutionMode.SYNC) instead."""
    global legacy_sync_flow
    if legacy_sync_flow is None:
        legacy_sync_flow = create_birding_flow()
    return legacy_sync_flow


def get_legacy_async_flow():
    """Get the legacy async flow (deprecated). Use create_unified_birding_flow(ExecutionMode.ASYNC) instead."""
    global legacy_async_flow
    if legacy_async_flow is None:
        legacy_async_flow = create_async_birding_flow()
    return legacy_async_flow


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
    logger.info(
        f"Start location: {input_data['input']['constraints']['start_location']}"
    )
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
                "itinerary_generation_stats": result.get(
                    "itinerary_generation_stats", {}
                ),
            },
            "execution_mode": "local",
        }

    except Exception as e:
        logger.error(f"Birding pipeline failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "itinerary_markdown": "# Pipeline Execution Failed\n\nAn error occurred during pipeline execution. Please check the logs for details.",
            "pipeline_statistics": {},
            "execution_mode": "local",
        }
