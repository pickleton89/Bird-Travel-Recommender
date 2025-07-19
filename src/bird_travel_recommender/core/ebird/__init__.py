"""
Unified eBird API client architecture.

This module provides a single, unified client that eliminates the duplication
between sync and async eBird API implementations.
"""

from .client import EBirdClient
from .models import (
    TaxonomyModel,
    ObservationModel,
    LocationModel,
    RegionModel,
    ChecklistModel,
    FrequencyModel,
    HotspotModel,
)
from .protocols import (
    EBirdTransportProtocol,
    EBirdClientProtocol,
    MiddlewareProtocol,
    CacheProtocol,
)
from .transport import HttpxTransport, AiohttpTransport
from .middleware.rate_limiting import RateLimitMiddleware
from .middleware.caching import CachingMiddleware, MemoryCache
from .mixins.taxonomy import TaxonomyMixin
from .mixins.observations import ObservationsMixin
from .mixins.locations import LocationsMixin
from .mixins.regions import RegionsMixin
from .mixins.checklists import ChecklistsMixin
from .adapters import (
    EBirdAPIClient,
    EBirdAsyncAPIClient,
    create_legacy_ebird_client,
    create_legacy_async_ebird_client,
)

__all__ = [
    # Main client
    "EBirdClient",
    # Models
    "TaxonomyModel",
    "ObservationModel", 
    "LocationModel",
    "RegionModel",
    "ChecklistModel",
    "FrequencyModel",
    "HotspotModel",
    # Protocols
    "EBirdTransportProtocol",
    "EBirdClientProtocol",
    "MiddlewareProtocol",
    "CacheProtocol",
    # Transport
    "HttpxTransport",
    "AiohttpTransport",
    # Middleware
    "RateLimitMiddleware",
    "CachingMiddleware",
    "MemoryCache",
    # Mixins
    "TaxonomyMixin",
    "ObservationsMixin",
    "LocationsMixin",
    "RegionsMixin",
    "ChecklistsMixin",
    # Backward compatibility
    "EBirdAPIClient",
    "EBirdAsyncAPIClient", 
    "create_legacy_ebird_client",
    "create_legacy_async_ebird_client",
]