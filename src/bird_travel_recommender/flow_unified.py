"""
Unified Birding Flow using the new node architecture.

This module demonstrates the Phase 3 refactoring by replacing the duplicate
sync/async flows with a single unified flow that supports both execution modes.
"""

from pocketflow import Flow
from typing import Dict, Any, Optional
import logging

# Import unified nodes from the new architecture
from .core.nodes import (
    NodeFactory, 
    ExecutionMode, 
    NodeDependencies,
    create_workflow_nodes,
    validate_workflow_nodes
)
from .core.nodes.implementations import (
    UnifiedSightingsNode,
    UnifiedSpeciesValidationNode
)

# Import remaining nodes that haven't been migrated yet
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

logger = logging.getLogger(__name__)


class UnifiedBirdingFlow:
    """
    Unified birding flow that supports both sync and async execution modes.
    
    This class eliminates the need for separate sync/async flows by using
    the new unified node architecture with execution mode selection.
    """
    
    def __init__(self, execution_mode: ExecutionMode = ExecutionMode.ASYNC, 
                 shared_dependencies: Optional[NodeDependencies] = None):
        """
        Initialize the unified birding flow.
        
        Args:
            execution_mode: Whether to run in sync or async mode
            shared_dependencies: Optional shared dependencies for all nodes
        """
        self.execution_mode = execution_mode
        self.shared_dependencies = shared_dependencies or NodeDependencies.create_default(execution_mode)
        self.flow = None
        self._create_flow()
    
    def _create_flow(self):
        """Create the flow with unified nodes."""
        
        logger.info(f"Creating unified birding flow in {self.execution_mode.value} mode")
        
        # Validate that all required nodes are available
        required_nodes = ["sightings", "species_validation"]
        missing_nodes = validate_workflow_nodes(required_nodes)
        if missing_nodes:
            raise ValueError(f"Missing required nodes: {missing_nodes}")
        
        # Create unified nodes using the factory
        unified_nodes = create_workflow_nodes(
            required_nodes,
            mode=self.execution_mode,
            shared_dependencies=self.shared_dependencies
        )
        
        # Create pipeline nodes
        validate_species = unified_nodes["species_validation"]
        fetch_sightings = unified_nodes["sightings"]
        
        # Create remaining nodes (these will be migrated in future phases)
        filter_constraints = FilterConstraintsNode()
        cluster_hotspots = ClusterHotspotsNode(cluster_radius_km=CLUSTER_RADIUS_KM_DEFAULT)
        score_locations = ScoreLocationsNode()
        optimize_route = OptimizeRouteNode(
            max_locations_for_optimization=MAX_LOCATIONS_FOR_OPTIMIZATION
        )
        generate_itinerary = GenerateItineraryNode(
            max_retries=MAX_RETRIES_DEFAULT
        )
        
        # Create adapter nodes to bridge new and old architectures
        validate_species_adapter = NodeToFlowAdapter(validate_species)
        fetch_sightings_adapter = NodeToFlowAdapter(fetch_sightings)
        
        # Connect nodes in pipeline sequence
        (
            validate_species_adapter
            >> fetch_sightings_adapter
            >> filter_constraints
            >> cluster_hotspots
            >> score_locations
            >> optimize_route
            >> generate_itinerary
        )
        
        # Create flow starting with species validation
        self.flow = Flow(start=validate_species_adapter)
        
        logger.info(f"Unified birding flow created successfully in {self.execution_mode.value} mode")
    
    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the unified flow with input data.
        
        Args:
            input_data: Input data for the flow
            
        Returns:
            Flow execution results
        """
        if not self.flow:
            raise RuntimeError("Flow not initialized")
        
        logger.info(f"Starting unified birding flow execution in {self.execution_mode.value} mode")
        
        # Create a shared store to track state
        shared_store = input_data.copy()
        
        # Execute the flow
        flow_result = self.flow.run(shared_store)
        
        logger.info(f"Unified birding flow completed: {flow_result}")
        
        return shared_store


class NodeToFlowAdapter:
    """
    Adapter to bridge new unified nodes with the existing PocketFlow architecture.
    
    This adapter allows the new BaseNode implementations to work within the
    existing PocketFlow framework until all nodes are migrated.
    """
    
    def __init__(self, unified_node):
        """
        Initialize the adapter.
        
        Args:
            unified_node: Unified node instance to adapt
        """
        self.unified_node = unified_node
        self.logger = logging.getLogger(f"Adapter_{unified_node.__class__.__name__}")
    
    def prep(self, shared_store: Dict[str, Any]) -> Any:
        """
        Preparation phase - delegate to unified node if available.
        
        Args:
            shared_store: Shared data store
            
        Returns:
            Prep result
        """
        if hasattr(self.unified_node, 'prep'):
            return self.unified_node.prep(shared_store)
        return shared_store
    
    def exec(self, prep_result: Any) -> Any:
        """
        Execution phase - run the unified node.
        
        Args:
            prep_result: Result from prep phase
            
        Returns:
            Execution result
        """
        # For the adapter, we need to handle the shared store differently
        if isinstance(prep_result, dict):
            shared_store = prep_result
        else:
            # If prep_result is not a dict, assume it's the original shared store
            shared_store = prep_result
        
        # Execute the unified node
        if hasattr(self.unified_node.deps, 'execution_mode') and self.unified_node.deps.execution_mode == ExecutionMode.SYNC:
            # Use sync execution
            from .core.nodes.base import NodeExecutor
            result_store = NodeExecutor.execute_sync(self.unified_node, shared_store)
        else:
            # Use async execution - we need to run it in the current context
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Create a new event loop in a thread
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, self.unified_node.execute(shared_store))
                        result_store = future.result()
                else:
                    result_store = asyncio.run(self.unified_node.execute(shared_store))
            except RuntimeError:
                result_store = asyncio.run(self.unified_node.execute(shared_store))
        
        return result_store
    
    def post(self, shared_store: Dict[str, Any], prep_result: Any, exec_result: Any) -> str:
        """
        Post-processing phase - handle any cleanup.
        
        Args:
            shared_store: Shared data store
            prep_result: Result from prep phase
            exec_result: Result from exec phase
            
        Returns:
            Next node transition (typically "default")
        """
        # Update shared store with execution results
        if isinstance(exec_result, dict):
            shared_store.update(exec_result)
        
        if hasattr(self.unified_node, 'post_process'):
            # The unified node's post_process expects the result as a NodeOutput
            # For the adapter, we just pass through
            pass
        
        return "default"
    
    def __rshift__(self, other):
        """Support PocketFlow's >> operator for chaining."""
        # This is needed to maintain compatibility with PocketFlow's chaining syntax
        if hasattr(other, '__lshift__'):
            return other.__lshift__(self)
        # For now, return a simple connection - full PocketFlow integration would require more work
        return FlowConnection(self, other)


