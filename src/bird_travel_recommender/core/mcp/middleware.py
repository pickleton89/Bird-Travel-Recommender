"""Middleware system for MCP tools."""

import asyncio
import time
import traceback
from functools import wraps
from typing import Dict, Any, Callable, Optional, Union
from datetime import datetime

import logging


def middleware(func: Callable) -> Callable:
    """Decorator to mark a function as middleware."""
    func._is_middleware = True
    return func


@middleware
async def error_handling_middleware(tool_func: Callable, kwargs: Dict[str, Any], 
                                  correlation_id: str) -> Dict[str, Any]:
    """Comprehensive error handling middleware."""
    logger = logging.getLogger(f"middleware.error_handling")
    
    # Add error context to kwargs
    kwargs['_error_context'] = {
        'tool_name': tool_func.__name__,
        'correlation_id': correlation_id,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # Log the tool execution attempt
    logger.debug(f"Starting tool execution: {tool_func.__name__}", extra={
        "correlation_id": correlation_id,
        "tool_name": tool_func.__name__
    })
    
    return kwargs


@middleware
async def validation_middleware(tool_func: Callable, kwargs: Dict[str, Any], 
                              correlation_id: str) -> Dict[str, Any]:
    """Input validation middleware."""
    logger = logging.getLogger(f"middleware.validation")
    
    # Get function signature for validation
    import inspect
    sig = inspect.signature(tool_func)
    
    # Validate required parameters are present
    for param_name, param in sig.parameters.items():
        if (param.default == inspect.Parameter.empty and 
            param_name not in kwargs and 
            param_name not in ['self', 'args', 'kwargs', '_error_context']):
            
            logger.error(f"Missing required parameter: {param_name}", extra={
                "correlation_id": correlation_id,
                "tool_name": tool_func.__name__
            })
            raise ValueError(f"Missing required parameter: {param_name}")
    
    # Basic type validation (can be enhanced)
    for param_name, value in kwargs.items():
        if param_name.startswith('_'):  # Skip internal parameters
            continue
            
        if param_name in sig.parameters:
            param = sig.parameters[param_name]
            param_type = param.annotation
            
            # Skip validation if no type annotation
            if param_type == inspect.Parameter.empty:
                continue
                
            # Handle Optional types
            if hasattr(param_type, '__origin__') and param_type.__origin__ is Union:
                args = param_type.__args__
                if len(args) == 2 and type(None) in args:
                    # This is Optional[T], extract T
                    actual_type = args[0] if args[1] is type(None) else args[1]
                    if value is not None and actual_type != inspect.Parameter.empty:
                        if not isinstance(value, actual_type):
                            try:
                                kwargs[param_name] = actual_type(value)
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Type conversion failed for {param_name}: {e}", extra={
                                    "correlation_id": correlation_id
                                })
    
    logger.debug(f"Validation completed for {tool_func.__name__}", extra={
        "correlation_id": correlation_id
    })
    
    return kwargs


@middleware 
async def performance_middleware(tool_func: Callable, kwargs: Dict[str, Any], 
                               correlation_id: str) -> Dict[str, Any]:
    """Performance monitoring middleware."""
    logger = logging.getLogger(f"middleware.performance")
    
    # Add performance tracking to kwargs
    kwargs['_performance_context'] = {
        'start_time': time.time(),
        'correlation_id': correlation_id,
        'tool_name': tool_func.__name__
    }
    
    return kwargs


def error_handler(retry_count: int = 0, fallback_result: Any = None, 
                 suppress_errors: bool = False):
    """Decorator for advanced error handling with retry and fallback support.
    
    Args:
        retry_count: Number of retry attempts
        fallback_result: Result to return if all retries fail
        suppress_errors: Whether to suppress exceptions and return fallback
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            logger = logging.getLogger(f"error_handler.{func.__name__}")
            correlation_id = kwargs.get('_error_context', {}).get('correlation_id', 'unknown')
            
            last_exception = None
            
            for attempt in range(max(1, retry_count + 1)):
                try:
                    if attempt > 0:
                        logger.info(f"Retry attempt {attempt} for {func.__name__}", extra={
                            "correlation_id": correlation_id,
                            "attempt": attempt
                        })
                        
                    result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                    
                    # Log performance metrics if available
                    perf_context = kwargs.get('_performance_context')
                    if perf_context:
                        duration = time.time() - perf_context['start_time']
                        logger.info(f"Tool {func.__name__} completed in {duration:.3f}s", extra={
                            "correlation_id": correlation_id,
                            "duration_seconds": duration,
                            "attempt": attempt + 1
                        })
                    
                    return result
                    
                except Exception as e:
                    last_exception = e
                    logger.error(f"Tool {func.__name__} failed on attempt {attempt + 1}: {e}", extra={
                        "correlation_id": correlation_id,
                        "attempt": attempt + 1,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "traceback": traceback.format_exc()
                    })
                    
                    if attempt == retry_count:  # Last attempt
                        break
                        
                    # Simple exponential backoff
                    if retry_count > 0:
                        await asyncio.sleep(2 ** attempt)
            
            # All retries failed
            if suppress_errors:
                logger.warning(f"Returning fallback result for {func.__name__}", extra={
                    "correlation_id": correlation_id,
                    "fallback_result": str(fallback_result)
                })
                return fallback_result
            else:
                logger.error(f"All retry attempts failed for {func.__name__}", extra={
                    "correlation_id": correlation_id,
                    "total_attempts": retry_count + 1
                })
                raise last_exception
                
        return wrapper
    return decorator


def performance_monitor(log_execution: bool = True, track_memory: bool = False):
    """Decorator for detailed performance monitoring.
    
    Args:
        log_execution: Whether to log execution details
        track_memory: Whether to track memory usage (requires psutil)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            logger = logging.getLogger(f"performance.{func.__name__}")
            correlation_id = kwargs.get('_error_context', {}).get('correlation_id', 'unknown')
            
            start_time = time.time()
            start_memory = None
            
            if track_memory:
                try:
                    import psutil
                    import os
                    process = psutil.Process(os.getpid())
                    start_memory = process.memory_info().rss / 1024 / 1024  # MB
                except ImportError:
                    logger.warning("psutil not available for memory tracking")
            
            try:
                if log_execution:
                    logger.info(f"Starting execution of {func.__name__}", extra={
                        "correlation_id": correlation_id,
                        "start_time": datetime.utcnow().isoformat()
                    })
                
                result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                
                # Calculate metrics
                duration = time.time() - start_time
                metrics = {
                    "correlation_id": correlation_id,
                    "duration_seconds": duration,
                    "success": True
                }
                
                if start_memory is not None:
                    try:
                        end_memory = process.memory_info().rss / 1024 / 1024  # MB
                        metrics["memory_used_mb"] = end_memory - start_memory
                    except:
                        pass
                
                if log_execution:
                    logger.info(f"Completed execution of {func.__name__}", extra=metrics)
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"Failed execution of {func.__name__}", extra={
                    "correlation_id": correlation_id,
                    "duration_seconds": duration,
                    "success": False,
                    "error_type": type(e).__name__
                })
                raise
                
        return wrapper
    return decorator