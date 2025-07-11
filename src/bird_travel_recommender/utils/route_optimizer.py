"""
Route optimization utilities for birding travel planning.

This module provides TSP-style route optimization algorithms for visiting
multiple birding locations efficiently, with fallback strategies for
computational constraints.
"""

from typing import List, Dict, Any
from .geo_utils import haversine_distance
from ..constants import AVERAGE_DRIVING_SPEED
import logging

logger = logging.getLogger(__name__)


def optimize_birding_route(start_location: Dict[str, float], locations: List[Dict[str, Any]], 
                          max_locations: int = 15) -> Dict[str, Any]:
    """
    Optimize visiting order for birding locations using TSP-style algorithm with fallback.
    
    Args:
        start_location: Dictionary with 'lat' and 'lng' keys for starting point
        locations: List of location dictionaries with scoring and coordinate data
        max_locations: Maximum number of locations to optimize (TSP is NP-hard)
        
    Returns:
        Dictionary with optimized route, distances, and optimization metadata
    """
    if not locations:
        return {
            "optimized_route": [],
            "total_distance_km": 0.0,
            "optimization_method": "empty",
            "optimization_stats": {"locations_processed": 0}
        }
    
    if len(locations) == 1:
        return {
            "optimized_route": locations,
            "total_distance_km": haversine_distance(
                start_location["lat"], start_location["lng"],
                locations[0]["center_lat"], locations[0]["center_lng"]
            ) * 2,  # Round trip
            "optimization_method": "single_location",
            "optimization_stats": {"locations_processed": 1}
        }
    
    # Limit locations for computational feasibility
    if len(locations) > max_locations:
        # Use top-scored locations
        sorted_locations = sorted(locations, key=lambda loc: loc.get("final_score", 0), reverse=True)
        locations_to_optimize = sorted_locations[:max_locations]
        logger.info(f"Limited optimization to top {max_locations} locations (from {len(locations)})")
    else:
        locations_to_optimize = locations
    
    # Choose optimization method based on problem size
    if len(locations_to_optimize) <= 8:
        # Use more sophisticated algorithm for small problems
        return _optimize_small_route(start_location, locations_to_optimize)
    else:
        # Use nearest neighbor heuristic for larger problems
        return _optimize_large_route_nearest_neighbor(start_location, locations_to_optimize)


