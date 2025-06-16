"""
Node implementations for the Bird Travel Recommender PocketFlow pipeline.

This module provides backward compatibility imports for all node classes
while maintaining the new modular structure.
"""

# Backward compatibility imports - maintain existing import paths
from .validation.species import ValidateSpeciesNode
from .fetching.sightings import FetchSightingsNode
from .fetching.async_sightings import AsyncFetchSightingsNode
from .processing.constraints import FilterConstraintsNode
from .processing.clustering import ClusterHotspotsNode
from .processing.scoring import ScoreLocationsNode
from .processing.routing import OptimizeRouteNode
from .processing.itinerary import GenerateItineraryNode

# TODO: The following classes will be imported from original nodes.py
# during the migration process. This will be updated as each class is migrated.

__all__ = [
    # Migrated nodes
    "ValidateSpeciesNode",
    "FetchSightingsNode", 
    "AsyncFetchSightingsNode",
    "FilterConstraintsNode",
    "ClusterHotspotsNode",
    "ScoreLocationsNode",
    "OptimizeRouteNode",
    "GenerateItineraryNode",
]

# Note: Other node classes (FetchSightingsNode, AsyncFetchSightingsNode, etc.)
# are temporarily unavailable through this import path during migration.
# Import them directly from bird_travel_recommender.nodes (original module) if needed.