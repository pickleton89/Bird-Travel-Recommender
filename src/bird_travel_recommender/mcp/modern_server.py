"""Modern MCP Server using the new registry system.

This server maintains full backward compatibility while using the new
decorator-based tool registry and middleware system.
"""

import asyncio
import json
import logging

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

# Import existing components for compatibility
from .handlers.species import SpeciesHandlers
from .handlers.community import CommunityHandlers
from .handlers.location import LocationHandlers
from .handlers.pipeline import PipelineHandlers
from .handlers.planning import PlanningHandlers
from .handlers.advisory import AdvisoryHandlers
from .auth import AuthManager
from .rate_limiting import RateLimiter

# Import new registry system
from ..core.mcp.adapter import create_adapter
from ..core.mcp.registry import registry

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


class ModernBirdTravelMCPServer:
    """
    Modern MCP Server for Bird Travel Recommendations using registry system.

    This version eliminates the 30 if/elif conditions and uses the new
    decorator-based tool registry with middleware support.
    """

    def __init__(self):
        # Create handlers container
        self.handlers = HandlersContainer()
        
        # Create adapter to bridge new registry with existing handlers
        self.adapter = create_adapter(self.handlers)
        
        logger.info("Initialized Modern Bird Travel MCP Server")
        
        # Log registry statistics
        stats = self.adapter.get_registry_stats()
        logger.info(f"Registry stats: {stats}")
        
        # Log tool categories
        for category in registry.get_categories():
            tools_in_category = len(registry.list_tools(category))
            logger.info(f"{category.title()} tools: {tools_in_category}")

    async def handle_call_tool(self, request: CallToolRequest) -> CallToolResult:
        """Handle tool execution requests using the registry system."""
        tool_name = request.params.name
        arguments = request.params.arguments or {}

        logger.info(f"Handling tool call: {tool_name}")

        try:
            # Use adapter to route through registry system
            result = await self.adapter.route_tool_call(tool_name, arguments)

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
            logger.error(error_msg, extra={
                "tool_name": tool_name,
                "error_type": type(e).__name__,
                "arguments_provided": bool(arguments)
            })

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

    def get_tools(self) -> list[Tool]:
        """Get tools using the registry system."""
        tools_data = self.adapter.get_tools_for_mcp()
        
        # Convert to MCP Tool format
        tools = []
        for tool_data in tools_data:
            tools.append(Tool(
                name=tool_data["name"],
                description=tool_data["description"],
                inputSchema=tool_data["inputSchema"]
            ))
        
        return tools


# Backward compatibility - create alias to old server name
BirdTravelMCPServer = ModernBirdTravelMCPServer


# Server setup and entry point
async def run_modern_server():
    """Run the Modern Bird Travel MCP Server with registry system."""

    # Create server instance
    mcp_server = ModernBirdTravelMCPServer()

    # Create MCP server with notification options
    server = Server("bird-travel-recommender")

    # Register handlers
    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        return mcp_server.get_tools()

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
    logger.info("Starting Modern Bird Travel Recommender MCP Server...")
    total_tools = len(mcp_server.get_tools())
    total_categories = len(registry.get_categories())
    logger.info(f"Serving {total_tools} tools across {total_categories} categories")
    logger.info("Using new registry system with middleware support")

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="bird-travel-recommender",
                server_version="2.1.0",  # Incremented version for registry system
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


# For backward compatibility, provide the old run_server function
async def run_server():
    """Backward compatibility wrapper for run_modern_server."""
    await run_modern_server()


if __name__ == "__main__":
    asyncio.run(run_modern_server())