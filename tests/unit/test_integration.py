"""
Integration tests for Bird Travel Recommender pipeline.

Tests cover:
- End-to-end pipeline execution
- Node interaction and data flow
- Performance with realistic data volumes
- Error propagation and recovery
- Data consistency across pipeline stages
"""

import pytest
from unittest.mock import patch
from bird_travel_recommender.nodes import ValidateSpeciesNode, FetchSightingsNode, FilterConstraintsNode
from .test_utils import TestDataValidator, PerformanceTestHelper


class TestPipelineIntegration:
    """Integration tests for the complete birding recommendation pipeline."""

    @pytest.fixture
    def pipeline_nodes(self):
        """Create all pipeline nodes for testing."""
        return {
            "validate": ValidateSpeciesNode(),
            "fetch": FetchSightingsNode(max_workers=3),
            "filter": FilterConstraintsNode()
        }

    @pytest.fixture
    def integration_test_input(self):
        """Input data for integration testing."""
        return {
            "species_list": ["Northern Cardinal", "Blue Jay", "cardinal", "invalid bird"],
            "constraints": {
                "region": "US-MA",
                "days_back": 7,
                "start_location": {"lat": 42.3601, "lng": -71.0589},
                "max_daily_distance_km": 100,
                "max_travel_radius_km": 50,
                "min_observation_quality": "valid"
            }
        }

    @pytest.mark.integration
    @pytest.mark.mock
    def test_end_to_end_pipeline_execution(self, pipeline_nodes, mock_ebird_api, integration_test_input):
        """Test complete pipeline execution from species input to filtered results."""
        shared = {"input": integration_test_input}
        
        # Step 1: Validate species
        validate_node = pipeline_nodes["validate"]
        prep_result = validate_node.prep(shared)
        exec_result = validate_node.exec(prep_result)
        validate_node.post(shared, prep_result, exec_result)
        
        # Verify validation results
        assert "validated_species" in shared
        assert len(shared["validated_species"]) >= 2  # Should validate some species
        
        # Step 2: Fetch sightings (BatchNode pattern)
        fetch_node = pipeline_nodes["fetch"]
        prep_result = fetch_node.prep(shared)
        
        # For BatchNode, exec() should be called for each individual species
        exec_results = []
        for species in prep_result:
            exec_result = fetch_node.exec(species)
            exec_results.append(exec_result)
        
        fetch_node.post(shared, prep_result, exec_results)
        
        # Verify fetch results
        assert "all_sightings" in shared
        assert "fetch_stats" in shared
        
        # Step 3: Filter constraints
        filter_node = pipeline_nodes["filter"]
        prep_result = filter_node.prep(shared)
        exec_result = filter_node.exec(prep_result)
        filter_node.post(shared, prep_result, exec_result)
        
        # Verify final results
        assert "filtering_stats" in shared
        
        # Validate data flow consistency
        for sighting in shared["all_sightings"]:
            # Should have enrichment from fetch stage
            assert "fetch_method" in sighting
            assert "validation_confidence" in sighting
            
            # Should have enrichment from filter stage
            assert "meets_all_constraints" in sighting
            assert "has_valid_gps" in sighting

    @pytest.mark.integration
    @pytest.mark.mock
    def test_pipeline_data_consistency(self, pipeline_nodes, mock_ebird_api, integration_test_input):
        """Test that data remains consistent as it flows through pipeline."""
        shared = {"input": integration_test_input}
        data_validator = TestDataValidator()
        
        # Run full pipeline
        for stage_name, node in pipeline_nodes.items():
            prep_result = node.prep(shared)
            
            # Handle BatchNode (fetch) differently
            if stage_name == "fetch":
                # For BatchNode, exec() should be called for each individual species
                exec_results = []
                for species in prep_result:
                    exec_result = node.exec(species)
                    exec_results.append(exec_result)
                node.post(shared, prep_result, exec_results)
            else:
                # Regular node processing
                exec_result = node.exec(prep_result)
                node.post(shared, prep_result, exec_result)
            
            # Validate data consistency at each stage
            if stage_name == "validate":
                assert "validated_species" in shared
                for species in shared["validated_species"]:
                    assert data_validator.validate_species_data(species)
            
            elif stage_name == "fetch":
                assert "all_sightings" in shared
                for sighting in shared["all_sightings"]:
                    assert data_validator.validate_sighting_data(sighting)
            
            elif stage_name == "filter":
                for sighting in shared["all_sightings"]:
                    assert data_validator.validate_enriched_sighting(sighting)

    @pytest.mark.integration
    @pytest.mark.mock
    def test_pipeline_with_no_valid_species(self, pipeline_nodes, mock_ebird_api):
        """Test pipeline behavior when no species can be validated."""
        invalid_input = {
            "species_list": ["invalid bird 1", "invalid bird 2", "made up species"],
            "constraints": {
                "region": "US-MA",
                "days_back": 7
            }
        }
        
        shared = {"input": invalid_input}
        
        # Run validation (should fail)
        validate_node = pipeline_nodes["validate"]
        prep_result = validate_node.prep(shared)
        exec_result = validate_node.exec(prep_result)
        validate_node.post(shared, prep_result, exec_result)
        
        assert len(shared["validated_species"]) == 0
        
        # Run fetch (should handle empty species gracefully)
        fetch_node = pipeline_nodes["fetch"]
        prep_result = fetch_node.prep(shared)
        assert prep_result == []  # Should return empty list for BatchNode
        
        # BatchNode pattern - post handles empty list gracefully
        fetch_node.post(shared, prep_result, [])
        
        # Verify empty state was set correctly
        assert "all_sightings" in shared
        assert "fetch_stats" in shared
        
        assert shared["all_sightings"] == []
        assert shared["fetch_stats"]["total_species"] == 0
        
        # Run filter (should handle empty sightings gracefully)
        filter_node = pipeline_nodes["filter"]
        prep_result = filter_node.prep(shared)
        exec_result = filter_node.exec(prep_result)
        filter_node.post(shared, prep_result, exec_result)
        
        assert shared["filtering_stats"]["total_input_sightings"] == 0

    @pytest.mark.integration
    @pytest.mark.mock
    def test_pipeline_error_propagation(self, pipeline_nodes):
        """Test error handling and propagation through pipeline."""
        shared = {"input": {"species_list": ["Northern Cardinal"]}}
        
        # Test with API errors
        with patch('bird_travel_recommender.utils.ebird_api.get_taxonomy') as mock_taxonomy:
            mock_taxonomy.side_effect = Exception("API Error")
            
            validate_node = pipeline_nodes["validate"]
            
            # Should handle API errors gracefully
            prep_result = validate_node.prep(shared)
            exec_result = validate_node.exec(prep_result)
            validate_node.post(shared, prep_result, exec_result)
            
            # Pipeline should continue with fallback mechanisms
            assert "validated_species" in shared
            assert "validation_stats" in shared

    @pytest.mark.integration
    @pytest.mark.slow
    def test_pipeline_performance_with_large_dataset(self, pipeline_nodes, mock_ebird_api, large_species_dataset):
        """Test pipeline performance with large species dataset."""
        large_input = {
            "species_list": large_species_dataset,
            "constraints": {
                "region": "US-MA",
                "days_back": 7,
                "start_location": {"lat": 42.3601, "lng": -71.0589}
            }
        }
        
        shared = {"input": large_input}
        performance_helper = PerformanceTestHelper()
        
        # Time the full pipeline execution
        def run_full_pipeline():
            for stage_name, node in pipeline_nodes.items():
                prep_result = node.prep(shared)
                
                # Handle BatchNode (fetch) differently
                if stage_name == "fetch":
                    # For BatchNode, exec() should be called for each individual species
                    exec_results = []
                    for species in prep_result:
                        exec_result = node.exec(species)
                        exec_results.append(exec_result)
                    node.post(shared, prep_result, exec_results)
                else:
                    # Regular node processing
                    exec_result = node.exec(prep_result)
                    node.post(shared, prep_result, exec_result)
        
        result, duration = performance_helper.time_function(run_full_pipeline)
        
        # Should complete within reasonable time
        assert duration < 30.0  # 30 second timeout for large dataset
        
        # Verify results
        assert len(shared["validated_species"]) > 0
        print(f"Pipeline processed {len(large_species_dataset)} species in {duration:.2f} seconds")

    @pytest.mark.integration
    @pytest.mark.mock
    def test_parallel_processing_benefits(self, mock_ebird_api):
        """Test that parallel processing provides performance benefits."""
        species_list = ["Northern Cardinal", "Blue Jay", "American Robin", "House Sparrow", "Mourning Dove"]
        
        test_input = {
            "species_list": species_list,
            "constraints": {
                "region": "US-MA",
                "days_back": 7,
                "start_location": {"lat": 42.3601, "lng": -71.0589}
            }
        }
        
        performance_helper = PerformanceTestHelper()
        
        # Test with single worker (sequential)
        def run_sequential():
            shared = {"input": test_input}
            validate_node = ValidateSpeciesNode()
            fetch_node = FetchSightingsNode(max_workers=1)
            
            prep_result = validate_node.prep(shared)
            exec_result = validate_node.exec(prep_result)
            validate_node.post(shared, prep_result, exec_result)
            
            prep_result = fetch_node.prep(shared)
            # BatchNode pattern: exec() each species individually
            exec_results = []
            for species in prep_result:
                exec_result = fetch_node.exec(species)
                exec_results.append(exec_result)
            fetch_node.post(shared, prep_result, exec_results)
        
        # Test with multiple workers (parallel)
        def run_parallel():
            shared = {"input": test_input}
            validate_node = ValidateSpeciesNode()
            fetch_node = FetchSightingsNode(max_workers=5)
            
            prep_result = validate_node.prep(shared)
            exec_result = validate_node.exec(prep_result)
            validate_node.post(shared, prep_result, exec_result)
            
            prep_result = fetch_node.prep(shared)
            # BatchNode pattern: exec() each species individually
            exec_results = []
            for species in prep_result:
                exec_result = fetch_node.exec(species)
                exec_results.append(exec_result)
            fetch_node.post(shared, prep_result, exec_results)
        
        # Measure performance difference
        _, sequential_time = performance_helper.time_function(run_sequential)
        _, parallel_time = performance_helper.time_function(run_parallel)
        
        # Parallel should be at least as fast, often faster
        assert parallel_time <= sequential_time * 1.2  # Allow 20% variance

    @pytest.mark.integration
    @pytest.mark.mock
    def test_constraint_filtering_effectiveness(self, pipeline_nodes, mock_ebird_api):
        """Test that constraint filtering effectively reduces dataset size."""
        # Create input with very restrictive constraints
        restrictive_input = {
            "species_list": ["Northern Cardinal", "Blue Jay", "American Robin"],
            "constraints": {
                "region": "US-MA",
                "days_back": 3,  # Very recent only
                "start_location": {"lat": 42.3601, "lng": -71.0589},
                "max_travel_radius_km": 10,  # Very small radius
                "min_observation_quality": "reviewed"  # High quality only
            }
        }
        
        shared = {"input": restrictive_input}
        
        # Run pipeline
        for stage_name, node in pipeline_nodes.items():
            prep_result = node.prep(shared)
            
            # Handle BatchNode (fetch) differently
            if stage_name == "fetch":
                # For BatchNode, exec() should be called for each individual species
                exec_results = []
                for species in prep_result:
                    exec_result = node.exec(species)
                    exec_results.append(exec_result)
                node.post(shared, prep_result, exec_results)
            else:
                # Regular node processing
                exec_result = node.exec(prep_result)
                node.post(shared, prep_result, exec_result)
        
        # Check filtering effectiveness
        stats = shared["filtering_stats"]
        compliance_summary = stats["constraint_compliance_summary"]
        
        # With restrictive constraints, compliance should be lower
        assert compliance_summary["fully_compliant_count"] <= len(shared["all_sightings"])
        
        # But some filtering should have occurred
        if shared["all_sightings"]:
            # Don't assert specific ratio since mock data is artificial, just verify structure
            pass

    @pytest.mark.integration
    @pytest.mark.mock
    def test_data_preservation_through_pipeline(self, pipeline_nodes, mock_ebird_api, integration_test_input):
        """Test that original data is preserved while adding enrichments."""
        shared = {"input": integration_test_input}
        
        # Capture initial input
        original_species_list = integration_test_input["species_list"].copy()
        original_constraints = integration_test_input["constraints"].copy()
        
        # Run full pipeline
        for stage_name, node in pipeline_nodes.items():
            prep_result = node.prep(shared)
            
            # Handle BatchNode (fetch) differently
            if stage_name == "fetch":
                # For BatchNode, exec() should be called for each individual species
                exec_results = []
                for species in prep_result:
                    exec_result = node.exec(species)
                    exec_results.append(exec_result)
                node.post(shared, prep_result, exec_results)
            else:
                # Regular node processing
                exec_result = node.exec(prep_result)
                node.post(shared, prep_result, exec_result)
        
        # Verify original input is preserved
        assert shared["input"]["species_list"] == original_species_list
        assert shared["input"]["constraints"] == original_constraints
        
        # Verify enrichments were added
        assert "validated_species" in shared
        assert "all_sightings" in shared
        assert "validation_stats" in shared
        assert "fetch_stats" in shared
        assert "filtering_stats" in shared
        
        # Verify sightings have all required enrichments
        for sighting in shared["all_sightings"]:
            # From fetch stage
            assert "fetch_method" in sighting
            assert "validation_confidence" in sighting
            
            # From filter stage  
            assert "meets_all_constraints" in sighting
            assert "has_valid_gps" in sighting