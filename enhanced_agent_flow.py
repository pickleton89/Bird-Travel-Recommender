"""
Enhanced 3-Node Agent Orchestration Pattern with LLM-Powered NLP

This module implements an enhanced version of the agent orchestration pattern
with improved natural language processing using LLM for intent classification
and parameter extraction.

Enhanced Features:
- LLM-powered intent understanding
- Semantic parameter extraction
- Context-aware conversation handling
- Improved tool selection logic
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

from pocketflow import Node, BatchNode
from mcp_server import BirdTravelMCPServer

# Import enhanced NLP components
from utils.enhanced_nlp import (
    EnhancedNLPProcessor, 
    IntentAnalysis, 
    BirdingIntent
)

# Import existing components
from agent_flow import (
    BirdingToolType,
    ExecuteBirdingToolNode,
    ProcessResultsNode
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EnhancedToolExecutionPlan:
    """Enhanced tool execution plan with NLP analysis"""
    tools: List[Dict[str, Any]]
    strategy: str  # "sequential", "parallel", "monolithic"
    intent_analysis: IntentAnalysis
    confidence_score: float
    fallback_enabled: bool = True
    max_retries: int = 3


class EnhancedDecideBirdingToolNode(Node):
    """
    Enhanced Node 1: LLM-Powered Tool Selection and Orchestration
    
    Uses advanced NLP to understand user intent and extract parameters
    semantically, with improved tool selection based on birding expertise.
    """
    
    def __init__(self):
        super().__init__()
        self.name = "EnhancedDecideBirdingToolNode"
        self.nlp_processor = EnhancedNLPProcessor()
        
    def prep(self, shared_store: Dict[str, Any]) -> None:
        """Prepare enhanced tool selection analysis"""
        user_request = shared_store.get("user_request", "")
        context = shared_store.get("context", {})
        logger.info(f"Enhanced NLP analysis for request: {user_request[:100]}...")
        
        # Add conversation history if available
        if "conversation_history" in shared_store:
            context["conversation_history"] = shared_store["conversation_history"]
    
    def exec(self, shared_store: Dict[str, Any]) -> Dict[str, Any]:
        """Execute enhanced intelligent tool selection with LLM analysis"""
        try:
            user_request = shared_store.get("user_request", "")
            context = shared_store.get("context", {})
            
            # Step 1: LLM-powered intent analysis and parameter extraction
            intent_analysis = self.nlp_processor.analyze_birding_request(user_request, context)
            
            # Step 2: Create enhanced execution plan based on intent analysis
            execution_plan = self._create_execution_plan_from_intent(intent_analysis, user_request, context)
            
            # Step 3: Store comprehensive results
            shared_store["tool_execution_plan"] = execution_plan
            shared_store["intent_analysis"] = intent_analysis
            shared_store["enhanced_parameters"] = self.nlp_processor.get_enhanced_parameters_for_tool(
                intent_analysis, context
            )
            shared_store["tool_selection_metadata"] = {
                "analysis_method": "llm_enhanced_nlp",
                "primary_intent": intent_analysis.primary_intent.value,
                "confidence_score": intent_analysis.confidence_score,
                "strategy_selected": execution_plan.strategy,
                "total_tools_planned": len(execution_plan.tools),
                "parameters_extracted": len([p for p in [
                    intent_analysis.parameters.species,
                    intent_analysis.parameters.locations,
                    intent_analysis.parameters.timeframes
                ] if p]),
                "fallback_enabled": execution_plan.fallback_enabled
            }
            
            logger.info(f"Enhanced analysis complete - Intent: {intent_analysis.primary_intent.value}, "
                       f"Strategy: {execution_plan.strategy}, Confidence: {intent_analysis.confidence_score:.2f}")
            
            return {
                "success": True,
                "execution_plan": execution_plan,
                "intent_analysis": intent_analysis,
                "strategy": execution_plan.strategy,
                "confidence": intent_analysis.confidence_score
            }
            
        except Exception as e:
            logger.error(f"Error in enhanced tool selection: {str(e)}")
            
            # Enhanced fallback with NLP processor fallback
            try:
                fallback_analysis = self.nlp_processor._fallback_rule_based_analysis(user_request, context)
                fallback_plan = self._create_simple_fallback_plan(user_request, fallback_analysis)
            except Exception as fallback_error:
                logger.error(f"Fallback analysis also failed: {str(fallback_error)}")
                fallback_plan = self._create_emergency_fallback_plan(user_request)
            
            shared_store["tool_execution_plan"] = fallback_plan
            shared_store["tool_selection_error"] = str(e)
            
            return {
                "success": True,  # Still provide response
                "execution_plan": fallback_plan,
                "strategy": "emergency_fallback",
                "error": str(e)
            }
    
    def post(self, shared_store: Dict[str, Any]) -> None:
        """Post-process enhanced tool selection results"""
        plan = shared_store.get("tool_execution_plan")
        intent_analysis = shared_store.get("intent_analysis")
        
        if plan and intent_analysis:
            logger.info(f"Enhanced tool selection complete - Intent: {intent_analysis.primary_intent.value}, "
                       f"Strategy: {plan.strategy}, Tools: {len(plan.tools)}")
    
    def _create_execution_plan_from_intent(self, intent_analysis: IntentAnalysis, 
                                         user_request: str, context: Dict[str, Any]) -> EnhancedToolExecutionPlan:
        """
        Create execution plan based on LLM intent analysis
        
        Uses sophisticated intent understanding to determine optimal tool strategy
        """
        primary_intent = intent_analysis.primary_intent
        parameters = intent_analysis.parameters
        confidence = intent_analysis.confidence_score
        
        # Get enhanced parameters for tools
        enhanced_params = self.nlp_processor.get_enhanced_parameters_for_tool(intent_analysis, context)
        
        # Intent-based strategy selection with enhanced logic
        if primary_intent == BirdingIntent.COMPLETE_TRIP_PLANNING:
            if confidence > 0.7 and parameters.species and parameters.locations:
                # High confidence complete trip planning - use full pipeline
                execution_plan = self._create_complete_trip_plan(enhanced_params, intent_analysis)
            else:
                # Lower confidence or missing parameters - use monolithic with error handling
                execution_plan = self._create_monolithic_trip_plan(enhanced_params, intent_analysis)
        
        elif primary_intent in [BirdingIntent.SPECIES_ADVICE, BirdingIntent.TIMING_ADVICE, 
                               BirdingIntent.EQUIPMENT_ADVICE, BirdingIntent.TECHNIQUE_ADVICE]:
            execution_plan = self._create_advice_plan(enhanced_params, intent_analysis)
        
        elif primary_intent == BirdingIntent.LOCATION_DISCOVERY:
            execution_plan = self._create_location_discovery_plan(enhanced_params, intent_analysis)
        
        elif primary_intent == BirdingIntent.QUICK_LOOKUP:
            execution_plan = self._create_quick_lookup_plan(enhanced_params, intent_analysis)
        
        elif primary_intent == BirdingIntent.ROUTE_OPTIMIZATION:
            execution_plan = self._create_route_optimization_plan(enhanced_params, intent_analysis)
        
        else:  # GENERAL_ADVICE or unknown
            execution_plan = self._create_general_advice_plan(enhanced_params, intent_analysis)
        
        return execution_plan
    
    def _create_complete_trip_plan(self, params: Dict[str, Any], 
                                 intent_analysis: IntentAnalysis) -> EnhancedToolExecutionPlan:
        """Create comprehensive trip planning execution plan"""
        
        # Check if we should use sequential granular approach or monolithic
        if (len(intent_analysis.parameters.species) > 3 or 
            intent_analysis.parameters.duration_days and intent_analysis.parameters.duration_days > 2):
            # Complex trip - use sequential approach for better control
            tools = [
                {"name": "validate_species", "params": {"species_names": params["species_names"]}},
                {"name": "fetch_sightings", "params": {
                    "region": params["region"], 
                    "days_back": 14,
                    "validated_species": "from_previous_step"
                }},
                {"name": "filter_constraints", "params": {
                    "start_location": params["start_location"],
                    "max_distance_km": params["max_distance_km"],
                    "sightings": "from_previous_step"
                }},
                {"name": "cluster_hotspots", "params": {
                    "region": params["region"],
                    "filtered_sightings": "from_previous_step"
                }},
                {"name": "score_locations", "params": {
                    "target_species": params["species_names"],
                    "hotspot_clusters": "from_previous_step"
                }},
                {"name": "optimize_route", "params": {
                    "start_location": params["start_location"],
                    "scored_locations": "from_previous_step"
                }},
                {"name": "generate_itinerary", "params": {
                    "target_species": params["species_names"],
                    "trip_duration_days": params["trip_duration_days"],
                    "optimized_route": "from_previous_step"
                }}
            ]
            strategy = "sequential"
        else:
            # Simple trip - use monolithic approach
            tools = [{"name": "plan_complete_trip", "params": params}]
            strategy = "monolithic"
        
        return EnhancedToolExecutionPlan(
            tools=tools,
            strategy=strategy,
            intent_analysis=intent_analysis,
            confidence_score=intent_analysis.confidence_score,
            fallback_enabled=True
        )
    
    def _create_monolithic_trip_plan(self, params: Dict[str, Any], 
                                   intent_analysis: IntentAnalysis) -> EnhancedToolExecutionPlan:
        """Create simple monolithic trip plan for lower confidence scenarios"""
        return EnhancedToolExecutionPlan(
            tools=[{"name": "plan_complete_trip", "params": params}],
            strategy="monolithic",
            intent_analysis=intent_analysis,
            confidence_score=intent_analysis.confidence_score,
            fallback_enabled=True
        )
    
    def _create_advice_plan(self, params: Dict[str, Any], 
                          intent_analysis: IntentAnalysis) -> EnhancedToolExecutionPlan:
        """Create advice-focused execution plan"""
        
        # Enhance query with extracted context
        enhanced_query = self._enhance_advice_query(intent_analysis)
        
        return EnhancedToolExecutionPlan(
            tools=[{
                "name": "get_birding_advice",
                "params": {
                    "query": enhanced_query,
                    "context": {
                        "species": params.get("species_names", []),
                        "location": params.get("region", ""),
                        "experience_level": params.get("experience_level", "intermediate"),
                        "special_interests": params.get("special_interests", []),
                        "season": params.get("season", ""),
                        "timeframes": params.get("timeframes", [])
                    }
                }
            }],
            strategy="monolithic",
            intent_analysis=intent_analysis,
            confidence_score=intent_analysis.confidence_score,
            fallback_enabled=True
        )
    
    def _create_location_discovery_plan(self, params: Dict[str, Any], 
                                      intent_analysis: IntentAnalysis) -> EnhancedToolExecutionPlan:
        """Create location discovery execution plan"""
        
        if intent_analysis.parameters.species:
            # Species-specific location discovery
            tools = [
                {"name": "validate_species", "params": {"species_names": params["species_names"]}},
                {"name": "fetch_sightings", "params": {
                    "region": params["region"],
                    "days_back": 14,
                    "validated_species": "from_previous_step"
                }},
                {"name": "cluster_hotspots", "params": {
                    "region": params["region"],
                    "filtered_sightings": "from_previous_step"
                }}
            ]
            strategy = "sequential"
        else:
            # General location discovery
            tools = [{"name": "get_birding_advice", "params": {
                "query": f"Best birding locations in {params.get('region', 'your area')}",
                "context": params
            }}]
            strategy = "monolithic"
        
        return EnhancedToolExecutionPlan(
            tools=tools,
            strategy=strategy,
            intent_analysis=intent_analysis,
            confidence_score=intent_analysis.confidence_score,
            fallback_enabled=True
        )
    
    def _create_quick_lookup_plan(self, params: Dict[str, Any], 
                                intent_analysis: IntentAnalysis) -> EnhancedToolExecutionPlan:
        """Create quick lookup execution plan"""
        
        if intent_analysis.parameters.species:
            # Species-specific sightings lookup
            tools = [
                {"name": "validate_species", "params": {"species_names": params["species_names"]}},
                {"name": "fetch_sightings", "params": {
                    "region": params["region"],
                    "days_back": 7,  # Shorter timeframe for quick lookup
                    "validated_species": "from_previous_step"
                }}
            ]
            strategy = "sequential"
        else:
            # General quick advice
            tools = [{"name": "get_birding_advice", "params": {
                "query": intent_analysis.reasoning,  # Use original reasoning as query
                "context": params
            }}]
            strategy = "monolithic"
        
        return EnhancedToolExecutionPlan(
            tools=tools,
            strategy=strategy,
            intent_analysis=intent_analysis,
            confidence_score=intent_analysis.confidence_score,
            fallback_enabled=True
        )
    
    def _create_route_optimization_plan(self, params: Dict[str, Any], 
                                      intent_analysis: IntentAnalysis) -> EnhancedToolExecutionPlan:
        """Create route optimization execution plan"""
        
        # Route optimization requires locations - if we don't have them, get them first
        if not intent_analysis.parameters.locations and intent_analysis.parameters.species:
            tools = [
                {"name": "validate_species", "params": {"species_names": params["species_names"]}},
                {"name": "fetch_sightings", "params": {
                    "region": params["region"],
                    "days_back": 14,
                    "validated_species": "from_previous_step"
                }},
                {"name": "cluster_hotspots", "params": {
                    "region": params["region"],
                    "filtered_sightings": "from_previous_step"
                }},
                {"name": "optimize_route", "params": {
                    "start_location": params["start_location"],
                    "scored_locations": "from_previous_step"
                }}
            ]
            strategy = "sequential"
        else:
            # Direct route optimization advice
            tools = [{"name": "get_birding_advice", "params": {
                "query": f"Optimize route for birding trip visiting {', '.join(intent_analysis.parameters.locations)}",
                "context": params
            }}]
            strategy = "monolithic"
        
        return EnhancedToolExecutionPlan(
            tools=tools,
            strategy=strategy,
            intent_analysis=intent_analysis,
            confidence_score=intent_analysis.confidence_score,
            fallback_enabled=True
        )
    
    def _create_general_advice_plan(self, params: Dict[str, Any], 
                                  intent_analysis: IntentAnalysis) -> EnhancedToolExecutionPlan:
        """Create general advice execution plan"""
        
        enhanced_query = self._enhance_advice_query(intent_analysis)
        
        return EnhancedToolExecutionPlan(
            tools=[{
                "name": "get_birding_advice",
                "params": {
                    "query": enhanced_query,
                    "context": params
                }
            }],
            strategy="monolithic",
            intent_analysis=intent_analysis,
            confidence_score=intent_analysis.confidence_score,
            fallback_enabled=True
        )
    
    def _enhance_advice_query(self, intent_analysis: IntentAnalysis) -> str:
        """Enhance advice query with extracted context"""
        base_query = intent_analysis.reasoning
        params = intent_analysis.parameters
        
        # Add extracted context to make query more specific
        context_parts = []
        
        if params.species:
            context_parts.append(f"for {', '.join(params.species)}")
        
        if params.locations:
            context_parts.append(f"in {', '.join(params.locations)}")
        
        if params.season:
            context_parts.append(f"during {params.season}")
        
        if params.experience_level:
            context_parts.append(f"for {params.experience_level} birder")
        
        if params.special_interests:
            context_parts.append(f"focusing on {', '.join(params.special_interests)}")
        
        if context_parts:
            enhanced_query = f"{base_query} {' '.join(context_parts)}"
        else:
            enhanced_query = base_query
        
        return enhanced_query
    
    def _create_simple_fallback_plan(self, user_request: str, 
                                   fallback_analysis: IntentAnalysis) -> EnhancedToolExecutionPlan:
        """Create simple fallback plan using rule-based analysis"""
        return EnhancedToolExecutionPlan(
            tools=[{"name": "get_birding_advice", "params": {"query": user_request}}],
            strategy="fallback",
            intent_analysis=fallback_analysis,
            confidence_score=0.3,
            fallback_enabled=True
        )
    
    def _create_emergency_fallback_plan(self, user_request: str) -> EnhancedToolExecutionPlan:
        """Create emergency fallback plan when all analysis fails"""
        from utils.enhanced_nlp import BirdingIntent, ExtractedParameters, IntentAnalysis
        
        emergency_analysis = IntentAnalysis(
            primary_intent=BirdingIntent.GENERAL_ADVICE,
            secondary_intents=[],
            parameters=ExtractedParameters(
                species=[], locations=[], region_codes=[], coordinates=[],
                timeframes=[], duration_days=None, max_distance_km=None,
                experience_level=None, special_interests=[], season=None,
                confidence_score=0.1
            ),
            strategy_recommendation="emergency",
            confidence_score=0.1,
            reasoning="Emergency fallback due to analysis failure"
        )
        
        return EnhancedToolExecutionPlan(
            tools=[{"name": "get_birding_advice", "params": {"query": user_request}}],
            strategy="emergency",
            intent_analysis=emergency_analysis,
            confidence_score=0.1,
            fallback_enabled=True
        )


def create_enhanced_agent_flow(mcp_server: BirdTravelMCPServer) -> List[Node]:
    """
    Create the enhanced 3-node agent orchestration flow with improved NLP
    
    Returns a list of nodes that can be used with PocketFlow for enhanced agent execution
    """
    return [
        EnhancedDecideBirdingToolNode(),
        ExecuteBirdingToolNode(mcp_server),  # Reuse existing execution node
        ProcessResultsNode()  # Reuse existing processing node
    ]


# Convenience function for standalone execution with enhanced NLP
async def execute_enhanced_agent_request(user_request: str, context: Dict[str, Any] = None, 
                                       mcp_server: BirdTravelMCPServer = None) -> Dict[str, Any]:
    """
    Execute a birding request through the enhanced 3-node agent pattern
    
    Args:
        user_request: User's birding request or question
        context: Optional context (conversation history, preferences, etc.)
        mcp_server: MCP server instance (creates new if None)
    
    Returns:
        Final processed response with enhanced NLP analysis
    """
    if mcp_server is None:
        mcp_server = BirdTravelMCPServer()
    
    # Create shared store with enhanced context
    shared_store = {
        "user_request": user_request,
        "context": context or {},
        "conversation_history": context.get("conversation_history", []) if context else []
    }
    
    # Create and execute enhanced agent flow
    nodes = create_enhanced_agent_flow(mcp_server)
    
    # Execute each node in sequence
    for node in nodes:
        try:
            node.prep(shared_store)
            if isinstance(node, ExecuteBirdingToolNode):
                result = await node.exec(shared_store)
            else:
                result = node.exec(shared_store)
            node.post(shared_store)
            
            if not result.get("success", False) and not shared_store.get("final_response"):
                # Early termination if critical failure
                break
                
        except Exception as e:
            logger.error(f"Error in enhanced node {node.name}: {str(e)}")
            shared_store["node_error"] = str(e)
            break
    
    # Add enhanced metadata to response
    final_response = shared_store.get("final_response", {
        "type": "execution_error",
        "message": "Enhanced agent execution failed. Please try again.",
        "error": shared_store.get("node_error", "Unknown error")
    })
    
    # Include NLP analysis in response if available
    if "intent_analysis" in shared_store:
        final_response["nlp_analysis"] = {
            "intent": shared_store["intent_analysis"].primary_intent.value,
            "confidence": shared_store["intent_analysis"].confidence_score,
            "extracted_species": shared_store["intent_analysis"].parameters.species,
            "extracted_locations": shared_store["intent_analysis"].parameters.locations,
            "analysis_method": "llm_enhanced"
        }
    
    return final_response


if __name__ == "__main__":
    # Test the enhanced agent pattern
    async def test_enhanced_agent():
        request = "I'd love to plan a birding trip to see some warblers and cardinals around the Boston area next weekend"
        context = {
            "default_coordinates": {"lat": 42.3601, "lng": -71.0589},
            "user_preferences": {"experience_level": "intermediate", "interests": ["migration", "photography"]}
        }
        
        response = await execute_enhanced_agent_request(request, context)
        print("Enhanced Agent Response:")
        print(json.dumps(response, indent=2))
    
    asyncio.run(test_enhanced_agent())