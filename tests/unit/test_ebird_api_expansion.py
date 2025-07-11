#!/usr/bin/env python3
"""
Unit tests for eBird API expansion endpoints.

Tests the 4 new eBird API endpoints implemented in Phase 1:
- get_nearest_observations()
- get_species_list()
- get_region_info()
- get_hotspot_info()

Covers parameter validation, error handling, response format validation,
and rate limiting behavior with comprehensive mock responses.
"""

import pytest
import requests
from unittest.mock import Mock, patch
from src.bird_travel_recommender.utils.ebird_api import EBirdClient, EBirdAPIError


class TestEBirdAPIExpansion:
    """Test suite for new eBird API expansion endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create EBirdClient instance for testing."""
        with patch.dict('os.environ', {'EBIRD_API_KEY': 'test_key_12345'}):
            return EBirdClient()
    
    @pytest.fixture
    def mock_session(self, client):
        """Mock the requests session for controlled testing."""
        with patch.object(client, 'session') as mock_session:
            yield mock_session

    # Tests for get_nearest_observations()
    def test_get_nearest_observations_success(self, client, mock_session):
        """Test successful get_nearest_observations call."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "speciesCode": "norcar",
                "comName": "Northern Cardinal",
                "lat": 42.3598,
                "lng": -71.0921,
                "locName": "Central Park",
                "locId": "L123456",
                "obsDate": "2024-01-15",
                "distance": 1.2
            },
            {
                "speciesCode": "norcar", 
                "comName": "Northern Cardinal",
                "lat": 42.3701,
                "lng": -71.0915,
                "locName": "Boston Common",
                "locId": "L123457",
                "obsDate": "2024-01-14",
                "distance": 2.1
            }
        ]
        mock_session.get.return_value = mock_response
        
        # Test the method
        result = client.get_nearest_observations(
            species_code="norcar",
            lat=42.3601,
            lng=-71.0942,
            days_back=14,
            distance_km=25
        )
        
        # Verify results
        assert len(result) == 2
        assert result[0]["speciesCode"] == "norcar"
        assert result[0]["distance"] == 1.2
        
        # Verify API call parameters
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert "/data/nearest/geo/recent/norcar" in call_args[0][0]
        assert call_args[1]["params"]["lat"] == 42.3601
        assert call_args[1]["params"]["lng"] == -71.0942
        assert call_args[1]["params"]["back"] == 14
        assert call_args[1]["params"]["dist"] == 25

    def test_get_nearest_observations_parameter_validation(self, client, mock_session):
        """Test parameter validation and limits for get_nearest_observations."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_session.get.return_value = mock_response
        
        # Test parameter limits are enforced
        client.get_nearest_observations(
            species_code="norcar",
            lat=42.3601,
            lng=-71.0942,
            days_back=35,  # Should be limited to 30
            distance_km=75,  # Should be limited to 50
            max_results=5000  # Should be limited to 3000
        )
        
        call_args = mock_session.get.call_args
        params = call_args[1]["params"]
        assert params["back"] == 30  # Limited
        assert params["dist"] == 50   # Limited
        assert params["maxResults"] == 3000  # Limited

    def test_get_nearest_observations_404_error(self, client, mock_session):
        """Test 404 error handling for invalid species code."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_session.get.return_value = mock_response
        
        with pytest.raises(EBirdAPIError, match="Not found: Invalid region or species code"):
            client.get_nearest_observations(
                species_code="invalidspecies",
                lat=42.3601,
                lng=-71.0942
            )

    def test_get_nearest_observations_empty_response(self, client, mock_session):
        """Test handling of empty response when no observations found."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_session.get.return_value = mock_response
        
        result = client.get_nearest_observations(
            species_code="rarebird",
            lat=42.3601,
            lng=-71.0942
        )
        
        assert result == []

    # Tests for get_species_list()
    def test_get_species_list_success(self, client, mock_session):
        """Test successful get_species_list call."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            "norcar", "blujay", "amerob", "houspa", "eurost", "commgr"
        ]
        mock_session.get.return_value = mock_response
        
        result = client.get_species_list("US-MA")
        
        assert len(result) == 6
        assert "norcar" in result
        assert "blujay" in result
        
        # Verify API call
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert "/product/spplist/US-MA" in call_args[0][0]

    def test_get_species_list_invalid_region(self, client, mock_session):
        """Test error handling for invalid region code."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_session.get.return_value = mock_response
        
        with pytest.raises(EBirdAPIError, match="Not found: Invalid region or species code"):
            client.get_species_list("INVALID-REGION")

    def test_get_species_list_large_response(self, client, mock_session):
        """Test handling of large species lists."""
        # Generate a large mock response (like for a country)
        large_species_list = [f"species{i:04d}" for i in range(1000)]
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = large_species_list
        mock_session.get.return_value = mock_response
        
        result = client.get_species_list("US")
        
        assert len(result) == 1000
        assert result[0] == "species0000"
        assert result[-1] == "species0999"

    # Tests for get_region_info()
    def test_get_region_info_success(self, client, mock_session):
        """Test successful get_region_info call."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": "US-MA",
            "name": "Massachusetts, United States",
            "nameFormat": "detailed",
            "parent": "US",
            "bounds": {
                "minLat": 41.2371,
                "maxLat": 42.8868,
                "minLng": -73.5081,
                "maxLng": -69.9258
            }
        }
        mock_session.get.return_value = mock_response
        
        result = client.get_region_info("US-MA")
        
        assert result["code"] == "US-MA"
        assert result["name"] == "Massachusetts, United States"
        assert "bounds" in result
        
        # Verify API call
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert "/ref/region/info/US-MA" in call_args[0][0]
        assert call_args[1]["params"]["nameFormat"] == "detailed"

    def test_get_region_info_name_formats(self, client, mock_session):
        """Test different name format options."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": "US-MA",
            "name": "Massachusetts",
            "nameFormat": "short"
        }
        mock_session.get.return_value = mock_response
        
        client.get_region_info("US-MA", name_format="short")
        
        call_args = mock_session.get.call_args
        assert call_args[1]["params"]["nameFormat"] == "short"

    def test_get_region_info_hierarchical_regions(self, client, mock_session):
        """Test region info for different hierarchical levels."""
        # Test country level
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": "US",
            "name": "United States",
            "type": "country"
        }
        mock_session.get.return_value = mock_response
        
        result = client.get_region_info("US")
        assert result["code"] == "US"
        assert result["type"] == "country"

    # Tests for get_hotspot_info()
    def test_get_hotspot_info_success(self, client, mock_session):
        """Test successful get_hotspot_info call."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "locId": "L123456",
            "name": "Central Park",
            "lat": 40.7829,
            "lng": -73.9654,
            "countryCode": "US",
            "subnational1Code": "US-NY",
            "isHotspot": True,
            "numSpeciesAllTime": 287,
            "numChecklistsAllTime": 15432
        }
        mock_session.get.return_value = mock_response
        
        result = client.get_hotspot_info("L123456")
        
        assert result["locId"] == "L123456"
        assert result["name"] == "Central Park"
        assert result["numSpeciesAllTime"] == 287
        assert result["isHotspot"] is True
        
        # Verify API call
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert "/ref/hotspot/info/L123456" in call_args[0][0]

    def test_get_hotspot_info_invalid_location(self, client, mock_session):
        """Test error handling for invalid location ID."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_session.get.return_value = mock_response
        
        with pytest.raises(EBirdAPIError, match="Not found: Invalid region or species code"):
            client.get_hotspot_info("INVALID-LOCATION")

    def test_get_hotspot_info_non_hotspot_location(self, client, mock_session):
        """Test behavior with personal location (non-hotspot)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "locId": "L987654",
            "name": "Personal Location",
            "isHotspot": False,
            "numSpeciesAllTime": 0,
            "numChecklistsAllTime": 1
        }
        mock_session.get.return_value = mock_response
        
        result = client.get_hotspot_info("L987654")
        assert result["isHotspot"] is False
        assert result["numSpeciesAllTime"] == 0

    # General error handling tests
    def test_rate_limiting_retry(self, client, mock_session):
        """Test rate limiting and retry behavior."""
        # First call returns 429, second call succeeds
        mock_responses = [
            Mock(status_code=429),
            Mock(status_code=200)
        ]
        mock_responses[1].json.return_value = ["norcar", "blujay"]
        mock_session.get.side_effect = mock_responses
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = client.get_species_list("US-MA")
            
        assert result == ["norcar", "blujay"]
        assert mock_session.get.call_count == 2

    def test_server_error_retry(self, client, mock_session):
        """Test server error retry behavior."""
        # First call returns 500, second call succeeds
        mock_responses = [
            Mock(status_code=500),
            Mock(status_code=200)
        ]
        mock_responses[1].json.return_value = {"locId": "L123456", "name": "Test Location"}
        mock_session.get.side_effect = mock_responses
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = client.get_hotspot_info("L123456")
            
        assert result["locId"] == "L123456"
        assert mock_session.get.call_count == 2

    def test_max_retries_exceeded(self, client, mock_session):
        """Test behavior when max retries are exceeded."""
        mock_response = Mock(status_code=429)
        mock_session.get.return_value = mock_response
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            with pytest.raises(EBirdAPIError, match="Rate limit exceeded"):
                client.get_species_list("US-MA")
        
        assert mock_session.get.call_count == 3  # Initial + 2 retries

    def test_connection_error_handling(self, client, mock_session):
        """Test handling of connection errors."""
        mock_session.get.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            with pytest.raises(EBirdAPIError, match="Connection error"):
                client.get_region_info("US-MA")

    def test_timeout_error_handling(self, client, mock_session):
        """Test handling of timeout errors."""
        mock_session.get.side_effect = requests.exceptions.Timeout("Request timed out")
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            with pytest.raises(EBirdAPIError, match="Request timeout"):
                client.get_nearest_observations("norcar", 42.36, -71.09)

    # Convenience function tests
    def test_convenience_functions_exist(self):
        """Test that convenience functions are properly imported."""
        from src.bird_travel_recommender.utils.ebird_api import (
            get_nearest_observations,
            get_species_list,
            get_region_info,
            get_hotspot_info
        )
        
        # Verify functions exist and are callable
        assert callable(get_nearest_observations)
        assert callable(get_species_list)
        assert callable(get_region_info)
        assert callable(get_hotspot_info)

    @patch('src.bird_travel_recommender.utils.ebird_api.get_client')
    def test_convenience_functions_delegate(self, mock_get_client):
        """Test that convenience functions properly delegate to client methods."""
        from src.bird_travel_recommender.utils.ebird_api import (
            get_nearest_observations,
            get_species_list,
            get_region_info,
            get_hotspot_info
        )
        
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        # Test each convenience function
        get_nearest_observations("norcar", 42.36, -71.09)
        mock_client.get_nearest_observations.assert_called_once_with("norcar", 42.36, -71.09)
        
        get_species_list("US-MA")
        mock_client.get_species_list.assert_called_once_with("US-MA")
        
        get_region_info("US-MA")
        mock_client.get_region_info.assert_called_once_with("US-MA")
        
        get_hotspot_info("L123456")
        mock_client.get_hotspot_info.assert_called_once_with("L123456")


if __name__ == "__main__":
    # Run tests if script is executed directly
    pytest.main([__file__, "-v"])