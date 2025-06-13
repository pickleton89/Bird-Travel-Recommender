"""
Core birding pipeline processing MCP tool definitions
"""

from mcp.types import Tool

# Core pipeline processing tools
PIPELINE_TOOLS = [
    Tool(
        name="fetch_sightings",
        description="Retrieve recent bird sighting data from eBird for target species and locations",
        inputSchema={
            "type": "object",
            "properties": {
                "species_codes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of eBird species codes to fetch sightings for"
                },
                "regions": {
                    "type": "array", 
                    "items": {"type": "string"},
                    "description": "Array of eBird region codes to search within"
                },
                "days_back": {
                    "type": "integer",
                    "description": "Number of days back to search (default: 30)",
                    "default": 30
                }
            },
            "required": ["species_codes", "regions"]
        }
    ),
    Tool(
        name="filter_constraints",
        description="Apply geographic, temporal, and preference-based filtering to sighting data",
        inputSchema={
            "type": "object",
            "properties": {
                "data": {
                    "type": "object",
                    "description": "Sighting data from fetch_sightings"
                },
                "filters": {
                    "type": "object",
                    "properties": {
                        "max_distance_km": {"type": "number"},
                        "min_confidence": {"type": "number"},
                        "exclude_locations": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "description": "Filtering criteria to apply"
                }
            },
            "required": ["data"]
        }
    ),
    Tool(
        name="cluster_hotspots",
        description="Group birding locations geographically to identify optimal birding areas",
        inputSchema={
            "type": "object",
            "properties": {
                "data": {
                    "type": "object",
                    "description": "Filtered sighting data from filter_constraints"
                },
                "cluster_params": {
                    "type": "object",
                    "properties": {
                        "max_cluster_radius": {"type": "number"},
                        "min_locations_per_cluster": {"type": "integer"}
                    },
                    "description": "Clustering parameters"
                }
            },
            "required": ["data"]
        }
    ),
    Tool(
        name="score_locations",
        description="Rank birding locations based on species diversity, rarity, and accessibility",
        inputSchema={
            "type": "object",
            "properties": {
                "data": {
                    "type": "object",
                    "description": "Clustered sighting data from cluster_hotspots"
                },
                "scoring_weights": {
                    "type": "object",
                    "properties": {
                        "species_diversity": {"type": "number"},
                        "rarity_bonus": {"type": "number"},
                        "accessibility": {"type": "number"}
                    },
                    "description": "Scoring weights for location ranking"
                }
            },
            "required": ["data"]
        }
    ),
    Tool(
        name="optimize_route",
        description="Calculate optimal travel routes between high-scoring birding locations",
        inputSchema={
            "type": "object",
            "properties": {
                "data": {
                    "type": "object",
                    "description": "Scored location data from score_locations"
                },
                "route_params": {
                    "type": "object",
                    "properties": {
                        "max_daily_driving": {"type": "number"},
                        "preferred_start_location": {"type": "string"},
                        "optimization_goal": {
                            "type": "string",
                            "enum": ["shortest_distance", "highest_score", "balanced"]
                        }
                    },
                    "description": "Route optimization parameters"
                }
            },
            "required": ["data"]
        }
    )
]