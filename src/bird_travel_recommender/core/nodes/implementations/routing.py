"""
UnifiedOptimizeRouteNode - Calculate optimal visiting order for birding locations.

This module provides the unified implementation for optimizing the visiting order
for birding locations using TSP-style algorithms with fallback strategies.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

from ..base import BaseNode, NodeInput, NodeOutput
from ..factory import register_node
from ..mixins import ValidationMixin, LoggingMixin, ErrorHandlingMixin

logger = logging.getLogger(__name__)


class RoutingInput(NodeInput):
    """Input validation for route optimization node."""
    max_locations_for_optimization: int = Field(default=12, ge=1, le=50)
    max_locations_per_day: int = Field(default=12, ge=1, le=20)
    max_daily_distance_km: float = Field(default=400, ge=50, le=2000)
    min_location_score: float = Field(default=0.3, ge=0.0, le=1.0)


class RoutingOutput(NodeOutput):
    """Output model for route optimization node."""
    input_locations: int = 0
    locations_optimized: int = 0
    optimization_method: str = "none"
    total_route_distance_km: float = 0.0
    estimated_total_drive_time_hours: float = 0.0


@register_node("optimize_route")
class UnifiedOptimizeRouteNode(BaseNode, ValidationMixin, LoggingMixin, ErrorHandlingMixin):
    """
    Unified implementation for calculating optimal visiting order for birding locations 
    using TSP-style algorithms.

    Features:
    - TSP-style optimization for small location sets
    - Nearest neighbor heuristic with improvements for larger sets
    - Fallback strategies for computational constraints
    - Route segment calculation with travel times and distances
    - Unified sync/async execution through dependency injection
    """

    def __init__(self, dependencies, max_locations_for_optimization: int = 12):
        super().__init__(dependencies)
        self.max_locations_for_optimization = max_locations_for_optimization
        
        # Initialize mixins
        ValidationMixin.__init__(self)
        LoggingMixin.__init__(self)
        ErrorHandlingMixin.__init__(self)

    def validate_input(self, data: Dict[str, Any]) -> RoutingInput:
        """Validate routing-specific input."""
        constraints = data.get("constraints", {})
        
        return RoutingInput(
            max_locations_for_optimization=constraints.get(
                "max_locations_for_optimization", self.max_locations_for_optimization
            ),
            max_locations_per_day=constraints.get("max_locations_per_day", 12),
            max_daily_distance_km=constraints.get("max_daily_distance_km", 400),
            min_location_score=constraints.get("min_location_score", 0.3)
        )

    async def process(self, shared_store: Dict[str, Any]) -> RoutingOutput:
        """
        Core route optimization processing logic.

        Args:
            shared_store: Shared data store containing scored locations

        Returns:
            RoutingOutput with optimized route and statistics
        """
        try:
            # Get validated input
            input_data = self.validate_input(shared_store.get("input", {}))
            
            # Extract data from shared store
            scored_locations = shared_store.get("scored_locations", [])
            constraints = shared_store.get("input", {}).get("constraints", {})

            self.log_info(f"Optimizing route for {len(scored_locations)} scored locations")

            # Initialize route statistics
            route_stats = {
                "input_locations": len(scored_locations),
                "locations_optimized": 0,
                "optimization_method": "none",
                "total_route_distance_km": 0.0,
                "estimated_total_drive_time_hours": 0.0,
                "computational_efficiency": "n/a",
            }

            if not scored_locations:
                self.log_warning("No scored locations to optimize")
                return RoutingOutput(
                    success=True,
                    data={
                        "optimized_route": [],
                        "route_segments": [],
                        "route_stats": route_stats,
                        "optimization_details": {}
                    },
                    input_locations=0,
                    locations_optimized=0,
                    optimization_method="none",
                    total_route_distance_km=0.0,
                    estimated_total_drive_time_hours=0.0
                )

            # Extract start location from constraints
            start_location = await self._get_start_location(constraints, scored_locations)

            # Apply user preferences for location selection
            selected_locations = self._select_locations_for_route(
                scored_locations, input_data
            )

            # Perform route optimization
            optimization_result = await self._optimize_route(start_location, selected_locations)

            # Calculate detailed route segments
            route_segments = await self._calculate_route_segments(
                start_location, optimization_result["optimized_route"]
            )

            # Update statistics
            route_stats.update({
                "input_locations": len(scored_locations),
                "locations_optimized": len(selected_locations),
                "optimization_method": optimization_result.get("optimization_method", "unknown"),
                "total_route_distance_km": optimization_result.get("total_distance_km", 0.0),
                "estimated_total_drive_time_hours": sum(
                    seg.get("estimated_drive_time_hours", 0) for seg in route_segments
                ),
                "computational_efficiency": self._assess_computational_efficiency(optimization_result),
            })

            self.log_info(
                f"Route optimization completed: {len(optimization_result['optimized_route'])} locations, "
                f"{route_stats['total_route_distance_km']:.1f}km total distance, "
                f"method: {route_stats['optimization_method']}"
            )

            return RoutingOutput(
                success=True,
                data={
                    "optimized_route": optimization_result["optimized_route"],
                    "route_segments": route_segments,
                    "route_stats": route_stats,
                    "optimization_details": optimization_result.get("optimization_stats", {}),
                },
                input_locations=len(scored_locations),
                locations_optimized=len(selected_locations),
                optimization_method=route_stats["optimization_method"],
                total_route_distance_km=route_stats["total_route_distance_km"],
                estimated_total_drive_time_hours=route_stats["estimated_total_drive_time_hours"]
            )

        except Exception as e:
            error_msg = f"Route optimization failed: {str(e)}"
            self.log_error(error_msg)
            return RoutingOutput(
                success=False,
                error=error_msg
            )

    async def _get_start_location(
        self, constraints: Dict[str, Any], scored_locations: List[Dict]
    ) -> Dict[str, Any]:
        """Get or determine start location for route optimization."""
        start_location = constraints.get("start_location")
        
        if (
            not start_location
            or not start_location.get("lat")
            or not start_location.get("lng")
        ):
            self.log_warning("No valid start location found, using first scored location")
            if scored_locations:
                start_location = {
                    "lat": scored_locations[0]["center_lat"],
                    "lng": scored_locations[0]["center_lng"],
                }
            else:
                start_location = {"lat": 42.3601, "lng": -71.0589}  # Default to Boston

        return start_location

    def _select_locations_for_route(
        self, scored_locations: List[Dict], input_data: RoutingInput
    ) -> List[Dict]:
        """Select subset of locations for route optimization based on user preferences."""
        # Filter by minimum score
        candidate_locations = [
            loc
            for loc in scored_locations
            if loc.get("final_score", 0) >= input_data.min_location_score
        ]

        if not candidate_locations:
            self.log_warning(
                f"No locations meet minimum score threshold {input_data.min_location_score}, using all locations"
            )
            candidate_locations = scored_locations

        # Limit to top scoring locations
        candidate_locations = sorted(
            candidate_locations, key=lambda loc: loc.get("final_score", 0), reverse=True
        )

        max_locations = min(input_data.max_locations_per_day, input_data.max_locations_for_optimization)
        
        if len(candidate_locations) > max_locations:
            selected_locations = candidate_locations[:max_locations]
            self.log_info(f"Selected top {max_locations} locations for route optimization")
        else:
            selected_locations = candidate_locations

        return selected_locations

    async def _optimize_route(
        self, start_location: Dict, locations: List[Dict]
    ) -> Dict[str, Any]:
        """Perform route optimization using appropriate algorithm."""
        try:
            # Try to use external route optimizer if available
            optimization_result = await self._try_external_route_optimizer(
                start_location, locations
            )
            if optimization_result:
                return optimization_result
                
            # Fallback to built-in optimization
            return await self._builtin_route_optimization(start_location, locations)

        except Exception as e:
            self.log_error(f"Route optimization failed: {e}")
            # Final fallback: return locations in original score order
            return {
                "optimized_route": locations,
                "total_distance_km": self._calculate_simple_route_distance(start_location, locations),
                "optimization_method": "fallback_score_order",
                "optimization_stats": {"error": str(e)},
            }

    async def _try_external_route_optimizer(
        self, start_location: Dict, locations: List[Dict]
    ) -> Optional[Dict[str, Any]]:
        """Try to use external route optimization utility."""
        try:
            # Try to import and use the route optimizer
            from ....utils.route_optimizer import optimize_birding_route
            
            result = optimize_birding_route(
                start_location=start_location,
                locations=locations,
                max_locations=self.max_locations_for_optimization,
            )
            return result
        except ImportError:
            self.log_debug("External route optimizer not available")
            return None
        except Exception as e:
            self.log_warning(f"External route optimizer failed: {e}")
            return None

    async def _builtin_route_optimization(
        self, start_location: Dict, locations: List[Dict]
    ) -> Dict[str, Any]:
        """Built-in route optimization using nearest neighbor heuristic."""
        if not locations:
            return {
                "optimized_route": [],
                "total_distance_km": 0.0,
                "optimization_method": "empty",
                "optimization_stats": {"locations_processed": 0},
            }

        if len(locations) == 1:
            return {
                "optimized_route": locations,
                "total_distance_km": self._calculate_simple_route_distance(start_location, locations),
                "optimization_method": "single_location",
                "optimization_stats": {"locations_processed": 1},
            }

        # Nearest neighbor heuristic
        optimized_route = []
        remaining_locations = locations.copy()
        current_lat, current_lng = start_location["lat"], start_location["lng"]

        while remaining_locations:
            # Find nearest location
            nearest_location = min(
                remaining_locations,
                key=lambda loc: self._haversine_distance(
                    current_lat, current_lng, loc["center_lat"], loc["center_lng"]
                )
            )
            
            optimized_route.append(nearest_location)
            remaining_locations.remove(nearest_location)
            current_lat, current_lng = nearest_location["center_lat"], nearest_location["center_lng"]

        total_distance = self._calculate_simple_route_distance(start_location, optimized_route)

        return {
            "optimized_route": optimized_route,
            "total_distance_km": total_distance,
            "optimization_method": "nearest_neighbor",
            "optimization_stats": {"locations_processed": len(locations)},
        }

    async def _calculate_route_segments(
        self, start_location: Dict, route: List[Dict]
    ) -> List[Dict]:
        """Calculate detailed route segments."""
        try:
            # Try external route segment calculator
            from ....utils.route_optimizer import calculate_route_segments
            return calculate_route_segments(start_location, route)
        except (ImportError, Exception) as e:
            self.log_debug(f"External route segment calculator not available: {e}")
            # Fallback to simple segment calculation
            return self._calculate_simple_route_segments(start_location, route)

    def _calculate_simple_route_segments(
        self, start_location: Dict, route: List[Dict]
    ) -> List[Dict]:
        """Simple route segment calculation for fallback."""
        if not route:
            return []

        segments = []
        current_lat, current_lng = start_location["lat"], start_location["lng"]

        for i, location in enumerate(route):
            distance_km = self._haversine_distance(
                current_lat, current_lng, location["center_lat"], location["center_lng"]
            )
            
            # Estimate drive time (assuming 60 km/h average speed)
            drive_time_hours = distance_km / 60.0

            segment = {
                "segment_number": i + 1,
                "from_lat": current_lat,
                "from_lng": current_lng,
                "to_lat": location["center_lat"],
                "to_lng": location["center_lng"],
                "distance_km": distance_km,
                "estimated_drive_time_hours": drive_time_hours,
                "destination": location["cluster_name"],
            }

            segments.append(segment)
            current_lat, current_lng = location["center_lat"], location["center_lng"]

        return segments

    def _calculate_simple_route_distance(
        self, start_location: Dict, locations: List[Dict]
    ) -> float:
        """Simple distance calculation for fallback scenarios."""
        if not locations:
            return 0.0

        total_distance = 0.0
        current_lat, current_lng = start_location["lat"], start_location["lng"]

        for location in locations:
            distance = self._haversine_distance(
                current_lat, current_lng, location["center_lat"], location["center_lng"]
            )
            total_distance += distance
            current_lat, current_lng = location["center_lat"], location["center_lng"]

        # Add return distance
        return_distance = self._haversine_distance(
            current_lat, current_lng, start_location["lat"], start_location["lng"]
        )
        total_distance += return_distance

        return total_distance

    def _assess_computational_efficiency(self, optimization_result: Dict) -> str:
        """Assess the computational efficiency of the optimization."""
        method = optimization_result.get("optimization_method", "unknown")
        locations_count = optimization_result.get("optimization_stats", {}).get("locations_processed", 0)

        if method == "empty" or method == "single_location":
            return "trivial"
        elif method == "2-opt" and locations_count <= 8:
            return "optimal"
        elif method == "enhanced_nearest_neighbor":
            return "good_heuristic"
        elif method == "nearest_neighbor":
            return "standard_heuristic"
        elif method == "fallback_score_order":
            return "fallback"
        else:
            return "unknown"

    def _haversine_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate haversine distance between two points in kilometers."""
        import math
        
        # Convert to radians
        lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth's radius in kilometers
        r = 6371
        
        return c * r