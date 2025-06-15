"""
Pytest configuration and shared fixtures for Bird Travel Recommender tests.

This module provides:
- Mock eBird API responses
- Test data fixtures
- Shared test utilities
- API mocking infrastructure
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import json
import os
from typing import Dict, List, Any


@pytest.fixture
def mock_ebird_taxonomy():
    """Mock eBird taxonomy data for testing."""
    return [
        {
            "sciName": "Cardinalis cardinalis",
            "comName": "Northern Cardinal",
            "speciesCode": "norcar",
            "category": "species",
            "taxonOrder": 37823.0,
            "bandingCodes": ["NOCA"],
            "comNameCodes": ["NOCA"],
            "sciNameCodes": ["CACA"],
            "order": "Passeriformes",
            "familyCode": "cardin1",
            "familyComName": "Cardinals, Grosbeaks, and Allies",
            "familySciName": "Cardinalidae"
        },
        {
            "sciName": "Cyanocitta cristata",
            "comName": "Blue Jay",
            "speciesCode": "blujay",
            "category": "species",
            "taxonOrder": 20362.0,
            "bandingCodes": ["BLJA"],
            "comNameCodes": ["BLJA"],
            "sciNameCodes": ["CYCR"],
            "order": "Passeriformes",
            "familyCode": "corvid1",
            "familyComName": "Crows, Jays, and Magpies",
            "familySciName": "Corvidae"
        },
        {
            "sciName": "Turdus migratorius",
            "comName": "American Robin",
            "speciesCode": "amerob",
            "category": "species",
            "taxonOrder": 16764.0,
            "bandingCodes": ["AMRO"],
            "comNameCodes": ["AMRO"],
            "sciNameCodes": ["TUMI"],
            "order": "Passeriformes",
            "familyCode": "turdid1",
            "familyComName": "Thrushes and Allies",
            "familySciName": "Turdidae"
        }
    ]


@pytest.fixture
def mock_ebird_observations():
    """Mock eBird observations data for testing."""
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    
    return [
        {
            "speciesCode": "norcar",
            "comName": "Northern Cardinal",
            "sciName": "Cardinalis cardinalis",
            "locId": "L123456",
            "locName": "Boston Common",
            "obsDt": yesterday.strftime("%Y-%m-%d %H:%M"),
            "howMany": 2,
            "lat": 42.3601,
            "lng": -71.0589,
            "obsValid": True,
            "obsReviewed": False,
            "locationPrivate": False,
            "subId": "S123456789"
        },
        {
            "speciesCode": "blujay",
            "comName": "Blue Jay",
            "sciName": "Cyanocitta cristata",
            "locId": "L234567",
            "locName": "Harvard Yard",
            "obsDt": today.strftime("%Y-%m-%d %H:%M"),
            "howMany": 1,
            "lat": 42.3736,
            "lng": -71.1097,
            "obsValid": True,
            "obsReviewed": True,
            "locationPrivate": False,
            "subId": "S234567890"
        },
        {
            "speciesCode": "amerob",
            "comName": "American Robin",
            "sciName": "Turdus migratorius",
            "locId": "L345678",
            "locName": "Central Park",
            "obsDt": yesterday.strftime("%Y-%m-%d %H:%M"),
            "howMany": 3,
            "lat": 40.7829,
            "lng": -73.9654,
            "obsValid": True,
            "obsReviewed": False,
            "locationPrivate": False,
            "subId": "S345678901"
        }
    ]


@pytest.fixture
def mock_ebird_hotspots():
    """Mock eBird hotspots data for testing."""
    return [
        {
            "locId": "L123456",
            "locName": "Boston Common",
            "countryCode": "US",
            "subnational1Code": "US-MA",
            "subnational2Code": "US-MA-025",
            "lat": 42.3601,
            "lng": -71.0589,
            "latestObsDt": "2025-06-11",
            "numSpeciesAllTime": 127
        },
        {
            "locId": "L234567",
            "locName": "Harvard Yard",
            "countryCode": "US",
            "subnational1Code": "US-MA",
            "subnational2Code": "US-MA-017",
            "lat": 42.3736,
            "lng": -71.1097,
            "latestObsDt": "2025-06-11",
            "numSpeciesAllTime": 89
        },
        {
            "locId": "L345678",
            "locName": "Central Park",
            "countryCode": "US",
            "subnational1Code": "US-NY",
            "subnational2Code": "US-NY-061",
            "lat": 40.7829,
            "lng": -73.9654,
            "latestObsDt": "2025-06-11",
            "numSpeciesAllTime": 312
        }
    ]


@pytest.fixture
def mock_validated_species():
    """Mock validated species data for testing."""
    return [
        {
            "original_name": "Northern Cardinal",
            "common_name": "Northern Cardinal",
            "scientific_name": "Cardinalis cardinalis",
            "species_code": "norcar",
            "validation_method": "direct_common_name",
            "confidence": 1.0,
            "seasonal_notes": "Year-round resident in most of range",
            "behavioral_notes": "Seed feeders, dense cover, active at feeders dawn and dusk"
        },
        {
            "original_name": "Blue Jay",
            "common_name": "Blue Jay",
            "scientific_name": "Cyanocitta cristata",
            "species_code": "blujay",
            "validation_method": "direct_common_name",
            "confidence": 1.0,
            "seasonal_notes": "Year-round resident in most of range",
            "behavioral_notes": "Vocal and conspicuous, mixed habitats, often in family groups"
        }
    ]


@pytest.fixture
def test_constraints():
    """Standard test constraints for testing."""
    return {
        "region": "US-MA",
        "days_back": 7,
        "start_location": {"lat": 42.3601, "lng": -71.0589},  # Boston
        "max_daily_distance_km": 100,
        "max_travel_radius_km": 50,
        "min_observation_quality": "valid"
    }


@pytest.fixture
def mock_ebird_api_responses():
    """Mock all eBird API endpoints with realistic responses."""
    
    def mock_get_taxonomy(region=None, species_code=None):
        """Mock get_taxonomy responses."""
        taxonomy = [
            {
                "sciName": "Cardinalis cardinalis",
                "comName": "Northern Cardinal",
                "speciesCode": "norcar",
                "category": "species",
                "taxonOrder": 37823.0
            },
            {
                "sciName": "Cyanocitta cristata", 
                "comName": "Blue Jay",
                "speciesCode": "blujay",
                "category": "species",
                "taxonOrder": 20362.0
            },
            {
                "sciName": "Turdus migratorius",
                "comName": "American Robin", 
                "speciesCode": "amerob",
                "category": "species",
                "taxonOrder": 16764.0
            }
        ]
        
        if species_code:
            return [t for t in taxonomy if t["speciesCode"] == species_code]
        return taxonomy
    
    def mock_get_recent_observations(region_code, days_back=14):
        """Mock get_recent_observations responses."""
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        observations = [
            {
                "speciesCode": "norcar",
                "comName": "Northern Cardinal",
                "sciName": "Cardinalis cardinalis",
                "locId": "L123456",
                "locName": "Boston Common",
                "obsDt": yesterday.strftime("%Y-%m-%d %H:%M"),
                "howMany": 2,
                "lat": 42.3601,
                "lng": -71.0589,
                "obsValid": True,
                "obsReviewed": False,
                "locationPrivate": False
            },
            {
                "speciesCode": "blujay",
                "comName": "Blue Jay",
                "sciName": "Cyanocitta cristata",
                "locId": "L234567", 
                "locName": "Harvard Yard",
                "obsDt": today.strftime("%Y-%m-%d %H:%M"),
                "howMany": 1,
                "lat": 42.3736,
                "lng": -71.1097,
                "obsValid": True,
                "obsReviewed": True,
                "locationPrivate": False
            }
        ]
        
        return observations
    
    def mock_get_species_observations(region_code, species_code, days_back=30):
        """Mock get_species_observations responses."""
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        if species_code == "norcar":
            return [
                {
                    "speciesCode": "norcar",
                    "comName": "Northern Cardinal",
                    "sciName": "Cardinalis cardinalis",
                    "locId": "L123456",
                    "locName": "Boston Common",
                    "obsDt": yesterday.strftime("%Y-%m-%d %H:%M"),
                    "howMany": 2,
                    "lat": 42.3601,
                    "lng": -71.0589,
                    "obsValid": True,
                    "obsReviewed": False,
                    "locationPrivate": False
                }
            ]
        elif species_code == "blujay":
            return [
                {
                    "speciesCode": "blujay",
                    "comName": "Blue Jay",
                    "sciName": "Cyanocitta cristata",
                    "locId": "L234567",
                    "locName": "Harvard Yard", 
                    "obsDt": today.strftime("%Y-%m-%d %H:%M"),
                    "howMany": 1,
                    "lat": 42.3736,
                    "lng": -71.1097,
                    "obsValid": True,
                    "obsReviewed": True,
                    "locationPrivate": False
                }
            ]
        else:
            return []
    
    def mock_get_hotspots(region_code):
        """Mock get_hotspots responses."""
        return [
            {
                "locId": "L123456",
                "locName": "Boston Common",  
                "countryCode": "US",
                "subnational1Code": "US-MA",
                "lat": 42.3601,
                "lng": -71.0589,
                "latestObsDt": "2025-06-11",
                "numSpeciesAllTime": 127
            },
            {
                "locId": "L234567",
                "locName": "Harvard Yard",
                "countryCode": "US", 
                "subnational1Code": "US-MA",
                "lat": 42.3736,
                "lng": -71.1097,
                "latestObsDt": "2025-06-11",
                "numSpeciesAllTime": 89
            }
        ]
    
    def mock_get_nearby_observations(lat, lng, distance_km, days_back=14, species_code=None):
        """Mock get_nearby_observations responses."""
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        # Return observations near the provided location
        observations = [
            {
                "speciesCode": "norcar",
                "comName": "Northern Cardinal",
                "sciName": "Cardinalis cardinalis",
                "locId": "L123456",
                "locName": "Boston Common",
                "obsDt": yesterday.strftime("%Y-%m-%d %H:%M"),
                "howMany": 2,
                "lat": 42.3601,
                "lng": -71.0589,
                "obsValid": True,
                "obsReviewed": False,
                "locationPrivate": False
            },
            {
                "speciesCode": "blujay",
                "comName": "Blue Jay",
                "sciName": "Cyanocitta cristata",
                "locId": "L234567", 
                "locName": "Harvard Yard",
                "obsDt": today.strftime("%Y-%m-%d %H:%M"),
                "howMany": 1,
                "lat": 42.3736,
                "lng": -71.1097,
                "obsValid": True,
                "obsReviewed": True,
                "locationPrivate": False
            }
        ]
        
        # Filter by species if specified
        if species_code:
            observations = [obs for obs in observations if obs["speciesCode"] == species_code]
        
        return observations

    return {
        "get_taxonomy": mock_get_taxonomy,
        "get_recent_observations": mock_get_recent_observations,
        "get_species_observations": mock_get_species_observations,
        "get_hotspots": mock_get_hotspots,
        "get_nearby_observations": mock_get_nearby_observations
    }


@pytest.fixture
def mock_ebird_api(mock_ebird_api_responses):
    """Mock the entire eBird API client."""
    with patch('bird_travel_recommender.nodes.get_client') as mock_get_client, \
         patch('bird_travel_recommender.utils.ebird_api.EBirdClient.get_taxonomy') as mock_taxonomy, \
         patch('bird_travel_recommender.utils.ebird_api.EBirdClient.get_recent_observations') as mock_recent, \
         patch('bird_travel_recommender.utils.ebird_api.EBirdClient.get_species_observations') as mock_species, \
         patch('bird_travel_recommender.utils.ebird_api.EBirdClient.get_hotspots') as mock_hotspots, \
         patch('bird_travel_recommender.utils.ebird_api.EBirdClient.get_nearby_observations') as mock_nearby, \
         patch('bird_travel_recommender.utils.ebird_observations.EBirdObservationsMixin.get_nearby_observations') as mock_nearby_mixin:
        
        # Create a mock client instance with all the mocked methods
        mock_client = Mock()
        mock_client.get_taxonomy = mock_taxonomy
        mock_client.get_recent_observations = mock_recent
        mock_client.get_species_observations = mock_species
        mock_client.get_hotspots = mock_hotspots
        mock_client.get_nearby_observations = mock_nearby
        
        # Make get_client() return our mock client
        mock_get_client.return_value = mock_client
        
        mock_taxonomy.side_effect = mock_ebird_api_responses["get_taxonomy"]
        mock_recent.side_effect = mock_ebird_api_responses["get_recent_observations"]
        mock_species.side_effect = mock_ebird_api_responses["get_species_observations"]
        mock_hotspots.side_effect = mock_ebird_api_responses["get_hotspots"]
        mock_nearby.side_effect = mock_ebird_api_responses["get_nearby_observations"]
        mock_nearby_mixin.side_effect = mock_ebird_api_responses["get_nearby_observations"]
        
        yield {
            "client": mock_client,
            "get_client": mock_get_client,
            "taxonomy": mock_taxonomy,
            "recent_observations": mock_recent,
            "species_observations": mock_species,
            "hotspots": mock_hotspots,
            "nearby_observations": mock_nearby
        }


@pytest.fixture
def sample_shared_store():
    """Sample shared store structure for testing nodes."""
    return {
        "input": {
            "species_list": ["Northern Cardinal", "Blue Jay"],
            "constraints": {
                "region": "US-MA",
                "days_back": 7,
                "start_location": {"lat": 42.3601, "lng": -71.0589},
                "max_daily_distance_km": 100
            }
        }
    }


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    os.environ["EBIRD_API_KEY"] = "test_api_key"
    os.environ["OPENAI_API_KEY"] = "test_openai_key"
    yield
    # Cleanup is handled automatically by pytest