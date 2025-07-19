"""
Core module for the Bird Travel Recommender.

This module contains the foundational components that eliminate code duplication
and provide a unified architecture for the entire application.
"""

# MCP Registry System
from .mcp import (
    ToolRegistry,
    tool,
    registry,
    middleware,
    error_handler,
    performance_monitor,
    ToolDependencies,
    get_dependencies
)

__all__ = [
    # MCP System
    "ToolRegistry",
    "tool",
    "registry", 
    "middleware",
    "error_handler",
    "performance_monitor",
    "ToolDependencies",
    "get_dependencies"
]