def _optimize_small_route(start_location: Dict[str, float], locations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Optimize small routes using 2-opt improvement on nearest neighbor solution.
    
    Args:
        start_location: Starting point coordinates
        locations: List of location dictionaries to visit
        
    Returns:
        Optimized route dictionary
    """
    logger.debug(f"Using 2-opt optimization for {len(locations)} locations")
    
    # Start with nearest neighbor solution
    nn_result = _nearest_neighbor_route(start_location, locations)
    route = nn_result["route"]
    
    # Apply 2-opt improvements
    improved_route = _two_opt_improvement(start_location, route)
    
    # Calculate final metrics
    total_distance = _calculate_route_distance(start_location, improved_route)
    
    return {
        "optimized_route": improved_route,
        "total_distance_km": total_distance,
        "optimization_method": "2-opt",
        "optimization_stats": {
            "locations_processed": len(locations),
            "initial_distance": nn_result["total_distance"],
            "optimized_distance": total_distance,
            "improvement_pct": ((nn_result["total_distance"] - total_distance) / nn_result["total_distance"] * 100) if nn_result["total_distance"] > 0 else 0
        }
    }


def _optimize_large_route_nearest_neighbor(start_location: Dict[str, float], 
                                         locations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Optimize larger routes using enhanced nearest neighbor with local improvements.
    
    Args:
        start_location: Starting point coordinates
        locations: List of location dictionaries to visit
        
    Returns:
        Optimized route dictionary
    """
    logger.debug(f"Using enhanced nearest neighbor for {len(locations)} locations")
    
    # Try multiple starting points and pick the best
    best_route = None
    best_distance = float('inf')
    
    # Try starting from different high-scored locations
    start_candidates = [None]  # None means start from start_location
    if len(locations) >= 3:
        # Add top 3 scoring locations as potential intermediate starts
        sorted_locs = sorted(locations, key=lambda loc: loc.get("final_score", 0), reverse=True)
        start_candidates.extend(sorted_locs[:3])
    
    for start_candidate in start_candidates:
        if start_candidate is None:
            # Regular nearest neighbor from start_location
            result = _nearest_neighbor_route(start_location, locations)
        else:
            # Start from high-scoring location, then return to start
            remaining_locations = [loc for loc in locations if loc != start_candidate]
            partial_result = _nearest_neighbor_route_from_location(start_candidate, remaining_locations)
            
            # Calculate total distance including start->first and last->start
            first_distance = haversine_distance(
                start_location["lat"], start_location["lng"],
                start_candidate["center_lat"], start_candidate["center_lng"]
            )
            last_location = partial_result["route"][-1] if partial_result["route"] else start_candidate
            return_distance = haversine_distance(
                last_location["center_lat"], last_location["center_lng"],
                start_location["lat"], start_location["lng"]
            )
            
            result = {
                "route": [start_candidate] + partial_result["route"],
                "total_distance": first_distance + partial_result["total_distance"] + return_distance
            }
        
        if result["total_distance"] < best_distance:
            best_distance = result["total_distance"]
            best_route = result["route"]
    
    return {
        "optimized_route": best_route,
        "total_distance_km": best_distance,
        "optimization_method": "enhanced_nearest_neighbor",
        "optimization_stats": {
            "locations_processed": len(locations),
            "start_points_tested": len(start_candidates)
        }
    }


def _nearest_neighbor_route(start_location: Dict[str, float], locations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Basic nearest neighbor algorithm starting from start_location.
    
    Args:
        start_location: Starting point coordinates
        locations: List of locations to visit
        
    Returns:
        Route dictionary with ordered locations and total distance
    """
    if not locations:
        return {"route": [], "total_distance": 0.0}
    
    route = []
    remaining = locations.copy()
    current_lat, current_lng = start_location["lat"], start_location["lng"]
    total_distance = 0.0
    
    while remaining:
        # Find nearest unvisited location
        nearest_location = None
        min_distance = float('inf')
        
        for location in remaining:
            distance = haversine_distance(
                current_lat, current_lng,
                location["center_lat"], location["center_lng"]
            )
            if distance < min_distance:
                min_distance = distance
                nearest_location = location
        
        # Visit nearest location
        route.append(nearest_location)
        remaining.remove(nearest_location)
        total_distance += min_distance
        current_lat, current_lng = nearest_location["center_lat"], nearest_location["center_lng"]
    
    # Add return distance to start
    if route:
        return_distance = haversine_distance(
            current_lat, current_lng,
            start_location["lat"], start_location["lng"]
        )
        total_distance += return_distance
    
    return {"route": route, "total_distance": total_distance}


def _nearest_neighbor_route_from_location(start_location: Dict[str, Any], 
                                        remaining_locations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Nearest neighbor starting from a specific location (not start_location).
    
    Args:
        start_location: Location dictionary to start from
        remaining_locations: Other locations to visit
        
    Returns:
        Route dictionary (doesn't include return to original start_location)
    """
    if not remaining_locations:
        return {"route": [], "total_distance": 0.0}
    
    route = []
    remaining = remaining_locations.copy()
    current_lat, current_lng = start_location["center_lat"], start_location["center_lng"]
    total_distance = 0.0
    
    while remaining:
        # Find nearest unvisited location
        nearest_location = None
        min_distance = float('inf')
        
        for location in remaining:
            distance = haversine_distance(
                current_lat, current_lng,
                location["center_lat"], location["center_lng"]
            )
            if distance < min_distance:
                min_distance = distance
                nearest_location = location
        
        # Visit nearest location
        route.append(nearest_location)
        remaining.remove(nearest_location)
        total_distance += min_distance
        current_lat, current_lng = nearest_location["center_lat"], nearest_location["center_lng"]
    
    return {"route": route, "total_distance": total_distance}


def _two_opt_improvement(start_location: Dict[str, float], route: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Apply 2-opt improvement to a route.
    
    Args:
        start_location: Starting point coordinates
        route: Current route to improve
        
    Returns:
        Improved route
    """
    if len(route) < 3:
        return route
    
    best_route = route.copy()
    best_distance = _calculate_route_distance(start_location, best_route)
    
    improved = True
    max_iterations = 100  # Prevent infinite loops
    iterations = 0
    
    while improved and iterations < max_iterations:
        improved = False
        iterations += 1
        
        for i in range(len(route)):
            for j in range(i + 2, len(route)):
                if j == len(route) - 1 and i == 0:
                    continue  # Skip reversing entire route
                
                # Create new route by reversing segment between i and j
                new_route = route[:i] + route[i:j+1][::-1] + route[j+1:]
                new_distance = _calculate_route_distance(start_location, new_route)
                
                if new_distance < best_distance:
                    best_route = new_route
                    best_distance = new_distance
                    route = new_route
                    improved = True
                    break
            
            if improved:
                break
    
    logger.debug(f"2-opt completed after {iterations} iterations")
    return best_route


def _calculate_route_distance(start_location: Dict[str, float], route: List[Dict[str, Any]]) -> float:
    """
    Calculate total distance for a route including return to start.
    
    Args:
        start_location: Starting point coordinates
        route: List of locations in visiting order
        
    Returns:
        Total distance in kilometers
    """
    if not route:
        return 0.0
    
    total_distance = 0.0
    current_lat, current_lng = start_location["lat"], start_location["lng"]
    
    # Distance to each location in route
    for location in route:
        distance = haversine_distance(
            current_lat, current_lng,
            location["center_lat"], location["center_lng"]
        )
        total_distance += distance
        current_lat, current_lng = location["center_lat"], location["center_lng"]
    
    # Return distance to start
    return_distance = haversine_distance(
        current_lat, current_lng,
        start_location["lat"], start_location["lng"]
    )
    total_distance += return_distance
    
    return total_distance


def calculate_route_segments(start_location: Dict[str, float], route: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calculate detailed route segments with distances and travel times.
    
    Args:
        start_location: Starting point coordinates
        route: Optimized route list
        
    Returns:
        List of route segment dictionaries
    """
    if not route:
        return []
    
    segments = []
    current_lat, current_lng = start_location["lat"], start_location["lng"]
    current_name = "Starting Location"
    
    for i, location in enumerate(route):
        distance = haversine_distance(
            current_lat, current_lng,
            location["center_lat"], location["center_lng"]
        )
        
        segment = {
            "segment_number": i + 1,
            "from_location": current_name,
            "to_location": location["cluster_name"],
            "to_coordinates": {
                "lat": location["center_lat"],
                "lng": location["center_lng"]
            },
            "distance_km": distance,
            "estimated_drive_time_hours": distance / AVERAGE_DRIVING_SPEED,
            "cumulative_distance_km": sum(seg.get("distance_km", 0) for seg in segments) + distance,
            "location_score": location.get("final_score", 0),
            "species_diversity": location.get("statistics", {}).get("species_diversity", 0)
        }
        
        segments.append(segment)
        current_lat, current_lng = location["center_lat"], location["center_lng"]
        current_name = location["cluster_name"]
    
    # Add return segment
    if route:
        return_distance = haversine_distance(
            current_lat, current_lng,
            start_location["lat"], start_location["lng"]
        )
        
        segments.append({
            "segment_number": len(route) + 1,
            "from_location": current_name,
            "to_location": "Starting Location",
            "to_coordinates": {
                "lat": start_location["lat"],
                "lng": start_location["lng"]
            },
            "distance_km": return_distance,
            "estimated_drive_time_hours": return_distance / AVERAGE_DRIVING_SPEED,
            "cumulative_distance_km": segments[-1]["cumulative_distance_km"] + return_distance,
            "location_score": 0,
            "species_diversity": 0
        })
    
    return segments