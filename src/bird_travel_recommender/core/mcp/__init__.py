"""Core MCP registry and middleware system.

This module provides a modern tool registry and middleware stack for the MCP server,
replacing the traditional if/elif routing with a decorator-based approach.
"""

from .registry import ToolRegistry, tool, registry
from .middleware import middleware, error_handler, performance_monitor
from .dependencies import ToolDependencies, get_dependencies

__all__ = [
    "ToolRegistry",
    "tool", 
    "registry",
    "middleware",
    "error_handler",
    "performance_monitor", 
    "ToolDependencies",
    "get_dependencies"
]