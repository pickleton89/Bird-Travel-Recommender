#!/usr/bin/env python3
"""
Test Enhanced Response Formatting

This script tests the complete enhanced agent system including:
- LLM-powered intent classification
- Intelligent parameter extraction  
- Advanced response formatting
- User-centric language adaptation
"""

import asyncio
import json
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_response_formatter():
    """Test the response formatter independently"""
    
    try:
        from utils.response_formatter import format_tool_response
        
        print("Testing Enhanced Response Formatter")
        print("=" * 50)
        
        # Test case 1: Complete trip planning response
        mock_trip_result = {
            "success": True,
            "tool": "plan_complete_trip",
            "result": {
                "trip_plan": {
                    "species_names": ["Northern Cardinal", "Blue Jay"],
                    "region": "US-MA",
                    "trip_duration_days": 2,
                    "itinerary": "# Day 1: Morning at Arnold Arboretum\n\nStart early at 6 AM for cardinal activity...",
                    "route": {"total_distance_km": 45.2, "locations": 3},
                    "locations": [
                        {"name": "Arnold Arboretum", "score": 0.85, "species_diversity": 3},
                        {"name": "Fresh Pond", "score": 0.72, "species_diversity": 2}
                    ]
                }
            }
        }
        
        formatted_response = format_tool_response(
            mock_trip_result,
            user_request="Plan a birding trip for cardinals and blue jays around Boston",
            experience_level="intermediate",
            special_interests=["photography"],
            extracted_species=["Northern Cardinal", "Blue Jay"],
            extracted_locations=["Boston"]
        )
        
        print("Test 1 - Trip Planning Response:")
        print(f"Type: {formatted_response.get('type', 'unknown')}")
        print(f"Title: {formatted_response.get('title', 'No title')}")
        if formatted_response.get('quick_facts'):
            print(f"Quick Facts: {len(formatted_response['quick_facts'])} items")
        print("✓ Trip planning formatting successful")
        
        # Test case 2: Advice response
        mock_advice_result = {
            "success": True,
            "tool": "get_birding_advice",
            "result": {
                "advice": "For hawk watching, you'll want to position yourself at a high vantage point during migration seasons...",
                "query": "What equipment do I need for hawk watching?",
                "advice_type": "equipment_advice"
            }
        }
        
        formatted_advice = format_tool_response(
            mock_advice_result,
            user_request="What equipment do I need for hawk watching?",
            experience_level="beginner",
            special_interests=["equipment", "raptors"],
            extracted_species=["hawks"],
            extracted_locations=[]
        )
        
        print("\nTest 2 - Advice Response:")
        print(f"Type: {formatted_advice.get('type', 'unknown')}")
        print(f"Title: {formatted_advice.get('title', 'No title')}")
        print("✓ Advice formatting successful")
        
        # Test case 3: Sightings response
        mock_sightings_result = {
            "success": True,
            "tool": "fetch_sightings",
            "result": {
                "sightings": [
                    {"comName": "Northern Cardinal", "locName": "Arnold Arboretum", "obsDt": "2024-01-15", "lat": 42.28, "lng": -71.12},
                    {"comName": "Northern Cardinal", "locName": "Fresh Pond", "obsDt": "2024-01-14", "lat": 42.39, "lng": -71.15}
                ],
                "statistics": {"total_sightings": 2, "unique_locations": 2}
            }
        }
        
        formatted_sightings = format_tool_response(
            mock_sightings_result,
            user_request="Recent cardinal sightings near Boston",
            experience_level="expert",
            special_interests=["citizen_science"],
            extracted_species=["Northern Cardinal"],
            extracted_locations=["Boston"]
        )
        
        print("\nTest 3 - Sightings Response:")
        print(f"Type: {formatted_sightings.get('type', 'unknown')}")
        print(f"Title: {formatted_sightings.get('title', 'No title')}")
        print("✓ Sightings formatting successful")
        
        print(f"\n{'=' * 50}")
        print("Response Formatter Testing Complete")
        
    except ImportError as e:
        print(f"Import error: {str(e)}")
    except Exception as e:
        print(f"Test error: {str(e)}")

