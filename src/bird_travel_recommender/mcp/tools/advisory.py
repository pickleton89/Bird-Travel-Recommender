"""
LLM-enhanced birding advice MCP tool definitions
"""

from mcp.types import Tool

# LLM-enhanced birding advice tools
ADVISORY_TOOLS = [
    Tool(
        name="get_birding_advice",
        description="Get expert birding advice enhanced with LLM intelligence and current eBird data",
        inputSchema={
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Birding question or scenario needing expert advice",
                },
                "location": {
                    "type": "string",
                    "description": "Location context (city, region, or coordinates)",
                },
                "species_of_interest": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific species the user is interested in (optional)",
                },
                "time_of_year": {
                    "type": "string",
                    "description": "Time period for advice (e.g., 'March', 'spring migration', 'current') - defaults to current",
                },
                "experience_level": {
                    "type": "string",
                    "enum": ["beginner", "intermediate", "advanced"],
                    "description": "Birder's experience level for tailored advice",
                },
            },
            "required": ["question", "location"],
        },
    )
]
