"""
Node implementations for the Bird Travel Recommender PocketFlow pipeline.

This module provides backward compatibility imports for all node classes
while maintaining the new modular structure.
"""

# Backward compatibility imports - maintain existing import paths
from .validation.species import ValidateSpeciesNode
from .fetching.sightings import FetchSightingsNode
from .processing.constraints import FilterConstraintsNode
from .processing.clustering import ClusterHotspotsNode
from .processing.scoring import ScoreLocationsNode
from .processing.routing import OptimizeRouteNode
from .processing.itinerary import GenerateItineraryNode

# Note: All node classes have been successfully migrated to the new modular structure

__all__ = [
    # Migrated nodes
    "ValidateSpeciesNode",
    "FetchSightingsNode",
    "FilterConstraintsNode",
    "ClusterHotspotsNode",
    "ScoreLocationsNode",
    "OptimizeRouteNode",
    "GenerateItineraryNode",
]

# Note: Other node classes (FetchSightingsNode, etc.)
# are temporarily unavailable through this import path during migration.
# Import them directly from bird_travel_recommender.nodes (original module) if needed.
