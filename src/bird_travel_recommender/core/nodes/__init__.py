"""
Core node infrastructure for the Bird Travel Recommender.

This module provides the foundation for unified node implementations that support
both sync and async execution modes, eliminating code duplication and providing
a clean, modern architecture.
"""

from .base import (
    BaseNode, 
    NodeInput, 
    NodeOutput, 
    ExecutionMode, 
    NodeExecutor,
    BatchProcessingMixin
)
from .factory import (
    NodeFactory, 
    register_node, 
    NodeDependencies,
    create_workflow_nodes,
    validate_workflow_nodes
)
from .mixins import (
    ValidationMixin, 
    CachingMixin, 
    LoggingMixin,
    MetricsMixin,
    ErrorHandlingMixin
)

# Import implementations to trigger auto-registration
from .implementations import *

__all__ = [
    # Base classes and enums
    "BaseNode",
    "NodeInput", 
    "NodeOutput",
    "ExecutionMode",
    "NodeExecutor",
    "BatchProcessingMixin",
    
    # Factory and dependencies
    "NodeFactory",
    "register_node",
    "NodeDependencies",
    "create_workflow_nodes",
    "validate_workflow_nodes",
    
    # Mixins
    "ValidationMixin",
    "CachingMixin", 
    "LoggingMixin",
    "MetricsMixin",
    "ErrorHandlingMixin",
]