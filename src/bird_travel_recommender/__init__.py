"""
Bird Travel Recommender - A PocketFlow-based birding travel planning system.

This package provides intelligent birding trip recommendations using eBird data
and LLM-powered itinerary generation.
"""

__version__ = "0.1.0"
__author__ = "Bird Travel Recommender Team"

# Only import flow-related modules if not running as MCP server
import sys

if not any("mcp" in arg for arg in sys.argv) and "mcp_server" not in sys.modules:
    try:
        from .flow import run_birding_pipeline, create_birding_flow
        from .main import main

        __all__ = ["run_birding_pipeline", "create_birding_flow", "main"]
    except ImportError:
        # Running without pocketflow dependencies
        __all__ = []
else:
    # MCP server mode - minimal imports
    __all__ = []
