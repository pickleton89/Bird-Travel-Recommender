"""
Complete Enhanced Agent Flow with Advanced NLP and Response Formatting

This module combines the enhanced NLP processing with advanced response formatting
to create a sophisticated birding assistant that understands user intent and
provides beautifully formatted, contextual responses.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union

from pocketflow import Node, BatchNode

# Import enhanced components
from enhanced_agent_flow import EnhancedDecideBirdingToolNode, EnhancedToolExecutionPlan
from agent_flow import ExecuteBirdingToolNode  # Reuse existing execution node
from enhanced_process_results import EnhancedProcessResultsNode
from mcp_server import BirdTravelMCPServer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_complete_enhanced_agent_flow(mcp_server: BirdTravelMCPServer) -> List[Node]:
    """
    Create the complete enhanced 3-node agent flow with advanced NLP and formatting
    
    Returns a list of nodes with:
    1. Enhanced NLP-powered tool selection
    2. Robust tool execution (reused from original)
    3. Advanced response formatting with user-centric language
    """
    return [
        EnhancedDecideBirdingToolNode(),  # Enhanced NLP analysis
        ExecuteBirdingToolNode(mcp_server),  # Proven tool execution
        EnhancedProcessResultsNode()  # Advanced response formatting
    ]


async def execute_complete_enhanced_agent(user_request: str, 
                                        context: Dict[str, Any] = None,
                                        mcp_server: BirdTravelMCPServer = None) -> Dict[str, Any]:
    """
    Execute a birding request through the complete enhanced agent pattern
    
    This function provides the full enhanced experience:
    - LLM-powered intent classification and parameter extraction
    - Intelligent tool selection and execution
    - User-friendly response formatting with appropriate language complexity
    
    Args:
        user_request: User's birding request or question
        context: Optional context (experience level, interests, location preferences, etc.)
        mcp_server: MCP server instance (creates new if None)
    
    Returns:
        Beautifully formatted response with user guidance and follow-up suggestions
    """
    if mcp_server is None:
        mcp_server = BirdTravelMCPServer()
    
    # Create enhanced shared store with comprehensive context
    shared_store = {
        "user_request": user_request,
        "context": context or {},
        "conversation_history": context.get("conversation_history", []) if context else [],
        "user_preferences": context.get("user_preferences", {}) if context else {}
    }
    
    # Add default context if not provided
    if not shared_store["context"].get("experience_level"):
        shared_store["context"]["experience_level"] = "intermediate"
    
    if not shared_store["context"].get("default_coordinates"):
        shared_store["context"]["default_coordinates"] = {"lat": 42.3601, "lng": -71.0589}  # Boston area
    
    # Create and execute complete enhanced agent flow
    nodes = create_complete_enhanced_agent_flow(mcp_server)
    
    # Execute each node with comprehensive error handling
    for i, node in enumerate(nodes):
        try:
            logger.info(f"Executing enhanced node {i+1}/3: {node.name}")
            
            node.prep(shared_store)
            
            if isinstance(node, ExecuteBirdingToolNode):
                # Async execution for tool node
                result = await node.exec(shared_store)
            else:
                # Sync execution for analysis and formatting nodes
                result = node.exec(shared_store)
            
            node.post(shared_store)
            
            # Check for critical failures
            if not result.get("success", False) and not shared_store.get("final_response"):
                logger.warning(f"Node {node.name} reported failure, but continuing with fallback")
                # Continue processing - enhanced nodes have robust fallback handling
                
        except Exception as e:
            logger.error(f"Error in enhanced node {node.name}: {str(e)}")
            shared_store["node_error"] = str(e)
            shared_store["failed_node"] = node.name
            
            # Enhanced error recovery - try to continue with partial results
            if not shared_store.get("final_response"):
                # Create emergency response if no other response exists
                shared_store["final_response"] = _create_emergency_response(
                    user_request, str(e), node.name
                )
            break
    
    # Get final response with enhanced metadata
    final_response = shared_store.get("final_response", {
        "type": "execution_error",
        "title": "Birding Assistant Error",
        "message": "I encountered an error while processing your birding request.",
        "error": shared_store.get("node_error", "Unknown error"),
        "user_guidance": [
            "Try rephrasing your request with more specific details",
            "Check that species names and locations are spelled correctly",
            "Consider asking for a different type of birding information"
        ]
    })
    
    # Add comprehensive metadata about the enhanced processing
    final_response["processing_metadata"] = {
        "enhanced_nlp_used": "intent_analysis" in shared_store,
        "response_formatting_used": "EnhancedProcessResultsNode",
        "nodes_executed": len([n for n in nodes if shared_store.get(f"{n.name}_completed", False)]),
        "total_nodes": len(nodes),
        "execution_timestamp": "now",  # Would use actual timestamp in production
        "user_context": {
            "experience_level": shared_store["context"].get("experience_level", "unknown"),
            "has_conversation_history": len(shared_store.get("conversation_history", [])) > 0,
            "has_preferences": len(shared_store.get("user_preferences", {})) > 0
        }
    }
    
    # Include NLP analysis if available (for debugging/advanced users)
    if "intent_analysis" in shared_store:
        final_response["nlp_analysis"] = {
            "detected_intent": shared_store["intent_analysis"].primary_intent.value,
            "confidence": shared_store["intent_analysis"].confidence_score,
            "extracted_species": shared_store["intent_analysis"].parameters.species,
            "extracted_locations": shared_store["intent_analysis"].parameters.locations,
            "strategy_used": shared_store.get("tool_execution_plan", {}).get("strategy", "unknown")
        }
    
    logger.info("Complete enhanced agent execution finished")
    return final_response


def _create_emergency_response(user_request: str, error: str, failed_node: str) -> Dict[str, Any]:
    """Create emergency response when all else fails"""
    
    return {
        "type": "emergency_fallback",
        "title": "Birding Assistant - Service Issue",
        "message": "I'm experiencing a technical issue, but I'm here to help with your birding needs.",
        "user_request": user_request,
        "error_context": f"Error in {failed_node}: {error}",
        "immediate_suggestions": [
            "🔄 Try a simpler request like 'recent bird sightings near [your city]'",
            "📍 Provide specific location details (city, state, or coordinates)",
            "🐦 Ask about common bird species in your area",
            "❓ Request general birding advice or equipment recommendations"
        ],
        "alternative_resources": [
            "Check eBird.org for recent sightings in your area",
            "Use the Merlin Bird ID app for species identification",
            "Contact local birding groups or Audubon chapters",
            "Visit nearby nature centers for current bird activity"
        ],
        "system_status": "Experiencing technical difficulties - please try again shortly"
    }


# Test function for the complete enhanced system
async def test_complete_enhanced_system():
    """Test the complete enhanced system with various scenarios"""
    
    test_cases = [
        {
            "request": "I want to plan a 2-day birding trip around Boston to see cardinals and warblers",
            "context": {
                "experience_level": "intermediate",
                "special_interests": ["photography", "migration"],
                "user_preferences": {"max_distance": 150, "preferred_time": "early_morning"}
            }
        },
        {
            "request": "What equipment do I need for hawk watching as a beginner?",
            "context": {
                "experience_level": "beginner",
                "special_interests": ["equipment", "raptors"]
            }
        },
        {
            "request": "Recent cardinal sightings near Boston",
            "context": {
                "experience_level": "expert",
                "special_interests": ["citizen_science", "data_analysis"]
            }
        }
    ]
    
    print("Testing Complete Enhanced Agent System")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print(f"Request: {test_case['request']}")
        print(f"Context: {test_case['context']}")
        print("-" * 40)
        
        try:
            response = await execute_complete_enhanced_agent(
                test_case['request'], 
                test_case['context']
            )
            
            print(f"Response Type: {response.get('type', 'unknown')}")
            print(f"Title: {response.get('title', 'No title')}")
            
            if response.get('nlp_analysis'):
                nlp = response['nlp_analysis']
                print(f"Detected Intent: {nlp.get('detected_intent', 'unknown')}")
                print(f"Confidence: {nlp.get('confidence', 0):.2f}")
                print(f"Strategy: {nlp.get('strategy_used', 'unknown')}")
            
            if response.get('user_guidance'):
                print(f"User Guidance: {len(response['user_guidance'])} items")
            
            if response.get('follow_up_suggestions'):
                print(f"Follow-up Suggestions: {len(response['follow_up_suggestions'])} items")
            
            print("✓ Test completed successfully")
            
        except Exception as e:
            print(f"✗ Test failed: {str(e)}")


if __name__ == "__main__":
    # Run test of complete enhanced system
    asyncio.run(test_complete_enhanced_system())


# Export main functions for easy import
__all__ = [
    'create_complete_enhanced_agent_flow',
    'execute_complete_enhanced_agent',
    'test_complete_enhanced_system'
]