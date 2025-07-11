"""
Itinerary generation and trip planning MCP tool definitions
"""

from mcp.types import Tool

# Itinerary generation and trip planning tools
PLANNING_TOOLS = [
    Tool(
        name="generate_itinerary",
        description="Create detailed day-by-day birding itineraries with timing and logistics",
        inputSchema={
            "type": "object",
            "properties": {
                "data": {
                    "type": "object",
                    "description": "Optimized route data from optimize_route",
                },
                "trip_preferences": {
                    "type": "object",
                    "properties": {
                        "trip_duration_days": {"type": "integer"},
                        "daily_start_time": {"type": "string"},
                        "birding_hours_per_day": {"type": "number"},
                        "accommodation_preferences": {"type": "string"},
                    },
                    "description": "Trip planning preferences",
                },
            },
            "required": ["data"],
        },
    ),
    Tool(
        name="plan_complete_trip",
        description="End-to-end birding trip planning with comprehensive orchestration of all pipeline components",
        inputSchema={
            "type": "object",
            "properties": {
                "target_species": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of target bird species names",
                },
                "regions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "eBird region codes to search within",
                },
                "trip_duration_days": {
                    "type": "integer",
                    "description": "Duration of the trip in days",
                },
                "max_daily_driving_hours": {
                    "type": "number",
                    "description": "Maximum driving hours per day (default: 4)",
                    "default": 4,
                },
                "birding_skill_level": {
                    "type": "string",
                    "enum": ["beginner", "intermediate", "advanced"],
                    "description": "Birder's skill level for appropriate recommendations",
                },
            },
            "required": ["target_species", "regions", "trip_duration_days"],
        },
    ),
]
