"""
Reusable behavior mixins for nodes.

This module provides common functionality that can be mixed into node
implementations to avoid code duplication and provide consistent behavior.
"""

from typing import Dict, Any, Optional, List
import time
import hashlib
import json
from abc import ABC

from ..config.logging import get_logger
from ..exceptions.base import BirdTravelRecommenderError


class LoggingMixin:
    """
    Mixin providing enhanced logging capabilities for nodes.
    """
    
    def log_execution_start(self, operation: str, **context):
        """
        Log the start of an operation with context.
        
        Args:
            operation: Name of the operation
            **context: Additional context to log
        """
        if hasattr(self, 'logger'):
            self.logger.info(f"Starting {operation}", extra={
                "operation": operation,
                "node_class": self.__class__.__name__,
                **context
            })
    
    def log_execution_end(self, operation: str, success: bool, duration_ms: Optional[float] = None, **context):
        """
        Log the end of an operation with results.
        
        Args:
            operation: Name of the operation
            success: Whether the operation succeeded
            duration_ms: Operation duration in milliseconds
            **context: Additional context to log
        """
        if hasattr(self, 'logger'):
            level = "info" if success else "error"
            message = f"Completed {operation} ({'success' if success else 'failure'})"
            
            extra = {
                "operation": operation,
                "node_class": self.__class__.__name__,
                "success": success,
                **context
            }
            
            if duration_ms is not None:
                extra["duration_ms"] = duration_ms
            
            getattr(self.logger, level)(message, extra=extra)
    
    def log_performance_metrics(self, operation: str, metrics: Dict[str, Any]):
        """
        Log performance metrics for an operation.
        
        Args:
            operation: Name of the operation
            metrics: Performance metrics to log
        """
        if hasattr(self, 'logger'):
            self.logger.info(f"Performance metrics for {operation}", extra={
                "operation": operation,
                "node_class": self.__class__.__name__,
                "metrics": metrics
            })


class ValidationMixin:
    """
    Mixin providing input validation utilities for nodes.
    """
    
    def validate_required_fields(self, data: Dict[str, Any], required_fields: List[str]) -> None:
        """
        Validate that required fields are present in data.
        
        Args:
            data: Data to validate
            required_fields: List of required field names
            
        Raises:
            BirdTravelRecommenderError: If required fields are missing
        """
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            raise BirdTravelRecommenderError(
                f"Missing required fields: {', '.join(missing_fields)}",
                code="VALIDATION_ERROR_MISSING_FIELDS",
                context={
                    "missing_fields": missing_fields,
                    "provided_fields": list(data.keys()),
                    "node_class": self.__class__.__name__
                }
            )
    
    def validate_field_types(self, data: Dict[str, Any], field_types: Dict[str, type]) -> None:
        """
        Validate that fields have the correct types.
        
        Args:
            data: Data to validate
            field_types: Mapping of field names to expected types
            
        Raises:
            BirdTravelRecommenderError: If field types are incorrect
        """
        type_errors = []
        
        for field, expected_type in field_types.items():
            if field in data:
                value = data[field]
                if not isinstance(value, expected_type):
                    type_errors.append({
                        "field": field,
                        "expected_type": expected_type.__name__,
                        "actual_type": type(value).__name__,
                        "value": str(value)[:100]  # Truncate for safety
                    })
        
        if type_errors:
            raise BirdTravelRecommenderError(
                f"Field type validation failed for {len(type_errors)} fields",
                code="VALIDATION_ERROR_WRONG_TYPES",
                context={
                    "type_errors": type_errors,
                    "node_class": self.__class__.__name__
                }
            )
    
    def validate_field_ranges(self, data: Dict[str, Any], field_ranges: Dict[str, Dict[str, Any]]) -> None:
        """
        Validate that numeric fields are within acceptable ranges.
        
        Args:
            data: Data to validate
            field_ranges: Mapping of field names to range specifications
                         (e.g., {"min": 0, "max": 100})
            
        Raises:
            BirdTravelRecommenderError: If field values are out of range
        """
        range_errors = []
        
        for field, range_spec in field_ranges.items():
            if field in data:
                value = data[field]
                
                if isinstance(value, (int, float)):
                    min_val = range_spec.get("min")
                    max_val = range_spec.get("max")
                    
                    if min_val is not None and value < min_val:
                        range_errors.append({
                            "field": field,
                            "value": value,
                            "min": min_val,
                            "error": "below_minimum"
                        })
                    
                    if max_val is not None and value > max_val:
                        range_errors.append({
                            "field": field,
                            "value": value,
                            "max": max_val,
                            "error": "above_maximum"
                        })
        
        if range_errors:
            raise BirdTravelRecommenderError(
                f"Field range validation failed for {len(range_errors)} fields",
                code="VALIDATION_ERROR_OUT_OF_RANGE",
                context={
                    "range_errors": range_errors,
                    "node_class": self.__class__.__name__
                }
            )


