#!/usr/bin/env python3
"""
Bird Travel Recommender MCP Server

This MCP server provides 9 birding tools that integrate with the eBird API
and our advanced birding pipeline to help users plan birding trips.

Based on proven patterns from moonbirdai/ebird-mcp-server with enhancements
for comprehensive birding travel planning.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Sequence

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import (
    CallToolRequest, 
    CallToolResult,
    ListToolsRequest,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)
import mcp.types as types

# Import our existing birding pipeline components
from ..utils.ebird_api import EBirdClient
from nodes import (
    ValidateSpeciesNode, 
    FetchSightingsNode, 
    FilterConstraintsNode,
    ClusterHotspotsNode,
    ScoreLocationsNode,
    OptimizeRouteNode,
    GenerateItineraryNode
)
from ..utils.route_optimizer import optimize_birding_route
from ..utils.geo_utils import haversine_distance

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BirdTravelMCPServer:
    """
    MCP Server for Bird Travel Recommendations
    
    Provides 9 tools:
    - 7 Core eBird Tools: validate_species, fetch_sightings, filter_constraints, 
      cluster_hotspots, score_locations, optimize_route, generate_itinerary
    - 2 Business Logic Tools: plan_complete_trip, get_birding_advice
    """
    
    def __init__(self):
        self.server = Server("bird-travel-recommender")
        self.ebird_api = EBirdClient()
        
        # Initialize pipeline nodes
        self.validate_species_node = ValidateSpeciesNode()
        self.fetch_sightings_node = FetchSightingsNode()
        self.filter_constraints_node = FilterConstraintsNode()
        self.cluster_hotspots_node = ClusterHotspotsNode()
        self.score_locations_node = ScoreLocationsNode()
        self.optimize_route_node = OptimizeRouteNode()
        self.generate_itinerary_node = GenerateItineraryNode()
        
        # Register MCP handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all MCP server handlers"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List all available birding tools"""
            return [
                # Core eBird Tools
                Tool(
                    name="validate_species",
                    description="Validate bird species names using eBird taxonomy with LLM fallback for fuzzy matching",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "species_names": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of bird species names to validate"
                            }
                        },
                        "required": ["species_names"]
                    }
                ),
                Tool(
                    name="fetch_sightings",
                    description="Fetch recent bird sightings using parallel eBird API queries with smart endpoint selection",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "validated_species": {
                                "type": "array",
                                "description": "List of validated species from validate_species tool"
                            },
                            "region": {
                                "type": "string",
                                "description": "Region code (e.g., 'US-MA', 'CA-ON') or location name"
                            },
                            "days_back": {
                                "type": "integer",
                                "description": "Number of days to look back for sightings (1-30)",
                                "default": 14
                            }
                        },
                        "required": ["validated_species", "region"]
                    }
                ),
                Tool(
                    name="filter_constraints",
                    description="Apply geographic and temporal constraints to sightings using enrichment-in-place strategy",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "sightings": {
                                "type": "array",
                                "description": "Sightings data from fetch_sightings tool"
                            },
                            "start_location": {
                                "type": "object",
                                "properties": {
                                    "lat": {"type": "number"},
                                    "lng": {"type": "number"}
                                },
                                "required": ["lat", "lng"],
                                "description": "Starting location coordinates"
                            },
                            "max_distance_km": {
                                "type": "number",
                                "description": "Maximum travel distance in kilometers",
                                "default": 100
                            },
                            "date_range": {
                                "type": "object",
                                "properties": {
                                    "start": {"type": "string", "format": "date"},
                                    "end": {"type": "string", "format": "date"}
                                },
                                "description": "Optional date range filter"
                            }
                        },
                        "required": ["sightings", "start_location"]
                    }
                ),
                Tool(
                    name="cluster_hotspots",
                    description="Cluster birding locations and integrate with eBird hotspots using dual discovery methods",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "filtered_sightings": {
                                "type": "array",
                                "description": "Filtered sightings from filter_constraints tool"
                            },
                            "region": {
                                "type": "string",
                                "description": "Region code for hotspot discovery"
                            },
                            "cluster_radius_km": {
                                "type": "number",
                                "description": "Clustering radius in kilometers",
                                "default": 15
                            }
                        },
                        "required": ["filtered_sightings", "region"]
                    }
                ),
                Tool(
                    name="score_locations",
                    description="Score and rank birding locations using multi-criteria analysis with optional LLM enhancement",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "hotspot_clusters": {
                                "type": "array",
                                "description": "Hotspot clusters from cluster_hotspots tool"
                            },
                            "target_species": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Priority species for scoring"
                            },
                            "use_llm_enhancement": {
                                "type": "boolean",
                                "description": "Enable LLM habitat evaluation",
                                "default": true
                            }
                        },
                        "required": ["hotspot_clusters", "target_species"]
                    }
                ),
                Tool(
                    name="optimize_route",
                    description="Optimize travel route between birding locations using TSP algorithms",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "scored_locations": {
                                "type": "array",
                                "description": "Scored locations from score_locations tool"
                            },
                            "start_location": {
                                "type": "object",
                                "properties": {
                                    "lat": {"type": "number"},
                                    "lng": {"type": "number"}
                                },
                                "required": ["lat", "lng"],
                                "description": "Starting location coordinates"
                            },
                            "max_locations": {
                                "type": "integer",
                                "description": "Maximum number of locations to include",
                                "default": 8
                            }
                        },
                        "required": ["scored_locations", "start_location"]
                    }
                ),
                Tool(
                    name="generate_itinerary",
                    description="Generate professional birding itinerary with LLM enhancement and template fallback",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "optimized_route": {
                                "type": "object",
                                "description": "Optimized route from optimize_route tool"
                            },
                            "target_species": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Target species for the trip"
                            },
                            "trip_duration_days": {
                                "type": "integer",
                                "description": "Duration of the birding trip in days",
                                "default": 1
                            }
                        },
                        "required": ["optimized_route", "target_species"]
                    }
                ),
                
                # Business Logic Tools
                Tool(
                    name="plan_complete_trip",
                    description="End-to-end birding trip planning combining all pipeline stages for comprehensive recommendations",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "species_names": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Target bird species names"
                            },
                            "region": {
                                "type": "string",
                                "description": "Region code or location name"
                            },
                            "start_location": {
                                "type": "object",
                                "properties": {
                                    "lat": {"type": "number"},
                                    "lng": {"type": "number"}
                                },
                                "required": ["lat", "lng"],
                                "description": "Starting coordinates"
                            },
                            "max_distance_km": {
                                "type": "number",
                                "description": "Maximum travel distance",
                                "default": 100
                            },
                            "trip_duration_days": {
                                "type": "integer",
                                "description": "Trip duration in days",
                                "default": 1
                            },
                            "days_back": {
                                "type": "integer",
                                "description": "Days to look back for sightings",
                                "default": 14
                            }
                        },
                        "required": ["species_names", "region", "start_location"]
                    }
                ),
                Tool(
                    name="get_birding_advice",
                    description="Get expert birding advice for species, locations, or techniques using enhanced LLM prompting",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Birding question or advice request"
                            },
                            "context": {
                                "type": "object",
                                "properties": {
                                    "species": {"type": "array", "items": {"type": "string"}},
                                    "location": {"type": "string"},
                                    "season": {"type": "string"},
                                    "experience_level": {"type": "string"}
                                },
                                "description": "Optional context for personalized advice"
                            }
                        },
                        "required": ["query"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(request: CallToolRequest) -> CallToolResult:
            """Handle tool calls"""
            try:
                tool_name = request.params.name
                arguments = request.params.arguments or {}
                
                # Route to appropriate tool handler
                if tool_name == "validate_species":
                    result = await self._handle_validate_species(**arguments)
                elif tool_name == "fetch_sightings":
                    result = await self._handle_fetch_sightings(**arguments)
                elif tool_name == "filter_constraints":
                    result = await self._handle_filter_constraints(**arguments)
                elif tool_name == "cluster_hotspots":
                    result = await self._handle_cluster_hotspots(**arguments)
                elif tool_name == "score_locations":
                    result = await self._handle_score_locations(**arguments)
                elif tool_name == "optimize_route":
                    result = await self._handle_optimize_route(**arguments)
                elif tool_name == "generate_itinerary":
                    result = await self._handle_generate_itinerary(**arguments)
                elif tool_name == "plan_complete_trip":
                    result = await self._handle_plan_complete_trip(**arguments)
                elif tool_name == "get_birding_advice":
                    result = await self._handle_get_birding_advice(**arguments)
                else:
                    raise ValueError(f"Unknown tool: {tool_name}")
                
                return CallToolResult(content=[TextContent(type="text", text=json.dumps(result, indent=2))])
                
            except Exception as e:
                logger.error(f"Error handling tool call {request.params.name}: {str(e)}")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")],
                    isError=True
                )
    
    # Tool implementation methods
    async def _handle_validate_species(self, species_names: List[str], **kwargs):
        """Handle validate_species tool"""
        try:
            logger.info(f"Validating {len(species_names)} species")
            
            # Create mock shared store for node execution
            shared_store = {"species_list": species_names}
            
            # Execute ValidateSpeciesNode
            self.validate_species_node.prep(shared_store)
            result = self.validate_species_node.exec(shared_store)
            self.validate_species_node.post(shared_store)
            
            # Return validated species data
            validated_species = shared_store.get("validated_species", [])
            
            return {
                "success": True,
                "validated_species": validated_species,
                "statistics": {
                    "input_count": len(species_names),
                    "validated_count": len(validated_species),
                    "success_rate": len(validated_species) / len(species_names) if species_names else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error in validate_species: {str(e)}")
            return {
                "success": False, 
                "error": str(e),
                "validated_species": []
            }
    
    async def _handle_fetch_sightings(self, validated_species: List[Dict], region: str, days_back: int = 14, **kwargs):
        """Handle fetch_sightings tool"""
        try:
            logger.info(f"Fetching sightings for {len(validated_species)} species in {region}")
            
            # Create mock shared store for node execution
            shared_store = {
                "validated_species": validated_species,
                "region": region,
                "days_back": days_back
            }
            
            # Execute FetchSightingsNode (BatchNode)
            self.fetch_sightings_node.prep(shared_store)
            result = self.fetch_sightings_node.exec(shared_store)
            self.fetch_sightings_node.post(shared_store)
            
            # Return sightings data
            all_sightings = shared_store.get("all_sightings", [])
            sighting_stats = shared_store.get("sighting_statistics", {})
            
            return {
                "success": True,
                "sightings": all_sightings,
                "statistics": sighting_stats,
                "region": region,
                "days_back": days_back
            }
            
        except Exception as e:
            logger.error(f"Error in fetch_sightings: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "sightings": []
            }
    
    async def _handle_filter_constraints(self, sightings: List[Dict], start_location: Dict[str, float], 
                                       max_distance_km: float = 100, date_range: Optional[Dict] = None, **kwargs):
        """Handle filter_constraints tool"""
        try:
            logger.info(f"Filtering {len(sightings)} sightings with constraints")
            
            # Create mock shared store for node execution
            shared_store = {
                "all_sightings": sightings,
                "start_location": start_location,
                "max_distance_km": max_distance_km,
                "date_range": date_range
            }
            
            # Execute FilterConstraintsNode
            self.filter_constraints_node.prep(shared_store)
            result = self.filter_constraints_node.exec(shared_store)
            self.filter_constraints_node.post(shared_store)
            
            # Return filtered sightings data
            filtered_sightings = shared_store.get("all_sightings", [])
            constraint_stats = shared_store.get("constraint_statistics", {})
            
            return {
                "success": True,
                "filtered_sightings": filtered_sightings,
                "statistics": constraint_stats,
                "constraints": {
                    "start_location": start_location,
                    "max_distance_km": max_distance_km,
                    "date_range": date_range
                }
            }
            
        except Exception as e:
            logger.error(f"Error in filter_constraints: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "filtered_sightings": []
            }
    
    async def _handle_cluster_hotspots(self, filtered_sightings: List[Dict], region: str, 
                                     cluster_radius_km: float = 15, **kwargs):
        """Handle cluster_hotspots tool"""
        try:
            logger.info(f"Clustering hotspots for {len(filtered_sightings)} sightings")
            
            # Create mock shared store for node execution
            shared_store = {
                "all_sightings": filtered_sightings,
                "region": region,
                "cluster_radius_km": cluster_radius_km
            }
            
            # Execute ClusterHotspotsNode
            self.cluster_hotspots_node.prep(shared_store)
            result = self.cluster_hotspots_node.exec(shared_store)
            self.cluster_hotspots_node.post(shared_store)
            
            # Return clustered hotspots data
            hotspot_clusters = shared_store.get("hotspot_clusters", [])
            cluster_stats = shared_store.get("cluster_statistics", {})
            
            return {
                "success": True,
                "hotspot_clusters": hotspot_clusters,
                "statistics": cluster_stats,
                "region": region,
                "cluster_radius_km": cluster_radius_km
            }
            
        except Exception as e:
            logger.error(f"Error in cluster_hotspots: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "hotspot_clusters": []
            }
    
    async def _handle_score_locations(self, hotspot_clusters: List[Dict], target_species: List[str], 
                                    use_llm_enhancement: bool = True, **kwargs):
        """Handle score_locations tool"""
        try:
            logger.info(f"Scoring {len(hotspot_clusters)} hotspot clusters")
            
            # Create mock shared store for node execution
            shared_store = {
                "hotspot_clusters": hotspot_clusters,
                "target_species": target_species,
                "use_llm_enhancement": use_llm_enhancement
            }
            
            # Execute ScoreLocationsNode
            self.score_locations_node.prep(shared_store)
            result = self.score_locations_node.exec(shared_store)
            self.score_locations_node.post(shared_store)
            
            # Return scored locations data
            scored_locations = shared_store.get("scored_locations", [])
            scoring_stats = shared_store.get("scoring_statistics", {})
            
            return {
                "success": True,
                "scored_locations": scored_locations,
                "statistics": scoring_stats,
                "target_species": target_species,
                "llm_enhancement_used": use_llm_enhancement
            }
            
        except Exception as e:
            logger.error(f"Error in score_locations: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "scored_locations": []
            }
    
    async def _handle_optimize_route(self, scored_locations: List[Dict], start_location: Dict[str, float], 
                                   max_locations: int = 8, **kwargs):
        """Handle optimize_route tool"""
        try:
            logger.info(f"Optimizing route for {len(scored_locations)} locations")
            
            # Create mock shared store for node execution
            shared_store = {
                "scored_locations": scored_locations,
                "start_location": start_location,
                "max_locations": max_locations
            }
            
            # Execute OptimizeRouteNode
            self.optimize_route_node.prep(shared_store)
            result = self.optimize_route_node.exec(shared_store)
            self.optimize_route_node.post(shared_store)
            
            # Return optimized route data
            optimized_route = shared_store.get("optimized_route", {})
            route_stats = shared_store.get("route_statistics", {})
            
            return {
                "success": True,
                "optimized_route": optimized_route,
                "statistics": route_stats,
                "start_location": start_location,
                "max_locations": max_locations
            }
            
        except Exception as e:
            logger.error(f"Error in optimize_route: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "optimized_route": {}
            }
    
    async def _handle_generate_itinerary(self, optimized_route: Dict, target_species: List[str], 
                                       trip_duration_days: int = 1, **kwargs):
        """Handle generate_itinerary tool"""
        try:
            logger.info(f"Generating itinerary for {trip_duration_days}-day trip")
            
            # Create mock shared store for node execution
            shared_store = {
                "optimized_route": optimized_route,
                "target_species": target_species,
                "trip_duration_days": trip_duration_days
            }
            
            # Execute GenerateItineraryNode
            self.generate_itinerary_node.prep(shared_store)
            result = self.generate_itinerary_node.exec(shared_store)
            self.generate_itinerary_node.post(shared_store)
            
            # Return itinerary data
            itinerary = shared_store.get("itinerary", "")
            itinerary_stats = shared_store.get("itinerary_statistics", {})
            
            return {
                "success": True,
                "itinerary": itinerary,
                "statistics": itinerary_stats,
                "target_species": target_species,
                "trip_duration_days": trip_duration_days
            }
            
        except Exception as e:
            logger.error(f"Error in generate_itinerary: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "itinerary": ""
            }
    
    async def _handle_plan_complete_trip(self, species_names: List[str], region: str, 
                                       start_location: Dict[str, float], max_distance_km: float = 100,
                                       trip_duration_days: int = 1, days_back: int = 14, **kwargs):
        """Handle plan_complete_trip tool - End-to-end birding trip planning"""
        try:
            logger.info(f"Planning complete trip for {len(species_names)} species in {region}")
            
            pipeline_results = {}
            
            # Step 1: Validate Species
            validate_result = await self._handle_validate_species(species_names)
            if not validate_result["success"]:
                return {
                    "success": False,
                    "error": f"Species validation failed: {validate_result.get('error', 'Unknown error')}",
                    "stage": "validate_species"
                }
            pipeline_results["species_validation"] = validate_result
            validated_species = validate_result["validated_species"]
            
            # Step 2: Fetch Sightings
            fetch_result = await self._handle_fetch_sightings(validated_species, region, days_back)
            if not fetch_result["success"]:
                return {
                    "success": False,
                    "error": f"Sightings fetch failed: {fetch_result.get('error', 'Unknown error')}",
                    "stage": "fetch_sightings",
                    "pipeline_results": pipeline_results
                }
            pipeline_results["sightings_fetch"] = fetch_result
            sightings = fetch_result["sightings"]
            
            # Step 3: Filter Constraints
            filter_result = await self._handle_filter_constraints(sightings, start_location, max_distance_km)
            if not filter_result["success"]:
                return {
                    "success": False,
                    "error": f"Constraint filtering failed: {filter_result.get('error', 'Unknown error')}",
                    "stage": "filter_constraints",
                    "pipeline_results": pipeline_results
                }
            pipeline_results["constraint_filtering"] = filter_result
            filtered_sightings = filter_result["filtered_sightings"]
            
            # Step 4: Cluster Hotspots
            cluster_result = await self._handle_cluster_hotspots(filtered_sightings, region)
            if not cluster_result["success"]:
                return {
                    "success": False,
                    "error": f"Hotspot clustering failed: {cluster_result.get('error', 'Unknown error')}",
                    "stage": "cluster_hotspots",
                    "pipeline_results": pipeline_results
                }
            pipeline_results["hotspot_clustering"] = cluster_result
            hotspot_clusters = cluster_result["hotspot_clusters"]
            
            # Step 5: Score Locations
            score_result = await self._handle_score_locations(hotspot_clusters, species_names)
            if not score_result["success"]:
                return {
                    "success": False,
                    "error": f"Location scoring failed: {score_result.get('error', 'Unknown error')}",
                    "stage": "score_locations",
                    "pipeline_results": pipeline_results
                }
            pipeline_results["location_scoring"] = score_result
            scored_locations = score_result["scored_locations"]
            
            # Step 6: Optimize Route
            route_result = await self._handle_optimize_route(scored_locations, start_location)
            if not route_result["success"]:
                return {
                    "success": False,
                    "error": f"Route optimization failed: {route_result.get('error', 'Unknown error')}",
                    "stage": "optimize_route",
                    "pipeline_results": pipeline_results
                }
            pipeline_results["route_optimization"] = route_result
            optimized_route = route_result["optimized_route"]
            
            # Step 7: Generate Itinerary
            itinerary_result = await self._handle_generate_itinerary(optimized_route, species_names, trip_duration_days)
            if not itinerary_result["success"]:
                return {
                    "success": False,
                    "error": f"Itinerary generation failed: {itinerary_result.get('error', 'Unknown error')}",
                    "stage": "generate_itinerary",
                    "pipeline_results": pipeline_results
                }
            pipeline_results["itinerary_generation"] = itinerary_result
            
            # Return complete trip plan
            return {
                "success": True,
                "trip_plan": {
                    "species_names": species_names,
                    "region": region,
                    "start_location": start_location,
                    "trip_duration_days": trip_duration_days,
                    "itinerary": itinerary_result["itinerary"],
                    "route": optimized_route,
                    "locations": scored_locations[:8]  # Top locations
                },
                "pipeline_results": pipeline_results,
                "summary": {
                    "total_species_validated": len(validated_species),
                    "total_sightings_found": len(sightings),
                    "sightings_after_filtering": len(filtered_sightings),
                    "hotspot_clusters": len(hotspot_clusters),
                    "route_distance_km": optimized_route.get("total_distance_km", 0),
                    "estimated_travel_time": optimized_route.get("total_travel_time_hours", 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Error in plan_complete_trip: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "stage": "pipeline_execution"
            }
    
    async def _handle_get_birding_advice(self, query: str, context: Optional[Dict] = None, **kwargs):
        """Handle get_birding_advice tool - Expert birding advice using enhanced LLM prompting"""
        try:
            logger.info(f"Providing birding advice for query: {query[:100]}...")
            
            # Import LLM function for advice generation
            from ..utils.call_llm import call_llm
            
            # Build context-aware prompt for expert birding advice
            context_info = ""
            if context:
                species = context.get("species", [])
                location = context.get("location", "")
                season = context.get("season", "")
                experience_level = context.get("experience_level", "")
                
                context_parts = []
                if species:
                    context_parts.append(f"Target species: {', '.join(species)}")
                if location:
                    context_parts.append(f"Location: {location}")
                if season:
                    context_parts.append(f"Season: {season}")
                if experience_level:
                    context_parts.append(f"Experience level: {experience_level}")
                
                if context_parts:
                    context_info = f"\n\nContext: {'; '.join(context_parts)}"
            
            expert_prompt = f"""You are an expert birding guide with decades of field experience and deep knowledge of bird behavior, habitats, and identification techniques. 
            
            Please provide professional birding advice for the following query: {query}{context_info}
            
            Your response should include:
            1. Direct answer to the specific question
            2. Relevant species-specific behavior and habitat information
            3. Practical field techniques and timing recommendations
            4. Equipment suggestions if applicable
            5. Seasonal considerations and migration patterns
            6. Safety and ethical birding practices
            
            Be specific, practical, and draw from ornithological knowledge and field experience. 
            Provide actionable advice that will help the birder succeed."""
            
            try:
                advice = call_llm(expert_prompt)
                
                return {
                    "success": True,
                    "advice": advice,
                    "query": query,
                    "context": context,
                    "advice_type": "expert_llm_response"
                }
                
            except Exception as llm_error:
                logger.warning(f"LLM advice generation failed: {str(llm_error)}, using fallback")
                
                # Fallback advice system
                fallback_advice = self._generate_fallback_advice(query, context)
                
                return {
                    "success": True,
                    "advice": fallback_advice,
                    "query": query,
                    "context": context,
                    "advice_type": "fallback_response",
                    "llm_error": str(llm_error)
                }
                
        except Exception as e:
            logger.error(f"Error in get_birding_advice: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "advice": ""
            }
    
    def _generate_fallback_advice(self, query: str, context: Optional[Dict] = None) -> str:
        """Generate fallback birding advice when LLM is unavailable"""
        
        # Basic advice patterns based on common queries
        query_lower = query.lower()
        
        if "best time" in query_lower or "when" in query_lower:
            return """**General Timing Advice:**
            
            • **Dawn (30 minutes before sunrise to 2 hours after):** Peak bird activity, especially songbirds
            • **Dusk (2 hours before sunset to 30 minutes after):** Second peak activity period
            • **Migration seasons:** Spring (March-May) and Fall (August-October) offer the most species diversity
            • **Weather:** Overcast days often provide better birding than bright sunny conditions
            • **After storms:** Check coastal areas and migrant traps for displaced species
            
            For specific species timing, consult local birding guides or eBird data for your region."""
            
        elif "equipment" in query_lower or "binoculars" in query_lower:
            return """**Essential Birding Equipment:**
            
            • **Binoculars:** 8x42 recommended for general birding (good balance of magnification and field of view)
            • **Field guide:** Regional guide specific to your area
            • **Notebook/app:** For recording observations and notes
            • **Camera (optional):** For documentation and identification confirmation
            • **Comfortable clothing:** Earth tones, layers for weather changes
            • **Sun protection:** Hat and sunscreen for extended field time
            
            Start with quality binoculars - they make the biggest difference in your birding experience."""
            
        elif "habitat" in query_lower or "where" in query_lower:
            return """**Habitat-Based Birding Strategy:**
            
            • **Forests:** Dawn chorus offers best songbird activity
            • **Wetlands:** Early morning and late afternoon for waterfowl
            • **Grasslands:** Morning for ground-dwelling species
            • **Coast:** Tide changes bring feeding opportunities
            • **Urban parks:** Surprisingly productive, especially during migration
            
            Edge habitats (where two habitat types meet) are often most productive for bird diversity."""
            
        else:
            return f"""**General Birding Advice for: "{query}"**
            
            • **Plan your trip:** Check eBird for recent sightings in your target area
            • **Timing matters:** Early morning (dawn + 2 hours) is typically best
            • **Be patient:** Spend time in productive areas rather than constantly moving
            • **Use playback sparingly:** Brief use to attract secretive species, then stop
            • **Record observations:** Use eBird to contribute to citizen science
            • **Join local groups:** Connect with birding clubs for local knowledge
            
            For more specific advice, please provide details about your location, target species, or experience level."""

async def main():
    """Run the MCP server"""
    server_instance = BirdTravelMCPServer()
    
    # Run the server
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await server_instance.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="bird-travel-recommender",
                server_version="1.0.0",
                capabilities={}
            )
        )

if __name__ == "__main__":
    asyncio.run(main())