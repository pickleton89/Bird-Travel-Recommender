#!/usr/bin/env python3
"""
Test script to demonstrate the proper tools for finding LeConte's Thrasher in Arizona
"""

import asyncio
import json

from bird_travel_recommender.mcp.handlers.species import SpeciesHandlers
from bird_travel_recommender.mcp.handlers.location import LocationHandlers

async def test_leconte_thrasher():
    print("Testing LeConte's Thrasher location tools in Arizona...")
    print("=" * 60)
    
    # Initialize handlers
    species_handlers = SpeciesHandlers()
    location_handlers = LocationHandlers()
    
    # 1. First validate the species name
    print("\n1. Validating species name...")
    try:
        validation_result = await species_handlers.handle_validate_species(
            species_names=["LeConte's Thrasher"]
        )
        print(json.dumps(validation_result, indent=2))
        
        # Extract the species code if validation succeeded
        if validation_result.get('success') and validation_result.get('validated_species'):
            species_code = validation_result['validated_species'][0]['species_code']
            print(f"\nSpecies code: {species_code}")
        else:
            print("Validation failed, using known code 'lecthr'")
            species_code = "lecthr"
            
    except Exception as e:
        print(f"Validation error: {e}")
        print("Using known species code 'lecthr'")
        species_code = "lecthr"
    
    # 2. Use find_nearest_species to find recent observations around Phoenix area
    print(f"\n2. Finding nearest recent observations of {species_code}...")
    try:
        # Phoenix coordinates as starting point
        phoenix_lat, phoenix_lon = 33.4484, -112.074
        
        nearest_result = await location_handlers.handle_find_nearest_species(
            species_code=species_code,
            lat=phoenix_lat,
            lng=phoenix_lon,
            distance_km=200,  # 200km radius to cover most of Arizona
            days_back=30
        )
        print(json.dumps(nearest_result, indent=2))
        
    except Exception as e:
        print(f"Error finding nearest species: {e}")
    
    # 3. Try searching in known LeConte's Thrasher habitat (Yuma area)
    print("\n3. Searching in Yuma area (known habitat)...")
    try:
        # Yuma area coordinates
        yuma_lat, yuma_lon = 32.6927, -114.6277
        
        yuma_result = await location_handlers.handle_find_nearest_species(
            species_code=species_code,
            lat=yuma_lat,
            lng=yuma_lon,
            distance_km=100,  # 100km radius around Yuma
            days_back=30
        )
        print(json.dumps(yuma_result, indent=2))
        
    except Exception as e:
        print(f"Error searching Yuma area: {e}")

if __name__ == "__main__":
    asyncio.run(test_leconte_thrasher())