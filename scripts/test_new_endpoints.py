#!/usr/bin/env python3
"""
Manual testing script for new eBird API endpoints.

This script provides comprehensive manual testing of the 4 new eBird API endpoints
implemented in the expansion project. It includes real API calls, parameter validation,
error scenarios, and performance testing.

Usage:
    python scripts/test_new_endpoints.py [--test-name]

Options:
    --all                   Run all tests (default)
    --nearest-observations  Test get_nearest_observations only
    --species-list         Test get_species_list only
    --region-info          Test get_region_info only
    --hotspot-info         Test get_hotspot_info only
    --quick                Run quick tests only (reduced API calls)
    --verbose              Enable verbose output
"""

import argparse
import time

from bird_travel_recommender.utils.ebird_api import EBirdClient, EBirdAPIError


class EndpointTester:
    """Manual testing class for eBird API expansion endpoints."""

    def __init__(self, verbose: bool = False):
        """Initialize tester with API client."""
        self.verbose = verbose
        self.client = None
        self.test_results = {"passed": 0, "failed": 0, "errors": []}

    def setup(self) -> bool:
        """Setup eBird API client and verify connection."""
        try:
            self.client = EBirdClient()
            self.log("✓ eBird API client initialized successfully")
            return True
        except Exception as e:
            self.log(f"✗ Failed to initialize eBird client: {e}")
            return False

    def log(self, message: str):
        """Log message with optional verbose output."""
        if self.verbose or "✓" in message or "✗" in message:
            print(message)

    def assert_test(self, condition: bool, test_name: str, details: str = ""):
        """Assert test condition and track results."""
        if condition:
            self.test_results["passed"] += 1
            self.log(f"✓ {test_name}")
            if details and self.verbose:
                self.log(f"   {details}")
        else:
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: {details}")
            self.log(f"✗ {test_name}")
            if details:
                self.log(f"   {details}")

    def test_nearest_observations(self, quick: bool = False):
        """Test get_nearest_observations endpoint."""
        print("\n" + "=" * 60)
        print("TESTING: get_nearest_observations()")
        print("=" * 60)

        try:
            # Test 1: Common species (Northern Cardinal)
            self.log("Test 1: Common species in populated area")
            result = self.client.get_nearest_observations(
                species_code="norcar",
                lat=42.3601,  # Boston area
                lng=-71.0942,
                days_back=7,
                distance_km=25,
            )
            self.assert_test(
                isinstance(result, list),
                "Returns list for common species",
                f"Got {len(result)} observations",
            )

            if result:
                obs = result[0]
                self.assert_test(
                    "speciesCode" in obs and obs["speciesCode"] == "norcar",
                    "Response contains correct species code",
                )
                self.assert_test(
                    "lat" in obs and "lng" in obs, "Response contains coordinates"
                )
                self.assert_test("obsDate" in obs, "Response contains observation date")

            # Test 2: Rare species (might return empty)
            if not quick:
                self.log("Test 2: Rare species")
                result = self.client.get_nearest_observations(
                    species_code="gyrfal",  # Gyrfalcon - rare in most areas
                    lat=42.3601,
                    lng=-71.0942,
                    days_back=30,
                )
                self.assert_test(
                    isinstance(result, list),
                    "Returns list for rare species (may be empty)",
                    f"Got {len(result)} observations",
                )

            # Test 3: Parameter validation
            self.log("Test 3: Parameter limits")
            result = self.client.get_nearest_observations(
                species_code="norcar",
                lat=40.7589,  # NYC
                lng=-73.9851,
                days_back=35,  # Should be limited to 30
                distance_km=75,  # Should be limited to 50
                max_results=5000,  # Should be limited to 3000
            )
            self.assert_test(
                isinstance(result, list), "Handles parameter limits correctly"
            )

            # Test 4: Hotspot-only filter
            if not quick:
                self.log("Test 4: Hotspot-only filter")
                hotspot_result = self.client.get_nearest_observations(
                    species_code="norcar", lat=40.7589, lng=-73.9851, hotspot_only=True
                )
                all_result = self.client.get_nearest_observations(
                    species_code="norcar", lat=40.7589, lng=-73.9851, hotspot_only=False
                )
                self.assert_test(
                    len(hotspot_result) <= len(all_result),
                    "Hotspot filter reduces results",
                    f"Hotspot: {len(hotspot_result)}, All: {len(all_result)}",
                )

        except EBirdAPIError as e:
            self.assert_test(False, "API error handling", str(e))
        except Exception as e:
            self.assert_test(False, "Unexpected error", str(e))

    def test_species_list(self, quick: bool = False):
        """Test get_species_list endpoint."""
        print("\n" + "=" * 60)
        print("TESTING: get_species_list()")
        print("=" * 60)

        try:
            # Test 1: State/Province level
            self.log("Test 1: State level (Massachusetts)")
            result = self.client.get_species_list("US-MA")
            self.assert_test(
                isinstance(result, list) and len(result) > 0,
                "Returns species list for state",
                f"Got {len(result)} species",
            )
            self.assert_test(
                all(isinstance(code, str) for code in result),
                "All species codes are strings",
            )
            self.assert_test(
                "norcar" in result,  # Northern Cardinal should be in MA
                "Contains expected common species",
            )

            # Test 2: Country level
            if not quick:
                self.log("Test 2: Country level (United States)")
                result = self.client.get_species_list("US")
                self.assert_test(
                    len(result) > 1000,  # US should have many species
                    "Country level returns large species list",
                    f"Got {len(result)} species",
                )

            # Test 3: County level
            self.log("Test 3: County level (Suffolk County, MA)")
            result = self.client.get_species_list("US-MA-025")  # Suffolk County
            self.assert_test(
                isinstance(result, list) and len(result) > 0,
                "Returns species list for county",
                f"Got {len(result)} species",
            )

            # Test 4: Invalid region
            self.log("Test 4: Invalid region code")
            try:
                result = self.client.get_species_list("INVALID-REGION")
                self.assert_test(False, "Should raise error for invalid region")
            except EBirdAPIError:
                self.assert_test(True, "Raises EBirdAPIError for invalid region")

        except Exception as e:
            self.assert_test(False, "Unexpected error", str(e))

    def test_region_info(self, quick: bool = False):
        """Test get_region_info endpoint."""
        print("\n" + "=" * 60)
        print("TESTING: get_region_info()")
        print("=" * 60)

        try:
            # Test 1: State with detailed format
            self.log("Test 1: State info with detailed format")
            result = self.client.get_region_info("US-MA", name_format="detailed")
            self.assert_test(
                isinstance(result, dict), "Returns dictionary for region info"
            )
            self.assert_test(
                "code" in result and result["code"] == "US-MA",
                "Contains correct region code",
            )
            self.assert_test(
                "name" in result and "Massachusetts" in result["name"],
                "Contains human-readable name",
                f"Name: {result.get('name', 'N/A')}",
            )

            # Test 2: Short name format
            self.log("Test 2: Short name format")
            result = self.client.get_region_info("US-MA", name_format="short")
            self.assert_test("name" in result, "Short format returns name")

            # Test 3: Country level
            if not quick:
                self.log("Test 3: Country level info")
                result = self.client.get_region_info("US")
                self.assert_test(
                    result["name"] == "United States",
                    "Country name is correct",
                    f"Got: {result.get('name', 'N/A')}",
                )

            # Test 4: Hierarchical regions
            self.log("Test 4: County level info")
            result = self.client.get_region_info("US-MA-025")  # Suffolk County
            self.assert_test(
                "name" in result and "Suffolk" in result["name"],
                "County info contains correct name",
            )

            # Test 5: Invalid region
            self.log("Test 5: Invalid region code")
            try:
                result = self.client.get_region_info("INVALID-REGION")
                self.assert_test(False, "Should raise error for invalid region")
            except EBirdAPIError:
                self.assert_test(True, "Raises EBirdAPIError for invalid region")

        except Exception as e:
            self.assert_test(False, "Unexpected error", str(e))

    def test_hotspot_info(self, quick: bool = False):
        """Test get_hotspot_info endpoint."""
        print("\n" + "=" * 60)
        print("TESTING: get_hotspot_info()")
        print("=" * 60)

        try:
            # Test 1: Known major hotspot (Central Park)
            self.log("Test 1: Major hotspot (Central Park)")
            result = self.client.get_hotspot_info("L109516")  # Central Park
            self.assert_test(
                isinstance(result, dict), "Returns dictionary for hotspot info"
            )
            self.assert_test(
                "locId" in result and result["locId"] == "L109516",
                "Contains correct location ID",
            )
            self.assert_test(
                "name" in result and "Central Park" in result["name"],
                "Contains correct hotspot name",
                f"Name: {result.get('name', 'N/A')}",
            )
            self.assert_test(
                "isHotspot" in result and result["isHotspot"] is True,
                "Correctly identifies as hotspot",
            )
            self.assert_test(
                "numSpeciesAllTime" in result and result["numSpeciesAllTime"] > 0,
                "Contains species count",
                f"Species: {result.get('numSpeciesAllTime', 0)}",
            )

            # Test 2: Another well-known hotspot
            if not quick:
                self.log("Test 2: Point Pelee National Park")
                result = self.client.get_hotspot_info("L206433")  # Point Pelee
                self.assert_test(
                    "Point Pelee" in result.get("name", ""),
                    "Point Pelee hotspot info correct",
                )

            # Test 3: Coordinates validation
            self.log("Test 3: Coordinate validation")
            result = self.client.get_hotspot_info("L109516")
            self.assert_test(
                "lat" in result and "lng" in result, "Contains coordinates"
            )
            self.assert_test(
                isinstance(result["lat"], (int, float))
                and isinstance(result["lng"], (int, float)),
                "Coordinates are numeric",
            )

            # Test 4: Invalid location ID
            self.log("Test 4: Invalid location ID")
            try:
                result = self.client.get_hotspot_info("INVALID-LOCATION")
                self.assert_test(False, "Should raise error for invalid location")
            except EBirdAPIError:
                self.assert_test(True, "Raises EBirdAPIError for invalid location")

            # Test 5: Non-hotspot location (if we can find one)
            # Note: This test might not always work as personal locations
            # are not accessible via this endpoint

        except Exception as e:
            self.assert_test(False, "Unexpected error", str(e))

    def test_performance(self):
        """Test performance characteristics of endpoints."""
        print("\n" + "=" * 60)
        print("TESTING: Performance Characteristics")
        print("=" * 60)

        try:
            # Test response times
            endpoints = [
                ("get_species_list", lambda: self.client.get_species_list("US-MA")),
                ("get_region_info", lambda: self.client.get_region_info("US-MA")),
                ("get_hotspot_info", lambda: self.client.get_hotspot_info("L109516")),
                (
                    "get_nearest_observations",
                    lambda: self.client.get_nearest_observations(
                        "norcar", 42.36, -71.09
                    ),
                ),
            ]

            for name, func in endpoints:
                start_time = time.time()
                func()
                end_time = time.time()
                duration = end_time - start_time

                self.assert_test(
                    duration < 10.0,  # Should complete within 10 seconds
                    f"{name} completes within reasonable time",
                    f"Took {duration:.2f} seconds",
                )

        except Exception as e:
            self.assert_test(False, "Performance test error", str(e))

    def test_convenience_functions(self):
        """Test convenience functions."""
        print("\n" + "=" * 60)
        print("TESTING: Convenience Functions")
        print("=" * 60)

        try:
            from bird_travel_recommender.utils.ebird_api import (
                get_nearest_observations,
                get_species_list,
                get_region_info,
                get_hotspot_info,
            )

            # Test that convenience functions work
            result = get_species_list("US-MA")
            self.assert_test(
                isinstance(result, list) and len(result) > 0,
                "get_species_list convenience function works",
            )

            result = get_region_info("US-MA")
            self.assert_test(
                isinstance(result, dict) and "name" in result,
                "get_region_info convenience function works",
            )

            result = get_hotspot_info("L109516")
            self.assert_test(
                isinstance(result, dict) and "locId" in result,
                "get_hotspot_info convenience function works",
            )

            result = get_nearest_observations("norcar", 42.36, -71.09)
            self.assert_test(
                isinstance(result, list),
                "get_nearest_observations convenience function works",
            )

        except Exception as e:
            self.assert_test(False, "Convenience function error", str(e))

    def run_all_tests(self, quick: bool = False):
        """Run all endpoint tests."""
        if not self.setup():
            return False

        print(
            f"\nStarting eBird API Expansion Endpoint Tests ({'Quick' if quick else 'Full'} Mode)"
        )
        print("=" * 80)

        self.test_nearest_observations(quick)
        self.test_species_list(quick)
        self.test_region_info(quick)
        self.test_hotspot_info(quick)

        if not quick:
            self.test_performance()

        self.test_convenience_functions()

        # Print summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"Tests passed: {self.test_results['passed']}")
        print(f"Tests failed: {self.test_results['failed']}")

        if self.test_results["errors"]:
            print("\nFailed tests:")
            for error in self.test_results["errors"]:
                print(f"  ✗ {error}")

        success_rate = (
            self.test_results["passed"]
            / (self.test_results["passed"] + self.test_results["failed"])
            * 100
        )
        print(f"\nSuccess rate: {success_rate:.1f}%")

        return self.test_results["failed"] == 0


