"""
OptimizeRouteNode - Calculate optimal visiting order for birding locations.

This module contains the OptimizeRouteNode which optimizes the visiting order
for birding locations using TSP-style algorithms with fallback strategies.
"""

from pocketflow import Node
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class OptimizeRouteNode(Node):
    """
    Calculate optimal visiting order for birding locations using TSP-style algorithms.

    Features:
    - TSP-style optimization for small location sets
    - Nearest neighbor heuristic with improvements for larger sets
    - Fallback strategies for computational constraints
    - Route segment calculation with travel times and distances
    """

    def __init__(self, max_locations_for_optimization: int = 12):
        super().__init__()
        self.max_locations_for_optimization = max_locations_for_optimization

    def prep(self, shared):
        """Extract scored locations and constraints from shared store."""
        scored_locations = shared.get("scored_locations", [])
        constraints = shared.get("input", {}).get("constraints", {})

        if not scored_locations:
            logger.warning("No scored locations found in shared store")

        return {"scored_locations": scored_locations, "constraints": constraints}

    def exec(self, prep_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize visiting order for scored locations.

        Args:
            prep_data: Dictionary with scored locations and constraints

        Returns:
            Dictionary with optimized route and optimization statistics
        """
        scored_locations = prep_data["scored_locations"]
        constraints = prep_data["constraints"]

        route_stats = {
            "input_locations": len(scored_locations),
            "locations_optimized": 0,
            "optimization_method": "none",
            "total_route_distance_km": 0.0,
            "estimated_total_drive_time_hours": 0.0,
            "computational_efficiency": "n/a",
        }

        if not scored_locations:
            logger.info("No scored locations to optimize")
            return {
                "optimized_route": [],
                "route_segments": [],
                "route_stats": route_stats,
            }

        # Extract start location from constraints
        start_location = constraints.get("start_location")
        if (
            not start_location
            or not start_location.get("lat")
            or not start_location.get("lng")
        ):
            logger.warning("No valid start location found, using first scored location")
            if scored_locations:
                start_location = {
                    "lat": scored_locations[0]["center_lat"],
                    "lng": scored_locations[0]["center_lng"],
                }
            else:
                start_location = {"lat": 42.3601, "lng": -71.0589}  # Default to Boston

        logger.info(
            f"Optimizing route for {len(scored_locations)} locations from start point "
            f"({start_location['lat']:.4f}, {start_location['lng']:.4f})"
        )

        # Apply user preferences for location selection
        selected_locations = self._select_locations_for_route(
            scored_locations, constraints
        )

        # Perform route optimization
        optimization_result = self._optimize_route(start_location, selected_locations)

        # Calculate detailed route segments
        route_segments = self._calculate_route_segments(
            start_location, optimization_result["optimized_route"]
        )

        # Update statistics
        route_stats.update(
            {
                "input_locations": len(scored_locations),
                "locations_optimized": len(selected_locations),
                "optimization_method": optimization_result.get(
                    "optimization_method", "unknown"
                ),
                "total_route_distance_km": optimization_result.get(
                    "total_distance_km", 0.0
                ),
                "estimated_total_drive_time_hours": sum(
                    seg.get("estimated_drive_time_hours", 0) for seg in route_segments
                ),
                "computational_efficiency": self._assess_computational_efficiency(
                    optimization_result
                ),
            }
        )

        logger.info(
            f"Route optimization completed: {len(optimization_result['optimized_route'])} locations, "
            f"{route_stats['total_route_distance_km']:.1f}km total distance, "
            f"method: {route_stats['optimization_method']}"
        )

        return {
            "optimized_route": optimization_result["optimized_route"],
            "route_segments": route_segments,
            "route_stats": route_stats,
            "optimization_details": optimization_result.get("optimization_stats", {}),
        }

    def _select_locations_for_route(
        self, scored_locations: List[Dict], constraints: Dict
    ) -> List[Dict]:
        """
        Select subset of locations for route optimization based on user preferences.

        Args:
            scored_locations: List of scored location dictionaries
            constraints: User constraints and preferences

        Returns:
            Filtered list of locations for optimization
        """
        # Extract route planning constraints
        max_locations = constraints.get(
            "max_locations_per_day", self.max_locations_for_optimization
        )
        constraints.get("max_daily_distance_km", 400)
        min_score_threshold = constraints.get("min_location_score", 0.3)

        # Filter by minimum score
        candidate_locations = [
            loc
            for loc in scored_locations
            if loc.get("final_score", 0) >= min_score_threshold
        ]

        if not candidate_locations:
            logger.warning(
                f"No locations meet minimum score threshold {min_score_threshold}, using all locations"
            )
            candidate_locations = scored_locations

        # Limit to top scoring locations
        candidate_locations = sorted(
            candidate_locations, key=lambda loc: loc.get("final_score", 0), reverse=True
        )

        if len(candidate_locations) > max_locations:
            selected_locations = candidate_locations[:max_locations]
            logger.info(
                f"Selected top {max_locations} locations for route optimization"
            )
        else:
            selected_locations = candidate_locations

        # TODO: Could add additional filtering based on geographic clustering
        # to ensure locations aren't too spread out for daily_distance constraints

        return selected_locations

    def _optimize_route(
        self, start_location: Dict, locations: List[Dict]
    ) -> Dict[str, Any]:
        """
        Perform route optimization using appropriate algorithm.

        Args:
            start_location: Starting point coordinates
            locations: List of locations to visit

        Returns:
            Optimization result dictionary
        """
        try:
            from ...utils.route_optimizer import optimize_birding_route

            result = optimize_birding_route(
                start_location=start_location,
                locations=locations,
                max_locations=self.max_locations_for_optimization,
            )

            return result

        except Exception as e:
            logger.error(f"Route optimization failed: {e}")
            # Fallback: return locations in original score order
            return {
                "optimized_route": locations,
                "total_distance_km": self._calculate_simple_route_distance(
                    start_location, locations
                ),
                "optimization_method": "fallback_score_order",
                "optimization_stats": {"error": str(e)},
            }

    def _calculate_route_segments(
        self, start_location: Dict, route: List[Dict]
    ) -> List[Dict]:
        """
        Calculate detailed route segments.

        Args:
            start_location: Starting point coordinates
            route: Optimized route

        Returns:
            List of route segment dictionaries
        """
        try:
            from ...utils.route_optimizer import calculate_route_segments

            return calculate_route_segments(start_location, route)
        except Exception as e:
            logger.error(f"Route segment calculation failed: {e}")
            return []

    def _calculate_simple_route_distance(
        self, start_location: Dict, locations: List[Dict]
    ) -> float:
        """
        Simple distance calculation for fallback scenarios.

        Args:
            start_location: Starting point
            locations: List of locations

        Returns:
            Total distance in kilometers
        """
        if not locations:
            return 0.0

        from ...utils.geo_utils import haversine_distance

        total_distance = 0.0
        current_lat, current_lng = start_location["lat"], start_location["lng"]

        for location in locations:
            distance = haversine_distance(
                current_lat, current_lng, location["center_lat"], location["center_lng"]
            )
            total_distance += distance
            current_lat, current_lng = location["center_lat"], location["center_lng"]

        # Add return distance
        return_distance = haversine_distance(
            current_lat, current_lng, start_location["lat"], start_location["lng"]
        )
        total_distance += return_distance

        return total_distance

    def _assess_computational_efficiency(self, optimization_result: Dict) -> str:
        """
        Assess the computational efficiency of the optimization.

        Args:
            optimization_result: Result from route optimization

        Returns:
            Efficiency assessment string
        """
        method = optimization_result.get("optimization_method", "unknown")
        locations_count = optimization_result.get("optimization_stats", {}).get(
            "locations_processed", 0
        )

        if method == "empty" or method == "single_location":
            return "trivial"
        elif method == "2-opt" and locations_count <= 8:
            return "optimal"
        elif method == "enhanced_nearest_neighbor":
            return "good_heuristic"
        elif method == "fallback_score_order":
            return "fallback"
        else:
            return "standard_heuristic"

    def post(self, shared, prep_res, exec_res):
        """Store optimized route in shared store."""
        shared["optimized_route"] = exec_res["optimized_route"]
        shared["route_segments"] = exec_res["route_segments"]
        shared["route_optimization_stats"] = exec_res["route_stats"]
        shared["optimization_details"] = exec_res["optimization_details"]

        # Check if optimization was successful
        optimized_locations = len(exec_res["optimized_route"])
        total_distance = exec_res["route_stats"]["total_route_distance_km"]

        if optimized_locations == 0:
            logger.warning("No locations in optimized route")
            return "no_route"

        if total_distance > 1000:  # More than 1000km seems excessive for a day trip
            logger.warning(f"Route distance very long: {total_distance:.1f}km")
            return "excessive_distance"

        # Check optimization method success
        method = exec_res["route_stats"]["optimization_method"]
        if method == "fallback_score_order":
            logger.warning("Route optimization fell back to score ordering")
            return "optimization_failed"

        logger.info(
            f"Route optimization successful: {optimized_locations} locations, "
            f"{total_distance:.1f}km, method: {method}"
        )
        return "default"
