"""
End-to-end integration tests using real eBird API data.

This test module performs comprehensive testing with live API calls to validate
the complete birding pipeline in realistic scenarios.

WARNING: These tests make real API calls and may take longer to execute.
"""

import pytest
import time
import json
import os
from datetime import datetime
from typing import Dict, Any, List

from bird_travel_recommender.flow import run_birding_pipeline, create_test_input
from bird_travel_recommender.utils.ebird_api import get_client, EBirdAPIError
from tests.test_utils import PerformanceTestHelper
import logging

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestEndToEndRealAPI:
    """End-to-end tests using real eBird API data."""

    @pytest.fixture(scope="class")
    def api_client(self):
        """Get eBird API client for real API testing."""
        try:
            return get_client()
        except Exception as e:
            pytest.skip(f"Cannot connect to eBird API: {e}")

    @pytest.fixture
    def performance_helper(self):
        """Performance measurement helper."""
        return PerformanceTestHelper()

    @pytest.fixture
    def real_test_scenarios(self):
        """Real-world test scenarios based on design document user stories."""
        return {
            "fall_migration_new_england": {
                "name": "Fall Migration Enthusiast",
                "description": "5 specific warblers during fall migration in New England over a 3-day weekend",
                "input": {
                    "species_list": [
                        "Yellow Warbler",
                        "Black-throated Blue Warbler", 
                        "American Redstart",
                        "Bay-breasted Warbler",
                        "Blackpoll Warbler"
                    ],
                    "constraints": {
                        "start_location": {"lat": 42.3601, "lng": -71.0589},  # Boston
                        "max_days": 3,
                        "max_daily_distance_km": 150,
                        "region": "US-MA",
                        "days_back": 14,  # Fall migration timing
                        "max_locations_per_day": 6
                    }
                }
            },
            "winter_waterfowl_boston": {
                "name": "Winter Birding Trip",
                "description": "Weekend trip from Boston to see winter waterfowl within 2 hours drive",
                "input": {
                    "species_list": [
                        "Mallard",
                        "Common Goldeneye",
                        "Bufflehead",
                        "Red-breasted Merganser",
                        "Canada Goose"
                    ],
                    "constraints": {
                        "start_location": {"lat": 42.3601, "lng": -71.0589},  # Boston
                        "max_days": 2,
                        "max_daily_distance_km": 200,  # ~2 hours drive
                        "region": "US-MA",
                        "days_back": 7,
                        "max_locations_per_day": 8
                    }
                }
            },
            "quick_cardinal_lookup": {
                "name": "Quick Lookup",
                "description": "Show me recent cardinal sightings near Boston",
                "input": {
                    "species_list": ["Northern Cardinal"],
                    "constraints": {
                        "start_location": {"lat": 42.3601, "lng": -71.0589},  # Boston
                        "max_days": 1,
                        "max_daily_distance_km": 50,
                        "region": "US-MA", 
                        "days_back": 7,
                        "max_locations_per_day": 5
                    }
                }
            },
            "hartford_hotspots": {
                "name": "Hotspot Discovery",
                "description": "Best birding locations within 50km of Hartford, CT",
                "input": {
                    "species_list": [
                        "American Robin",
                        "Blue Jay", 
                        "House Sparrow",
                        "Mourning Dove"
                    ],
                    "constraints": {
                        "start_location": {"lat": 41.7658, "lng": -72.6734},  # Hartford, CT
                        "max_days": 1,
                        "max_daily_distance_km": 100,  # 50km radius
                        "region": "US-CT",
                        "days_back": 7,
                        "max_locations_per_day": 8
                    }
                }
            }
        }

    @pytest.mark.api
    @pytest.mark.slow
    def test_api_connectivity(self, api_client):
        """Test basic eBird API connectivity."""
        try:
            # Test basic API call
            observations = api_client.get_recent_observations("US-MA", days_back=1)
            assert isinstance(observations, list)
            logger.info(f"API connectivity test successful: {len(observations)} recent observations")
        except Exception as e:
            pytest.fail(f"eBird API connectivity failed: {e}")

    @pytest.mark.api
    @pytest.mark.slow
    def test_end_to_end_pipeline_with_real_data(self, api_client, performance_helper, real_test_scenarios):
        """Test complete pipeline execution with real eBird API data."""
        
        # Use the quick cardinal lookup for fast testing
        scenario = real_test_scenarios["quick_cardinal_lookup"]
        test_input = {"input": scenario["input"]}
        
        logger.info(f"Testing scenario: {scenario['name']}")
        logger.info(f"Description: {scenario['description']}")
        
        # Time the complete pipeline execution
        def run_pipeline():
            return run_birding_pipeline(input_data=test_input, debug=True)
        
        start_time = time.time()
        result, duration = performance_helper.time_function(run_pipeline)
        
        # Verify pipeline success
        assert result["success"], f"Pipeline failed: {result.get('error', 'Unknown error')}"
        
        # Verify basic result structure
        assert "itinerary_markdown" in result
        assert "pipeline_statistics" in result
        assert len(result["itinerary_markdown"]) > 0
        
        # Verify statistics contain expected data
        stats = result["pipeline_statistics"]
        assert "validation_stats" in stats
        assert "fetch_stats" in stats
        assert "filtering_stats" in stats
        assert "clustering_stats" in stats
        assert "scoring_stats" in stats
        assert "route_optimization_stats" in stats
        assert "itinerary_generation_stats" in stats
        
        # Log performance metrics
        logger.info(f"Pipeline execution completed in {duration:.2f} seconds")
        successful_validations = stats['validation_stats']['direct_taxonomy_matches'] + stats['validation_stats']['llm_fuzzy_matches']
        logger.info(f"Species validated: {successful_validations}")
        logger.info(f"Observations fetched: {stats['fetch_stats']['total_observations']}")
        logger.info(f"Clusters created: {stats['clustering_stats']['clusters_created']}")
        
        # Verify reasonable performance (should complete within 30 seconds)
        assert duration < 30.0, f"Pipeline took too long: {duration:.2f} seconds"
        
        return result

    @pytest.mark.api
    @pytest.mark.slow
    def test_multiple_scenarios(self, api_client, real_test_scenarios, performance_helper):
        """Test multiple real-world scenarios."""
        
        results = {}
        total_start_time = time.time()
        
        # Test each scenario (limit to 2 for CI speed)
        scenarios_to_test = ["quick_cardinal_lookup", "winter_waterfowl_boston"]
        
        for scenario_name in scenarios_to_test:
            scenario = real_test_scenarios[scenario_name]
            test_input = {"input": scenario["input"]}
            
            logger.info(f"\n--- Testing Scenario: {scenario['name']} ---")
            
            try:
                result, duration = performance_helper.time_function(
                    lambda: run_birding_pipeline(input_data=test_input, debug=False)
                )
                
                assert result["success"], f"Scenario {scenario_name} failed: {result.get('error')}"
                
                results[scenario_name] = {
                    "success": True,
                    "duration": duration,
                    "stats": result["pipeline_statistics"],
                    "itinerary_length": len(result["itinerary_markdown"])
                }
                
                logger.info(f"✅ {scenario['name']} completed in {duration:.2f}s")
                
            except Exception as e:
                logger.error(f"❌ {scenario['name']} failed: {e}")
                results[scenario_name] = {
                    "success": False,
                    "error": str(e),
                    "duration": 0
                }
        
        total_duration = time.time() - total_start_time
        
        # Verify at least one scenario succeeded
        successful_scenarios = [name for name, result in results.items() if result["success"]]
        assert len(successful_scenarios) > 0, "No scenarios completed successfully"
        
        logger.info(f"\n📊 MULTI-SCENARIO TEST RESULTS:")
        logger.info(f"Total execution time: {total_duration:.2f} seconds")
        logger.info(f"Successful scenarios: {len(successful_scenarios)}/{len(scenarios_to_test)}")
        
        for name, result in results.items():
            if result["success"]:
                logger.info(f"  ✅ {name}: {result['duration']:.2f}s")
            else:
                logger.info(f"  ❌ {name}: {result['error']}")

    @pytest.mark.api
    @pytest.mark.slow
    def test_error_handling_with_real_api(self, api_client):
        """Test error handling with edge cases using real API."""
        
        # Test with invalid species
        invalid_species_input = {
            "input": {
                "species_list": ["Nonexistent Bird Species", "Made Up Warbler"],
                "constraints": {
                    "start_location": {"lat": 42.3601, "lng": -71.0589},
                    "max_days": 1,
                    "max_daily_distance_km": 50,
                    "region": "US-MA",
                    "days_back": 7
                }
            }
        }
        
        result = run_birding_pipeline(input_data=invalid_species_input, debug=True)
        
        # Pipeline should still succeed with graceful handling
        assert result["success"], "Pipeline should handle invalid species gracefully"
        
        # Check that validation stats show failed validations
        validation_stats = result["pipeline_statistics"]["validation_stats"]
        assert validation_stats["failed_validations"] > 0
        
        logger.info("✅ Invalid species handled gracefully")

    @pytest.mark.api
    @pytest.mark.slow  
    def test_performance_benchmarking(self, api_client, performance_helper):
        """Benchmark pipeline performance with real API data."""
        
        # Create a moderately complex scenario for benchmarking
        benchmark_input = {
            "input": {
                "species_list": [
                    "Northern Cardinal", "Blue Jay", "American Robin", 
                    "House Sparrow", "Mourning Dove", "Rock Pigeon"
                ],
                "constraints": {
                    "start_location": {"lat": 42.3601, "lng": -71.0589},
                    "max_days": 2, 
                    "max_daily_distance_km": 100,
                    "region": "US-MA",
                    "days_back": 7,
                    "max_locations_per_day": 6
                }
            }
        }
        
        # Run multiple iterations for performance measurement
        iterations = 3
        durations = []
        
        for i in range(iterations):
            logger.info(f"Performance test iteration {i+1}/{iterations}")
            
            result, duration = performance_helper.time_function(
                lambda: run_birding_pipeline(input_data=benchmark_input, debug=False)
            )
            
            assert result["success"], f"Benchmark iteration {i+1} failed"
            durations.append(duration)
        
        # Calculate performance metrics
        avg_duration = sum(durations) / len(durations)
        min_duration = min(durations)
        max_duration = max(durations)
        
        logger.info(f"\n📊 PERFORMANCE BENCHMARK RESULTS:")
        logger.info(f"Average execution time: {avg_duration:.2f}s")
        logger.info(f"Fastest execution: {min_duration:.2f}s")
        logger.info(f"Slowest execution: {max_duration:.2f}s")
        logger.info(f"Performance variation: {max_duration - min_duration:.2f}s")
        
        # Reasonable performance expectations
        assert avg_duration < 25.0, f"Average performance too slow: {avg_duration:.2f}s"
        assert max_duration < 40.0, f"Worst case performance too slow: {max_duration:.2f}s"

    @pytest.mark.api
    @pytest.mark.slow
    def test_data_quality_validation(self, api_client):
        """Test data quality and validation with real API responses."""
        
        test_input = {
            "input": {
                "species_list": ["Northern Cardinal", "Blue Jay"],
                "constraints": {
                    "start_location": {"lat": 42.3601, "lng": -71.0589},
                    "max_days": 1,
                    "max_daily_distance_km": 30,
                    "region": "US-MA",
                    "days_back": 7
                }
            }
        }
        
        result = run_birding_pipeline(input_data=test_input, debug=True)
        assert result["success"], "Pipeline execution failed"
        
        # Get the full shared store for detailed validation
        # Note: This requires modifying the flow to return shared store data
        stats = result["pipeline_statistics"]
        
        # Validate species validation stage
        validation_stats = stats["validation_stats"]
        assert validation_stats["total_input"] == 2
        assert validation_stats["successful_validations"] > 0
        
        # Validate fetch stage
        fetch_stats = stats["fetch_stats"]
        assert fetch_stats["total_species_processed"] > 0
        assert fetch_stats["total_observations"] >= 0  # Could be 0 for rare species
        
        # Validate filtering stage
        filtering_stats = stats["filtering_stats"]
        assert "constraint_compliance_summary" in filtering_stats
        assert "total_input_sightings" in filtering_stats
        
        # Validate clustering stage
        clustering_stats = stats["clustering_stats"]
        assert "clusters_created" in clustering_stats
        assert clustering_stats["clusters_created"] >= 0
        
        # Validate scoring stage
        scoring_stats = stats["scoring_stats"]
        assert "locations_scored" in scoring_stats
        
        # Validate route optimization
        route_stats = stats["route_optimization_stats"]
        assert "optimization_method" in route_stats
        
        # Validate itinerary generation
        itinerary_stats = stats["itinerary_generation_stats"]
        assert "itinerary_method" in itinerary_stats
        
        logger.info("✅ Data quality validation passed")

    @pytest.mark.api
    def test_save_real_test_results(self, api_client, tmp_path):
        """Save real test results for analysis and debugging."""
        
        test_input = {
            "input": {
                "species_list": ["Northern Cardinal"],
                "constraints": {
                    "start_location": {"lat": 42.3601, "lng": -71.0589},
                    "max_days": 1,
                    "max_daily_distance_km": 25,
                    "region": "US-MA",
                    "days_back": 3
                }
            }
        }
        
        result = run_birding_pipeline(input_data=test_input, debug=True)
        assert result["success"], "Pipeline execution failed"
        
        # Save results for analysis
        results_file = tmp_path / "real_api_test_results.json"
        
        # Prepare results for JSON serialization
        test_results = {
            "test_timestamp": datetime.now().isoformat(),
            "test_input": test_input,
            "pipeline_success": result["success"],
            "pipeline_statistics": result["pipeline_statistics"],
            "itinerary_length": len(result["itinerary_markdown"]),
            "itinerary_preview": result["itinerary_markdown"][:500] + "..." if len(result["itinerary_markdown"]) > 500 else result["itinerary_markdown"]
        }
        
        with open(results_file, 'w') as f:
            json.dump(test_results, f, indent=2)
        
        logger.info(f"Test results saved to: {results_file}")
        
        # Verify file was created and has content
        assert results_file.exists()
        assert results_file.stat().st_size > 0