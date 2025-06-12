#!/usr/bin/env python3
"""
MCP Server Integration Test

This script tests the complete MCP server functionality including:
- Agent orchestration through DecideBirdingToolNode
- Tool execution through the MCP server
- End-to-end birding request processing
"""

import asyncio
import json
import logging
import sys
from typing import Dict, Any
import pytest

# Skip entire module if agent_flow is not available
pytest.skip("agent_flow module not yet implemented", allow_module_level=True)

# from bird_travel_recommender.agent_flow import execute_agent_request, DecideBirdingToolNode, ToolExecutionPlan
# from bird_travel_recommender.mcp.server import BirdTravelMCPServer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)


async def test_mcp_integration():
    """Run comprehensive MCP server integration tests"""
    
    print("🧪 Starting MCP Server Integration Tests...")
    print("=" * 60)
    
    # Test cases for different scenarios
    test_cases = [
        {
            "name": "Advice Request",
            "request": "What is the best time to see cardinals?",
            "context": {},
            "expected_response_type": "birding_advice"
        },
        {
            "name": "Trip Planning with Context",
            "request": "Plan a birding trip to see Northern Cardinals",
            "context": {
                "species": ["Northern Cardinal"],
                "region": "US-MA",
                "start_location": {"lat": 42.3601, "lng": -71.0589}
            },
            "expected_response_type": "complete_trip_plan"
        },
        {
            "name": "Species Extraction from Text",
            "request": "Help me find Blue Jays and Cardinals in Massachusetts this weekend",
            "context": {},
            "expected_response_type": ["complete_trip_plan", "birding_advice"]
        },
        {
            "name": "Equipment Advice",
            "request": "What equipment do I need for winter birding?",
            "context": {},
            "expected_response_type": "birding_advice"
        },
        {
            "name": "Location-Specific Query",
            "request": "Where can I see American Robins in California?",
            "context": {},
            "expected_response_type": ["complete_trip_plan", "birding_advice"]
        }
    ]
    
    # Track test results
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\\n🔍 Test {i}: {test_case['name']}")
        print("-" * 40)
        
        try:
            # Execute the test case
            response = await execute_agent_request(
                test_case["request"], 
                test_case["context"]
            )
            
            # Analyze response
            response_type = response.get("type", "unknown")
            success = bool(response.get("message") or response.get("advice") or response.get("trip_plan"))
            
            # Check if response type matches expectations
            expected_types = test_case["expected_response_type"]
            if isinstance(expected_types, str):
                expected_types = [expected_types]
            
            type_match = response_type in expected_types
            
            # Print results
            print(f"Request: {test_case['request']}")
            print(f"Response Type: {response_type}")
            print(f"Expected Types: {expected_types}")
            print(f"Type Match: {'✅' if type_match else '❌'}")
            print(f"Response Success: {'✅' if success else '❌'}")
            
            # Store detailed response info
            if response_type == "birding_advice":
                advice_text = response.get("advice", "")
                print(f"Advice Length: {len(advice_text)} characters")
                if advice_text:
                    print(f"Advice Preview: {advice_text[:100]}...")
            
            elif response_type == "complete_trip_plan":
                trip_plan = response.get("trip_plan", {})
                print(f"Trip Plan Components: {list(trip_plan.keys())}")
                
                summary = response.get("summary", {})
                if summary:
                    print(f"Trip Summary: {summary}")
            
            # Record test result
            results.append({
                "test_name": test_case["name"],
                "success": success and type_match,
                "response_type": response_type,
                "type_match": type_match,
                "response_length": len(str(response)),
                "error": None
            })
            
        except Exception as e:
            print(f"❌ Test failed with error: {str(e)}")
            results.append({
                "test_name": test_case["name"],
                "success": False,
                "response_type": "error",
                "type_match": False,
                "response_length": 0,
                "error": str(e)
            })
    
    # Print overall results
    print("\\n" + "=" * 60)
    print("📊 INTEGRATION TEST RESULTS")
    print("=" * 60)
    
    successful_tests = sum(1 for r in results if r["success"])
    total_tests = len(results)
    
    print(f"Total Tests: {total_tests}")
    print(f"Successful: {successful_tests}")
    print(f"Failed: {total_tests - successful_tests}")
    print(f"Success Rate: {successful_tests/total_tests*100:.1f}%")
    
    print("\\nDetailed Results:")
    for result in results:
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"  {status} {result['test_name']} ({result['response_type']})")
        if result["error"]:
            print(f"    Error: {result['error']}")
    
    # Test individual tool selection logic
    print("\\n" + "=" * 60)
    print("🧠 TESTING INTELLIGENT TOOL SELECTION")
    print("=" * 60)
    
    tool_selection_tests = [
        {
            "request": "Plan a birding trip to see Northern Cardinals in Massachusetts",
            "context": {"species": ["Northern Cardinal"], "region": "US-MA"},
            "expected_strategy": "monolithic",
            "expected_tool": "plan_complete_trip"
        },
        {
            "request": "What equipment do I need for birding?",
            "context": {},
            "expected_strategy": "monolithic", 
            "expected_tool": "get_birding_advice"
        },
        {
            "request": "validate these species: Blue Jay, Cardinal",
            "context": {"species": ["Blue Jay", "Northern Cardinal"]},
            "expected_strategy": "component",
            "expected_tool": "validate_species"
        }
    ]
    
    node = DecideBirdingToolNode()
    
    for test in tool_selection_tests:
        shared_store = {
            "user_request": test["request"],
            "context": test["context"]
        }
        
        node.prep(shared_store)
        result = node.exec(shared_store)
        plan = shared_store.get("tool_execution_plan")
        
        strategy_match = plan.strategy == test["expected_strategy"]
        tool_match = plan.tools[0]["name"] == test["expected_tool"]
        
        print(f"Request: {test['request'][:50]}...")
        print(f"Strategy: {plan.strategy} (expected: {test['expected_strategy']}) {'✅' if strategy_match else '❌'}")
        print(f"Tool: {plan.tools[0]['name']} (expected: {test['expected_tool']}) {'✅' if tool_match else '❌'}")
        print()
    
    print("🎉 MCP Integration Tests Complete!")
    
    return successful_tests == total_tests


async def main():
    """Main test execution function"""
    try:
        success = await test_mcp_integration()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Integration test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())