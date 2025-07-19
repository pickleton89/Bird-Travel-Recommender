"""
Test backward compatibility of the new eBird client implementation.

These tests ensure that the new unified client can be used as a drop-in
replacement for the old client implementations.
"""

import pytest
from unittest.mock import Mock, patch
from src.bird_travel_recommender.core.ebird import EBirdClient, EBirdAPIClient
from src.bird_travel_recommender.core.ebird.adapters import create_legacy_ebird_client
from src.bird_travel_recommender.core.config.constants import ExecutionMode


class TestEBirdClientBackwardCompatibility:
    """Test suite for backward compatibility of eBird client."""
    
    def test_unified_client_imports(self):
        """Test that the new unified client imports correctly."""
        from src.bird_travel_recommender.core.ebird import EBirdClient
        assert EBirdClient is not None
        
    def test_legacy_adapter_imports(self):
        """Test that legacy adapters import correctly."""
        from src.bird_travel_recommender.core.ebird import EBirdAPIClient
        from src.bird_travel_recommender.core.ebird import create_legacy_ebird_client
        assert EBirdAPIClient is not None
        assert create_legacy_ebird_client is not None
        
    def test_unified_client_initialization(self):
        """Test that unified client initializes correctly."""
        # Test with default settings (should use env vars)
        try:
            client = EBirdClient.create_sync()
            assert client is not None
            client.close()
        except Exception as e:
            # Expected if no API key in environment
            assert "eBird API key" in str(e)
            
        # Test with explicit API key
        client = EBirdClient.create_sync(api_key="test_key")
        assert client is not None
        assert client.mode == ExecutionMode.SYNC
        client.close()
        
        # Test async mode
        client = EBirdClient.create_async(api_key="test_key")
        assert client is not None
        assert client.mode == ExecutionMode.ASYNC
        client.close()
        
    def test_legacy_adapter_initialization(self):
        """Test that legacy adapters initialize correctly."""
        # Test factory function
        legacy_client = create_legacy_ebird_client(api_key="test_key")
        assert legacy_client is not None
        legacy_client.close()
        
        # Test legacy class
        api_client = EBirdAPIClient(api_key="test_key")
        assert api_client is not None
        api_client.close()
        
    def test_unified_client_has_all_methods(self):
        """Test that unified client has all expected methods."""
        client = EBirdClient.create_sync(api_key="test_key")
        
        # Test taxonomy methods
        assert hasattr(client, 'get_taxonomy')
        assert hasattr(client, 'get_species_list')
        assert hasattr(client, 'get_taxonomic_forms')
        
        # Test observations methods
        assert hasattr(client, 'get_recent_observations')
        assert hasattr(client, 'get_recent_notable_observations')
        assert hasattr(client, 'get_species_observations')
        
        # Test locations methods
        assert hasattr(client, 'get_hotspots')
        assert hasattr(client, 'get_nearby_hotspots')
        assert hasattr(client, 'get_hotspot_info')
        
        # Test regions methods
        assert hasattr(client, 'get_region_info')
        assert hasattr(client, 'get_subregions')
        assert hasattr(client, 'get_countries')
        
        # Test checklists methods
        assert hasattr(client, 'get_recent_checklists')
        assert hasattr(client, 'get_checklist_details')
        assert hasattr(client, 'get_user_stats')
        
        client.close()
        
    def test_legacy_adapter_has_expected_methods(self):
        """Test that legacy adapter has expected methods."""
        legacy_client = create_legacy_ebird_client(api_key="test_key")
        
        # Test base methods
        assert hasattr(legacy_client, 'make_request')
        assert hasattr(legacy_client, 'close')
        
        legacy_client.close()
        
        # Test combined API client
        api_client = EBirdAPIClient(api_key="test_key")
        
        # Should have methods from all mixins
        assert hasattr(api_client, 'get_taxonomy')
        assert hasattr(api_client, 'get_recent_observations')
        assert hasattr(api_client, 'get_hotspots')
        
        api_client.close()
        
    @patch('src.bird_travel_recommender.core.ebird.client.EBirdClient.request')
    def test_legacy_adapter_method_calls(self, mock_request):
        """Test that legacy adapter methods call the underlying client correctly."""
        # Mock the request method to return sample data
        mock_request.return_value = [
            {
                "species_code": "amerob",
                "common_name": "American Robin",
                "scientific_name": "Turdus migratorius",
                "category": "species",
                "order": "Passeriformes",
                "family": "Turdidae"
            }
        ]
        
        api_client = EBirdAPIClient(api_key="test_key")
        
        # Test that calling legacy method works
        result = api_client.get_taxonomy()
        
        # Should return list of dicts (backward compatible format)
        assert isinstance(result, list)
        if result:  # If mock returned data
            assert isinstance(result[0], dict)
            assert "species_code" in result[0]
            
        api_client.close()
        
    def test_client_context_managers(self):
        """Test that clients work as context managers."""
        # Test sync client
        with EBirdClient.create_sync(api_key="test_key") as client:
            assert client is not None
            
        # Test legacy adapter
        legacy_client = create_legacy_ebird_client(api_key="test_key")
        try:
            assert legacy_client is not None
        finally:
            legacy_client.close()
            
    def test_client_info_methods(self):
        """Test client information and health check methods."""
        client = EBirdClient.create_sync(api_key="test_key")
        
        # Test client info
        info = client.get_client_info()
        assert isinstance(info, dict)
        assert "mode" in info
        assert "middleware_count" in info
        assert info["mode"] == "sync"
        
        client.close()


@pytest.mark.asyncio
class TestAsyncEBirdClientCompatibility:
    """Test suite for async eBird client compatibility."""
    
    async def test_async_unified_client(self):
        """Test async unified client functionality."""
        client = EBirdClient.create_async(api_key="test_key")
        assert client is not None
        assert client.mode == ExecutionMode.ASYNC
        
        # Test health check method
        health = await client.health_check()
        assert isinstance(health, dict)
        assert "status" in health
        
        client.close()
        
    async def test_async_context_manager(self):
        """Test async client as context manager."""
        async with EBirdClient.create_async(api_key="test_key") as client:
            assert client is not None
            info = client.get_client_info()
            assert info["mode"] == "async"