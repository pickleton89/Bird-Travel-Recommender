"""
3-Node Agent Orchestration Pattern for Bird Travel Recommender MCP Server

This module implements the agent orchestration pattern that intelligently uses
the 9 MCP tools to provide birding recommendations through a 3-node workflow:

1. DecideBirdingToolNode - Intelligent tool selection and orchestration
2. ExecuteBirdingToolNode - MCP tool execution with error handling  
3. ProcessResultsNode - Result aggregation and response formatting

Based on the design document's 3-node agent pattern with MCP tool integration.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

from pocketflow import Node, BatchNode
from mcp_server import BirdTravelMCPServer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BirdingToolType(Enum):
    """Enumeration of available birding tool types"""
    VALIDATE_SPECIES = "validate_species"
    FETCH_SIGHTINGS = "fetch_sightings"
    FILTER_CONSTRAINTS = "filter_constraints"
    CLUSTER_HOTSPOTS = "cluster_hotspots"
    SCORE_LOCATIONS = "score_locations"
    OPTIMIZE_ROUTE = "optimize_route"
    GENERATE_ITINERARY = "generate_itinerary"
    PLAN_COMPLETE_TRIP = "plan_complete_trip"
    GET_BIRDING_ADVICE = "get_birding_advice"


@dataclass
class ToolExecutionPlan:
    """Represents a plan for executing birding tools"""
    tools: List[Dict[str, Any]]
    strategy: str  # "sequential", "parallel", "monolithic"
    fallback_enabled: bool = True
    max_retries: int = 3


class DecideBirdingToolNode(Node):
    """
    Node 1: Intelligent tool selection and orchestration planning
    
    Analyzes user requests and determines the optimal combination of MCP tools
    to use, with fallback strategies for error recovery.
    """
    
    def __init__(self):
        super().__init__()
        self.name = "DecideBirdingToolNode"
    
    def prep(self, shared_store: Dict[str, Any]) -> None:
        """Prepare tool selection analysis"""
        user_request = shared_store.get("user_request", "")
        logger.info(f"Analyzing user request for tool selection: {user_request[:100]}...")
    
    def exec(self, shared_store: Dict[str, Any]) -> Dict[str, Any]:
        """Execute intelligent tool selection logic"""
        try:
            user_request = shared_store.get("user_request", "")
            context = shared_store.get("context", {})
            
            # Analyze request to determine optimal tool strategy
            execution_plan = self._analyze_request_and_plan_tools(user_request, context)
            
            # Store execution plan for next node
            shared_store["tool_execution_plan"] = execution_plan
            shared_store["tool_selection_metadata"] = {
                "analysis_method": "intelligent_parsing",
                "strategy_selected": execution_plan.strategy,
                "total_tools_planned": len(execution_plan.tools),
                "fallback_enabled": execution_plan.fallback_enabled
            }
            
            logger.info(f"Selected {execution_plan.strategy} strategy with {len(execution_plan.tools)} tools")
            
            return {
                "success": True,
                "execution_plan": execution_plan,
                "strategy": execution_plan.strategy
            }
            
        except Exception as e:
            logger.error(f"Error in tool selection: {str(e)}")
            # Fallback to simple monolithic strategy
            fallback_plan = ToolExecutionPlan(
                tools=[{"name": "get_birding_advice", "params": {"query": user_request}}],
                strategy="monolithic",
                fallback_enabled=True
            )
            shared_store["tool_execution_plan"] = fallback_plan
            shared_store["tool_selection_error"] = str(e)
            
            return {
                "success": True,  # Still successful with fallback
                "execution_plan": fallback_plan,
                "strategy": "fallback",
                "error": str(e)
            }
    
    def post(self, shared_store: Dict[str, Any]) -> None:
        """Post-process tool selection results"""
        plan = shared_store.get("tool_execution_plan")
        if plan:
            logger.info(f"Tool selection complete: {plan.strategy} strategy with {len(plan.tools)} tools")
    
    def _analyze_request_and_plan_tools(self, user_request: str, context: Dict[str, Any]) -> ToolExecutionPlan:
        """
        Analyze user request and create optimal tool execution plan
        
        This method implements intelligent request parsing to determine the best
        combination of MCP tools based on user intent and available context.
        """
        request_lower = user_request.lower()
        
        # Check for complete trip planning requests
        if any(phrase in request_lower for phrase in [
            "plan a trip", "birding trip", "plan my birding", "complete trip",
            "find birds", "where to see", "birding itinerary"
        ]):
            return self._plan_complete_trip_strategy(user_request, context)
        
        # Check for advice-only requests
        elif any(phrase in request_lower for phrase in [
            "advice", "how to", "what equipment", "best time", "when to",
            "where should", "help me", "recommend", "suggest"
        ]):
            return self._plan_advice_strategy(user_request, context)
        
        # Check for specific pipeline component requests
        elif any(phrase in request_lower for phrase in [
            "validate species", "find sightings", "cluster locations",
            "optimize route", "score locations"
        ]):
            return self._plan_component_strategy(user_request, context)
        
        # Default to complete trip planning
        else:
            return self._plan_complete_trip_strategy(user_request, context)
    
    def _plan_complete_trip_strategy(self, user_request: str, context: Dict[str, Any]) -> ToolExecutionPlan:
        """Plan complete trip using monolithic tool with granular fallback"""
        
        # Extract parameters from request and context
        species_names = context.get("species", [])
        region = context.get("region", "")
        start_location = context.get("start_location", {})
        
        # Parse species from user request if not in context
        if not species_names:
            species_names = self._extract_species_from_request(user_request)
        
        # Default region based on common patterns
        if not region:
            region = self._extract_region_from_request(user_request) or "US-MA"
        
        # Default start location if not provided
        if not start_location:
            start_location = {"lat": 42.3601, "lng": -71.0589}  # Boston area default
        
        # Use plan_complete_trip with enhanced parameter mapping
        return ToolExecutionPlan(
            tools=[{
                "name": "plan_complete_trip",
                "params": {
                    "species_names": species_names,
                    "region": region,
                    "start_location": start_location,
                    "max_distance_km": context.get("max_distance_km", 100),
                    "trip_duration_days": context.get("trip_duration_days", 1),
                    "days_back": context.get("days_back", 14)
                }
            }],
            strategy="monolithic",
            fallback_enabled=True
        )
    
    def _plan_advice_strategy(self, user_request: str, context: Dict[str, Any]) -> ToolExecutionPlan:
        """Plan advice-focused response"""
        return ToolExecutionPlan(
            tools=[{
                "name": "get_birding_advice",
                "params": {
                    "query": user_request,
                    "context": context
                }
            }],
            strategy="monolithic",
            fallback_enabled=True
        )
    
    def _plan_component_strategy(self, user_request: str, context: Dict[str, Any]) -> ToolExecutionPlan:
        """Plan specific component execution"""
        request_lower = user_request.lower()
        
        if "validate" in request_lower:
            tool_name = "validate_species"
            params = {"species_names": context.get("species", ["Northern Cardinal"])}
        elif "sightings" in request_lower:
            tool_name = "fetch_sightings"
            params = {
                "validated_species": context.get("validated_species", []),
                "region": context.get("region", "US-MA")
            }
        elif "cluster" in request_lower:
            tool_name = "cluster_hotspots"
            params = {
                "filtered_sightings": context.get("sightings", []),
                "region": context.get("region", "US-MA")
            }
        elif "optimize" in request_lower:
            tool_name = "optimize_route"
            params = {
                "scored_locations": context.get("scored_locations", []),
                "start_location": context.get("start_location", {"lat": 42.3601, "lng": -71.0589})
            }
        else:
            # Default to advice
            tool_name = "get_birding_advice"
            params = {"query": user_request, "context": context}
        
        return ToolExecutionPlan(
            tools=[{"name": tool_name, "params": params}],
            strategy="component",
            fallback_enabled=True
        )
    
    def _extract_species_from_request(self, user_request: str) -> List[str]:
        """Extract bird species names from user request using simple pattern matching"""
        # Common bird species patterns
        species_patterns = [
            "Northern Cardinal", "Blue Jay", "American Robin", "House Sparrow",
            "European Starling", "Red-winged Blackbird", "Common Grackle",
            "Mourning Dove", "American Goldfinch", "House Finch", "Song Sparrow",
            "White-breasted Nuthatch", "Downy Woodpecker", "Cardinals", "cardinal"
        ]
        
        found_species = []
        request_lower = user_request.lower()
        
        for species in species_patterns:
            if species.lower() in request_lower:
                # Map common names to full species names
                if species.lower() in ["cardinal", "cardinals"]:
                    found_species.append("Northern Cardinal")
                else:
                    found_species.append(species)
        
        # Remove duplicates and return
        return list(set(found_species)) if found_species else ["Northern Cardinal"]
    
    def _extract_region_from_request(self, user_request: str) -> Optional[str]:
        """Extract region code from user request using pattern matching"""
        region_patterns = {
            "massachusetts": "US-MA",
            "ma": "US-MA",
            "texas": "US-TX", 
            "tx": "US-TX",
            "california": "US-CA",
            "ca": "US-CA",
            "new york": "US-NY",
            "ny": "US-NY",
            "florida": "US-FL",
            "fl": "US-FL"
        }
        
        request_lower = user_request.lower()
        
        for location, region_code in region_patterns.items():
            if location in request_lower:
                return region_code
        
        return None


class ExecuteBirdingToolNode(BatchNode):
    """
    Node 2: MCP tool execution with error handling and retry logic
    
    Executes the planned tools using the MCP server, with comprehensive
    error handling and fallback strategies.
    """
    
    def __init__(self, mcp_server: BirdTravelMCPServer):
        super().__init__()
        self.name = "ExecuteBirdingToolNode"
        self.mcp_server = mcp_server
    
    def prep(self, shared_store: Dict[str, Any]) -> None:
        """Prepare tool execution"""
        execution_plan = shared_store.get("tool_execution_plan")
        if execution_plan:
            logger.info(f"Preparing to execute {len(execution_plan.tools)} tools using {execution_plan.strategy} strategy")
    
    async def exec(self, shared_store: Dict[str, Any]) -> Dict[str, Any]:
        """Execute planned tools with error handling"""
        try:
            execution_plan = shared_store.get("tool_execution_plan")
            if not execution_plan:
                raise ValueError("No execution plan found in shared store")
            
            # Execute tools based on strategy
            if execution_plan.strategy == "sequential":
                results = await self._execute_sequential(execution_plan.tools)
            elif execution_plan.strategy == "parallel":
                results = await self._execute_parallel(execution_plan.tools)
            else:  # monolithic, component, fallback
                results = await self._execute_monolithic(execution_plan.tools)
            
            # Store results for processing
            shared_store["tool_execution_results"] = results
            shared_store["execution_metadata"] = {
                "strategy_used": execution_plan.strategy,
                "tools_executed": len(execution_plan.tools),
                "successful_executions": sum(1 for r in results if r.get("success", False)),
                "failed_executions": sum(1 for r in results if not r.get("success", False))
            }
            
            logger.info(f"Tool execution complete: {len(results)} results")
            
            return {
                "success": True,
                "results": results,
                "execution_metadata": shared_store["execution_metadata"]
            }
            
        except Exception as e:
            logger.error(f"Error in tool execution: {str(e)}")
            
            # Emergency fallback to advice tool
            fallback_result = await self._execute_fallback_advice(shared_store.get("user_request", ""))
            shared_store["tool_execution_results"] = [fallback_result]
            shared_store["execution_error"] = str(e)
            
            return {
                "success": True,  # Still provide response
                "results": [fallback_result],
                "error": str(e),
                "fallback_used": True
            }
    
    def post(self, shared_store: Dict[str, Any]) -> None:
        """Post-process execution results"""
        results = shared_store.get("tool_execution_results", [])
        metadata = shared_store.get("execution_metadata", {})
        logger.info(f"Execution complete: {metadata.get('successful_executions', 0)} successful, {metadata.get('failed_executions', 0)} failed")
    
    async def _execute_sequential(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute tools sequentially with data flow"""
        results = []
        accumulated_data = {}
        
        for tool_spec in tools:
            try:
                # Update parameters with accumulated data
                params = tool_spec["params"].copy()
                params.update(accumulated_data)
                
                # Execute tool
                result = await self._execute_single_tool(tool_spec["name"], params)
                results.append(result)
                
                # Accumulate successful results for next tool
                if result.get("success", False):
                    accumulated_data.update(self._extract_data_for_next_tool(tool_spec["name"], result))
                
            except Exception as e:
                logger.error(f"Error executing tool {tool_spec['name']}: {str(e)}")
                results.append({
                    "success": False,
                    "error": str(e),
                    "tool": tool_spec["name"]
                })
        
        return results
    
    async def _execute_parallel(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute tools in parallel (for independent tools)"""
        async def execute_all():
            tasks = [
                self._execute_single_tool(tool["name"], tool["params"])
                for tool in tools
            ]
            return await asyncio.gather(*tasks, return_exceptions=True)
        
        results = await execute_all()
        
        # Convert exceptions to error results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "success": False,
                    "error": str(result),
                    "tool": tools[i]["name"]
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _execute_monolithic(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute single tool (monolithic strategy)"""
        if not tools:
            return []
        
        tool_spec = tools[0]  # Should only be one tool for monolithic
        try:
            result = await self._execute_single_tool(tool_spec["name"], tool_spec["params"])
            return [result]
        except Exception as e:
            logger.error(f"Error executing monolithic tool {tool_spec['name']}: {str(e)}")
            return [{
                "success": False,
                "error": str(e),
                "tool": tool_spec["name"]
            }]
    
    async def _execute_single_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single MCP tool with error handling"""
        try:
            # Map tool names to MCP server methods
            tool_handlers = {
                "validate_species": self.mcp_server._handle_validate_species,
                "fetch_sightings": self.mcp_server._handle_fetch_sightings,
                "filter_constraints": self.mcp_server._handle_filter_constraints,
                "cluster_hotspots": self.mcp_server._handle_cluster_hotspots,
                "score_locations": self.mcp_server._handle_score_locations,
                "optimize_route": self.mcp_server._handle_optimize_route,
                "generate_itinerary": self.mcp_server._handle_generate_itinerary,
                "plan_complete_trip": self.mcp_server._handle_plan_complete_trip,
                "get_birding_advice": self.mcp_server._handle_get_birding_advice
            }
            
            handler = tool_handlers.get(tool_name)
            if not handler:
                raise ValueError(f"Unknown tool: {tool_name}")
            
            logger.info(f"Executing tool: {tool_name}")
            result = await handler(**params)
            
            return {
                "success": True,
                "tool": tool_name,
                "result": result,
                "params_used": params
            }
            
        except Exception as e:
            logger.error(f"Tool execution failed for {tool_name}: {str(e)}")
            return {
                "success": False,
                "tool": tool_name,
                "error": str(e),
                "params_attempted": params
            }
    
    async def _execute_fallback_advice(self, user_request: str) -> Dict[str, Any]:
        """Emergency fallback to advice system"""
        try:
            result = await self.mcp_server._handle_get_birding_advice(
                query=user_request or "General birding advice needed"
            )
            return {
                "success": True,
                "tool": "get_birding_advice",
                "result": result,
                "fallback": True
            }
        except Exception as e:
            # Ultimate fallback with static response
            return {
                "success": True,
                "tool": "static_fallback",
                "result": {
                    "advice": "For birding advice and trip planning, please check eBird.org for recent sightings in your area and consult local birding guides.",
                    "fallback_reason": str(e)
                },
                "fallback": True
            }
    
    def _extract_data_for_next_tool(self, tool_name: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant data from tool result for sequential execution"""
        tool_result = result.get("result", {})
        
        if tool_name == "validate_species":
            return {"validated_species": tool_result.get("validated_species", [])}
        elif tool_name == "fetch_sightings":
            return {"sightings": tool_result.get("sightings", [])}
        elif tool_name == "filter_constraints":
            return {"filtered_sightings": tool_result.get("filtered_sightings", [])}
        elif tool_name == "cluster_hotspots":
            return {"hotspot_clusters": tool_result.get("hotspot_clusters", [])}
        elif tool_name == "score_locations":
            return {"scored_locations": tool_result.get("scored_locations", [])}
        elif tool_name == "optimize_route":
            return {"optimized_route": tool_result.get("optimized_route", {})}
        
        return {}


class ProcessResultsNode(Node):
    """
    Node 3: Result aggregation and response formatting
    
    Processes tool execution results and formats them into a coherent
    response for the user, with appropriate fallback handling.
    """
    
    def __init__(self):
        super().__init__()
        self.name = "ProcessResultsNode"
    
    def prep(self, shared_store: Dict[str, Any]) -> None:
        """Prepare result processing"""
        results = shared_store.get("tool_execution_results", [])
        logger.info(f"Preparing to process {len(results)} tool results")
    
    def exec(self, shared_store: Dict[str, Any]) -> Dict[str, Any]:
        """Process and format tool execution results"""
        try:
            results = shared_store.get("tool_execution_results", [])
            execution_plan = shared_store.get("tool_execution_plan")
            metadata = shared_store.get("execution_metadata", {})
            
            # Process results based on strategy and success
            processed_response = self._process_results_by_strategy(results, execution_plan, metadata)
            
            # Store final response
            shared_store["final_response"] = processed_response
            shared_store["processing_metadata"] = {
                "results_processed": len(results),
                "response_type": processed_response.get("type", "unknown"),
                "success_rate": metadata.get("successful_executions", 0) / max(len(results), 1)
            }
            
            logger.info(f"Result processing complete: {processed_response.get('type', 'unknown')} response")
            
            return {
                "success": True,
                "response": processed_response,
                "metadata": shared_store["processing_metadata"]
            }
            
        except Exception as e:
            logger.error(f"Error in result processing: {str(e)}")
            
            # Emergency fallback response
            fallback_response = {
                "type": "error_fallback",
                "message": "I apologize, but I encountered an error processing your birding request. Please try rephrasing your question or check eBird.org for recent birding information in your area.",
                "error": str(e)
            }
            
            shared_store["final_response"] = fallback_response
            shared_store["processing_error"] = str(e)
            
            return {
                "success": True,  # Still provide response
                "response": fallback_response,
                "error": str(e)
            }
    
    def post(self, shared_store: Dict[str, Any]) -> None:
        """Post-process final response"""
        response = shared_store.get("final_response", {})
        logger.info(f"Response processing complete: {response.get('type', 'unknown')} type")
    
    def _process_results_by_strategy(self, results: List[Dict[str, Any]], 
                                   execution_plan: ToolExecutionPlan, 
                                   metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process results based on execution strategy"""
        
        if not results:
            return {
                "type": "no_results",
                "message": "No results were generated. Please try a different approach or check your input parameters."
            }
        
        # Handle single successful result (monolithic, component, advice)
        if len(results) == 1 and results[0].get("success", False):
            return self._format_single_result(results[0])
        
        # Handle sequential/parallel results
        elif execution_plan and execution_plan.strategy in ["sequential", "parallel"]:
            return self._format_multi_result(results, execution_plan.strategy)
        
        # Handle mixed success/failure scenarios
        else:
            return self._format_partial_results(results, metadata)
    
    def _format_single_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format single successful tool result"""
        tool_name = result.get("tool", "unknown")
        tool_result = result.get("result", {})
        
        if tool_name == "plan_complete_trip":
            return {
                "type": "complete_trip_plan",
                "trip_plan": tool_result.get("trip_plan", {}),
                "summary": tool_result.get("summary", {}),
                "message": "Complete birding trip plan generated successfully!"
            }
        
        elif tool_name == "get_birding_advice":
            return {
                "type": "birding_advice",
                "advice": tool_result.get("advice", ""),
                "query": tool_result.get("query", ""),
                "advice_type": tool_result.get("advice_type", "unknown"),
                "message": "Birding advice provided based on your request."
            }
        
        else:
            return {
                "type": "tool_result",
                "tool": tool_name,
                "data": tool_result,
                "message": f"Successfully executed {tool_name} tool."
            }
    
    def _format_multi_result(self, results: List[Dict[str, Any]], strategy: str) -> Dict[str, Any]:
        """Format multiple tool results from sequential/parallel execution"""
        successful_results = [r for r in results if r.get("success", False)]
        failed_results = [r for r in results if not r.get("success", False)]
        
        return {
            "type": "multi_tool_results",
            "strategy": strategy,
            "successful_tools": len(successful_results),
            "failed_tools": len(failed_results),
            "results": {
                "successful": successful_results,
                "failed": failed_results
            },
            "message": f"Executed {len(results)} tools using {strategy} strategy. {len(successful_results)} succeeded, {len(failed_results)} failed."
        }
    
    def _format_partial_results(self, results: List[Dict[str, Any]], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Format partial results with fallback handling"""
        successful_results = [r for r in results if r.get("success", False)]
        
        if successful_results:
            # Use the best available result
            best_result = successful_results[0]
            return {
                "type": "partial_success",
                "primary_result": self._format_single_result(best_result),
                "total_attempts": len(results),
                "successful_attempts": len(successful_results),
                "message": f"Partial success: {len(successful_results)} of {len(results)} tools succeeded."
            }
        else:
            return {
                "type": "all_failed",
                "errors": [r.get("error", "Unknown error") for r in results],
                "message": "All tool executions failed. Please try rephrasing your request or check your input parameters."
            }


def create_agent_flow(mcp_server: BirdTravelMCPServer) -> List[Node]:
    """
    Create the 3-node agent orchestration flow
    
    Returns a list of nodes that can be used with PocketFlow for agent execution
    """
    return [
        DecideBirdingToolNode(),
        ExecuteBirdingToolNode(mcp_server),
        ProcessResultsNode()
    ]


# Convenience function for standalone execution
async def execute_agent_request(user_request: str, context: Dict[str, Any] = None, 
                              mcp_server: BirdTravelMCPServer = None) -> Dict[str, Any]:
    """
    Execute a birding request through the 3-node agent pattern
    
    Args:
        user_request: User's birding request or question
        context: Optional context (species, location, etc.)
        mcp_server: MCP server instance (creates new if None)
    
    Returns:
        Final processed response
    """
    if mcp_server is None:
        mcp_server = BirdTravelMCPServer()
    
    # Create shared store
    shared_store = {
        "user_request": user_request,
        "context": context or {}
    }
    
    # Create and execute agent flow
    nodes = create_agent_flow(mcp_server)
    
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
            logger.error(f"Error in node {node.name}: {str(e)}")
            shared_store["node_error"] = str(e)
            break
    
    return shared_store.get("final_response", {
        "type": "execution_error",
        "message": "Agent execution failed. Please try again.",
        "error": shared_store.get("node_error", "Unknown error")
    })


if __name__ == "__main__":
    # Test the agent pattern
    async def test_agent():
        request = "Plan a birding trip to see Northern Cardinals in Massachusetts"
        context = {
            "species": ["Northern Cardinal"],
            "region": "US-MA",
            "start_location": {"lat": 42.3601, "lng": -71.0589}
        }
        
        response = await execute_agent_request(request, context)
        print(json.dumps(response, indent=2))
    
    asyncio.run(test_agent())