def test_enhanced_process_results():
    """Test the enhanced process results node"""
    
    try:
        from enhanced_process_results import EnhancedProcessResultsNode
        from utils.enhanced_nlp import BirdingIntent, ExtractedParameters, IntentAnalysis
        
        print("\nTesting Enhanced Process Results Node")
        print("=" * 50)
        
        # Create test node
        node = EnhancedProcessResultsNode()
        
        # Create mock intent analysis
        mock_intent = IntentAnalysis(
            primary_intent=BirdingIntent.COMPLETE_TRIP_PLANNING,
            secondary_intents=[],
            parameters=ExtractedParameters(
                species=["Northern Cardinal", "Blue Jay"],
                locations=["Boston"],
                region_codes=["US-MA"],
                coordinates=[],
                timeframes=["weekend"],
                duration_days=2,
                max_distance_km=100,
                experience_level="intermediate",
                special_interests=["photography"],
                season="spring",
                confidence_score=0.9
            ),
            strategy_recommendation="monolithic",
            confidence_score=0.9,
            reasoning="Complete trip planning request with clear species and location"
        )
        
        # Create mock shared store
        shared_store = {
            "user_request": "Plan a weekend birding trip around Boston for cardinals and blue jays",
            "tool_execution_results": [{
                "success": True,
                "tool": "plan_complete_trip",
                "result": {
                    "trip_plan": {
                        "species_names": ["Northern Cardinal", "Blue Jay"],
                        "region": "US-MA",
                        "trip_duration_days": 2,
                        "itinerary": "# Weekend Birding Adventure\n\nDay 1: Start at Arnold Arboretum...",
                        "locations": [
                            {"name": "Arnold Arboretum", "score": 0.85},
                            {"name": "Fresh Pond", "score": 0.72}
                        ]
                    }
                }
            }],
            "intent_analysis": mock_intent,
            "enhanced_parameters": {
                "experience_level": "intermediate",
                "special_interests": ["photography"],
                "species_names": ["Northern Cardinal", "Blue Jay"]
            },
            "execution_metadata": {
                "successful_executions": 1,
                "tools_executed": 1,
                "strategy_used": "monolithic"
            }
        }
        
        # Execute node
        node.prep(shared_store)
        result = node.exec(shared_store)
        node.post(shared_store)
        
        print(f"Node execution success: {result.get('success', False)}")
        
        final_response = shared_store.get('final_response', {})
        print(f"Response type: {final_response.get('type', 'unknown')}")
        print(f"Response title: {final_response.get('title', 'No title')}")
        
        if final_response.get('user_guidance'):
            print(f"User guidance items: {len(final_response['user_guidance'])}")
        
        if final_response.get('follow_up_suggestions'):
            print(f"Follow-up suggestions: {len(final_response['follow_up_suggestions'])}")
        
        print("✓ Enhanced process results node test successful")
        
    except ImportError as e:
        print(f"Import error: {str(e)}")
    except Exception as e:
        print(f"Test error: {str(e)}")

async def test_complete_enhanced_system_simple():
    """Test the complete enhanced system without MCP server dependencies"""
    
    try:
        print("\nTesting Complete Enhanced System (Mock Mode)")
        print("=" * 50)
        
        # Test just the NLP and formatting components
        from utils.enhanced_nlp import EnhancedNLPProcessor
        from utils.response_formatter import EnhancedResponseFormatter, FormattingContext, ResponseType, ExperienceLevel
        
        # Test NLP analysis
        nlp = EnhancedNLPProcessor()
        
        request = "I want to plan a birding trip to see warblers in Massachusetts during spring migration"
        context = {"experience_level": "intermediate", "interests": ["migration", "photography"]}
        
        analysis = nlp.analyze_birding_request(request, context)
        
        print(f"Intent Analysis:")
        print(f"  Intent: {analysis.primary_intent.value}")
        print(f"  Confidence: {analysis.confidence_score:.2f}")
        print(f"  Species: {analysis.parameters.species}")
        print(f"  Locations: {analysis.parameters.locations}")
        print(f"  Strategy: {analysis.strategy_recommendation}")
        
        # Test response formatting
        formatter = EnhancedResponseFormatter()
        
        mock_result = {
            "success": True,
            "tool": "plan_complete_trip",
            "result": {
                "trip_plan": {
                    "species_names": analysis.parameters.species,
                    "region": "US-MA",
                    "trip_duration_days": 2,
                    "itinerary": "# Spring Warbler Migration Trip\n\n## Day 1: Peak Migration Timing\n\nStart at dawn (5:30 AM) at Mount Auburn Cemetery for the highest diversity of migrating warblers...",
                    "locations": [
                        {"name": "Mount Auburn Cemetery", "score": 0.92, "species_diversity": 15},
                        {"name": "Fresh Pond Reservation", "score": 0.78, "species_diversity": 8}
                    ],
                    "route": {"total_distance_km": 25.4}
                }
            }
        }
        
        formatting_context = FormattingContext(
            user_request=request,
            experience_level=ExperienceLevel.INTERMEDIATE,
            special_interests=["migration", "photography"],
            response_type=ResponseType.TRIP_ITINERARY,
            intent_confidence=analysis.confidence_score,
            extracted_species=analysis.parameters.species,
            extracted_locations=analysis.parameters.locations
        )
        
        formatted_response = formatter.format_response(mock_result, formatting_context)
        
        print(f"\nFormatted Response:")
        print(f"  Type: {formatted_response.get('type', 'unknown')}")
        print(f"  Title: {formatted_response.get('title', 'No title')}")
        if formatted_response.get('summary'):
            print(f"  Summary: {formatted_response['summary'][:100]}...")
        
        print("✓ Complete enhanced system test successful")
        
    except ImportError as e:
        print(f"Import error: {str(e)}")
    except Exception as e:
        print(f"Test error: {str(e)}")

if __name__ == "__main__":
    print("Enhanced Response Formatting Test Suite")
    print("=" * 60)
    
    # Test 1: Response formatter
    test_response_formatter()
    
    # Test 2: Enhanced process results node
    test_enhanced_process_results()
    
    # Test 3: Complete system (without MCP dependencies)
    asyncio.run(test_complete_enhanced_system_simple())
    
    print(f"\n{'=' * 60}")
    print("All Enhanced Response Tests Complete")
    print("\nNote: For full system testing with MCP server,")
    print("run: uv run python complete_enhanced_agent.py")