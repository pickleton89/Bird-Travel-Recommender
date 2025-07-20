"""
Bird Travel Recommender - A PocketFlow-based birding travel planning system.

This package provides intelligent birding trip recommendations using eBird data
and LLM-powered itinerary generation.
"""

__version__ = "0.1.0"
__author__ = "Bird Travel Recommender Team"

# Only import flow-related modules if not running as MCP server
import sys
import os

# Check if running as MCP server - use environment variable as well
is_mcp_server = (
    os.environ.get('BIRD_TRAVEL_MCP_SERVER') == '1' or
    any("mcp" in arg for arg in sys.argv) or 
    "mcp_server" in sys.modules or
    # Check if being imported by MCP server module or running as mcp.server
    any("bird_travel_recommender.mcp" in mod for mod in sys.modules) or
    # Check if __main__ module is the MCP server
    (hasattr(sys.modules.get('__main__'), '__file__') and 
     sys.modules['__main__'].__file__ and 
     'mcp' in sys.modules['__main__'].__file__) or
    # Check if running with -m and the module name contains mcp
    (len(sys.argv) > 0 and sys.argv[0] == '-m' and 
     hasattr(sys.modules.get('__main__'), '__spec__') and 
     sys.modules['__main__'].__spec__ and 
     'mcp' in sys.modules['__main__'].__spec__.name)
)

if not is_mcp_server:
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
