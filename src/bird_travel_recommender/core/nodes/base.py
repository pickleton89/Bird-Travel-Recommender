"""
Abstract base classes for unified node implementations.

This module provides the foundation for all nodes in the Bird Travel Recommender,
supporting both sync and async execution modes through a common interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Protocol, TYPE_CHECKING
from enum import Enum
from pydantic import BaseModel, Field
import asyncio
from datetime import datetime

from ..config.logging import get_logger
from ..exceptions.base import BirdTravelRecommenderError

if TYPE_CHECKING:
    from .factory import NodeDependencies


class ExecutionMode(Enum):
    """Execution mode for node operations."""
    SYNC = "sync"
    ASYNC = "async"


class NodeInput(BaseModel):
    """Base class for node inputs with validation."""
    
    class Config:
        extra = "allow"  # Allow additional fields
        validate_assignment = True


class NodeOutput(BaseModel):
    """Base class for node outputs with validation."""
    
    success: bool = Field(..., description="Whether the operation succeeded")
    data: Optional[Dict[str, Any]] = Field(None, description="Output data from the node")
    error: Optional[str] = Field(None, description="Error message if operation failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    execution_time_ms: Optional[float] = Field(None, description="Execution time in milliseconds")


class NodeProtocol(Protocol):
    """Protocol defining the node interface."""
    
    async def execute(self, shared_store: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the node with the shared store."""
        ...


