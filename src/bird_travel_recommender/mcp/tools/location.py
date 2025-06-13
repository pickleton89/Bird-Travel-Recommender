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
    ),
    Tool(
        name="get_top_locations",
        description="Get most active birding locations in a region for community activity insights",
        inputSchema={
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "description": "eBird region code (e.g., 'US-CA', 'MX-ROO')"
                },
                "days_back": {
                    "type": "integer",
                    "description": "Number of days back to consider (1-30, default: 7)",
                    "default": 7
                },
                "max_results": {
                    "type": "integer", 
                    "description": "Maximum locations to return (default: 100, max: 200)",
                    "default": 100
                },
                "locale": {
                    "type": "string",
                    "description": "Language code for common names (default: 'en')",
                    "default": "en"
                }
            },
            "required": ["region"]
        }
    ),
    Tool(
        name="get_regional_statistics",
        description="Get comprehensive species counts and birding activity statistics for a region",
        inputSchema={
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "description": "eBird region code (e.g., 'US-CA', 'MX-ROO')"
                },
                "days_back": {
                    "type": "integer",
                    "description": "Number of days back to analyze (1-30, default: 30)",
                    "default": 30
                },
                "locale": {
                    "type": "string",
                    "description": "Language code for common names (default: 'en')",
                    "default": "en"
                }
            },
            "required": ["region"]
        }
    ),
    Tool(
        name="get_location_species_list",
        description="Get complete list of all bird species ever reported at a specific location",
        inputSchema={
            "type": "object",
            "properties": {
                "location_id": {
                    "type": "string",
                    "description": "eBird location ID (e.g., 'L99381') or coordinates as 'lat,lng'"
                },
                "locale": {
                    "type": "string",
                    "description": "Language code for common names (default: 'en')",
                    "default": "en"
                }
            },
            "required": ["location_id"]
        }
    ),
    Tool(
        name="get_subregions",
        description="Get list of subregions (counties, states, provinces) within a geographic region for hierarchical navigation",
        inputSchema={
            "type": "object",
            "properties": {
                "region_code": {
                    "type": "string",
                    "description": "eBird region code (e.g., 'US' for states, 'US-CA' for counties)"
                },
                "region_type": {
                    "type": "string",
                    "description": "Type of subregions to return",
                    "enum": ["country", "subnational1", "subnational2"],
                    "default": "subnational1"
                }
            },
            "required": ["region_code"]
        }
    ),
    Tool(
        name="get_adjacent_regions",
        description="Get neighboring/adjacent regions for cross-border birding trip planning",
        inputSchema={
            "type": "object",
            "properties": {
                "region_code": {
                    "type": "string",
                    "description": "eBird region code (e.g., 'US-CA', 'MX-BCN')"
                }
            },
            "required": ["region_code"]
        }
    ),
    Tool(
        name="get_elevation_data",
        description="Get elevation information and habitat zone analysis for birding locations",
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
                "radius_km": {
                    "type": "integer",
                    "description": "Search radius in kilometers (default: 25, max: 50)",
                    "default": 25
                }
            },
            "required": ["latitude", "longitude"]
        }
    )
]