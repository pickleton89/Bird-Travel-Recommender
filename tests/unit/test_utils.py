"""
Test utilities and helper functions for Bird Travel Recommender tests.

Provides:
- Data validation utilities
- Test data generators
- Performance testing helpers
- API response validators
"""

import pytest
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json
import time
from utils.geo_utils import haversine_distance


class TestDataValidator:
    """Utilities for validating test data and results."""
    
    @staticmethod
    def validate_species_data(species: Dict[str, Any]) -> bool:
        """Validate that species data has required fields."""
        required_fields = [
            "original_name", "common_name", "scientific_name", "species_code",
            "validation_method", "confidence", "seasonal_notes", "behavioral_notes"
        ]
        
        for field in required_fields:
            if field not in species:
                return False
        
        # Validate confidence is between 0 and 1
        if not (0 <= species["confidence"] <= 1):
            return False
        
        # Validate method is valid
        valid_methods = [
            "direct_common_name", "direct_scientific_name", "direct_species_code",
            "partial_common_name", "partial_scientific_name", "llm_fuzzy_match"
        ]
        if species["validation_method"] not in valid_methods:
            return False
        
        return True
    
    @staticmethod
    def validate_sighting_data(sighting: Dict[str, Any]) -> bool:
        """Validate that sighting data has required eBird fields."""
        required_ebird_fields = [
            "speciesCode", "comName", "sciName", "locName", "obsDt",
            "lat", "lng", "locId", "obsValid"
        ]
        
        for field in required_ebird_fields:
            if field not in sighting:
                return False
        
        # Validate coordinates if present
        if sighting["lat"] is not None and sighting["lng"] is not None:
            if not (-90 <= sighting["lat"] <= 90):
                return False
            if not (-180 <= sighting["lng"] <= 180):
                return False
        
        return True
    
    @staticmethod
    def validate_enriched_sighting(sighting: Dict[str, Any]) -> bool:
        """Validate that sighting has been enriched with constraint flags."""
        required_flags = [
            "has_valid_gps", "within_travel_radius", "within_date_range",
            "quality_compliant", "is_duplicate", "meets_all_constraints"
        ]
        
        for flag in required_flags:
            if flag not in sighting:
                return False
            if not isinstance(sighting[flag], bool):
                return False
        
        return True
    
    @staticmethod
    def validate_statistics(stats: Dict[str, Any], stat_type: str) -> bool:
        """Validate statistics structure based on type."""
        if stat_type == "validation":
            required_fields = [
                "total_input_species", "successfully_validated", "validation_rate",
                "validation_methods_used"
            ]
        elif stat_type == "fetch":
            required_fields = [
                "total_species", "successful_fetches", "api_errors", "empty_results",
                "total_observations", "unique_locations", "fetch_method_stats"
            ]
        elif stat_type == "filtering":
            required_fields = [
                "total_input_sightings", "valid_coordinates", "within_travel_radius",
                "within_date_range", "constraint_compliance_summary"
            ]
        else:
            return False
        
        for field in required_fields:
            if field not in stats:
                return False
        
        return True


