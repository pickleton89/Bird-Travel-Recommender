"""
Node factory and dependency injection system.

This module provides the factory pattern for creating nodes with proper
dependencies, enabling clean separation of concerns and easy testing.
"""

from typing import Type, Dict, Any, Optional, List, Protocol
from dataclasses import dataclass

from .base import BaseNode, ExecutionMode, NodeExecutor
from ..config.settings import settings
from ..config.logging import get_logger
from ..ebird.client import EBirdClient


class CacheProtocol(Protocol):
    """Protocol for cache implementations."""
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        ...
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        ...
    
    async def delete(self, key: str) -> None:
        """Delete value from cache."""
        ...


class MetricsProtocol(Protocol):
    """Protocol for metrics collection."""
    
    def increment(self, metric_name: str, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        ...
    
    def timing(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a timing metric."""
        ...
    
    def gauge(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a gauge metric."""
        ...


@dataclass
class NodeDependencies:
    """
    Dependency injection container for nodes.
    
    This class encapsulates all external dependencies that nodes might need,
    enabling clean separation of concerns and easy testing through mocking.
    """
    
    ebird_client: EBirdClient
    executor: NodeExecutor
    execution_mode: ExecutionMode
    cache: Optional[CacheProtocol] = None
    metrics: Optional[MetricsProtocol] = None
    logger_factory: Optional[callable] = None
    
    @classmethod
    def create_default(cls, mode: ExecutionMode = ExecutionMode.ASYNC) -> 'NodeDependencies':
        """
        Create default dependencies using application settings.
        
        Args:
            mode: Execution mode for the eBird client
            
        Returns:
            NodeDependencies with default implementations
        """
        # Import here to avoid circular imports
        from ..ebird.client import EBirdClient
        
        return cls(
            ebird_client=EBirdClient(
                api_key=settings.ebird_api_key,
                mode=mode
            ),
            executor=NodeExecutor(),
            execution_mode=mode,
            cache=_get_cache_implementation() if settings.cache_enabled else None,
            metrics=_get_metrics_implementation() if hasattr(settings, 'metrics_enabled') and settings.metrics_enabled else None,
            logger_factory=get_logger
        )
    
    @classmethod
    def create_for_testing(cls, mode: ExecutionMode = ExecutionMode.ASYNC, **overrides) -> 'NodeDependencies':
        """
        Create dependencies for testing with optional overrides.
        
        Args:
            mode: Execution mode
            **overrides: Specific dependencies to override
            
        Returns:
            NodeDependencies with test-friendly implementations
        """
        defaults = cls.create_default(mode)
        
        # Apply any overrides
        for key, value in overrides.items():
            if hasattr(defaults, key):
                setattr(defaults, key, value)
        
        return defaults


class NodeFactory:
    """
    Factory for creating nodes with proper dependencies.
    
    This factory manages node registration and creation, ensuring that all
    nodes receive the appropriate dependencies for their execution context.
    """
    
    _node_registry: Dict[str, Type[BaseNode]] = {}
    _node_aliases: Dict[str, str] = {}
    
    @classmethod
    def register_node(cls, name: str, node_class: Type[BaseNode], aliases: Optional[List[str]] = None):
        """
        Register a node class with the factory.
        
        Args:
            name: Primary name for the node
            node_class: Node class to register
            aliases: Optional list of alternative names
        """
        if not issubclass(node_class, BaseNode):
            raise ValueError(f"Node class {node_class} must inherit from BaseNode")
        
        cls._node_registry[name] = node_class
        
        # Register aliases
        if aliases:
            for alias in aliases:
                cls._node_aliases[alias] = name
        
        # Log registration
        logger = get_logger("NodeFactory")
        logger.debug(f"Registered node '{name}' -> {node_class.__name__}")
    
    @classmethod
    def create_node(cls, name: str, mode: ExecutionMode = ExecutionMode.ASYNC, 
                   dependencies: Optional[NodeDependencies] = None, **kwargs) -> BaseNode:
        """
        Create a node instance with dependencies.
        
        Args:
            name: Name of the node to create
            mode: Execution mode for the node
            dependencies: Pre-configured dependencies (optional)
            **kwargs: Additional arguments for node construction
            
        Returns:
            Configured node instance
            
        Raises:
            ValueError: If node name is not registered
        """
        # Resolve aliases
        actual_name = cls._node_aliases.get(name, name)
        
        if actual_name not in cls._node_registry:
            raise ValueError(f"Unknown node: {name}. Available nodes: {cls.list_available_nodes()}")
        
        node_class = cls._node_registry[actual_name]
        
        # Create dependencies if not provided
        if dependencies is None:
            dependencies = NodeDependencies.create_default(mode)
        
        # Create and return the node
        return node_class(dependencies, **kwargs)
    
    @classmethod
    def create_sightings_node(cls, mode: ExecutionMode = ExecutionMode.ASYNC, **kwargs) -> BaseNode:
        """
        Convenience method for creating sightings node.
        
        Args:
            mode: Execution mode
            **kwargs: Additional arguments
            
        Returns:
            Configured sightings node
        """
        return cls.create_node("sightings", mode, **kwargs)
    
    @classmethod
    def create_validation_node(cls, mode: ExecutionMode = ExecutionMode.ASYNC, **kwargs) -> BaseNode:
        """
        Convenience method for creating species validation node.
        
        Args:
            mode: Execution mode
            **kwargs: Additional arguments
            
        Returns:
            Configured validation node
        """
        return cls.create_node("species_validation", mode, **kwargs)
    
    @classmethod
    def list_available_nodes(cls) -> List[str]:
        """
        List all registered node names.
        
        Returns:
            List of available node names
        """
        nodes = list(cls._node_registry.keys())
        aliases = list(cls._node_aliases.keys())
        return sorted(nodes + aliases)
    
    @classmethod
    def get_node_info(cls, name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a registered node.
        
        Args:
            name: Node name to query
            
        Returns:
            Node information dictionary or None if not found
        """
        actual_name = cls._node_aliases.get(name, name)
        
        if actual_name not in cls._node_registry:
            return None
        
        node_class = cls._node_registry[actual_name]
        
        return {
            "name": actual_name,
            "class": node_class.__name__,
            "module": node_class.__module__,
            "doc": node_class.__doc__,
            "aliases": [alias for alias, target in cls._node_aliases.items() if target == actual_name]
        }
    
    @classmethod
    def clear_registry(cls):
        """Clear the node registry (useful for testing)."""
        cls._node_registry.clear()
        cls._node_aliases.clear()


def register_node(name: str, aliases: Optional[List[str]] = None):
    """
    Decorator to auto-register nodes with the factory.
    
    Args:
        name: Primary name for the node
        aliases: Optional list of alternative names
        
    Returns:
        Decorator function
    """
    def decorator(node_class: Type[BaseNode]):
        NodeFactory.register_node(name, node_class, aliases)
        return node_class
    return decorator


# Helper functions for dependency creation

def _get_cache_implementation() -> Optional[CacheProtocol]:
    """
    Get the configured cache implementation.
    
    Returns:
        Cache implementation or None if not available
    """
    try:
        # Try to import and create cache implementation
        # This is a placeholder - actual implementation would depend on configuration
        if hasattr(settings, 'redis_url') and settings.redis_url:
            from .cache_implementations import RedisCache
            return RedisCache(settings.redis_url)
        else:
            from .cache_implementations import MemoryCache
            return MemoryCache()
    except ImportError:
        # Cache implementation not available
        return None


def _get_metrics_implementation() -> Optional[MetricsProtocol]:
    """
    Get the configured metrics implementation.
    
    Returns:
        Metrics implementation or None if not available
    """
    try:
        # Try to import and create metrics implementation
        # This is a placeholder - actual implementation would depend on configuration
        if hasattr(settings, 'metrics_backend') and settings.metrics_backend:
            if settings.metrics_backend == 'statsd':
                from .metrics_implementations import StatsDMetrics
                return StatsDMetrics(settings.statsd_host, settings.statsd_port)
            elif settings.metrics_backend == 'prometheus':
                from .metrics_implementations import PrometheusMetrics
                return PrometheusMetrics()
        
        # Fallback to logging metrics
        from .metrics_implementations import LoggingMetrics
        return LoggingMetrics()
    except ImportError:
        # Metrics implementation not available
        return None


# Batch creation utilities

def create_workflow_nodes(node_names: List[str], mode: ExecutionMode = ExecutionMode.ASYNC, 
                         shared_dependencies: Optional[NodeDependencies] = None) -> Dict[str, BaseNode]:
    """
    Create multiple nodes for a workflow with shared dependencies.
    
    Args:
        node_names: List of node names to create
        mode: Execution mode for all nodes
        shared_dependencies: Shared dependencies (created if None)
        
    Returns:
        Dictionary mapping node names to instances
    """
    if shared_dependencies is None:
        shared_dependencies = NodeDependencies.create_default(mode)
    
    nodes = {}
    for name in node_names:
        try:
            nodes[name] = NodeFactory.create_node(name, mode, shared_dependencies)
        except ValueError as e:
            logger = get_logger("NodeFactory")
            logger.error(f"Failed to create node '{name}': {e}")
            raise
    
    return nodes


def validate_workflow_nodes(node_names: List[str]) -> List[str]:
    """
    Validate that all required nodes are available.
    
    Args:
        node_names: List of node names to validate
        
    Returns:
        List of missing node names (empty if all available)
    """
    available_nodes = set(NodeFactory.list_available_nodes())
    missing_nodes = []
    
    for name in node_names:
        actual_name = NodeFactory._node_aliases.get(name, name)
        if actual_name not in available_nodes:
            missing_nodes.append(name)
    
    return missing_nodes