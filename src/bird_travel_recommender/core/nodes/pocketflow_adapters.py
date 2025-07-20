"""
PocketFlow-compatible adapters for unified nodes.

This module provides adapter classes that make the unified node implementations
compatible with PocketFlow's Node interface while preserving all the benefits
of the unified architecture.
"""

from typing import Dict, Any
from pocketflow import Node, AsyncNode
import asyncio
import logging

from .factory import NodeDependencies, ExecutionMode
from .implementations import (
    UnifiedSightingsNode,
    UnifiedSpeciesValidationNode,
    UnifiedClusterHotspotsNode,
    UnifiedFilterConstraintsNode,
    UnifiedScoreLocationsNode,
    UnifiedOptimizeRouteNode,
    UnifiedGenerateItineraryNode,
)

logger = logging.getLogger(__name__)


class PocketFlowNodeAdapter(Node):
    """
    Base adapter that makes unified nodes compatible with PocketFlow.
    
    This adapter implements the PocketFlow Node interface (prep/exec/post)
    while delegating to unified node implementations internally.
    """
    
    def __init__(self, unified_node_class, execution_mode: ExecutionMode = ExecutionMode.ASYNC, **kwargs):
        """
        Initialize the adapter with a unified node.
        
        Args:
            unified_node_class: The unified node class to adapt
            execution_mode: Execution mode for the unified node
            **kwargs: Additional arguments for the unified node
        """
        super().__init__()
        self.execution_mode = execution_mode
        
        # Create shared dependencies for the unified node
        self.dependencies = NodeDependencies.create_default(execution_mode)
        
        # Create the unified node instance
        self.unified_node = unified_node_class(self.dependencies, **kwargs)
        
        logger.debug(f"Created PocketFlow adapter for {unified_node_class.__name__} in {execution_mode.value} mode")
    
    def prep(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        """
        PocketFlow prep method - extracts and validates input data.
        
        Args:
            shared: PocketFlow shared store
            
        Returns:
            Prepared data for exec method
        """
        # The unified node expects the full shared store for processing
        # We'll pass it through and let the unified node handle validation
        return shared
    
    def exec(self, prep_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        PocketFlow exec method - delegates to unified node processing.
        
        Args:
            prep_data: Data from prep method
            
        Returns:
            Processing results
        """
        try:
            # Execute the unified node's async process method
            if self.execution_mode == ExecutionMode.ASYNC:
                # Run async method in current event loop or create new one
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If we're in an async context, we need to handle this differently
                        # For now, we'll use a simple approach
                        import nest_asyncio
                        nest_asyncio.apply()
                        result = loop.run_until_complete(self.unified_node.process(prep_data))
                    else:
                        result = loop.run_until_complete(self.unified_node.process(prep_data))
                except RuntimeError:
                    # No event loop, create one
                    result = asyncio.run(self.unified_node.process(prep_data))
            else:
                # For sync mode, run in new event loop
                result = asyncio.run(self.unified_node.process(prep_data))
            
            # Extract data from the unified node result
            if hasattr(result, 'dict'):
                result_dict = result.dict()
            else:
                result_dict = result
            
            return result_dict.get('data', {})
            
        except Exception as e:
            logger.error(f"Error in unified node execution: {e}")
            # Return error result in format expected by PocketFlow
            return {"error": str(e), "success": False}
    
    def post(self, shared: Dict[str, Any], prep_res: Any, exec_res: Dict[str, Any]) -> str:
        """
        PocketFlow post method - updates shared store with results.
        
        Args:
            shared: PocketFlow shared store
            prep_res: Result from prep method
            exec_res: Result from exec method
            
        Returns:
            Next node name or "default"
        """
        # Update shared store with results
        if isinstance(exec_res, dict):
            shared.update(exec_res)
        
        # Check for errors
        if exec_res.get("error"):
            logger.error(f"Node execution failed: {exec_res['error']}")
            return "error"
        
        # Return default for successful execution
        return "default"


class PocketFlowAsyncNodeAdapter(AsyncNode):
    """
    Async adapter that makes unified nodes compatible with PocketFlow AsyncNode.
    """
    
    def __init__(self, unified_node_class, execution_mode: ExecutionMode = ExecutionMode.ASYNC, **kwargs):
        """
        Initialize the async adapter with a unified node.
        
        Args:
            unified_node_class: The unified node class to adapt
            execution_mode: Execution mode for the unified node
            **kwargs: Additional arguments for the unified node
        """
        super().__init__()
        self.execution_mode = execution_mode
        
        # Create shared dependencies for the unified node
        self.dependencies = NodeDependencies.create_default(execution_mode)
        
        # Create the unified node instance
        self.unified_node = unified_node_class(self.dependencies, **kwargs)
        
        logger.debug(f"Created PocketFlow async adapter for {unified_node_class.__name__} in {execution_mode.value} mode")
    
    def prep(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        """Async prep method."""
        return shared
    
    async def exec(self, prep_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Async exec method - delegates to unified node processing.
        
        Args:
            prep_data: Data from prep method
            
        Returns:
            Processing results
        """
        try:
            # Execute the unified node's async process method
            result = await self.unified_node.process(prep_data)
            
            # Extract data from the unified node result
            if hasattr(result, 'dict'):
                result_dict = result.dict()
            else:
                result_dict = result
            
            return result_dict.get('data', {})
            
        except Exception as e:
            logger.error(f"Error in unified async node execution: {e}")
            return {"error": str(e), "success": False}
    
    def post(self, shared: Dict[str, Any], prep_res: Any, exec_res: Dict[str, Any]) -> str:
        """Post method - updates shared store with results."""
        # Update shared store with results
        if isinstance(exec_res, dict):
            shared.update(exec_res)
        
        # Check for errors
        if exec_res.get("error"):
            logger.error(f"Async node execution failed: {exec_res['error']}")
            return "error"
        
        return "default"


# Factory functions for creating PocketFlow-compatible nodes

def create_sightings_node(execution_mode: ExecutionMode = ExecutionMode.ASYNC, **kwargs):
    """Create a PocketFlow-compatible sightings node."""
    if execution_mode == ExecutionMode.ASYNC:
        return PocketFlowAsyncNodeAdapter(UnifiedSightingsNode, execution_mode, **kwargs)
    else:
        return PocketFlowNodeAdapter(UnifiedSightingsNode, execution_mode, **kwargs)


def create_species_validation_node(execution_mode: ExecutionMode = ExecutionMode.ASYNC, **kwargs):
    """Create a PocketFlow-compatible species validation node."""
    if execution_mode == ExecutionMode.ASYNC:
        return PocketFlowAsyncNodeAdapter(UnifiedSpeciesValidationNode, execution_mode, **kwargs)
    else:
        return PocketFlowNodeAdapter(UnifiedSpeciesValidationNode, execution_mode, **kwargs)


def create_cluster_hotspots_node(execution_mode: ExecutionMode = ExecutionMode.ASYNC, **kwargs):
    """Create a PocketFlow-compatible cluster hotspots node."""
    if execution_mode == ExecutionMode.ASYNC:
        return PocketFlowAsyncNodeAdapter(UnifiedClusterHotspotsNode, execution_mode, **kwargs)
    else:
        return PocketFlowNodeAdapter(UnifiedClusterHotspotsNode, execution_mode, **kwargs)


def create_filter_constraints_node(execution_mode: ExecutionMode = ExecutionMode.ASYNC, **kwargs):
    """Create a PocketFlow-compatible filter constraints node."""
    if execution_mode == ExecutionMode.ASYNC:
        return PocketFlowAsyncNodeAdapter(UnifiedFilterConstraintsNode, execution_mode, **kwargs)
    else:
        return PocketFlowNodeAdapter(UnifiedFilterConstraintsNode, execution_mode, **kwargs)


def create_score_locations_node(execution_mode: ExecutionMode = ExecutionMode.ASYNC, **kwargs):
    """Create a PocketFlow-compatible score locations node."""
    if execution_mode == ExecutionMode.ASYNC:
        return PocketFlowAsyncNodeAdapter(UnifiedScoreLocationsNode, execution_mode, **kwargs)
    else:
        return PocketFlowNodeAdapter(UnifiedScoreLocationsNode, execution_mode, **kwargs)


def create_optimize_route_node(execution_mode: ExecutionMode = ExecutionMode.ASYNC, **kwargs):
    """Create a PocketFlow-compatible optimize route node."""
    if execution_mode == ExecutionMode.ASYNC:
        return PocketFlowAsyncNodeAdapter(UnifiedOptimizeRouteNode, execution_mode, **kwargs)
    else:
        return PocketFlowNodeAdapter(UnifiedOptimizeRouteNode, execution_mode, **kwargs)


def create_generate_itinerary_node(execution_mode: ExecutionMode = ExecutionMode.ASYNC, **kwargs):
    """Create a PocketFlow-compatible generate itinerary node."""
    if execution_mode == ExecutionMode.ASYNC:
        return PocketFlowAsyncNodeAdapter(UnifiedGenerateItineraryNode, execution_mode, **kwargs)
    else:
        return PocketFlowNodeAdapter(UnifiedGenerateItineraryNode, execution_mode, **kwargs)


# Convenience mapping for easy access
POCKETFLOW_NODE_FACTORIES = {
    "sightings": create_sightings_node,
    "species_validation": create_species_validation_node,
    "cluster_hotspots": create_cluster_hotspots_node,
    "filter_constraints": create_filter_constraints_node,
    "score_locations": create_score_locations_node,
    "optimize_route": create_optimize_route_node,
    "generate_itinerary": create_generate_itinerary_node,
}


def create_pocketflow_node(node_type: str, execution_mode: ExecutionMode = ExecutionMode.ASYNC, **kwargs):
    """
    Create a PocketFlow-compatible node by type.
    
    Args:
        node_type: Type of node to create
        execution_mode: Execution mode for the node
        **kwargs: Additional arguments for the node
        
    Returns:
        PocketFlow-compatible node instance
    """
    if node_type not in POCKETFLOW_NODE_FACTORIES:
        raise ValueError(f"Unknown node type: {node_type}. Available: {list(POCKETFLOW_NODE_FACTORIES.keys())}")
    
    factory = POCKETFLOW_NODE_FACTORIES[node_type]
    return factory(execution_mode, **kwargs)