class FlowConnection:
    """Simple connection object for flow chaining."""
    
    def __init__(self, left_node, right_node):
        self.left_node = left_node
        self.right_node = right_node
    
    def __rshift__(self, other):
        """Continue the chain."""
        return FlowConnection(self, other)


def create_unified_birding_flow(execution_mode: ExecutionMode = ExecutionMode.ASYNC) -> UnifiedBirdingFlow:
    """
    Create a unified birding flow with the specified execution mode.
    
    This function replaces both create_birding_flow() and create_async_birding_flow()
    with a single implementation that supports both modes.
    
    Args:
        execution_mode: Whether to run in sync or async mode
        
    Returns:
        UnifiedBirdingFlow instance
    """
    return UnifiedBirdingFlow(execution_mode)


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


def run_unified_birding_pipeline(
    input_data: Optional[Dict[str, Any]] = None,
    execution_mode: ExecutionMode = ExecutionMode.ASYNC,
    debug: bool = False
) -> Dict[str, Any]:
    """
    Run the unified birding pipeline with specified execution mode.
    
    This function replaces the separate sync/async pipeline functions with
    a single implementation that supports both modes.
    
    Args:
        input_data: Optional input data dictionary. If None, uses test data.
        execution_mode: Whether to run in sync or async mode
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
    
    logger.info(f"Starting unified birding pipeline in {execution_mode.value} mode")
    logger.info(f"Target species: {input_data['input']['species_list']}")
    logger.info(f"Start location: {input_data['input']['constraints']['start_location']}")
    logger.info(f"Region: {input_data['input']['constraints']['region']}")
    
    try:
        # Create unified flow
        unified_flow = create_unified_birding_flow(execution_mode)
        
        # Execute the flow
        result = unified_flow.run(input_data)
        
        logger.info("Unified birding pipeline completed successfully")
        
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
                "itinerary_generation_stats": result.get("itinerary_generation_stats", {}),
            },
            "execution_mode": execution_mode.value,
        }
        
    except Exception as e:
        logger.error(f"Unified birding pipeline failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "itinerary_markdown": "# Pipeline Execution Failed\n\nAn error occurred during pipeline execution. Please check the logs for details.",
            "pipeline_statistics": {},
            "execution_mode": execution_mode.value,
        }


# Convenience functions for backward compatibility

def create_birding_flow():
    """
    Backward-compatible function that creates a sync flow.
    
    Returns:
        UnifiedBirdingFlow in sync mode
    """
    logger.warning("create_birding_flow() is deprecated. Use create_unified_birding_flow(ExecutionMode.SYNC) instead.")
    return create_unified_birding_flow(ExecutionMode.SYNC)


def create_async_birding_flow():
    """
    Backward-compatible function that creates an async flow.
    
    Returns:
        UnifiedBirdingFlow in async mode
    """
    logger.warning("create_async_birding_flow() is deprecated. Use create_unified_birding_flow(ExecutionMode.ASYNC) instead.")
    return create_unified_birding_flow(ExecutionMode.ASYNC)


def run_birding_pipeline(input_data=None, debug=False):
    """
    Backward-compatible function that runs the pipeline in sync mode.
    
    Args:
        input_data: Optional input data dictionary
        debug: Enable debug logging
        
    Returns:
        Dict: Pipeline results
    """
    logger.warning("run_birding_pipeline() is deprecated. Use run_unified_birding_pipeline() instead.")
    return run_unified_birding_pipeline(input_data, ExecutionMode.SYNC, debug)