#!/usr/bin/env python3
"""
Bird Travel Recommender MCP Server (Modular Version)

This MCP server provides 15 birding tools that integrate with the eBird API
and our advanced birding pipeline to help users plan birding trips.

Modularized architecture with separate tool and handler modules for maintainability.
"""

import asyncio
import json
import logging
from typing import Any, Dict

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    Tool,
    TextContent,
)
import mcp.types as types

# Tool definitions are now inline with handlers

# Import modularized handlers
from .handlers.species import SpeciesHandlers
from .handlers.community import CommunityHandlers
from .handlers.location import LocationHandlers
from .handlers.pipeline import PipelineHandlers
from .handlers.planning import PlanningHandlers
from .handlers.advisory import AdvisoryHandlers

# Import security modules
from .auth import AuthManager
from .rate_limiting import RateLimiter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HandlersContainer:
    """Container for all handler instances to facilitate cross-handler communication"""

    def __init__(self, enable_auth: bool = True):
        # Initialize security components
        self.auth_manager = AuthManager() if enable_auth else None
        self.rate_limiter = RateLimiter() if enable_auth else None

        # Initialize handlers
        self.species_handlers = SpeciesHandlers()
        self.location_handlers = LocationHandlers()
        self.pipeline_handlers = PipelineHandlers()
        self.planning_handlers = PlanningHandlers()
        self.advisory_handlers = AdvisoryHandlers()
        self.community_handlers = CommunityHandlers()

        # Inject security components into handlers
        if enable_auth:
            for handler in [
                self.species_handlers,
                self.location_handlers,
                self.pipeline_handlers,
                self.planning_handlers,
                self.advisory_handlers,
                self.community_handlers,
            ]:
                handler.auth_manager = self.auth_manager
                handler.rate_limiter = self.rate_limiter