class TestDataGenerator:
    """Generate test data for various scenarios."""
    
    @staticmethod
    def generate_species_list(count: int, include_invalid: bool = False) -> List[str]:
        """Generate a list of bird species names for testing."""
        valid_species = [
            "Northern Cardinal", "Blue Jay", "American Robin", "House Sparrow",
            "Mourning Dove", "Red-winged Blackbird", "American Goldfinch",
            "Common Grackle", "European Starling", "Song Sparrow"
        ]
        
        species_list = valid_species[:count]
        
        if include_invalid:
            invalid_species = ["Invalid Bird", "Made Up Species", "Nonexistent Fowl"]
            species_list.extend(invalid_species[:min(2, count // 3)])
        
        return species_list
    
    @staticmethod
    def generate_coordinates_near(center_lat: float, center_lng: float, 
                                count: int, max_distance_km: float = 50) -> List[tuple]:
        """Generate random coordinates near a center point."""
        import random
        
        coordinates = []
        for _ in range(count):
            # Simple random offset (not perfectly uniform but good for testing)
            lat_offset = random.uniform(-0.5, 0.5)  # Roughly ±55km
            lng_offset = random.uniform(-0.5, 0.5)
            
            new_lat = center_lat + lat_offset
            new_lng = center_lng + lng_offset
            
            # Check if within desired distance
            distance = haversine_distance(center_lat, center_lng, new_lat, new_lng)
            if distance <= max_distance_km:
                coordinates.append((new_lat, new_lng))
        
        return coordinates
    
    @staticmethod
    def generate_mock_sightings(species_codes: List[str], 
                              locations: List[tuple],
                              days_back: int = 7) -> List[Dict[str, Any]]:
        """Generate mock eBird sightings for testing."""
        import random
        
        species_map = {
            "norcar": {"comName": "Northern Cardinal", "sciName": "Cardinalis cardinalis"},
            "blujay": {"comName": "Blue Jay", "sciName": "Cyanocitta cristata"},
            "amerob": {"comName": "American Robin", "sciName": "Turdus migratorius"},
            "houspa": {"comName": "House Sparrow", "sciName": "Passer domesticus"},
            "moudov": {"comName": "Mourning Dove", "sciName": "Zenaida macroura"}
        }
        
        sightings = []
        base_date = datetime.now()
        
        for i, species_code in enumerate(species_codes):
            if species_code not in species_map:
                continue
                
            for j, (lat, lng) in enumerate(locations):
                # Random date within the specified range
                days_offset = random.randint(0, days_back)
                obs_date = base_date - timedelta(days=days_offset)
                
                sighting = {
                    "speciesCode": species_code,
                    "comName": species_map[species_code]["comName"],
                    "sciName": species_map[species_code]["sciName"],
                    "locName": f"Test Location {i}-{j}",
                    "obsDt": obs_date.strftime("%Y-%m-%d %H:%M"),
                    "howMany": random.randint(1, 5),
                    "lat": lat,
                    "lng": lng,
                    "locId": f"L{i:03d}{j:03d}",
                    "obsValid": random.choice([True, True, True, False]),  # Mostly valid
                    "obsReviewed": random.choice([True, False]),
                    "locationPrivate": False,
                    "fetch_method": random.choice(["nearby_observations", "species_observations"]),
                    "validation_confidence": random.uniform(0.7, 1.0)
                }
                
                sightings.append(sighting)
        
        return sightings


class PerformanceTestHelper:
    """Helper for performance testing."""
    
    @staticmethod
    def time_function(func, *args, **kwargs):
        """Time a function execution and return result and duration."""
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        duration = end_time - start_time
        return result, duration
    
    @staticmethod
    def measure_parallel_speedup(func, sequential_args, parallel_args):
        """Measure speedup from parallelization."""
        # Run sequential version
        _, sequential_time = PerformanceTestHelper.time_function(func, *sequential_args)
        
        # Run parallel version
        _, parallel_time = PerformanceTestHelper.time_function(func, *parallel_args)
        
        speedup = sequential_time / parallel_time if parallel_time > 0 else 0
        return speedup, sequential_time, parallel_time


class APIResponseValidator:
    """Validate API responses match expected eBird format."""
    
    @staticmethod
    def validate_taxonomy_response(response: List[Dict[str, Any]]) -> bool:
        """Validate eBird taxonomy API response format."""
        required_fields = ["sciName", "comName", "speciesCode", "category"]
        
        for item in response:
            for field in required_fields:
                if field not in item:
                    return False
        
        return True
    
    @staticmethod
    def validate_observations_response(response: List[Dict[str, Any]]) -> bool:
        """Validate eBird observations API response format."""
        required_fields = [
            "speciesCode", "comName", "sciName", "locName", "obsDt",
            "lat", "lng", "locId", "obsValid"
        ]
        
        for item in response:
            for field in required_fields:
                if field not in item:
                    return False
        
        return True
    
    @staticmethod
    def validate_hotspots_response(response: List[Dict[str, Any]]) -> bool:
        """Validate eBird hotspots API response format."""
        required_fields = [
            "locId", "locName", "countryCode", "subnational1Code",
            "lat", "lng", "latestObsDt"
        ]
        
        for item in response:
            for field in required_fields:
                if field not in item:
                    return False
        
        return True


# Test fixtures using the utilities above
@pytest.fixture
def data_validator():
    """Provide TestDataValidator instance."""
    return TestDataValidator()


@pytest.fixture
def data_generator():
    """Provide TestDataGenerator instance.""" 
    return TestDataGenerator()


@pytest.fixture
def performance_helper():
    """Provide PerformanceTestHelper instance."""
    return PerformanceTestHelper()


@pytest.fixture
def api_validator():
    """Provide APIResponseValidator instance."""
    return APIResponseValidator()


@pytest.fixture
def large_species_dataset(data_generator):
    """Generate large species dataset for performance testing."""
    return data_generator.generate_species_list(50, include_invalid=True)


@pytest.fixture
def boston_area_locations(data_generator):
    """Generate locations in Boston area for testing."""
    boston_lat, boston_lng = 42.3601, -71.0589
    return data_generator.generate_coordinates_near(
        boston_lat, boston_lng, count=20, max_distance_km=30
    )


@pytest.fixture
def comprehensive_test_sightings(data_generator, boston_area_locations):
    """Generate comprehensive test sightings dataset."""
    species_codes = ["norcar", "blujay", "amerob", "houspa", "moudov"]
    return data_generator.generate_mock_sightings(
        species_codes, boston_area_locations[:10], days_back=14
    )