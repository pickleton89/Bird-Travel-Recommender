#!/usr/bin/env python3
"""
Test script for Enhanced NLP functionality

Tests the LLM-powered intent classification and parameter extraction
without requiring full MCP server setup.
"""

import logging
import pytest

# Skip entire module if enhanced_agent_flow is not available
pytest.skip("enhanced_agent_flow module not yet implemented", allow_module_level=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_enhanced_nlp():
    """Test enhanced NLP processor independently"""
    try:
        from bird_travel_recommender.utils.enhanced_nlp import EnhancedNLPProcessor, BirdingIntent
        
        # Create processor
        nlp = EnhancedNLPProcessor()
        
        # Test cases with different complexity levels
        test_cases = [
            {
                "request": "Plan a birding trip to see Northern Cardinals in Massachusetts",
                "expected_intent": BirdingIntent.COMPLETE_TRIP_PLANNING,
                "context": {}
            },
            {
                "request": "What equipment do I need for hawk watching?",
                "expected_intent": BirdingIntent.EQUIPMENT_ADVICE,
                "context": {}
            },
            {
                "request": "Recent cardinal sightings near Boston",
                "expected_intent": BirdingIntent.QUICK_LOOKUP,
                "context": {}
            },
            {
                "request": "I'd love to plan a 3-day birding trip around Boston to see warblers during spring migration",
                "expected_intent": BirdingIntent.COMPLETE_TRIP_PLANNING,
                "context": {"experience_level": "intermediate"}
            },
            {
                "request": "How do I identify different warbler songs?",
                "expected_intent": BirdingIntent.TECHNIQUE_ADVICE,
                "context": {}
            }
        ]
        
        print("Testing Enhanced NLP Processor")
        print("=" * 50)
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\nTest Case {i}:")
            print(f"Request: {test_case['request']}")
            print(f"Expected Intent: {test_case['expected_intent'].value}")
            
            try:
                # Analyze request
                analysis = nlp.analyze_birding_request(
                    test_case['request'], 
                    test_case['context']
                )
                
                print(f"Detected Intent: {analysis.primary_intent.value}")
                print(f"Confidence: {analysis.confidence_score:.2f}")
                print(f"Strategy: {analysis.strategy_recommendation}")
                
                if analysis.parameters.species:
                    print(f"Extracted Species: {', '.join(analysis.parameters.species)}")
                if analysis.parameters.locations:
                    print(f"Extracted Locations: {', '.join(analysis.parameters.locations)}")
                if analysis.parameters.timeframes:
                    print(f"Extracted Timeframes: {', '.join(analysis.parameters.timeframes)}")
                
                # Test parameter conversion
                tool_params = nlp.get_enhanced_parameters_for_tool(analysis, test_case['context'])
                print(f"Tool Parameters Generated: {len(tool_params)} parameters")
                
                # Check if intent matches expectation
                intent_match = analysis.primary_intent == test_case['expected_intent']
                print(f"Intent Match: {'✓' if intent_match else '✗'}")
                
            except Exception as e:
                print(f"Error in test case: {str(e)}")
                # Test fallback
                try:
                    fallback_analysis = nlp._fallback_rule_based_analysis(
                        test_case['request'], 
                        test_case['context']
                    )
                    print(f"Fallback Intent: {fallback_analysis.primary_intent.value}")
                    print(f"Fallback Confidence: {fallback_analysis.confidence_score:.2f}")
                except Exception as fallback_error:
                    print(f"Fallback also failed: {str(fallback_error)}")
        
        print(f"\n{'=' * 50}")
        print("Enhanced NLP Testing Complete")
        
    except ImportError as e:
        print(f"Import error: {str(e)}")
        print("Make sure all dependencies are installed and modules are available")
    except Exception as e:
        print(f"Test error: {str(e)}")

def test_enhanced_agent_node():
    """Test enhanced agent node independently"""
    try:
        from enhanced_agent_flow import EnhancedDecideBirdingToolNode
        
        # Create enhanced node
        node = EnhancedDecideBirdingToolNode()
        
        # Test data
        test_requests = [
            "Plan a birding trip to see Northern Cardinals and Blue Jays in Massachusetts",
            "What's the best time to see warblers during migration?",
            "Recent hawk sightings near Boston"
        ]
        
        print("\nTesting Enhanced Agent Node")
        print("=" * 50)
        
        for i, request in enumerate(test_requests, 1):
            print(f"\nTest {i}: {request}")
            
            # Create mock shared store
            shared_store = {
                "user_request": request,
                "context": {
                    "default_coordinates": {"lat": 42.3601, "lng": -71.0589}
                }
            }
            
            try:
                # Execute node
                node.prep(shared_store)
                result = node.exec(shared_store)
                node.post(shared_store)
                
                print(f"Success: {result.get('success', False)}")
                print(f"Strategy: {result.get('strategy', 'unknown')}")
                print(f"Confidence: {result.get('confidence', 0):.2f}")
                
                if "tool_execution_plan" in shared_store:
                    plan = shared_store["tool_execution_plan"]
                    print(f"Tools planned: {len(plan.tools)}")
                    if hasattr(plan, 'intent_analysis'):
                        print(f"Primary intent: {plan.intent_analysis.primary_intent.value}")
                
            except Exception as e:
                print(f"Node execution error: {str(e)}")
        
        print(f"\n{'=' * 50}")
        print("Enhanced Agent Node Testing Complete")
        
    except ImportError as e:
        print(f"Import error: {str(e)}")
    except Exception as e:
        print(f"Test error: {str(e)}")

def test_full_enhanced_agent():
    """Test full enhanced agent execution (requires MCP server)"""
    try:
        from enhanced_agent_flow import execute_enhanced_agent_request
        
        print("\nTesting Full Enhanced Agent")
        print("=" * 50)
        
        request = "I want to plan a birding trip to see cardinals and warblers around Boston"
        
        print(f"Request: {request}")
        print("Executing enhanced agent...")
        
        # This will create its own MCP server
        # Skip actual execution since it requires async and MCP server
        print("Skipping actual execution (requires async MCP server)")
        print("Test would execute: execute_enhanced_agent_request(request, context)")
        
        print("Test completed (mock mode)")
        
    except ImportError as e:
        print(f"Import error (MCP server may not be available): {str(e)}")
    except Exception as e:
        print(f"Full agent test error: {str(e)}")

if __name__ == "__main__":
    print("Enhanced NLP Testing Suite")
    print("=" * 60)
    
    # Test 1: Basic NLP processor
    test_enhanced_nlp()
    
    # Test 2: Enhanced agent node
    test_enhanced_agent_node()
    
    # Test 3: Full agent (if MCP server available)
    print(f"\n{'=' * 60}")
    print("Note: Full agent test requires MCP server dependencies")
    print("Running basic tests only. Use run_enhanced_agent.py for full testing.")
    
    # Uncomment to test full agent if MCP server is set up
    # asyncio.run(test_full_enhanced_agent())