class BirdTravelMCPServer:
    """
    MCP Server for Bird Travel Recommendations

    Modularized architecture with 30 birding tools organized by category:
    - Species (2 tools): Species validation and regional species lists
    - Location (11 tools): Geographic and hotspot information + Phase 5B geographic tools
    - Pipeline (11 tools): Core birding data processing + Phase 5A temporal + Phase 5C migration
    - Planning (2 tools): Itinerary generation and complete trip planning
    - Advisory (1 tool): LLM-enhanced birding advice
    - Community (3 tools): Checklist and user data intelligence
    """

    def __init__(self):
        # Create handlers container for cross-handler communication
        self.handlers = HandlersContainer()

        # Define basic tool set inline (simplified for cleanup)
        self.tools = [
            Tool(
                name="validate_species",
                description="Validate bird species names using eBird taxonomy",
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
            )
        ]

        logger.info(f"Initialized Bird Travel MCP Server with {len(self.tools)} tools")

    async def handle_call_tool(self, request: CallToolRequest) -> CallToolResult:
        """Handle tool execution requests with modular handler delegation"""
        tool_name = request.params.name
        arguments = request.params.arguments or {}

        logger.info(f"Handling tool call: {tool_name}")

        try:
            # Route to appropriate handler based on tool name
            result = await self._route_tool_call(tool_name, arguments)

            # Convert result to TextContent format for MCP response
            return CallToolResult(
                content=[
                    TextContent(
                        type="text", text=json.dumps(result, indent=2, default=str)
                    )
                ]
            )

        except Exception as e:
            error_msg = f"Error executing tool {tool_name}: {str(e)}"
            logger.error(error_msg)

            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": False,
                                "error": error_msg,
                                "tool_name": tool_name,
                            },
                            indent=2,
                        ),
                    )
                ]
            )

    async def _route_tool_call(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Route tool calls to appropriate handler modules"""

        # Species tools
        if tool_name == "validate_species":
            return await self.handlers.species_handlers.handle_validate_species(
                **arguments
            )
        elif tool_name == "get_regional_species_list":
            return (
                await self.handlers.species_handlers.handle_get_regional_species_list(
                    **arguments
                )
            )

        # Location tools
        elif tool_name == "get_region_details":
            return await self.handlers.location_handlers.handle_get_region_details(
                **arguments
            )
        elif tool_name == "get_hotspot_details":
            return await self.handlers.location_handlers.handle_get_hotspot_details(
                **arguments
            )
        elif tool_name == "find_nearest_species":
            return await self.handlers.location_handlers.handle_find_nearest_species(
                **arguments
            )
        elif tool_name == "get_nearby_notable_observations":
            return await self.handlers.location_handlers.handle_get_nearby_notable_observations(
                **arguments
            )
        elif tool_name == "get_nearby_species_observations":
            return await self.handlers.location_handlers.handle_get_nearby_species_observations(
                **arguments
            )
        elif tool_name == "get_top_locations":
            return await self.handlers.location_handlers.handle_get_top_locations(
                **arguments
            )
        elif tool_name == "get_regional_statistics":
            return await self.handlers.location_handlers.handle_get_regional_statistics(
                **arguments
            )
        elif tool_name == "get_location_species_list":
            return (
                await self.handlers.location_handlers.handle_get_location_species_list(
                    **arguments
                )
            )
        elif tool_name == "get_subregions":
            return await self.handlers.location_handlers.handle_get_subregions(
                **arguments
            )
        elif tool_name == "get_adjacent_regions":
            return await self.handlers.location_handlers.handle_get_adjacent_regions(
                **arguments
            )
        elif tool_name == "get_elevation_data":
            return await self.handlers.location_handlers.handle_get_elevation_data(
                **arguments
            )

        # Pipeline tools
        elif tool_name == "fetch_sightings":
            return await self.handlers.pipeline_handlers.handle_fetch_sightings(
                **arguments
            )
        elif tool_name == "filter_constraints":
            return await self.handlers.pipeline_handlers.handle_filter_constraints(
                **arguments
            )
        elif tool_name == "cluster_hotspots":
            return await self.handlers.pipeline_handlers.handle_cluster_hotspots(
                **arguments
            )
        elif tool_name == "score_locations":
            return await self.handlers.pipeline_handlers.handle_score_locations(
                **arguments
            )
        elif tool_name == "optimize_route":
            return await self.handlers.pipeline_handlers.handle_optimize_route(
                **arguments
            )
        elif tool_name == "get_historic_observations":
            return (
                await self.handlers.pipeline_handlers.handle_get_historic_observations(
                    **arguments
                )
            )
        elif tool_name == "get_seasonal_trends":
            return await self.handlers.pipeline_handlers.handle_get_seasonal_trends(
                **arguments
            )
        elif tool_name == "get_yearly_comparisons":
            return await self.handlers.pipeline_handlers.handle_get_yearly_comparisons(
                **arguments
            )
        elif tool_name == "get_migration_data":
            return await self.handlers.pipeline_handlers.handle_get_migration_data(
                **arguments
            )
        elif tool_name == "get_peak_times":
            return await self.handlers.pipeline_handlers.handle_get_peak_times(
                **arguments
            )
        elif tool_name == "get_seasonal_hotspots":
            return await self.handlers.pipeline_handlers.handle_get_seasonal_hotspots(
                **arguments
            )

        # Planning tools
        elif tool_name == "generate_itinerary":
            return await self.handlers.planning_handlers.handle_generate_itinerary(
                **arguments
            )
        elif tool_name == "plan_complete_trip":
            return await self.handlers.planning_handlers.handle_plan_complete_trip(
                handlers_container=self.handlers, **arguments
            )

        # Advisory tools
        elif tool_name == "get_birding_advice":
            return await self.handlers.advisory_handlers.handle_get_birding_advice(
                handlers_container=self.handlers, **arguments
            )

        # Community tools
        elif tool_name == "get_recent_checklists":
            return await self.handlers.community_handlers.handle_get_recent_checklists(
                **arguments
            )
        elif tool_name == "get_checklist_details":
            return await self.handlers.community_handlers.handle_get_checklist_details(
                **arguments
            )
        elif tool_name == "get_user_stats":
            return await self.handlers.community_handlers.handle_get_user_stats(
                **arguments
            )

        else:
            raise ValueError(f"Unknown tool: {tool_name}")


# Server setup and entry point
async def run_server():
    """Run the Bird Travel MCP Server"""

    # Create server instance
    mcp_server = BirdTravelMCPServer()

    # Create MCP server with notification options
    server = Server("bird-travel-recommender")

    # Register handlers
    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        return mcp_server.tools

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        request = CallToolRequest(
            method="tools/call",
            params=types.CallToolRequestParams(name=name, arguments=arguments),
        )
        result = await mcp_server.handle_call_tool(request)
        return result.content

    # Run server with stdio transport
    logger.info("Starting Bird Travel Recommender MCP Server...")
    logger.info(f"Serving {len(mcp_server.tools)} tools across 5 categories")

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="bird-travel-recommender",
                server_version="2.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.info("Server shut down by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        import sys

        sys.exit(1)
