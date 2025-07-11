#!/usr/bin/env python3
"""
Bird Travel Recommender - Main Entry Point

This is the main execution script for the Bird Travel Recommender system.
It runs the complete 7-node pipeline to generate optimized birding itineraries
based on eBird data and user constraints.
"""

import sys
import argparse
import json
from .flow import run_birding_pipeline, create_test_input
import logging


def main():
    """
    Main entry point for the Bird Travel Recommender.

    Supports both interactive and programmatic execution modes.
    """
    parser = argparse.ArgumentParser(
        description="Bird Travel Recommender - Generate optimized birding itineraries",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  # Run with test data
  python main.py

  # Run with debug logging
  python main.py --debug

  # Run with custom input file
  python main.py --input my_trip.json

  # Save results to file
  python main.py --output my_itinerary.md
        """,
    )

    parser.add_argument(
        "--input",
        "-i",
        help="JSON file with trip input data (species list and constraints)",
    )
    parser.add_argument(
        "--output", "-o", help="Output file for generated itinerary (markdown format)"
    )
    parser.add_argument(
        "--debug", "-d", action="store_true", help="Enable debug logging"
    )
    parser.add_argument(
        "--test", action="store_true", help="Run with test data (default behavior)"
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logger = logging.getLogger(__name__)
    logger.info("Bird Travel Recommender - Starting pipeline execution")

    # Load input data
    input_data = None
    if args.input:
        try:
            with open(args.input, "r") as f:
                input_data = json.load(f)
            logger.info(f"Loaded input data from {args.input}")
        except Exception as e:
            logger.error(f"Failed to load input file {args.input}: {e}")
            sys.exit(1)
    else:
        input_data = create_test_input()
        logger.info("Using built-in test data")

    # Display trip summary
    species_list = input_data.get("input", {}).get("species_list", [])
    constraints = input_data.get("input", {}).get("constraints", {})
    start_location = constraints.get("start_location", {})

    print("\n" + "=" * 60)
    print("BIRD TRAVEL RECOMMENDER - TRIP PLANNING")
    print("=" * 60)
    print(f"Target Species: {', '.join(species_list)}")
    print(
        f"Starting Location: ({start_location.get('lat', 'unknown')}, {start_location.get('lng', 'unknown')})"
    )
    print(f"Region: {constraints.get('region', 'Not specified')}")
    print(
        f"Max Distance: {constraints.get('max_daily_distance_km', 'Not specified')} km"
    )
    print("=" * 60)
    print()

    # Execute pipeline
    try:
        logger.info("Executing birding pipeline...")
        result = run_birding_pipeline(input_data=input_data, debug=args.debug)

        if result["success"]:
            print("✅ Pipeline completed successfully!")

            # Display summary statistics
            stats = result["pipeline_statistics"]
            print("\n📊 PIPELINE STATISTICS:")
            print(
                f"   Species validated: {stats.get('validation_stats', {}).get('total_input', 0)}"
            )
            print(
                f"   Observations analyzed: {stats.get('fetch_stats', {}).get('total_observations', 0)}"
            )
            print(
                f"   Locations clustered: {stats.get('clustering_stats', {}).get('clusters_created', 0)}"
            )
            print(
                f"   Route distance: {stats.get('route_optimization_stats', {}).get('total_route_distance_km', 0):.1f} km"
            )
            print(
                f"   Itinerary method: {stats.get('itinerary_generation_stats', {}).get('itinerary_method', 'unknown')}"
            )

            # Handle output
            itinerary = result["itinerary_markdown"]

            if args.output:
                try:
                    with open(args.output, "w") as f:
                        f.write(itinerary)
                    print(f"\n💾 Itinerary saved to: {args.output}")
                except Exception as e:
                    logger.error(f"Failed to save output file {args.output}: {e}")
                    print(f"\n❌ Failed to save output file: {e}")
            else:
                print("\n📋 GENERATED ITINERARY:")
                print("-" * 40)
                # Print first 1000 characters for preview
                preview = (
                    itinerary[:1000] + "..." if len(itinerary) > 1000 else itinerary
                )
                print(preview)
                if len(itinerary) > 1000:
                    print(
                        f"\n(Preview only - full itinerary is {len(itinerary)} characters)"
                    )
                    print("Use --output flag to save full itinerary to file")

        else:
            print("❌ Pipeline execution failed!")
            print(f"Error: {result.get('error', 'Unknown error')}")
            logger.error(f"Pipeline failed: {result.get('error')}")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠️  Pipeline execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

    print("\n🦅 Happy birding!")


def create_example_input_file():
    """
    Create an example input file for users to customize.
    """
    example_input = {
        "input": {
            "species_list": [
                "Northern Cardinal",
                "Blue Jay",
                "American Robin",
                "Yellow Warbler",
                "Red-tailed Hawk",
            ],
            "constraints": {
                "start_location": {"lat": 42.3601, "lng": -71.0589},
                "max_days": 3,
                "max_daily_distance_km": 200,
                "date_range": {"start": "2024-09-01", "end": "2024-09-30"},
                "region": "US-MA",
                "max_locations_per_day": 8,
                "min_location_score": 0.3,
            },
        }
    }

    with open("example_input.json", "w") as f:
        json.dump(example_input, f, indent=2)

    print("Created example_input.json - customize this file for your trip!")


if __name__ == "__main__":
    main()
