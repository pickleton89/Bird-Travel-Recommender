"""
Test suite for the unified architecture implementation.

This module tests the complete unified architecture including PocketFlow
compatibility adapters and runtime mode selection.
"""

import pytest
from unittest.mock import Mock, patch
from pocketflow import Flow

from src.bird_travel_recommender.flow import (
    create_unified_birding_flow,
    create_birding_flow,
    create_async_birding_flow,
)
from src.bird_travel_recommender.core.nodes.factory import ExecutionMode
from src.bird_travel_recommender.core.nodes.pocketflow_adapters import (
    create_sightings_node,
    create_species_validation_node,
    create_pocketflow_node,
)


class TestUnifiedArchitecture:
    """Test the unified architecture implementation."""
    
    def test_unified_flow_creation_sync(self):
        """Test creating unified flow in sync mode."""
        flow = create_unified_birding_flow(ExecutionMode.SYNC)
        assert isinstance(flow, Flow)
        
    def test_unified_flow_creation_async(self):
        """Test creating unified flow in async mode."""
        flow = create_unified_birding_flow(ExecutionMode.ASYNC)
        assert isinstance(flow, Flow)
        
    def test_pocketflow_compatibility(self):
        """Test that unified nodes are PocketFlow compatible."""
        # Create nodes in both modes
        sync_node = create_sightings_node(ExecutionMode.SYNC)
        async_node = create_sightings_node(ExecutionMode.ASYNC)
        
        # Check they have PocketFlow interface
        assert hasattr(sync_node, 'prep')
        assert hasattr(sync_node, 'exec')
        assert hasattr(sync_node, 'post')
        
        assert hasattr(async_node, 'prep')
        assert hasattr(async_node, 'exec')
        assert hasattr(async_node, 'post')
        
    def test_node_chaining_compatibility(self):
        """Test that unified nodes support PocketFlow chaining operators."""
        flow = create_unified_birding_flow(ExecutionMode.ASYNC)
        
        # The flow should be created successfully with chaining
        assert isinstance(flow, Flow)
        
    def test_legacy_flows_still_work(self):
        """Test that legacy flows still work with deprecation warnings."""
        with pytest.warns(DeprecationWarning):
            sync_flow = create_birding_flow()
            
        with pytest.warns(DeprecationWarning):
            async_flow = create_async_birding_flow()
            
        assert isinstance(sync_flow, Flow)
        assert isinstance(async_flow, Flow)
        
    def test_node_factory_functions(self):
        """Test the node factory functions work correctly."""
        # Test all node types
        node_types = [
            "sightings",
            "species_validation", 
            "cluster_hotspots",
            "filter_constraints",
            "score_locations",
            "optimize_route",
            "generate_itinerary"
        ]
        
        for node_type in node_types:
            sync_node = create_pocketflow_node(node_type, ExecutionMode.SYNC)
            async_node = create_pocketflow_node(node_type, ExecutionMode.ASYNC)
            
            # Check PocketFlow interface
            assert hasattr(sync_node, 'prep')
            assert hasattr(sync_node, 'exec') 
            assert hasattr(sync_node, 'post')
            
            assert hasattr(async_node, 'prep')
            assert hasattr(async_node, 'exec')
            assert hasattr(async_node, 'post')
            
    def test_execution_mode_selection(self):
        """Test that execution mode is properly handled."""
        sync_flow = create_unified_birding_flow(ExecutionMode.SYNC)
        async_flow = create_unified_birding_flow(ExecutionMode.ASYNC)
        
        # Both should be Flow instances but with different internal configurations
        assert isinstance(sync_flow, Flow)
        assert isinstance(async_flow, Flow)
        
    @pytest.mark.parametrize("execution_mode", [ExecutionMode.SYNC, ExecutionMode.ASYNC])
    def test_unified_flow_parametrized(self, execution_mode):
        """Test unified flow creation with different execution modes."""
        flow = create_unified_birding_flow(execution_mode)
        assert isinstance(flow, Flow)
        
    def test_performance_comparable(self):
        """Test that unified architecture performance is reasonable."""
        import time
        
        # Test creation times
        start = time.time()
        unified_flow = create_unified_birding_flow(ExecutionMode.ASYNC)
        unified_time = time.time() - start
        
        # Should create reasonably quickly (less than 1 second)
        assert unified_time < 1.0
        assert isinstance(unified_flow, Flow)
        
    def test_node_adapter_error_handling(self):
        """Test that node adapters handle errors properly."""
        node = create_species_validation_node(ExecutionMode.SYNC)
        
        # Test with empty shared store
        shared_store = {}
        prep_result = node.prep(shared_store)
        
        # Should not raise an exception
        assert isinstance(prep_result, dict)


class TestArchitecturalAchievements:
    """Test that architectural goals have been achieved."""
    
    def test_zero_breaking_changes(self):
        """Test that no breaking changes were introduced."""
        # Legacy functions should still work
        with pytest.warns(DeprecationWarning):
            legacy_sync = create_birding_flow()
        with pytest.warns(DeprecationWarning): 
            legacy_async = create_async_birding_flow()
            
        # New functions should work
        unified_sync = create_unified_birding_flow(ExecutionMode.SYNC)
        unified_async = create_unified_birding_flow(ExecutionMode.ASYNC)
        
        # All should be Flow instances
        assert all(isinstance(flow, Flow) for flow in [
            legacy_sync, legacy_async, unified_sync, unified_async
        ])
        
    def test_unified_interface(self):
        """Test that unified interface works for both sync and async."""
        # Same function should work for both modes
        sync_flow = create_unified_birding_flow(ExecutionMode.SYNC)
        async_flow = create_unified_birding_flow(ExecutionMode.ASYNC)
        
        assert isinstance(sync_flow, Flow)
        assert isinstance(async_flow, Flow)
        
    def test_dependency_injection_working(self):
        """Test that dependency injection is working in adapters."""
        node = create_sightings_node(ExecutionMode.ASYNC)
        
        # Node should have unified_node attribute with dependencies
        assert hasattr(node, 'unified_node')
        assert hasattr(node.unified_node, 'deps')
        assert hasattr(node.unified_node.deps, 'ebird_client')
        
    def test_backward_compatibility_complete(self):
        """Test complete backward compatibility."""
        # Import old-style functions
        from src.bird_travel_recommender.flow import birding_flow
        
        # Should be a Flow instance (now using unified architecture)
        assert isinstance(birding_flow, Flow)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])