"""
Geospatial utility functions for bird travel planning.

This module provides distance calculations and geographic filtering
functions for eBird observation data processing.
"""

import math
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth using the Haversine formula.
    
    Args:
        lat1: Latitude of first point in decimal degrees
        lng1: Longitude of first point in decimal degrees
        lat2: Latitude of second point in decimal degrees
        lng2: Longitude of second point in decimal degrees
        
    Returns:
        Distance in kilometers
    """
    # Convert latitude and longitude from degrees to radians
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of earth in kilometers
    earth_radius_km = 6371.0
    
    return earth_radius_km * c


def calculate_bearing(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate the initial bearing from point 1 to point 2.
    
    Args:
        lat1: Latitude of first point in decimal degrees
        lng1: Longitude of first point in decimal degrees
        lat2: Latitude of second point in decimal degrees
        lng2: Longitude of second point in decimal degrees
        
    Returns:
        Bearing in degrees (0-360)
    """
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    
    dlng = lng2 - lng1
    
    y = math.sin(dlng) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlng)
    
    bearing = math.atan2(y, x)
    bearing = math.degrees(bearing)
    bearing = (bearing + 360) % 360
    
    return bearing


def is_within_radius(center_lat: float, center_lng: float, point_lat: float, point_lng: float, 
                    radius_km: float) -> bool:
    """
    Check if a point is within a given radius of a center point.
    
    Args:
        center_lat: Latitude of center point
        center_lng: Longitude of center point
        point_lat: Latitude of point to check
        point_lng: Longitude of point to check
        radius_km: Radius in kilometers
        
    Returns:
        True if point is within radius, False otherwise
    """
    distance = haversine_distance(center_lat, center_lng, point_lat, point_lng)
    return distance <= radius_km


def validate_coordinates(lat: Optional[float], lng: Optional[float]) -> bool:
    """
    Validate that coordinates are within valid ranges.
    
    Args:
        lat: Latitude to validate
        lng: Longitude to validate
        
    Returns:
        True if coordinates are valid, False otherwise
    """
    if lat is None or lng is None:
        return False
    
    if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
        return False
    
    # Check valid latitude range: -90 to 90 degrees
    if lat < -90 or lat > 90:
        return False
    
    # Check valid longitude range: -180 to 180 degrees
    if lng < -180 or lng > 180:
        return False
    
    return True


def parse_ebird_datetime(ebird_datetime: str) -> Optional[datetime]:
    """
    Parse eBird datetime string to Python datetime object.
    
    eBird uses format: "2024-01-15 10:30" or "2024-01-15"
    
    Args:
        ebird_datetime: eBird datetime string
        
    Returns:
        Python datetime object or None if parsing fails
    """
    if not ebird_datetime:
        return None
    
    try:
        # Try full datetime format first
        if ' ' in ebird_datetime:
            return datetime.strptime(ebird_datetime, "%Y-%m-%d %H:%M")
        else:
            # Try date-only format
            return datetime.strptime(ebird_datetime, "%Y-%m-%d")
    except ValueError:
        logger.warning(f"Could not parse eBird datetime: {ebird_datetime}")
        return None


def is_within_date_range(observation_date: str, start_date: Optional[str] = None, 
                        end_date: Optional[str] = None, days_back: int = 30) -> bool:
    """
    Check if an observation date falls within the specified date range.
    
    Args:
        observation_date: eBird observation date string
        start_date: Optional start date (YYYY-MM-DD format)
        end_date: Optional end date (YYYY-MM-DD format)
        days_back: Number of days back from today if no dates specified
        
    Returns:
        True if observation is within date range, False otherwise
    """
    obs_dt = parse_ebird_datetime(observation_date)
    if not obs_dt:
        return False
    
    # If no specific dates provided, use days_back from today
    if not start_date and not end_date:
        cutoff_date = datetime.now() - timedelta(days=days_back)
        return obs_dt >= cutoff_date
    
    # Check start date
    if start_date:
        start_dt = parse_ebird_datetime(start_date)
        if start_dt and obs_dt < start_dt:
            return False
    
    # Check end date
    if end_date:
        end_dt = parse_ebird_datetime(end_date)
        if end_dt and obs_dt > end_dt:
            return False
    
    return True


def calculate_travel_time_estimate(distance_km: float, avg_speed_kmh: float = 60.0) -> float:
    """
    Estimate travel time between two points.
    
    Args:
        distance_km: Distance in kilometers
        avg_speed_kmh: Average travel speed in km/h (default: 60 km/h)
        
    Returns:
        Estimated travel time in hours
    """
    if distance_km <= 0:
        return 0.0
    
    return distance_km / avg_speed_kmh


def get_regional_bounds(region_code: str) -> Optional[Dict[str, float]]:
    """
    Get approximate geographic bounds for common eBird regions.
    
    This is a simplified implementation for common US states.
    In production, this would use a proper geographic database.
    
    Args:
        region_code: eBird region code (e.g., "US-MA", "US-CA")
        
    Returns:
        Dictionary with 'min_lat', 'max_lat', 'min_lng', 'max_lng' or None
    """
    # Simplified bounds for common regions
    region_bounds = {
        "US-MA": {"min_lat": 41.2, "max_lat": 42.9, "min_lng": -73.5, "max_lng": -69.9},
        "US-CA": {"min_lat": 32.5, "max_lat": 42.0, "min_lng": -124.4, "max_lng": -114.1},
        "US-NY": {"min_lat": 40.5, "max_lat": 45.0, "min_lng": -79.8, "max_lng": -71.9},
        "US-FL": {"min_lat": 24.4, "max_lat": 31.0, "min_lng": -87.6, "max_lng": -80.0},
        "US-TX": {"min_lat": 25.8, "max_lat": 36.5, "min_lng": -106.6, "max_lng": -93.5}
    }
    
    return region_bounds.get(region_code)


def is_within_region(lat: float, lng: float, region_code: str) -> bool:
    """
    Check if coordinates fall within a given eBird region.
    
    Args:
        lat: Latitude to check
        lng: Longitude to check
        region_code: eBird region code
        
    Returns:
        True if coordinates are within region bounds, False otherwise
    """
    bounds = get_regional_bounds(region_code)
    if not bounds:
        # If we don't have bounds data, assume it's valid
        logger.warning(f"No bounds data available for region {region_code}")
        return True
    
    return (bounds["min_lat"] <= lat <= bounds["max_lat"] and 
            bounds["min_lng"] <= lng <= bounds["max_lng"])


if __name__ == "__main__":
    # Test the geo utility functions
    print("Testing geo utility functions...")
    
    # Test distance calculation
    boston_lat, boston_lng = 42.3601, -71.0589
    cambridge_lat, cambridge_lng = 42.3736, -71.1097
    
    distance = haversine_distance(boston_lat, boston_lng, cambridge_lat, cambridge_lng)
    print(f"Distance from Boston to Cambridge: {distance:.2f} km")
    
    # Test coordinate validation
    print(f"Valid coordinates (42.36, -71.06): {validate_coordinates(42.36, -71.06)}")
    print(f"Invalid coordinates (200, 300): {validate_coordinates(200, 300)}")
    
    # Test date parsing
    test_date = "2024-01-15 10:30"
    parsed = parse_ebird_datetime(test_date)
    print(f"Parsed eBird date '{test_date}': {parsed}")
    
    # Test within radius
    within = is_within_radius(boston_lat, boston_lng, cambridge_lat, cambridge_lng, 10.0)
    print(f"Cambridge within 10km of Boston: {within}")
    
    print("Geo utility testing completed!")