class CachingMixin:
    """
    Mixin providing caching capabilities for nodes.
    """
    
    def _generate_cache_key(self, operation: str, **params) -> str:
        """
        Generate a cache key for an operation with parameters.
        
        Args:
            operation: Name of the operation
            **params: Parameters to include in the key
            
        Returns:
            Cache key string
        """
        # Create a deterministic representation of parameters
        param_str = json.dumps(params, sort_keys=True, default=str)
        
        # Create hash for the key
        key_data = f"{self.__class__.__name__}:{operation}:{param_str}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        
        return f"node_cache:{key_hash}"
    
    async def get_cached_result(self, operation: str, **params) -> Optional[Any]:
        """
        Get a cached result for an operation.
        
        Args:
            operation: Name of the operation
            **params: Parameters used for the operation
            
        Returns:
            Cached result or None if not found
        """
        if not hasattr(self, 'deps') or not self.deps.cache:
            return None
        
        cache_key = self._generate_cache_key(operation, **params)
        
        try:
            result = await self.deps.cache.get(cache_key)
            if result is not None and hasattr(self, 'logger'):
                self.logger.debug(f"Cache hit for {operation}", extra={
                    "cache_key": cache_key,
                    "operation": operation
                })
            return result
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.warning(f"Cache get failed for {operation}: {e}")
            return None
    
    async def set_cached_result(self, operation: str, result: Any, ttl: Optional[int] = None, **params) -> None:
        """
        Set a cached result for an operation.
        
        Args:
            operation: Name of the operation
            result: Result to cache
            ttl: Time to live in seconds (optional)
            **params: Parameters used for the operation
        """
        if not hasattr(self, 'deps') or not self.deps.cache:
            return
        
        cache_key = self._generate_cache_key(operation, **params)
        
        try:
            await self.deps.cache.set(cache_key, result, ttl)
            if hasattr(self, 'logger'):
                self.logger.debug(f"Cache set for {operation}", extra={
                    "cache_key": cache_key,
                    "operation": operation,
                    "ttl": ttl
                })
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.warning(f"Cache set failed for {operation}: {e}")
    
    async def cached_operation(self, operation: str, operation_func, ttl: Optional[int] = None, **params):
        """
        Execute an operation with caching.
        
        Args:
            operation: Name of the operation
            operation_func: Async function to execute if not cached
            ttl: Time to live for cached result
            **params: Parameters for the operation
            
        Returns:
            Operation result (from cache or execution)
        """
        # Try to get cached result
        cached_result = await self.get_cached_result(operation, **params)
        if cached_result is not None:
            return cached_result
        
        # Execute operation
        result = await operation_func(**params)
        
        # Cache the result
        await self.set_cached_result(operation, result, ttl, **params)
        
        return result


