"""Dependency injection system for MCP tools."""

from dataclasses import dataclass
from typing import Optional, Any, Dict
import os

import logging
from ...utils.ebird_api import EBirdClient


@dataclass
class ToolDependencies:
    """Container for tool dependencies with lazy initialization."""
    
    _ebird_client: Optional[EBirdClient] = None
    _logger_cache: Dict[str, Any] = None
    _settings: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize the dependencies container."""
        if self._logger_cache is None:
            self._logger_cache = {}
        if self._settings is None:
            self._settings = self._load_settings()
    
    def _load_settings(self) -> Dict[str, Any]:
        """Load application settings from environment."""
        return {
            'ebird_api_key': os.getenv('EBIRD_API_KEY'),
            'openai_api_key': os.getenv('OPENAI_API_KEY'),
            'environment': os.getenv('ENVIRONMENT', 'development'),
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
            'max_concurrent_requests': int(os.getenv('MAX_CONCURRENT_REQUESTS', '10')),
            'request_timeout': int(os.getenv('REQUEST_TIMEOUT', '30')),
            'cache_enabled': os.getenv('CACHE_ENABLED', 'true').lower() == 'true',
            'cache_ttl': int(os.getenv('CACHE_TTL', '3600'))
        }
    
    @property
    def ebird_client(self) -> EBirdClient:
        """Get or create eBird client instance."""
        if self._ebird_client is None:
            api_key = self._settings.get('ebird_api_key')
            if not api_key:
                raise ValueError("EBIRD_API_KEY environment variable is required")
            
            self._ebird_client = EBirdClient(api_key=api_key)
            
        return self._ebird_client
    
    def get_logger(self, name: str):
        """Get a logger instance with caching."""
        if name not in self._logger_cache:
            self._logger_cache[name] = logging.getLogger(name)
        return self._logger_cache[name]
    
    @property
    def settings(self) -> Dict[str, Any]:
        """Get application settings."""
        return self._settings.copy()
    
    def close(self):
        """Clean up resources."""
        if self._ebird_client:
            # Close eBird client if it has a close method
            if hasattr(self._ebird_client, 'close'):
                self._ebird_client.close()


# Global dependencies instance
_global_dependencies: Optional[ToolDependencies] = None


def get_dependencies() -> ToolDependencies:
    """Get the global dependencies instance."""
    global _global_dependencies
    
    if _global_dependencies is None:
        _global_dependencies = ToolDependencies()
    
    return _global_dependencies


def set_dependencies(dependencies: ToolDependencies):
    """Set the global dependencies instance (useful for testing)."""
    global _global_dependencies
    _global_dependencies = dependencies


def clear_dependencies():
    """Clear the global dependencies (useful for testing)."""
    global _global_dependencies
    if _global_dependencies:
        _global_dependencies.close()
    _global_dependencies = None


# Dependency injection decorators
def inject_ebird_client(func):
    """Decorator to inject eBird client into function kwargs."""
    from functools import wraps
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if 'ebird_client' not in kwargs:
            kwargs['ebird_client'] = get_dependencies().ebird_client
        return await func(*args, **kwargs)
    
    return wrapper


def inject_logger(func):
    """Decorator to inject logger into function kwargs."""
    from functools import wraps
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if 'logger' not in kwargs:
            kwargs['logger'] = get_dependencies().get_logger(func.__name__)
        return await func(*args, **kwargs)
    
    return wrapper


def inject_settings(func):
    """Decorator to inject settings into function kwargs."""
    from functools import wraps
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if 'settings' not in kwargs:
            kwargs['settings'] = get_dependencies().settings
        return await func(*args, **kwargs)
    
    return wrapper