#!/usr/bin/env python3
"""
Test script for FetchSightingsNode to verify eBird API integration and parallel processing.
"""

import logging
from bird_travel_recommender.nodes import ValidateSpeciesNode, FetchSightingsNode

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def test_fetch_sightings_node():
    """Test FetchSightingsNode with validated species data."""

    print("Testing FetchSightingsNode with parallel eBird API integration...")

    # Step 1: First validate some species to get proper input data
    validate_node = ValidateSpeciesNode()
    fetch_node = FetchSightingsNode(max_workers=3)  # Use 3 workers for testing

    # Test scenarios
    test_scenarios = [
        {
            "name": "Common species with location",
            "species_list": ["Northern Cardinal", "Blue Jay"],
            "constraints": {
                "region": "US-MA",
                "days_back": 7,
                "start_location": {"lat": 42.3601, "lng": -71.0589},  # Boston
                "max_daily_distance_km": 100,
            },
        },
        {
            "name": "Multiple species without location",
            "species_list": ["American Robin", "cardinal", "jay"],
            "constraints": {
                "region": "US-CA",
                "days_back": 14,
                "max_daily_distance_km": 150,
            },
        },
        {
            "name": "Single species with nearby search",
            "species_list": ["Northern Cardinal"],
            "constraints": {
                "region": "US-NY",
                "days_back": 3,
                "start_location": {"lat": 40.7128, "lng": -74.0060},  # NYC
                "max_daily_distance_km": 50,
            },
        },
    ]

    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{'=' * 80}")
        print(f"SCENARIO {i}: {scenario['name']}")
        print(f"Species: {scenario['species_list']}")
        print(f"Constraints: {scenario['constraints']}")
        print(f"{'=' * 80}")

        # Create shared store
        shared = {
            "input": {
                "species_list": scenario["species_list"],
                "constraints": scenario["constraints"],
            }
        }

        try:
            # Step 1: Validate species
            print("Step 1: Validating species...")
            prep_result = validate_node.prep(shared)
            exec_result = validate_node.exec(prep_result)
            validate_node.post(shared, prep_result, exec_result)

            print(f"  Validated {len(shared['validated_species'])} species")
            for species in shared["validated_species"]:
                print(
                    f"    • {species['original_name']} → {species['common_name']} ({species['species_code']})"
                )

            # Step 2: Fetch sightings
            print("\nStep 2: Fetching sightings...")
            prep_result = fetch_node.prep(shared)
            exec_result = fetch_node.exec(prep_result)
            fetch_node.post(shared, prep_result, exec_result)

            # Display results
            print("\nFetch Results:")
            print(
                f"  Total observations: {shared['fetch_stats']['total_observations']}"
            )
            print(f"  Unique locations: {shared['fetch_stats']['unique_locations']}")
            print(
                f"  Success rate: {shared['fetch_stats']['successful_fetches']}/{shared['fetch_stats']['total_species']}"
            )
            print(f"  Empty results: {shared['fetch_stats']['empty_results']}")
            print(f"  API errors: {shared['fetch_stats']['api_errors']}")
            print(
                f"  Fetch methods used: {shared['fetch_stats']['fetch_method_stats']}"
            )

            # Show sample sightings
            if shared["all_sightings"]:
                print("\nSample Sightings (showing first 3):")
                for j, sighting in enumerate(shared["all_sightings"][:3]):
                    print(
                        f"  {j + 1}. {sighting.get('comName', 'Unknown')} at {sighting.get('locName', 'Unknown location')}"
                    )
                    print(
                        f"     Date: {sighting.get('obsDt', 'Unknown')}, Count: {sighting.get('howMany', 'X')}"
                    )
                    print(f"     Method: {sighting.get('fetch_method', 'Unknown')}")
                    print(
                        f"     Validation: {sighting.get('validation_method', 'Unknown')} (confidence: {sighting.get('validation_confidence', 0)})"
                    )
                    if sighting.get("seasonal_notes"):
                        print(f"     Seasonal: {sighting['seasonal_notes']}")
                    print()
            else:
                print("  No sightings found.")

        except Exception as e:
            print(f"ERROR in scenario {i}: {e}")
            import traceback

            traceback.print_exc()


def test_fetch_with_mock_data():
    """Test FetchSightingsNode with pre-validated species (bypass validation step)."""

    print(f"\n{'=' * 80}")
    print("MOCK DATA TEST: FetchSightingsNode with pre-validated species")
    print(f"{'=' * 80}")

    # Create mock validated species data
    mock_validated_species = [
        {
            "original_name": "Northern Cardinal",
            "common_name": "Northern Cardinal",
            "scientific_name": "Cardinalis cardinalis",
            "species_code": "norcar",
            "validation_method": "direct_common_name",
            "confidence": 1.0,
            "seasonal_notes": "Year-round resident in most of range",
            "behavioral_notes": "Seed feeders, dense cover, active at feeders dawn and dusk",
        },
        {
            "original_name": "Blue Jay",
            "common_name": "Blue Jay",
            "scientific_name": "Cyanocitta cristata",
            "species_code": "blujay",
            "validation_method": "direct_common_name",
            "confidence": 1.0,
            "seasonal_notes": "Year-round resident in most of range",
            "behavioral_notes": "Vocal and conspicuous, mixed habitats, often in family groups",
        },
    ]

    # Create shared store with mock data
    shared = {
        "validated_species": mock_validated_species,
        "input": {
            "constraints": {
                "region": "US-MA",
                "days_back": 7,
                "start_location": {"lat": 42.3601, "lng": -71.0589},
                "max_daily_distance_km": 100,
            }
        },
    }

    try:
        fetch_node = FetchSightingsNode(max_workers=2)

        print("Testing with mock validated species data...")
        prep_result = fetch_node.prep(shared)
        exec_result = fetch_node.exec(prep_result)
        fetch_node.post(shared, prep_result, exec_result)

        print("\nMock Test Results:")
        print(f"  Total observations: {shared['fetch_stats']['total_observations']}")
        print(
            f"  Success rate: {shared['fetch_stats']['successful_fetches']}/{shared['fetch_stats']['total_species']}"
        )
        print(f"  Fetch methods: {shared['fetch_stats']['fetch_method_stats']}")

    except Exception as e:
        print(f"ERROR in mock test: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_fetch_sightings_node()
    test_fetch_with_mock_data()
    print("\nFetchSightingsNode testing completed!")
