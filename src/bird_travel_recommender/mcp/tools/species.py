"""
Species-related MCP tool definitions
"""

from mcp.types import Tool

# Species validation and regional species tools
SPECIES_TOOLS = [
    Tool(
        name="validate_species",
        description="Validate bird species names using eBird taxonomy lookup",
        inputSchema={
            "type": "object",
            "properties": {
                "species_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of species names to validate"
                }
            },
            "required": ["species_names"]
        }
    ),
    Tool(
        name="get_regional_species_list",
        description="Get comprehensive list of all bird species ever reported in a region",
        inputSchema={
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "description": "eBird region code (e.g., 'US-CA' for California, 'MX' for Mexico)"
                }
            },
            "required": ["region"]
        }
    )
]