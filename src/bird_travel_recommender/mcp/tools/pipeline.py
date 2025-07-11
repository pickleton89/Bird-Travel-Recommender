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
                    "description": "Array of eBird species codes to fetch sightings for",
                },
                "regions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of eBird region codes to search within",
                },
                "days_back": {
                    "type": "integer",
                    "description": "Number of days back to search (default: 30)",
                    "default": 30,
                },
            },
            "required": ["species_codes", "regions"],
        },
    ),
    Tool(
        name="filter_constraints",
        description="Apply geographic, temporal, and preference-based filtering to sighting data",
        inputSchema={
            "type": "object",
            "properties": {
                "data": {
                    "type": "object",
                    "description": "Sighting data from fetch_sightings",
                },
                "filters": {
                    "type": "object",
                    "properties": {
                        "max_distance_km": {"type": "number"},
                        "min_confidence": {"type": "number"},
                        "exclude_locations": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "description": "Filtering criteria to apply",
                },
            },
            "required": ["data"],
        },
    ),
    Tool(
        name="cluster_hotspots",
        description="Group birding locations geographically to identify optimal birding areas",
        inputSchema={
            "type": "object",
            "properties": {
                "data": {
                    "type": "object",
                    "description": "Filtered sighting data from filter_constraints",
                },
                "cluster_params": {
                    "type": "object",
                    "properties": {
                        "max_cluster_radius": {"type": "number"},
                        "min_locations_per_cluster": {"type": "integer"},
                    },
                    "description": "Clustering parameters",
                },
            },
            "required": ["data"],
        },
    ),
    Tool(
        name="score_locations",
        description="Rank birding locations based on species diversity, rarity, and accessibility",
        inputSchema={
            "type": "object",
            "properties": {
                "data": {
                    "type": "object",
                    "description": "Clustered sighting data from cluster_hotspots",
                },
                "scoring_weights": {
                    "type": "object",
                    "properties": {
                        "species_diversity": {"type": "number"},
                        "rarity_bonus": {"type": "number"},
                        "accessibility": {"type": "number"},
                    },
                    "description": "Scoring weights for location ranking",
                },
            },
            "required": ["data"],
        },
    ),
    Tool(
        name="optimize_route",
        description="Calculate optimal travel routes between high-scoring birding locations",
        inputSchema={
            "type": "object",
            "properties": {
                "data": {
                    "type": "object",
                    "description": "Scored location data from score_locations",
                },
                "route_params": {
                    "type": "object",
                    "properties": {
                        "max_daily_driving": {"type": "number"},
                        "preferred_start_location": {"type": "string"},
                        "optimization_goal": {
                            "type": "string",
                            "enum": ["shortest_distance", "highest_score", "balanced"],
                        },
                    },
                    "description": "Route optimization parameters",
                },
            },
            "required": ["data"],
        },
    ),
    Tool(
        name="get_historic_observations",
        description="Get historical observations for a specific date in a region for seasonal planning and trend analysis",
        inputSchema={
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "description": "eBird region code (e.g., 'US-CA', 'MX-ROO')",
                },
                "year": {"type": "integer", "description": "Year (e.g., 2023)"},
                "month": {"type": "integer", "description": "Month (1-12)"},
                "day": {"type": "integer", "description": "Day (1-31)"},
                "species_code": {
                    "type": "string",
                    "description": "Optional species code to filter results",
                    "default": "",
                },
                "locale": {
                    "type": "string",
                    "description": "Language code for common names (default: 'en')",
                    "default": "en",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum observations to return (default: 1000)",
                    "default": 1000,
                },
            },
            "required": ["region", "year", "month", "day"],
        },
    ),
    Tool(
        name="get_seasonal_trends",
        description="Analyze seasonal birding trends by aggregating historical observations across months",
        inputSchema={
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "description": "eBird region code (e.g., 'US-CA', 'MX-ROO')",
                },
                "species_code": {
                    "type": "string",
                    "description": "Optional species code for species-specific trends",
                    "default": "",
                },
                "start_year": {
                    "type": "integer",
                    "description": "Starting year for analysis (default: 2020)",
                    "default": 2020,
                },
                "end_year": {
                    "type": "integer",
                    "description": "Ending year for analysis (default: current year)",
                },
                "locale": {
                    "type": "string",
                    "description": "Language code for common names (default: 'en')",
                    "default": "en",
                },
            },
            "required": ["region"],
        },
    ),
    Tool(
        name="get_yearly_comparisons",
        description="Compare birding activity across multiple years for the same date/season",
        inputSchema={
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "description": "eBird region code (e.g., 'US-CA', 'MX-ROO')",
                },
                "reference_date": {
                    "type": "string",
                    "description": "Date in MM-DD format (e.g., '05-15' for May 15th)",
                },
                "years_to_compare": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "List of years to compare (e.g., [2020, 2021, 2022, 2023])",
                },
                "species_code": {
                    "type": "string",
                    "description": "Optional species code for species-specific comparison",
                    "default": "",
                },
                "locale": {
                    "type": "string",
                    "description": "Language code for common names (default: 'en')",
                    "default": "en",
                },
            },
            "required": ["region", "reference_date", "years_to_compare"],
        },
    ),
    Tool(
        name="get_migration_data",
        description="Analyze species migration timing and routes with seasonal patterns",
        inputSchema={
            "type": "object",
            "properties": {
                "species_code": {
                    "type": "string",
                    "description": "eBird species code (e.g., 'norcar' for Northern Cardinal)",
                },
                "region_code": {
                    "type": "string",
                    "description": "eBird region code (default: 'US')",
                    "default": "US",
                },
                "months": {
                    "type": "array",
                    "items": {"type": "integer", "minimum": 1, "maximum": 12},
                    "description": "List of months to analyze (1-12, default: all months)",
                },
            },
            "required": ["species_code"],
        },
    ),
    Tool(
        name="get_peak_times",
        description="Get optimal daily timing recommendations for observing specific species",
        inputSchema={
            "type": "object",
            "properties": {
                "species_code": {
                    "type": "string",
                    "description": "eBird species code (e.g., 'norcar')",
                },
                "latitude": {"type": "number", "description": "Latitude coordinate"},
                "longitude": {"type": "number", "description": "Longitude coordinate"},
                "radius_km": {
                    "type": "integer",
                    "description": "Search radius in kilometers (default: 25)",
                    "default": 25,
                },
            },
            "required": ["species_code", "latitude", "longitude"],
        },
    ),
    Tool(
        name="get_seasonal_hotspots",
        description="Get location rankings optimized for specific seasons",
        inputSchema={
            "type": "object",
            "properties": {
                "region_code": {
                    "type": "string",
                    "description": "eBird region code (e.g., 'US-CA')",
                },
                "season": {
                    "type": "string",
                    "enum": ["spring", "summer", "fall", "winter"],
                    "description": "Season to analyze",
                    "default": "spring",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum hotspots to return (default: 20)",
                    "default": 20,
                },
            },
            "required": ["region_code"],
        },
    ),
]
