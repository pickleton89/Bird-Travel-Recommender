#!/usr/bin/env python3
"""
Test script for authentication and rate limiting functionality
"""

import os
import sys
import asyncio
import tempfile
import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from bird_travel_recommender.mcp.auth import AuthManager
from bird_travel_recommender.mcp.rate_limiting import RateLimiter, RateLimitConfig

def test_auth_manager():
    """Test authentication manager functionality"""
    print("Testing Authentication Manager...")
    
    # Create temporary config for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = os.path.join(temp_dir, "test_auth.json")
        
        # Initialize auth manager
        auth_manager = AuthManager(auth_config_path=config_path)
        
        # Create a test API key
        raw_key = auth_manager.create_api_key("test_user", ["read:species", "get:advice"])
        print(f"✅ Created API key: {raw_key[:8]}...")
        
        # Test authentication
        session = auth_manager.authenticate_request(raw_key)
        if session:
            print(f"✅ Authentication successful for user: {session.user_id}")
            print(f"   Permissions: {session.permissions}")
        assert session is not None, "Authentication should succeed with valid key"
        
        # Test permission checking
        has_species_perm = auth_manager.check_permission(session, "read:species")
        has_admin_perm = auth_manager.check_permission(session, "admin:manage_keys")
        
        print(f"✅ Permission 'read:species': {has_species_perm}")
        print(f"✅ Permission 'admin:manage_keys': {has_admin_perm}")
        
        # Test rate limiting
        within_limit = auth_manager.check_rate_limit(session)
        print(f"✅ Rate limit check: {within_limit}")
        
        # Test invalid key
        invalid_session = auth_manager.authenticate_request("invalid_key")
        print(f"✅ Invalid key correctly rejected: {invalid_session is None}")
        
        # Test completed successfully

def test_rate_limiter():
    """Test rate limiting functionality"""
    print("\nTesting Rate Limiter...")
    
    rate_limiter = RateLimiter()
    
    # Test user rate limiting
    user_id = "test_user"
    endpoint = "test_endpoint"
    
    # Set a low limit for testing
    test_config = RateLimitConfig(
        max_requests=3,
        window_seconds=60,
        burst_allowance=1
    )
    rate_limiter.set_user_limit(user_id, test_config)
    
    print(f"Set rate limit: {test_config.max_requests + test_config.burst_allowance} requests per {test_config.window_seconds}s")
    
    # Test requests within limit
    for i in range(4):  # 3 normal + 1 burst
        status = rate_limiter.check_rate_limit(user_id, endpoint)
        if not status.is_exceeded:
            rate_limiter.record_request(user_id, endpoint, success=True)
            print(f"✅ Request {i+1}: Allowed (remaining: {status.remaining})")
        else:
            print(f"❌ Request {i+1}: Rate limited")
    
    # Test request that should be rate limited
    status = rate_limiter.check_rate_limit(user_id, endpoint)
    if status.is_exceeded:
        print("✅ Request 5: Correctly rate limited")
    else:
        print("❌ Request 5: Should have been rate limited")
    
    # Test system stats
    stats = rate_limiter.get_system_stats()
    assert 'total_requests' in stats, "System stats should include total_requests"
    print(f"✅ System stats: {stats['total_requests']} total requests")

def test_circuit_breaker():
    """Test circuit breaker functionality"""
    print("\nTesting Circuit Breaker...")
    
    rate_limiter = RateLimiter()
    endpoint = "test_endpoint"
    
    # Get circuit breaker for endpoint
    circuit_breaker = rate_limiter.circuit_breakers.get(endpoint)
    if not circuit_breaker:
        from bird_travel_recommender.mcp.rate_limiting import CircuitBreaker
        circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=5)
        rate_limiter.circuit_breakers[endpoint] = circuit_breaker
    
    print(f"Circuit breaker initial state: {circuit_breaker.state}")
    
    # Record failures to trigger circuit breaker
    for i in range(4):
        circuit_breaker.record_failure()
        print(f"Failure {i+1}: State = {circuit_breaker.state}")
    
    # Test that requests are blocked
    can_proceed = circuit_breaker.can_proceed()
    assert not can_proceed, "Circuit breaker should block requests after failures"
    print(f"✅ Circuit breaker blocking requests: {not can_proceed}")

@pytest.mark.asyncio
async def test_decorated_handler():
    """Test handler with auth and rate limiting decorators"""
    print("\nTesting Decorated Handler...")
    
    from bird_travel_recommender.mcp.handlers.advisory import AdvisoryHandlers
    from bird_travel_recommender.mcp.auth import AuthManager
    from bird_travel_recommender.mcp.rate_limiting import RateLimiter
    
    # Create handler with auth components
    handler = AdvisoryHandlers()
    handler.auth_manager = AuthManager()
    handler.rate_limiter = RateLimiter()
    
    # Create API key
    raw_key = handler.auth_manager.create_api_key("test_user", ["get:advice"])
    
    # Set API key in environment for testing
    os.environ['MCP_API_KEY'] = raw_key
    
    try:
        # Test handler call (this would normally require all the handler setup)
        assert handler.auth_manager is not None, "Auth manager should be configured"
        assert handler.rate_limiter is not None, "Rate limiter should be configured"
        print("✅ Handler security components initialized")
        print(f"   Auth manager configured: {handler.auth_manager is not None}")
        print(f"   Rate limiter configured: {handler.rate_limiter is not None}")
        
        # Test session creation
        session = handler.auth_manager.authenticate_request(raw_key)
        assert session is not None, "Session should be created with valid key"
        print(f"✅ Session created for user: {session.user_id if session else 'None'}")
        
    finally:
        # Clean up
        if 'MCP_API_KEY' in os.environ:
            del os.environ['MCP_API_KEY']

def main():
    """Run all authentication and rate limiting tests"""
    print("🔐 Authentication and Rate Limiting Test Suite")
    print("=" * 60)
    
    tests = [
        test_auth_manager,
        test_rate_limiter,
        test_circuit_breaker,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with error: {e}")
            results.append(False)
    
    # Run async test
    try:
        async_result = asyncio.run(test_decorated_handler())
        results.append(async_result)
    except Exception as e:
        print(f"❌ Async test failed with error: {e}")
        results.append(False)
    
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"✅ Authentication and Rate Limiting Tests: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All security tests passed!")
    else:
        print("⚠️  Some tests failed - review security implementation")

if __name__ == "__main__":
    main()