def main():
    """Main function for command line execution."""
    parser = argparse.ArgumentParser(description="Test new eBird API endpoints")
    parser.add_argument(
        "--all", action="store_true", default=True, help="Run all tests"
    )
    parser.add_argument(
        "--nearest-observations",
        action="store_true",
        help="Test get_nearest_observations only",
    )
    parser.add_argument(
        "--species-list", action="store_true", help="Test get_species_list only"
    )
    parser.add_argument(
        "--region-info", action="store_true", help="Test get_region_info only"
    )
    parser.add_argument(
        "--hotspot-info", action="store_true", help="Test get_hotspot_info only"
    )
    parser.add_argument("--quick", action="store_true", help="Run quick tests only")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    tester = EndpointTester(verbose=args.verbose)

    # Check if specific test was requested
    specific_tests = [
        args.nearest_observations,
        args.species_list,
        args.region_info,
        args.hotspot_info,
    ]

    if any(specific_tests):
        if not tester.setup():
            return 1

        if args.nearest_observations:
            tester.test_nearest_observations(args.quick)
        if args.species_list:
            tester.test_species_list(args.quick)
        if args.region_info:
            tester.test_region_info(args.quick)
        if args.hotspot_info:
            tester.test_hotspot_info(args.quick)
    else:
        # Run all tests
        success = tester.run_all_tests(args.quick)
        return 0 if success else 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
