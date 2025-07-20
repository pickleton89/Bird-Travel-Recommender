"""Adapter layer for integrating new registry with existing MCP server."""

from typing import Dict, Any, List
import logging

from .registry import registry, tool
from .middleware import error_handling_middleware, validation_middleware, performance_middleware

# Import existing handlers for integration

logger = logging.getLogger(__name__)


class MCPServerAdapter:
    """Adapter that bridges new registry system with existing handlers."""
    
    def __init__(self, handlers_container):
        """Initialize adapter with existing handlers container."""
        self.handlers = handlers_container
        
        # Apply global middleware
        registry.add_global_middleware(error_handling_middleware)
        registry.add_global_middleware(validation_middleware) 
        registry.add_global_middleware(performance_middleware)
        
        # Register all existing tools using the new decorator system
        self._register_existing_tools()
        
        logger.info(f"MCPServerAdapter initialized with {len(registry.list_tools())} tools")
    
    def _register_existing_tools(self):
        """Register all existing tools with the new registry system."""
        
        # Species tools
        @tool("validate_species", "Validates bird species with taxonomic lookup", "species")
        async def validate_species(**kwargs):
            return await self.handlers.species_handlers.handle_validate_species(**kwargs)
        
        @tool("get_regional_species_list", "Get list of species for a region", "species") 
        async def get_regional_species_list(**kwargs):
            return await self.handlers.species_handlers.handle_get_regional_species_list(**kwargs)
        
        # Location tools
        @tool("get_region_details", "Get detailed information about a geographic region", "location")
        async def get_region_details(**kwargs):
            return await self.handlers.location_handlers.handle_get_region_details(**kwargs)
        
        @tool("get_hotspot_details", "Get detailed information about a birding hotspot", "location")
        async def get_hotspot_details(**kwargs):
            return await self.handlers.location_handlers.handle_get_hotspot_details(**kwargs)
        
        @tool("find_nearest_species", "Find nearest locations for observing a species", "location")
        async def find_nearest_species(**kwargs):
            return await self.handlers.location_handlers.handle_find_nearest_species(**kwargs)
        
        @tool("get_nearby_notable_observations", "Get notable bird observations near a location", "location")
        async def get_nearby_notable_observations(**kwargs):
            return await self.handlers.location_handlers.handle_get_nearby_notable_observations(**kwargs)
        
        @tool("get_nearby_species_observations", "Get species observations near a location", "location") 
        async def get_nearby_species_observations(**kwargs):
            return await self.handlers.location_handlers.handle_get_nearby_species_observations(**kwargs)
        
        @tool("get_top_locations", "Get top birding locations for a region", "location")
        async def get_top_locations(**kwargs):
            return await self.handlers.location_handlers.handle_get_top_locations(**kwargs)
        
        @tool("get_regional_statistics", "Get birding statistics for a region", "location")
        async def get_regional_statistics(**kwargs):
            return await self.handlers.location_handlers.handle_get_regional_statistics(**kwargs)
        
        @tool("get_location_species_list", "Get species list for a specific location", "location")
        async def get_location_species_list(**kwargs):
            return await self.handlers.location_handlers.handle_get_location_species_list(**kwargs)
        
        @tool("get_subregions", "Get subregions within a geographic region", "location")
        async def get_subregions(**kwargs):
            return await self.handlers.location_handlers.handle_get_subregions(**kwargs)
        
        @tool("get_adjacent_regions", "Get regions adjacent to a given region", "location")
        async def get_adjacent_regions(**kwargs):
            return await self.handlers.location_handlers.handle_get_adjacent_regions(**kwargs)
        
        @tool("get_elevation_data", "Get elevation data for coordinates", "location")
        async def get_elevation_data(**kwargs):
            return await self.handlers.location_handlers.handle_get_elevation_data(**kwargs)
        
        # Pipeline tools
        @tool("fetch_sightings", "Fetch bird sightings data", "pipeline")
        async def fetch_sightings(**kwargs):
            return await self.handlers.pipeline_handlers.handle_fetch_sightings(**kwargs)
        
        @tool("filter_constraints", "Apply filtering constraints to birding data", "pipeline")
        async def filter_constraints(**kwargs):
            return await self.handlers.pipeline_handlers.handle_filter_constraints(**kwargs)
        
        @tool("cluster_hotspots", "Cluster birding hotspots by location", "pipeline")
        async def cluster_hotspots(**kwargs):
            return await self.handlers.pipeline_handlers.handle_cluster_hotspots(**kwargs)
        
        @tool("score_locations", "Score birding locations based on criteria", "pipeline") 
        async def score_locations(**kwargs):
            return await self.handlers.pipeline_handlers.handle_score_locations(**kwargs)
        
        @tool("optimize_route", "Optimize birding route between locations", "pipeline")
        async def optimize_route(**kwargs):
            return await self.handlers.pipeline_handlers.handle_optimize_route(**kwargs)
        
        @tool("get_historic_observations", "Get historic bird observation data", "pipeline")
        async def get_historic_observations(**kwargs):
            return await self.handlers.pipeline_handlers.handle_get_historic_observations(**kwargs)
        
        @tool("get_seasonal_trends", "Get seasonal birding trends", "pipeline")
        async def get_seasonal_trends(**kwargs):
            return await self.handlers.pipeline_handlers.handle_get_seasonal_trends(**kwargs)
        
        @tool("get_yearly_comparisons", "Compare birding data across years", "pipeline")
        async def get_yearly_comparisons(**kwargs):
            return await self.handlers.pipeline_handlers.handle_get_yearly_comparisons(**kwargs)
        
        @tool("get_migration_data", "Get bird migration data", "pipeline")
        async def get_migration_data(**kwargs):
            return await self.handlers.pipeline_handlers.handle_get_migration_data(**kwargs)
        
        @tool("get_peak_times", "Get peak times for bird observations", "pipeline")
        async def get_peak_times(**kwargs):
            return await self.handlers.pipeline_handlers.handle_get_peak_times(**kwargs)
        
        @tool("get_seasonal_hotspots", "Get seasonal birding hotspots", "pipeline")
        async def get_seasonal_hotspots(**kwargs):
            return await self.handlers.pipeline_handlers.handle_get_seasonal_hotspots(**kwargs)
        
        # Planning tools
        @tool("generate_itinerary", "Generate a birding itinerary", "planning")
        async def generate_itinerary(**kwargs):
            return await self.handlers.planning_handlers.handle_generate_itinerary(**kwargs)
        
        @tool("plan_complete_trip", "Plan a complete birding trip", "planning")
        async def plan_complete_trip(**kwargs):
            return await self.handlers.planning_handlers.handle_plan_complete_trip(
                handlers_container=self.handlers, **kwargs
            )
        
        # Advisory tools
        @tool("get_birding_advice", "Get expert birding advice", "advisory") 
        async def get_birding_advice(**kwargs):
            return await self.handlers.advisory_handlers.handle_get_birding_advice(
                handlers_container=self.handlers, **kwargs
            )
        
        # Community tools
        @tool("get_recent_checklists", "Get recent eBird checklists", "community")
        async def get_recent_checklists(**kwargs):
            return await self.handlers.community_handlers.handle_get_recent_checklists(**kwargs)
        
        @tool("get_checklist_details", "Get detailed checklist information", "community")
        async def get_checklist_details(**kwargs):
            return await self.handlers.community_handlers.handle_get_checklist_details(**kwargs)
        
        @tool("get_user_stats", "Get eBird user statistics", "community")
        async def get_user_stats(**kwargs):
            return await self.handlers.community_handlers.handle_get_user_stats(**kwargs)
    
    async def route_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route tool call using the new registry system."""
        try:
            # Use registry to execute tool with middleware
            result = await registry.execute_tool(tool_name, arguments)
            return result
            
        except ValueError as e:
            # Tool not found in registry, fallback to legacy routing if needed
            logger.warning(f"Tool {tool_name} not found in registry: {e}")
            raise
        except Exception as e:
            # Log error with context
            logger.error(f"Error executing tool {tool_name}: {e}", extra={
                "tool_name": tool_name,
                "arguments": arguments,
                "error_type": type(e).__name__
            })
            raise
    
    def get_tools_for_mcp(self) -> List[Dict[str, Any]]:
        """Get tools in MCP format."""
        return registry.get_tools_for_mcp()
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics for monitoring."""
        return registry.get_stats()


def create_adapter(handlers_container) -> MCPServerAdapter:
    """Factory function to create adapter instance."""
    return MCPServerAdapter(handlers_container)