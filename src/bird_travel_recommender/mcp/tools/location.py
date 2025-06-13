"""
Location and geographic MCP tool definitions
"""

from mcp.types import Tool

# Geographic and location-based tools
LOCATION_TOOLS = [
    Tool(
        name="get_region_details",
        description="Get detailed information and metadata about a specific geographic region",
        inputSchema={
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "description": "eBird region code (e.g., 'US-CA', 'MX-ROO', 'CR')"
                }
            },
            "required": ["region"]
        }
    ),
    Tool(
        name="get_hotspot_details",
        description="Get comprehensive information about a specific birding hotspot",
        inputSchema={
            "type": "object",
            "properties": {
                "location_id": {
                    "type": "string",
                    "description": "eBird location ID (e.g., 'L99381')"
                }
            },
            "required": ["location_id"]
        }
    ),
    Tool(
        name="find_nearest_species",
        description="Find the closest recent observations of a specific bird species",
        inputSchema={
            "type": "object",
            "properties": {
                "species_code": {
                    "type": "string",
                    "description": "eBird species code (e.g., 'baleag' for Bald Eagle)"
                },
                "latitude": {
                    "type": "number",
                    "description": "Latitude coordinate"
                },
                "longitude": {
                    "type": "number", 
                    "description": "Longitude coordinate"
                },
                "radius": {
                    "type": "integer",
                    "description": "Search radius in kilometers (default: 50)",
                    "default": 50
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days back to search (default: 30)",
                    "default": 30
                }
            },
            "required": ["species_code", "latitude", "longitude"]
        }
    ),
    Tool(
        name="get_nearby_notable_observations",
        description="Get rare and notable bird observations near coordinates for enhanced geographic precision",
        inputSchema={
            "type": "object",
            "properties": {
                "latitude": {
                    "type": "number",
                    "description": "Latitude coordinate"
                },
                "longitude": {
                    "type": "number",
                    "description": "Longitude coordinate"
                },
                "radius": {
                    "type": "integer",
                    "description": "Search radius in kilometers (default: 25)",
                    "default": 25
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days back to search (1-30, default: 14)",
                    "default": 14
                }
            },
            "required": ["latitude", "longitude"]
        }
    ),
    Tool(
        name="get_nearby_species_observations",
        description="Get recent observations of specific species near coordinates with enhanced geographic precision",
        inputSchema={
            "type": "object",
            "properties": {
                "species_codes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of eBird species codes to search for"
                },
                "latitude": {
                    "type": "number",
                    "description": "Latitude coordinate"
                },
                "longitude": {
                    "type": "number",
                    "description": "Longitude coordinate"
                },
                "radius": {
                    "type": "integer",
                    "description": "Search radius in kilometers (default: 25)",
                    "default": 25
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days back to search (1-30, default: 14)",
                    "default": 14
                }
            },
            "required": ["species_codes", "latitude", "longitude"]
        }
    )
]