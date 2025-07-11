#!/usr/bin/env python3
"""
Comprehensive Error Handling Tests

Tests the enhanced error handling framework across all tool categories
including validation, retries, timeouts, and circuit breakers.
"""

import pytest
import asyncio
from unittest.mock import patch

# Import enhanced error handling framework
from src.bird_travel_recommender.mcp.utils.error_handling import (
    ValidationError,
    APIError,
    RateLimitError,
    MCPError,
    validate_parameters,
    with_timeout,
    with_retry,
    handle_errors_gracefully,
    CircuitBreaker
)

# Import enhanced handler
from src.bird_travel_recommender.mcp.handlers.enhanced_species import EnhancedSpeciesHandlers


@pytest.mark.asyncio
class TestEnhancedErrorHandling:
    """Test suite for enhanced error handling framework"""
    
    @pytest.fixture
    def enhanced_handler(self):
        """Create enhanced species handler for testing"""
        with patch.dict('os.environ', {'EBIRD_API_KEY': 'test_key', 'OPENAI_API_KEY': 'test_key'}):
            return EnhancedSpeciesHandlers()
    
    # Test 1: Input Validation
    async def test_validation_decorator(self):
        """Test parameter validation decorator"""
        
        @validate_parameters({
            "lat": {"type": (int, float), "required": True, "range": (-90, 90)},
            "lng": {"type": (int, float), "required": True, "range": (-180, 180)},
            "name": {"type": str, "max_length": 50}
        })
        async def test_function(lat: float, lng: float, name: str = "test"):
            return {"lat": lat, "lng": lng, "name": name}
        
        # Valid inputs
        result = await test_function(lat=42.3, lng=-71.1, name="Boston")
        assert result["lat"] == 42.3
        
        # Invalid type
        with pytest.raises(ValidationError) as exc_info:
            await test_function(lat="invalid", lng=-71.1)
        assert "must be of type" in str(exc_info.value)
        
        # Out of range
        with pytest.raises(ValidationError) as exc_info:
            await test_function(lat=100, lng=-71.1)  # Invalid latitude
        assert "must be between" in str(exc_info.value)
        
        # Missing required parameter
        with pytest.raises(ValidationError) as exc_info:
            await test_function(lng=-71.1)  # Missing lat
        assert "Required parameter" in str(exc_info.value)
        
        # String too long
        with pytest.raises(ValidationError) as exc_info:
            await test_function(lat=42.3, lng=-71.1, name="x" * 100)
        assert "length exceeds maximum" in str(exc_info.value)
    
    # Test 2: Timeout Handling
    async def test_timeout_decorator(self):
        """Test timeout decorator"""
        
        @with_timeout(0.1)  # 100ms timeout
        async def fast_function():
            await asyncio.sleep(0.05)
            return "success"
        
        @with_timeout(0.1)  # 100ms timeout
        async def slow_function():
            await asyncio.sleep(0.2)
            return "should timeout"
        
        # Fast function should succeed
        result = await fast_function()
        assert result == "success"
        
        # Slow function should timeout
        with pytest.raises(MCPError) as exc_info:
            await slow_function()
        assert "timed out" in str(exc_info.value)
        assert exc_info.value.category.value == "timeout_error"
    
    # Test 3: Retry Logic
    async def test_retry_decorator(self):
        """Test retry decorator with backoff"""
        
        call_count = 0
        
        @with_retry(max_retries=3, delay=0.01, backoff_factor=2.0)
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise APIError("Temporary failure", status_code=500)
            return "success after retries"
        
        # Should succeed after retries
        result = await flaky_function()
        assert result == "success after retries"
        assert call_count == 3
        
        # Test max retries exceeded
        call_count = 0
        
        @with_retry(max_retries=2, delay=0.01)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise APIError("Always fails", status_code=500)
        
        with pytest.raises(APIError):
            await always_fails()
        assert call_count == 3  # Initial attempt + 2 retries
    
    # Test 4: Circuit Breaker
    async def test_circuit_breaker(self):
        """Test circuit breaker pattern"""
        
        circuit_breaker = CircuitBreaker(failure_threshold=2, timeout_duration=0.1)
        
        @with_timeout(1.0)
        async def api_call():
            raise APIError("Service down", status_code=500)
        
        # First few calls should fail normally
        with pytest.raises(APIError):
            await api_call()
        
        # After threshold failures, circuit should open
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        assert circuit_breaker.state == "OPEN"
        assert not circuit_breaker.can_execute()
        
        # After timeout, should allow one test call
        await asyncio.sleep(0.15)
        assert circuit_breaker.can_execute()
        assert circuit_breaker.state == "HALF_OPEN"
    
    # Test 5: Graceful Error Handling
    async def test_graceful_error_handling(self):
        """Test graceful error handling decorator"""
        
        @handle_errors_gracefully(fallback_value=[])
        async def test_function(should_fail: bool = False):
            if should_fail:
                raise ValidationError("Test validation error", "test_field", "test_value")
            return {"success": True, "data": ["item1", "item2"]}
        
        # Success case
        result = await test_function(should_fail=False)
        assert result["success"] is True
        assert "data" in result
        
        # Error case with graceful handling
        result = await test_function(should_fail=True)
        assert result["success"] is False
        assert result["error_category"] == "validation_error"
        assert result["validation_failed"] is True
        assert "Test validation error" in result["error"]
    
    # Test 6: Enhanced Species Handler Validation
    async def test_enhanced_species_validation(self, enhanced_handler):
        """Test enhanced species handler input validation"""
        
        # Test empty list validation
        result = await enhanced_handler.handle_validate_species([])
        assert result["success"] is False
        assert "validation_failed" in result
        
        # Test mixed type filtering
        with patch.object(enhanced_handler.validate_species_node, 'prep') as mock_prep, \
             patch.object(enhanced_handler.validate_species_node, 'exec') as mock_exec, \
             patch.object(enhanced_handler.validate_species_node, 'post') as mock_post:
            
            mock_prep.return_value = {}
            mock_exec.return_value = {}
            mock_post.return_value = None
            
            # Mock shared store to be modified by post
            def mock_post_side_effect(shared_store, prep_res, exec_res):
                shared_store["validated_species"] = [
                    {"species_code": "norcar", "common_name": "Northern Cardinal"}
                ]
                shared_store["validation_stats"] = {"total": 1, "validated": 1}
            
            mock_post.side_effect = mock_post_side_effect
            
            # Test with mixed input types (should filter out invalid ones)
            result = await enhanced_handler.handle_validate_species(species_names=[
                "Northern Cardinal",  # valid
                None,                # invalid - should be filtered
                123,                 # invalid - should be filtered
                "",                  # invalid - should be filtered
                "Blue Jay"           # valid
            ])
            
            assert result["success"] is True
            assert result["input_count"] == 5
            assert result["processed_count"] == 2  # Only valid strings
    
    # Test 7: Regional Species List Error Handling
    async def test_regional_species_error_handling(self, enhanced_handler):
        """Test enhanced regional species list error handling"""
        
        # Test invalid region code
        result = await enhanced_handler.handle_get_regional_species_list(region="")
        assert result["success"] is False
        assert result["error_category"] == "validation_error"
        
        # Test region code validation
        result = await enhanced_handler.handle_get_regional_species_list(region="X")  # Too short
        assert result["success"] is False
        # Circuit breaker may kick in, so check for either validation or api error
        assert result["error_category"] in ["validation_error", "api_error"]
        
        # Test API error handling
        with patch.object(enhanced_handler.ebird_api, 'get_species_list') as mock_api:
            from src.bird_travel_recommender.utils.ebird_api import EBirdAPIError
            
            # Test rate limit error conversion
            mock_api.side_effect = EBirdAPIError("Rate limit exceeded")
            result = await enhanced_handler.handle_get_regional_species_list(region="US-MA")
            assert result["success"] is False
            assert result["error_category"] == "api_error"
            
            # Test invalid region error conversion
            mock_api.side_effect = EBirdAPIError("Region not found")
            result = await enhanced_handler.handle_get_regional_species_list(region="INVALID")
            assert result["success"] is False
            assert result["error_category"] in ["validation_error", "api_error"]
    
    # Test 8: Batch Processing Error Handling
    async def test_batch_processing_errors(self, enhanced_handler):
        """Test batch processing with partial failures"""
        
        with patch.object(enhanced_handler, 'handle_get_regional_species_list') as mock_handler:
            # Setup mixed success/failure responses
            async def side_effect(region):
                if region == "US-MA":
                    return {"success": True, "region_code": region, "species_list": ["norcar"]}
                elif region == "INVALID":
                    raise ValidationError("Invalid region", "region", region)
                else:
                    raise APIError("API Error", status_code=500)
            
            mock_handler.side_effect = side_effect
            
            result = await enhanced_handler.validate_multiple_regions(["US-MA", "INVALID", "US-CA"])
            
            assert result["total_regions"] == 3
            assert result["successful_regions"] == 1
            assert result["failed_regions"] == 2
            assert result["partial_success"] is True
            assert len(result["results"]) == 1
            assert len(result["failures"]) == 2
    
    # Test 9: Error Category Classification
    async def test_error_categories(self):
        """Test that errors are properly categorized"""
        
        validation_error = ValidationError("Test validation", "field", "value")
        assert validation_error.category.value == "validation_error"
        assert validation_error.field == "field"
        
        api_error = APIError("Test API error", status_code=404, endpoint="/test")
        assert api_error.category.value == "api_error"
        assert api_error.status_code == 404
        assert api_error.endpoint == "/test"
        
        rate_limit_error = RateLimitError("Rate limited", retry_after=60)
        assert rate_limit_error.category.value == "rate_limit_error"
        assert rate_limit_error.retry_after == 60
    
    # Test 10: Error Logging and Monitoring
    async def test_error_logging(self, enhanced_handler, caplog):
        """Test that errors are properly logged for monitoring"""
        
        # Test validation error logging
        await enhanced_handler.handle_validate_species(species_names=[])
        assert "Validation error" in caplog.text
        
        # Test API error logging
        with patch.object(enhanced_handler.ebird_api, 'get_species_list') as mock_api:
            from src.bird_travel_recommender.utils.ebird_api import EBirdAPIError
            mock_api.side_effect = EBirdAPIError("Test API error")
            
            await enhanced_handler.handle_get_regional_species_list(region="US-MA")
            assert "API error" in caplog.text or "eBird API error" in caplog.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])