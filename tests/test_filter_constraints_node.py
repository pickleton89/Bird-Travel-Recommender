"""
Unit tests for FilterConstraintsNode using pytest framework.

Tests cover:
- Enrichment-in-place strategy with constraint flags
- Geographic filtering (distance calculations)
- Temporal filtering (date range compliance)
- Data quality filtering (GPS validation, observation quality)
- Travel feasibility assessment
- Duplicate detection
- Comprehensive statistics generation
"""

import pytest
from datetime import datetime, timedelta
from nodes import FilterConstraintsNode


class TestFilterConstraintsNode:
    """Test suite for FilterConstraintsNode."""

    @pytest.fixture
    def filter_node(self):
        """Create FilterConstraintsNode instance for testing."""
        return FilterConstraintsNode()

    @pytest.fixture
    def mock_sightings_comprehensive(self):
        """Comprehensive mock sightings data for testing various constraint scenarios."""
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Boston area coordinates
        boston_lat, boston_lng = 42.3601, -71.0589
        cambridge_lat, cambridge_lng = 42.3736, -71.1097
        worcester_lat, worcester_lng = 42.2626, -71.8023  # ~65 km from Boston
        
        return [
            # Valid sighting near Boston - should meet all constraints
            {
                "speciesCode": "norcar",
                "comName": "Northern Cardinal",
                "sciName": "Cardinalis cardinalis",
                "locName": "Boston Common",
                "obsDt": yesterday.strftime("%Y-%m-%d %H:%M"),
                "howMany": 2,
                "lat": boston_lat,
                "lng": boston_lng,
                "locId": "L123456",
                "obsValid": True,
                "obsReviewed": False,
                "locationPrivate": False,
                "fetch_method": "nearby_observations",
                "validation_confidence": 1.0
            },
            # Valid sighting in Cambridge - close to Boston
            {
                "speciesCode": "blujay",
                "comName": "Blue Jay",
                "sciName": "Cyanocitta cristata",
                "locName": "Harvard Yard",
                "obsDt": today.strftime("%Y-%m-%d %H:%M"),
                "howMany": 1,
                "lat": cambridge_lat,
                "lng": cambridge_lng,
                "locId": "L234567",
                "obsValid": True,
                "obsReviewed": True,
                "locationPrivate": False,
                "fetch_method": "species_observations",
                "validation_confidence": 1.0
            },
            # Sighting far from Boston - should fail distance constraint
            {
                "speciesCode": "amerob",
                "comName": "American Robin",
                "sciName": "Turdus migratorius",
                "locName": "Worcester Park",
                "obsDt": yesterday.strftime("%Y-%m-%d %H:%M"),
                "howMany": 3,
                "lat": worcester_lat,
                "lng": worcester_lng,
                "locId": "L345678",
                "obsValid": True,
                "obsReviewed": False,
                "locationPrivate": False,
                "fetch_method": "species_observations",
                "validation_confidence": 0.8
            },
            # Old sighting - should fail date constraint
            {
                "speciesCode": "norcar",
                "comName": "Northern Cardinal",
                "sciName": "Cardinalis cardinalis",
                "locName": "Boston Common",
                "obsDt": month_ago.strftime("%Y-%m-%d %H:%M"),
                "howMany": 1,
                "lat": boston_lat,
                "lng": boston_lng,
                "locId": "L123456",
                "obsValid": True,
                "obsReviewed": False,
                "locationPrivate": False,
                "fetch_method": "nearby_observations",
                "validation_confidence": 1.0
            },
            # Invalid coordinates - should fail GPS validation
            {
                "speciesCode": "blujay",
                "comName": "Blue Jay",
                "sciName": "Cyanocitta cristata",
                "locName": "Invalid Location",
                "obsDt": yesterday.strftime("%Y-%m-%d %H:%M"),
                "howMany": 1,
                "lat": None,
                "lng": None,
                "locId": "L456789",
                "obsValid": True,
                "obsReviewed": False,
                "locationPrivate": False,
                "fetch_method": "species_observations",
                "validation_confidence": 1.0
            },
            # Low quality sighting - not validated
            {
                "speciesCode": "amerob",
                "comName": "American Robin",
                "sciName": "Turdus migratorius",
                "locName": "Near Boston",
                "obsDt": today.strftime("%Y-%m-%d %H:%M"),
                "howMany": 1,
                "lat": boston_lat + 0.01,
                "lng": boston_lng + 0.01,
                "locId": "L567890",
                "obsValid": False,  # Invalid observation
                "obsReviewed": False,
                "locationPrivate": True,
                "fetch_method": "nearby_observations",
                "validation_confidence": 0.5
            }
        ]

    @pytest.fixture
    def standard_constraints(self):
        """Standard test constraints for Boston area trip."""
        return {
            "start_location": {"lat": 42.3601, "lng": -71.0589},  # Boston
            "max_daily_distance_km": 100,
            "max_travel_radius_km": 50,
            "days_back": 14,
            "region": "US-MA",
            "min_observation_quality": "valid"
        }

    @pytest.mark.unit
    @pytest.mark.mock
    def test_prep_phase(self, filter_node, mock_sightings_comprehensive, standard_constraints):
        """Test the preparation phase of FilterConstraintsNode."""
        shared = {
            "all_sightings": mock_sightings_comprehensive,
            "input": {"constraints": standard_constraints}
        }
        
        result = filter_node.prep(shared)
        
        assert result is not None
        assert "sightings" in result
        assert "constraints" in result
        assert len(result["sightings"]) == len(mock_sightings_comprehensive)

    @pytest.mark.unit
    @pytest.mark.mock
    def test_geographic_filtering(self, filter_node, mock_sightings_comprehensive, standard_constraints):
        """Test geographic distance filtering."""
        shared = {
            "all_sightings": mock_sightings_comprehensive.copy(),
            "input": {"constraints": standard_constraints}
        }
        
        prep_result = filter_node.prep(shared)
        exec_result = filter_node.exec(prep_result)
        filter_node.post(shared, prep_result, exec_result)
        
        # Check that distance calculations were added
        for sighting in shared["all_sightings"]:
            if sighting.get("has_valid_gps"):
                assert "distance_from_start_km" in sighting
                assert "within_travel_radius" in sighting
                assert isinstance(sighting["distance_from_start_km"], (int, float))
        
        # Check statistics
        stats = shared["filtering_stats"]
        assert "within_travel_radius" in stats
        
        # Worcester sighting should be outside radius (>65km from Boston)
        worcester_sighting = next((s for s in shared["all_sightings"] if "Worcester" in s.get("locName", "")), None)
        if worcester_sighting and worcester_sighting.get("has_valid_gps"):
            assert not worcester_sighting["within_travel_radius"]

    @pytest.mark.unit
    @pytest.mark.mock
    def test_temporal_filtering(self, filter_node, mock_sightings_comprehensive, standard_constraints):
        """Test temporal date range filtering."""
        shared = {
            "all_sightings": mock_sightings_comprehensive.copy(),
            "input": {"constraints": standard_constraints}
        }
        
        prep_result = filter_node.prep(shared)
        exec_result = filter_node.exec(prep_result)
        filter_node.post(shared, prep_result, exec_result)
        
        # Check that temporal filtering was applied
        for sighting in shared["all_sightings"]:
            assert "within_date_range" in sighting
            assert isinstance(sighting["within_date_range"], bool)
        
        # Old sighting (month ago) should be outside date range
        month_old_sightings = [s for s in shared["all_sightings"] 
                              if not s.get("within_date_range", True)]
        assert len(month_old_sightings) >= 1

    @pytest.mark.unit
    @pytest.mark.mock
    def test_gps_validation(self, filter_node, mock_sightings_comprehensive, standard_constraints):
        """Test GPS coordinate validation."""
        shared = {
            "all_sightings": mock_sightings_comprehensive.copy(),
            "input": {"constraints": standard_constraints}
        }
        
        prep_result = filter_node.prep(shared)
        exec_result = filter_node.exec(prep_result)
        filter_node.post(shared, prep_result, exec_result)
        
        # Check GPS validation flags
        for sighting in shared["all_sightings"]:
            assert "has_valid_gps" in sighting
            
            if sighting["lat"] is None or sighting["lng"] is None:
                assert not sighting["has_valid_gps"]
            else:
                assert sighting["has_valid_gps"]

    @pytest.mark.unit
    @pytest.mark.mock
    def test_observation_quality_filtering(self, filter_node, mock_sightings_comprehensive):
        """Test observation quality filtering with different requirements."""
        # Test with strict quality requirements
        strict_constraints = {
            "region": "US-MA",
            "days_back": 14,
            "min_observation_quality": "reviewed"  # Only reviewed observations
        }
        
        shared = {
            "all_sightings": mock_sightings_comprehensive.copy(),
            "input": {"constraints": strict_constraints}
        }
        
        prep_result = filter_node.prep(shared)
        exec_result = filter_node.exec(prep_result)
        filter_node.post(shared, prep_result, exec_result)
        
        # Check quality compliance
        for sighting in shared["all_sightings"]:
            assert "quality_compliant" in sighting
            
            if strict_constraints["min_observation_quality"] == "reviewed":
                if sighting.get("obsReviewed"):
                    assert sighting["quality_compliant"]
                else:
                    assert not sighting["quality_compliant"]

    @pytest.mark.unit
    @pytest.mark.mock
    def test_duplicate_detection(self, filter_node, standard_constraints):
        """Test duplicate sighting detection."""
        # Create sightings with duplicates
        today = datetime.now()
        duplicate_sightings = [
            {
                "speciesCode": "norcar",
                "comName": "Northern Cardinal",
                "locName": "Boston Common",
                "obsDt": today.strftime("%Y-%m-%d %H:%M"),
                "lat": 42.3601,
                "lng": -71.0589,
                "locId": "L123456",
                "obsValid": True,
                "howMany": 2
            },
            {
                "speciesCode": "norcar",
                "comName": "Northern Cardinal", 
                "locName": "Boston Common",
                "obsDt": today.strftime("%Y-%m-%d %H:%M"),
                "lat": 42.3601,
                "lng": -71.0589,
                "locId": "L123456",
                "obsValid": True,
                "howMany": 3  # Different count but same location/species/date
            }
        ]
        
        shared = {
            "all_sightings": duplicate_sightings,
            "input": {"constraints": standard_constraints}
        }
        
        prep_result = filter_node.prep(shared)
        exec_result = filter_node.exec(prep_result)
        filter_node.post(shared, prep_result, exec_result)
        
        # Check duplicate detection
        duplicate_flags = [s.get("is_duplicate", False) for s in shared["all_sightings"]]
        assert any(duplicate_flags), "Should detect duplicates"
        
        stats = shared["filtering_stats"]
        assert stats["duplicates_flagged"] >= 1

    @pytest.mark.unit
    @pytest.mark.mock
    def test_enrichment_in_place_strategy(self, filter_node, mock_sightings_comprehensive, standard_constraints):
        """Test that enrichment-in-place preserves original data while adding flags."""
        original_sightings = mock_sightings_comprehensive.copy()
        
        shared = {
            "all_sightings": mock_sightings_comprehensive.copy(),
            "input": {"constraints": standard_constraints}
        }
        
        prep_result = filter_node.prep(shared)
        exec_result = filter_node.exec(prep_result)
        filter_node.post(shared, prep_result, exec_result)
        
        # Check that original data is preserved
        for i, sighting in enumerate(shared["all_sightings"]):
            original = original_sightings[i]
            
            # Original eBird fields should be unchanged
            for key in ["speciesCode", "comName", "locName", "obsDt", "howMany"]:
                assert sighting[key] == original[key]
            
            # New constraint flags should be added
            constraint_flags = [
                "has_valid_gps", "within_travel_radius", "within_date_range",
                "quality_compliant", "is_duplicate", "meets_all_constraints"
            ]
            for flag in constraint_flags:
                assert flag in sighting

    @pytest.mark.unit
    @pytest.mark.mock
    def test_comprehensive_statistics_generation(self, filter_node, mock_sightings_comprehensive, standard_constraints):
        """Test that comprehensive filtering statistics are generated."""
        shared = {
            "all_sightings": mock_sightings_comprehensive.copy(),
            "input": {"constraints": standard_constraints}
        }
        
        prep_result = filter_node.prep(shared)
        exec_result = filter_node.exec(prep_result)
        filter_node.post(shared, prep_result, exec_result)
        
        stats = shared["filtering_stats"]
        
        # Check all required statistics fields
        required_fields = [
            "total_input_sightings", "valid_coordinates", "within_travel_radius",
            "within_date_range", "within_region", "high_quality_observations",
            "duplicates_flagged", "travel_feasible", "constraint_compliance_summary"
        ]
        
        for field in required_fields:
            assert field in stats
        
        # Check compliance summary
        summary = stats["constraint_compliance_summary"]
        required_summary_fields = [
            "fully_compliant_count", "valid_coordinates_pct", "within_travel_radius_pct",
            "within_date_range_pct", "high_quality_pct", "travel_feasible_pct"
        ]
        
        for field in required_summary_fields:
            assert field in summary
            if field.endswith("_pct"):
                assert 0 <= summary[field] <= 100

    @pytest.mark.unit
    @pytest.mark.mock
    def test_no_location_constraints(self, filter_node, mock_sightings_comprehensive):
        """Test filtering when no location constraints are provided."""
        constraints_no_location = {
            "days_back": 30,
            "region": "US-MA",
            "min_observation_quality": "any"
        }
        
        shared = {
            "all_sightings": mock_sightings_comprehensive.copy(),
            "input": {"constraints": constraints_no_location}
        }
        
        prep_result = filter_node.prep(shared)
        exec_result = filter_node.exec(prep_result)
        filter_node.post(shared, prep_result, exec_result)
        
        # Should handle missing location constraints gracefully
        for sighting in shared["all_sightings"]:
            # Travel radius constraints should be marked as compliant when no location provided
            if "within_travel_radius" in sighting:
                assert sighting["within_travel_radius"] == True

    @pytest.mark.unit
    @pytest.mark.mock
    def test_empty_sightings_list(self, filter_node, standard_constraints):
        """Test handling of empty sightings list."""
        shared = {
            "all_sightings": [],
            "input": {"constraints": standard_constraints}
        }
        
        prep_result = filter_node.prep(shared)
        exec_result = filter_node.exec(prep_result)
        filter_node.post(shared, prep_result, exec_result)
        
        # Should handle empty list gracefully
        assert shared["all_sightings"] == []
        stats = shared["filtering_stats"]
        assert stats["total_input_sightings"] == 0
        assert stats["constraint_compliance_summary"]["fully_compliant_count"] == 0

    @pytest.mark.parametrize("quality_requirement,expected_compliant", [
        ("any", True),
        ("valid", True), 
        ("reviewed", False)  # Most test sightings are not reviewed
    ])
    @pytest.mark.unit
    @pytest.mark.mock
    def test_quality_requirements_parametrized(self, filter_node, quality_requirement, expected_compliant):
        """Test different observation quality requirements using parametrized testing."""
        # Valid unreviewed observation
        sighting = {
            "speciesCode": "norcar",
            "comName": "Northern Cardinal",
            "obsDt": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "lat": 42.3601,
            "lng": -71.0589,
            "obsValid": True,
            "obsReviewed": False,
            "locationPrivate": False
        }
        
        constraints = {
            "region": "US-MA",
            "days_back": 7,
            "min_observation_quality": quality_requirement
        }
        
        shared = {
            "all_sightings": [sighting],
            "input": {"constraints": constraints}
        }
        
        prep_result = filter_node.prep(shared)
        exec_result = filter_node.exec(prep_result)
        filter_node.post(shared, prep_result, exec_result)
        
        if quality_requirement == "reviewed":
            # Should not be compliant since obsReviewed is False
            assert not shared["all_sightings"][0]["quality_compliant"]
        else:
            # Should be compliant for "any" or "valid"
            assert shared["all_sightings"][0]["quality_compliant"]

    @pytest.mark.unit
    @pytest.mark.mock
    def test_regional_bounds_checking(self, filter_node, mock_sightings_comprehensive):
        """Test regional bounds checking for different US states."""
        constraints_ma = {
            "region": "US-MA",
            "days_back": 14
        }
        
        shared = {
            "all_sightings": mock_sightings_comprehensive.copy(),
            "input": {"constraints": constraints_ma}
        }
        
        prep_result = filter_node.prep(shared)
        exec_result = filter_node.exec(prep_result)
        filter_node.post(shared, prep_result, exec_result)
        
        # Check regional compliance
        for sighting in shared["all_sightings"]:
            if "within_region" in sighting:
                # Boston/Cambridge sightings should be within MA region
                if "Boston" in sighting.get("locName", "") or "Harvard" in sighting.get("locName", ""):
                    assert sighting["within_region"]