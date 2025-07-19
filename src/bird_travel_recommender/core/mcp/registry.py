"""Tool registry for MCP server with decorator-based registration."""

from typing import Dict, Any, List, Callable, Optional, Type, Union
from functools import wraps
from dataclasses import dataclass, field
import inspect
import asyncio
from datetime import datetime
import uuid

import logging


@dataclass
class ToolDefinition:
    """Complete tool definition with metadata and execution capabilities."""
    
    name: str
    func: Callable
    description: str
    category: str
    schema: Dict[str, Any]
    middleware_stack: List[Callable] = field(default_factory=list)
    
    def add_middleware(self, middleware: Callable) -> None:
        """Add middleware to this tool's execution stack."""
        self.middleware_stack.append(middleware)
        
    async def execute(self, **kwargs) -> Any:
        """Execute tool with middleware stack applied."""
        correlation_id = str(uuid.uuid4())
        logger = logging.getLogger(f"tool.{self.name}")
        
        try:
            # Apply middleware in order (pre-execution)
            for middleware in self.middleware_stack:
                if inspect.iscoroutinefunction(middleware):
                    kwargs = await middleware(self.func, kwargs, correlation_id)
                else:
                    kwargs = middleware(self.func, kwargs, correlation_id)
                    
            # Execute the actual function
            logger.info(f"Executing tool {self.name}", extra={"correlation_id": correlation_id})
            
            if inspect.iscoroutinefunction(self.func):
                result = await self.func(**kwargs)
            else:
                result = self.func(**kwargs)
                
            logger.info(f"Tool {self.name} completed successfully", extra={"correlation_id": correlation_id})
            return result
            
        except Exception as e:
            logger.error(f"Tool {self.name} execution failed: {e}", extra={
                "correlation_id": correlation_id,
                "error_type": type(e).__name__
            })
            raise


class ToolRegistry:
    """Global registry for all MCP tools with automatic routing."""
    
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._categories: Dict[str, List[str]] = {}
        self._global_middleware: List[Callable] = []
        
    def register_tool(self, tool_def: ToolDefinition) -> None:
        """Register a tool definition in the registry."""
        self._tools[tool_def.name] = tool_def
        
        # Add to category index
        category_tools = self._categories.setdefault(tool_def.category, [])
        if tool_def.name not in category_tools:
            category_tools.append(tool_def.name)
            
        # Apply global middleware to this tool
        for middleware in self._global_middleware:
            tool_def.add_middleware(middleware)
            
    def add_global_middleware(self, middleware: Callable) -> None:
        """Add middleware to all tools (existing and future)."""
        self._global_middleware.append(middleware)
        
        # Apply to existing tools
        for tool_def in self._tools.values():
            tool_def.add_middleware(middleware)
            
    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Get tool definition by name."""
        return self._tools.get(name)
        
    def list_tools(self, category: Optional[str] = None) -> List[str]:
        """List available tools, optionally filtered by category."""
        if category:
            return self._categories.get(category, [])
        return list(self._tools.keys())
        
    def get_categories(self) -> List[str]:
        """Get list of all tool categories."""
        return list(self._categories.keys())
        
    def get_tools_for_mcp(self) -> List[Dict[str, Any]]:
        """Generate MCP-compatible tool definitions."""
        tools = []
        
        for tool_def in self._tools.values():
            tools.append({
                "name": tool_def.name,
                "description": tool_def.description,
                "inputSchema": tool_def.schema
            })
            
        return tools
        
    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool by name with given arguments."""
        tool_def = self.get_tool(name)
        if not tool_def:
            raise ValueError(f"Tool '{name}' not found in registry")
            
        return await tool_def.execute(**arguments)
        
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_tools": len(self._tools),
            "categories": len(self._categories),
            "tools_by_category": {
                category: len(tools) 
                for category, tools in self._categories.items()
            },
            "global_middleware_count": len(self._global_middleware)
        }


def generate_schema_from_function(func: Callable) -> Dict[str, Any]:
    """Generate JSON schema from function signature and type hints."""
    sig = inspect.signature(func)
    properties = {}
    required = []
    
    for param_name, param in sig.parameters.items():
        if param_name in ['self', 'args', 'kwargs']:
            continue
            
        param_type = param.annotation
        param_schema = {"type": "string"}  # Default type
        
        # Map Python types to JSON schema types
        if param_type == int:
            param_schema = {"type": "integer"}
        elif param_type == float:
            param_schema = {"type": "number"}
        elif param_type == bool:
            param_schema = {"type": "boolean"}
        elif param_type == list or param_type == List:
            param_schema = {"type": "array"}
        elif param_type == dict or param_type == Dict:
            param_schema = {"type": "object"}
        elif hasattr(param_type, '__origin__'):
            # Handle generic types like Optional[str], List[str], etc.
            origin = param_type.__origin__
            args = getattr(param_type, '__args__', ())
            
            if origin is Union:
                # Handle Optional[T] (Union[T, None])
                if len(args) == 2 and type(None) in args:
                    non_none_type = args[0] if args[1] is type(None) else args[1]
                    param_schema = _type_to_schema(non_none_type)
                else:
                    param_schema = {"anyOf": [_type_to_schema(arg) for arg in args]}
            elif origin in (list, List):
                param_schema = {"type": "array"}
                if args:
                    param_schema["items"] = _type_to_schema(args[0])
            elif origin in (dict, Dict):
                param_schema = {"type": "object"}
                
        # Add description from docstring if available
        if func.__doc__:
            # Simple extraction - could be enhanced with proper docstring parsing
            param_schema["description"] = f"Parameter for {func.__name__}"
            
        properties[param_name] = param_schema
        
        # Add to required if no default value
        if param.default == inspect.Parameter.empty:
            required.append(param_name)
            
    return {
        "type": "object",
        "properties": properties,
        "required": required
    }


def _type_to_schema(type_hint) -> Dict[str, Any]:
    """Convert a type hint to JSON schema."""
    if type_hint == int:
        return {"type": "integer"}
    elif type_hint == float:
        return {"type": "number"}
    elif type_hint == bool:
        return {"type": "boolean"}
    elif type_hint == str:
        return {"type": "string"}
    elif type_hint in (list, List):
        return {"type": "array"}
    elif type_hint in (dict, Dict):
        return {"type": "object"}
    else:
        return {"type": "string"}  # Default fallback


def tool(name: str, description: str, category: str = "general", 
         schema: Optional[Dict[str, Any]] = None):
    """Decorator to register a function as an MCP tool.
    
    Args:
        name: Tool name for MCP registration
        description: Tool description for MCP
        category: Tool category for organization
        schema: Optional custom schema (auto-generated if not provided)
    """
    def decorator(func: Callable) -> Callable:
        # Generate schema from function signature if not provided
        tool_schema = schema or generate_schema_from_function(func)
        
        # Create tool definition
        tool_def = ToolDefinition(
            name=name,
            func=func,
            description=description,
            category=category,
            schema=tool_schema
        )
        
        # Register the tool
        registry.register_tool(tool_def)
        
        # Return the original function unchanged
        return func
        
    return decorator


# Global registry instance
registry = ToolRegistry()