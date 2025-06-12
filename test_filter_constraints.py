#!/usr/bin/env python3
"""
Test script for FilterConstraintsNode to verify constraint filtering and enrichment-in-place strategy.
"""

import logging
from datetime import datetime, timedelta
from nodes import FilterConstraintsNode

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def create_mock_sightings():
    """Create mock eBird sightings for testing."""
    
    # Boston area coordinates for testing
    boston_lat, boston_lng = 42.3601, -71.0589
    cambridge_lat, cambridge_lng = 42.3736, -71.1097
    worcester_lat, worcester_lng = 42.2626, -71.8023  # ~65 km from Boston
    
    # Create test sightings with various characteristics
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    mock_sightings = [
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
        
        # Duplicate sighting - same location, species, date as first sighting
        {
            "speciesCode": "norcar",
            "comName": "Northern Cardinal",
            "sciName": "Cardinalis cardinalis",
            "locName": "Boston Common",
            "obsDt": yesterday.strftime("%Y-%m-%d %H:%M"),
            "howMany": 3,  # Different count but same location/species/date
            "lat": boston_lat,
            "lng": boston_lng,
            "locId": "L123456",
            "obsValid": True,
            "obsReviewed": False,
            "locationPrivate": False,
            "fetch_method": "nearby_observations",
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
    
    return mock_sightings

def test_filter_constraints_node():
    """Test FilterConstraintsNode with various constraint scenarios."""
    
    print("Testing FilterConstraintsNode with enrichment-in-place strategy...")
    
    filter_node = FilterConstraintsNode()
    mock_sightings = create_mock_sightings()
    
    # Test scenarios with different constraints
    test_scenarios = [
        {
            "name": "Standard Boston area trip",
            "constraints": {
                "start_location": {"lat": 42.3601, "lng": -71.0589},  # Boston
                "max_daily_distance_km": 100,
                "max_travel_radius_km": 50,
                "days_back": 14,
                "region": "US-MA",
                "min_observation_quality": "valid"
            }
        },
        {
            "name": "Strict quality requirements",
            "constraints": {
                "start_location": {"lat": 42.3601, "lng": -71.0589},
                "max_daily_distance_km": 100,
                "max_travel_radius_km": 30,
                "days_back": 7,
                "region": "US-MA",
                "min_observation_quality": "reviewed"  # Only reviewed observations
            }
        },
        {
            "name": "No location constraints",
            "constraints": {
                "days_back": 30,
                "region": "US-MA",
                "min_observation_quality": "any"
            }
        },
        {
            "name": "Very restrictive",
            "constraints": {
                "start_location": {"lat": 42.3601, "lng": -71.0589},
                "max_daily_distance_km": 50,
                "max_travel_radius_km": 10,  # Very small radius
                "days_back": 3,  # Very recent only
                "region": "US-MA",
                "min_observation_quality": "reviewed"
            }
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{'='*80}")
        print(f"SCENARIO {i}: {scenario['name']}")
        print(f"Constraints: {scenario['constraints']}")
        print(f"{'='*80}")
        
        # Create shared store
        shared = {
            "all_sightings": mock_sightings.copy(),  # Use copy to avoid modifying original
            "input": {
                "constraints": scenario["constraints"]
            }
        }
        
        print(f"Input sightings: {len(shared['all_sightings'])}")
        
        try:
            # Run the filter node
            prep_result = filter_node.prep(shared)
            exec_result = filter_node.exec(prep_result)
            filter_node.post(shared, prep_result, exec_result)
            
            # Display results
            filtering_stats = shared['filtering_stats']
            enriched_sightings = shared['all_sightings']
            
            print(f"\nFiltering Results:")
            print(f"  Total processed: {filtering_stats['total_input_sightings']}")
            print(f"  Valid coordinates: {filtering_stats['valid_coordinates']}")
            print(f"  Within travel radius: {filtering_stats['within_travel_radius']}")
            print(f"  Within date range: {filtering_stats['within_date_range']}")
            print(f"  Within region: {filtering_stats['within_region']}")
            print(f"  High quality observations: {filtering_stats['high_quality_observations']}")
            print(f"  Duplicates flagged: {filtering_stats['duplicates_flagged']}")
            print(f"  Travel feasible: {filtering_stats['travel_feasible']}")
            
            compliance_summary = filtering_stats['constraint_compliance_summary']
            print(f"\nCompliance Summary:")
            print(f"  Fully compliant sightings: {compliance_summary['fully_compliant_count']}")
            print(f"  Valid coordinates: {compliance_summary['valid_coordinates_pct']:.1f}%")
            print(f"  Within travel radius: {compliance_summary['within_travel_radius_pct']:.1f}%")
            print(f"  Within date range: {compliance_summary['within_date_range_pct']:.1f}%")
            print(f"  High quality: {compliance_summary['high_quality_pct']:.1f}%")
            print(f"  Travel feasible: {compliance_summary['travel_feasible_pct']:.1f}%")
            
            # Show enriched sighting examples
            print(f"\nEnriched Sighting Examples:")
            compliant_sightings = [s for s in enriched_sightings if s.get("meets_all_constraints", False)]
            non_compliant_sightings = [s for s in enriched_sightings if not s.get("meets_all_constraints", False)]
            
            if compliant_sightings:
                print(f"  Compliant sightings ({len(compliant_sightings)}):")
                for sighting in compliant_sightings[:2]:  # Show first 2
                    print(f"    • {sighting['comName']} at {sighting['locName']}")
                    print(f"      Distance: {sighting.get('distance_from_start_km', 'N/A')} km")
                    print(f"      Date: {sighting['obsDt']}")
                    print(f"      Valid GPS: {sighting['has_valid_gps']}")
                    print(f"      Within radius: {sighting['within_travel_radius']}")
                    print(f"      Within date range: {sighting['within_date_range']}")
                    print(f"      Quality compliant: {sighting['quality_compliant']}")
                    print(f"      Is duplicate: {sighting['is_duplicate']}")
                    print()
            
            if non_compliant_sightings:
                print(f"  Non-compliant sightings ({len(non_compliant_sightings)}) - showing first 2:")
                for sighting in non_compliant_sightings[:2]:
                    print(f"    • {sighting['comName']} at {sighting['locName']}")
                    print(f"      Issues: ", end="")
                    issues = []
                    if not sighting['has_valid_gps']:
                        issues.append("invalid GPS")
                    if not sighting['within_travel_radius']:
                        issues.append("too far")
                    if not sighting['within_date_range']:
                        issues.append("outside date range")
                    if not sighting['quality_compliant']:
                        issues.append("low quality")
                    if sighting['is_duplicate']:
                        issues.append("duplicate")
                    print(", ".join(issues) if issues else "unknown")
                    print()
            
        except Exception as e:
            print(f"ERROR in scenario {i}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_filter_constraints_node()
    print("\nFilterConstraintsNode testing completed!")