class MetricsMixin:
    """
    Mixin providing metrics collection capabilities for nodes.
    """
    
    def _get_node_tags(self, additional_tags: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Get standard tags for metrics.
        
        Args:
            additional_tags: Additional tags to include
            
        Returns:
            Tags dictionary
        """
        tags = {
            "node_class": self.__class__.__name__,
            "node_module": self.__module__
        }
        
        if hasattr(self, 'deps') and hasattr(self.deps, 'execution_mode'):
            tags["execution_mode"] = self.deps.execution_mode.value
        
        if additional_tags:
            tags.update(additional_tags)
        
        return tags
    
    def increment_counter(self, metric_name: str, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Increment a counter metric.
        
        Args:
            metric_name: Name of the metric
            tags: Additional tags for the metric
        """
        if hasattr(self, 'deps') and self.deps.metrics:
            all_tags = self._get_node_tags(tags)
            self.deps.metrics.increment(metric_name, all_tags)
    
    def record_timing(self, metric_name: str, duration_ms: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Record a timing metric.
        
        Args:
            metric_name: Name of the metric
            duration_ms: Duration in milliseconds
            tags: Additional tags for the metric
        """
        if hasattr(self, 'deps') and self.deps.metrics:
            all_tags = self._get_node_tags(tags)
            self.deps.metrics.timing(metric_name, duration_ms, all_tags)
    
    def record_gauge(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Record a gauge metric.
        
        Args:
            metric_name: Name of the metric
            value: Gauge value
            tags: Additional tags for the metric
        """
        if hasattr(self, 'deps') and self.deps.metrics:
            all_tags = self._get_node_tags(tags)
            self.deps.metrics.gauge(metric_name, value, all_tags)
    
    def time_operation(self, metric_name: str, tags: Optional[Dict[str, str]] = None):
        """
        Context manager for timing operations.
        
        Args:
            metric_name: Name of the timing metric
            tags: Additional tags for the metric
            
        Returns:
            Context manager for timing
        """
        return TimingContext(self, metric_name, tags)


class TimingContext:
    """Context manager for timing operations with metrics."""
    
    def __init__(self, metrics_mixin: MetricsMixin, metric_name: str, tags: Optional[Dict[str, str]] = None):
        self.metrics_mixin = metrics_mixin
        self.metric_name = metric_name
        self.tags = tags
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration_ms = (time.time() - self.start_time) * 1000
            self.metrics_mixin.record_timing(self.metric_name, duration_ms, self.tags)


class ErrorHandlingMixin:
    """
    Mixin providing standardized error handling for nodes.
    """
    
    def handle_api_error(self, error: Exception, operation: str, **context) -> Dict[str, Any]:
        """
        Handle API-related errors with consistent formatting.
        
        Args:
            error: The exception that occurred
            operation: Name of the operation that failed
            **context: Additional context for the error
            
        Returns:
            Standardized error response
        """
        error_response = {
            "success": False,
            "error": str(error),
            "error_type": type(error).__name__,
            "operation": operation,
            "node_class": self.__class__.__name__,
            **context
        }
        
        if hasattr(self, 'logger'):
            self.logger.error(f"API error in {operation}: {error}", extra=error_response)
        
        # Record error metric if available
        if hasattr(self, 'increment_counter'):
            self.increment_counter("node_errors_total", {
                "error_type": type(error).__name__,
                "operation": operation
            })
        
        return error_response
    
    def handle_validation_error(self, error: Exception, data: Dict[str, Any], operation: str) -> Dict[str, Any]:
        """
        Handle validation errors with data context.
        
        Args:
            error: The validation exception
            data: Data that failed validation
            operation: Name of the operation
            
        Returns:
            Standardized error response
        """
        error_response = {
            "success": False,
            "error": str(error),
            "error_type": "ValidationError",
            "operation": operation,
            "node_class": self.__class__.__name__,
            "data_keys": list(data.keys()) if isinstance(data, dict) else None
        }
        
        if hasattr(self, 'logger'):
            self.logger.error(f"Validation error in {operation}: {error}", extra=error_response)
        
        # Record error metric if available
        if hasattr(self, 'increment_counter'):
            self.increment_counter("node_validation_errors_total", {
                "operation": operation
            })
        
        return error_response