class BaseNode(ABC):
    """
    Abstract base class for all nodes.
    
    Provides a unified interface for both sync and async execution modes,
    eliminating the need for separate sync/async implementations.
    """
    
    def __init__(self, dependencies: 'NodeDependencies'):
        """
        Initialize the node with dependencies.
        
        Args:
            dependencies: Injected dependencies for the node
        """
        self.deps = dependencies
        self.logger = get_logger(self.__class__.__name__)
        self._execution_mode = dependencies.execution_mode
        self._start_time: Optional[float] = None
    
    @abstractmethod
    async def process(self, shared_store: Dict[str, Any]) -> NodeOutput:
        """
        Core processing logic - always async.
        
        This method contains the actual business logic and should be implemented
        by concrete node classes. The execution mode is handled transparently
        by the infrastructure.
        
        Args:
            shared_store: Shared data store for the workflow
            
        Returns:
            NodeOutput with processing results
        """
        pass
    
    def prep(self, shared_store: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preparation logic - shared between sync/async.
        
        Override this method to perform any setup before processing.
        This method is always synchronous.
        
        Args:
            shared_store: Shared data store for the workflow
            
        Returns:
            Modified shared store
        """
        self.logger.info(f"Preparing {self.__class__.__name__}")
        return shared_store
    
    def validate_input(self, data: Dict[str, Any]) -> NodeInput:
        """
        Validate input data using Pydantic models.
        
        Override in subclasses with specific input models.
        
        Args:
            data: Input data to validate
            
        Returns:
            Validated input model
            
        Raises:
            ValidationError: If input validation fails
        """
        return NodeInput(**data)
    
    def post_process(self, shared_store: Dict[str, Any], result: NodeOutput) -> Dict[str, Any]:
        """
        Post-processing logic after execution.
        
        Override this method to perform any cleanup or additional processing
        after the main execution.
        
        Args:
            shared_store: Shared data store for the workflow
            result: Result from the process method
            
        Returns:
            Modified shared store
        """
        if result.success and result.data:
            shared_store.update(result.data)
            self.logger.info(f"{self.__class__.__name__} completed successfully")
        else:
            self.logger.error(f"{self.__class__.__name__} failed: {result.error}")
        
        return shared_store
    
    async def execute(self, shared_store: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main execution method with error handling and timing.
        
        This method orchestrates the complete node execution lifecycle:
        1. Preparation
        2. Input validation  
        3. Core processing
        4. Post-processing
        5. Error handling and timing
        
        Args:
            shared_store: Shared data store for the workflow
            
        Returns:
            Modified shared store
        """
        import time
        self._start_time = time.time()
        
        try:
            # Preparation phase
            prepared_store = self.prep(shared_store)
            
            # Input validation
            self.validate_input(prepared_store)
            
            # Core processing (always async)
            result = await self.process(prepared_store)
            
            # Add execution timing
            if self._start_time:
                execution_time = (time.time() - self._start_time) * 1000
                result.execution_time_ms = execution_time
                result.metadata["execution_mode"] = self._execution_mode.value
                result.metadata["node_class"] = self.__class__.__name__
                result.metadata["timestamp"] = datetime.utcnow().isoformat()
            
            # Post-processing
            final_store = self.post_process(prepared_store, result)
            
            return final_store
            
        except Exception as e:
            self.logger.error(f"Unexpected error in {self.__class__.__name__}: {e}")
            
            # Create error result
            error_result = NodeOutput(
                success=False,
                error=str(e),
                metadata={
                    "node_class": self.__class__.__name__,
                    "execution_mode": self._execution_mode.value,
                    "timestamp": datetime.utcnow().isoformat(),
                    "exception_type": type(e).__name__
                }
            )
            
            if self._start_time:
                error_result.execution_time_ms = (time.time() - self._start_time) * 1000
            
            # Still run post-processing for cleanup
            final_store = self.post_process(shared_store, error_result)
            
            # Re-raise the exception after cleanup
            raise BirdTravelRecommenderError(
                f"Node execution failed: {str(e)}",
                code=f"NODE_EXECUTION_ERROR_{self.__class__.__name__}",
                context={"node_class": self.__class__.__name__, "original_error": str(e)}
            )


class NodeExecutor:
    """
    Handles execution mode conversion between sync and async.
    
    This class provides the bridge between sync and async execution modes,
    allowing nodes to be used in both contexts transparently.
    """
    
    @staticmethod
    async def execute_async(node: BaseNode, shared_store: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute node in async mode.
        
        Args:
            node: Node to execute
            shared_store: Shared data store
            
        Returns:
            Modified shared store
        """
        return await node.execute(shared_store)
    
    @staticmethod
    def execute_sync(node: BaseNode, shared_store: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute node in sync mode using asyncio.
        
        This method handles the conversion from sync to async execution,
        managing event loops appropriately.
        
        Args:
            node: Node to execute
            shared_store: Shared data store
            
        Returns:
            Modified shared store
        """
        try:
            # Try to get current event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, we need to use a thread pool
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, node.execute(shared_store))
                    return future.result()
            else:
                # If no loop is running, use asyncio.run
                return asyncio.run(node.execute(shared_store))
        except RuntimeError:
            # Fallback for edge cases
            return asyncio.run(node.execute(shared_store))
    
    @classmethod
    def execute_by_mode(cls, node: BaseNode, shared_store: Dict[str, Any], 
                       mode: ExecutionMode) -> Dict[str, Any]:
        """
        Execute node according to the specified mode.
        
        Args:
            node: Node to execute
            shared_store: Shared data store
            mode: Execution mode (sync or async)
            
        Returns:
            Modified shared store
        """
        if mode == ExecutionMode.ASYNC:
            # For async mode, we need to be in an async context
            if asyncio.iscoroutinefunction(cls.execute_async):
                # If we're already in an async context, this will work
                return cls.execute_async(node, shared_store)
            else:
                # Convert to async
                return asyncio.run(cls.execute_async(node, shared_store))
        else:
            return cls.execute_sync(node, shared_store)


class BatchProcessingMixin:
    """
    Mixin for nodes that need to process multiple items in batch.
    
    This provides utilities for batch processing with proper error handling
    and result aggregation.
    """
    
    async def process_batch(self, items: list, process_func, max_concurrency: int = 10) -> list:
        """
        Process a batch of items with controlled concurrency.
        
        Args:
            items: List of items to process
            process_func: Async function to process each item
            max_concurrency: Maximum number of concurrent operations
            
        Returns:
            List of results (may include exceptions)
        """
        semaphore = asyncio.Semaphore(max_concurrency)
        
        async def bounded_process(item):
            async with semaphore:
                return await process_func(item)
        
        tasks = [bounded_process(item) for item in items]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    def aggregate_batch_results(self, results: list, item_count: int) -> Dict[str, Any]:
        """
        Aggregate results from batch processing.
        
        Args:
            results: List of results from batch processing
            item_count: Original number of items processed
            
        Returns:
            Aggregated statistics and data
        """
        successful_results = []
        failed_results = []
        exceptions = []
        
        for result in results:
            if isinstance(result, Exception):
                exceptions.append(result)
            elif isinstance(result, dict) and result.get("success", False):
                successful_results.append(result)
            else:
                failed_results.append(result)
        
        return {
            "total_items": item_count,
            "successful_count": len(successful_results),
            "failed_count": len(failed_results),
            "exception_count": len(exceptions),
            "success_rate": len(successful_results) / item_count if item_count > 0 else 0,
            "successful_results": successful_results,
            "failed_results": failed_results,
            "exceptions": [str(e) for e in exceptions]
        }