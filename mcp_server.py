#!/usr/bin/env python3
"""
MCP Server entry point for Bird Travel Recommender
This is a convenience wrapper that imports and runs the actual server
"""

import sys
import asyncio
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import and run the actual server
from bird_travel_recommender.mcp.server import main

if __name__ == "__main__":
    asyncio.run(main())