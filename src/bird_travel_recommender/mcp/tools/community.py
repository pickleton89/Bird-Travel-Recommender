"""
Community and checklist MCP tool definitions
"""

from mcp.types import Tool

# Community and checklist-based tools
COMMUNITY_TOOLS = [
    Tool(
        name="get_recent_checklists",
        description="Get most recent checklists in a region to understand current birding activity",
        inputSchema={
            "type": "object",
            "properties": {
                "region_code": {
                    "type": "string",
                    "description": "eBird region code (e.g., 'US-CA', 'MX-ROO')",
                },
                "days_back": {
                    "type": "integer",
                    "description": "Days back to search (1-30, default: 7)",
                    "default": 7,
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum checklists to return (default: 50)",
                    "default": 50,
                },
            },
            "required": ["region_code"],
        },
    ),
    Tool(
        name="get_checklist_details",
        description="Get detailed information about a specific birding checklist",
        inputSchema={
            "type": "object",
            "properties": {
                "checklist_id": {
                    "type": "string",
                    "description": "eBird checklist ID (e.g., 'S123456789')",
                }
            },
            "required": ["checklist_id"],
        },
    ),
    Tool(
        name="get_user_stats",
        description="Get birder profile and statistics for understanding birding activity patterns",
        inputSchema={
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "eBird username or identifier",
                },
                "region_code": {
                    "type": "string",
                    "description": "Region for statistics (default: 'world')",
                    "default": "world",
                },
                "year": {
                    "type": "integer",
                    "description": "Year for statistics (default: 2024)",
                    "default": 2024,
                },
            },
            "required": ["username"],
        },
    ),
]
