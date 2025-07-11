"""
FilterConstraintsNode - Apply user constraints to sightings using enrichment-in-place strategy.

This module contains the FilterConstraintsNode which applies geographic, temporal, and quality
filtering to bird sightings while preserving original data through enrichment-in-place.
"""

from pocketflow import Node
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class FilterConstraintsNode(Node):
    """
    Apply user constraints to sightings using enrichment-in-place strategy.
    
    Features:
    - Enrichment-in-place: adds constraint flags to original sighting records
    - Geographic filtering: distance calculations from start location
    - Temporal filtering: observation dates within travel window
    - Data quality filtering: valid GPS coordinates, duplicate handling
    - Travel feasibility: daily distance compliance
    """
    
    def __init__(self):
        super().__init__()
        # Import here to avoid circular imports
        from ...utils.geo_utils import (
            haversine_distance, validate_coordinates, is_within_date_range,
            is_within_radius, is_within_region, calculate_travel_time_estimate
        )
        self.haversine_distance = haversine_distance
        self.validate_coordinates = validate_coordinates
        self.is_within_date_range = is_within_date_range
        self.is_within_radius = is_within_radius
        self.is_within_region = is_within_region
        self.calculate_travel_time_estimate = calculate_travel_time_estimate
        
    def prep(self, shared):
        """Extract sightings and constraints from shared store."""
        all_sightings = shared.get("all_sightings", [])
        constraints = shared.get("input", {}).get("constraints", {})
        
        if not all_sightings:
            # Could be empty due to API issues - don't fail completely
            logger.warning("No sightings found in shared store - will process empty list")
        
        return {
            "all_sightings": all_sightings,
            "constraints": constraints
        }
    
    def exec(self, prep_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply constraints and enrich sightings with compliance flags.
        
        Args:
            prep_data: Dictionary with sightings and constraints
            
        Returns:
            Dictionary with enriched sightings and filtering statistics
        """
        all_sightings = prep_data["all_sightings"]
        constraints = prep_data["constraints"]
        
        # Extract constraint parameters with defaults
        start_location = constraints.get("start_location")
        max_daily_distance_km = constraints.get("max_daily_distance_km", 200)
        max_travel_radius_km = constraints.get("max_travel_radius_km", max_daily_distance_km)
        date_range_start = constraints.get("date_range", {}).get("start")
        date_range_end = constraints.get("date_range", {}).get("end")
        days_back = constraints.get("days_back", 30)
        region_code = constraints.get("region")
        min_observation_quality = constraints.get("min_observation_quality", "any")  # "reviewed", "valid", "any"
        
        filtering_stats = {
            "total_input_sightings": len(all_sightings),
            "valid_coordinates": 0,
            "within_travel_radius": 0,
            "within_date_range": 0,
            "within_region": 0,
            "high_quality_observations": 0,
            "duplicates_flagged": 0,
            "travel_feasible": 0,
            "constraint_compliance_summary": {}
        }
        
        if not all_sightings:
            logger.info("No sightings to filter")
            return {
                "enriched_sightings": [],
                "filtering_stats": filtering_stats
            }
        
        logger.info(f"Applying constraints to {len(all_sightings)} sightings")
        
        # Track seen observations for duplicate detection
        seen_observations = set()
        
        # Enrich each sighting with constraint compliance flags
        enriched_sightings = []
        for sighting in all_sightings:
            enriched_sighting = dict(sighting)  # Copy original sighting
            
            # 1. Geographic filtering
            lat, lng = sighting.get("lat"), sighting.get("lng")
            has_valid_gps = self.validate_coordinates(lat, lng)
            enriched_sighting["has_valid_gps"] = has_valid_gps
            
            if has_valid_gps:
                filtering_stats["valid_coordinates"] += 1
                
                # Distance from start location
                if start_location and start_location.get("lat") and start_location.get("lng"):
                    distance_from_start = self.haversine_distance(
                        start_location["lat"], start_location["lng"], lat, lng
                    )
                    enriched_sighting["distance_from_start_km"] = distance_from_start
                    enriched_sighting["within_travel_radius"] = distance_from_start <= max_travel_radius_km
                    
                    if enriched_sighting["within_travel_radius"]:
                        filtering_stats["within_travel_radius"] += 1
                        
                    # Travel time estimate
                    enriched_sighting["estimated_travel_time_hours"] = self.calculate_travel_time_estimate(distance_from_start)
                else:
                    enriched_sighting["distance_from_start_km"] = None
                    enriched_sighting["within_travel_radius"] = True  # No start location = no distance constraint
                    enriched_sighting["estimated_travel_time_hours"] = None
                
                # Region compliance
                if region_code:
                    within_region = self.is_within_region(lat, lng, region_code)
                    enriched_sighting["within_region"] = within_region
                    if within_region:
                        filtering_stats["within_region"] += 1
                else:
                    enriched_sighting["within_region"] = True
            else:
                # Invalid coordinates
                enriched_sighting["distance_from_start_km"] = None
                enriched_sighting["within_travel_radius"] = False
                enriched_sighting["estimated_travel_time_hours"] = None
                enriched_sighting["within_region"] = False
            
            # 2. Temporal filtering
            obs_date = sighting.get("obsDt")
            within_date_range = self.is_within_date_range(
                obs_date, date_range_start, date_range_end, days_back
            )
            enriched_sighting["within_date_range"] = within_date_range
            if within_date_range:
                filtering_stats["within_date_range"] += 1
            
            # 3. Data quality filtering
            obs_valid = sighting.get("obsValid", True)
            obs_reviewed = sighting.get("obsReviewed", False)
            location_private = sighting.get("locationPrivate", False)
            
            # Quality scoring
            if min_observation_quality == "reviewed":
                quality_compliant = obs_reviewed
            elif min_observation_quality == "valid":
                quality_compliant = obs_valid
            else:  # "any"
                quality_compliant = True
            
            enriched_sighting["quality_compliant"] = quality_compliant
            enriched_sighting["observation_valid"] = obs_valid
            enriched_sighting["observation_reviewed"] = obs_reviewed
            enriched_sighting["location_private"] = location_private
            
            if quality_compliant:
                filtering_stats["high_quality_observations"] += 1
            
            # 4. Duplicate detection
            # Create unique key: location + species + date
            duplicate_key = (
                sighting.get("locId", "unknown"),
                sighting.get("speciesCode", "unknown"),
                sighting.get("obsDt", "unknown")
            )
            
            is_duplicate = duplicate_key in seen_observations
            enriched_sighting["is_duplicate"] = is_duplicate
            
            if not is_duplicate:
                seen_observations.add(duplicate_key)
            else:
                filtering_stats["duplicates_flagged"] += 1
            
            # 5. Travel feasibility (daily distance compliance)
            # This is a simplified check - in production would consider route optimization
            travel_feasible = True
            if enriched_sighting.get("estimated_travel_time_hours"):
                # Assume max 8 hours driving per day
                max_daily_travel_hours = 8
                travel_feasible = enriched_sighting["estimated_travel_time_hours"] <= max_daily_travel_hours
            
            enriched_sighting["daily_distance_compliant"] = travel_feasible
            if travel_feasible:
                filtering_stats["travel_feasible"] += 1
            
            # 6. Overall constraint compliance
            all_constraints_met = (
                enriched_sighting.get("has_valid_gps", False) and
                enriched_sighting.get("within_travel_radius", False) and
                enriched_sighting.get("within_date_range", False) and
                enriched_sighting.get("within_region", False) and
                enriched_sighting.get("quality_compliant", False) and
                not enriched_sighting.get("is_duplicate", True) and
                enriched_sighting.get("daily_distance_compliant", False)
            )
            
            enriched_sighting["meets_all_constraints"] = all_constraints_met
            
            enriched_sightings.append(enriched_sighting)
        
        # Calculate constraint compliance summary
        total_sightings = len(enriched_sightings)
        if total_sightings > 0:
            filtering_stats["constraint_compliance_summary"] = {
                "valid_coordinates_pct": (filtering_stats["valid_coordinates"] / total_sightings) * 100,
                "within_travel_radius_pct": (filtering_stats["within_travel_radius"] / total_sightings) * 100,
                "within_date_range_pct": (filtering_stats["within_date_range"] / total_sightings) * 100,
                "high_quality_pct": (filtering_stats["high_quality_observations"] / total_sightings) * 100,
                "duplicate_rate_pct": (filtering_stats["duplicates_flagged"] / total_sightings) * 100,
                "travel_feasible_pct": (filtering_stats["travel_feasible"] / total_sightings) * 100,
                "fully_compliant_count": sum(1 for s in enriched_sightings if s.get("meets_all_constraints", False))
            }
        
        logger.info(f"Constraint filtering completed: {total_sightings} sightings enriched, "
                   f"{filtering_stats['constraint_compliance_summary'].get('fully_compliant_count', 0)} fully compliant")
        
        return {
            "enriched_sightings": enriched_sightings,
            "filtering_stats": filtering_stats
        }
    
    def post(self, shared, prep_res, exec_res):
        """Store enriched sightings in shared store."""
        # Replace all_sightings with enriched version
        shared["all_sightings"] = exec_res["enriched_sightings"]
        shared["filtering_stats"] = exec_res["filtering_stats"]
        
        # Check if we have sufficient compliant data
        total_sightings = len(exec_res["enriched_sightings"])
        fully_compliant = exec_res["filtering_stats"]["constraint_compliance_summary"].get("fully_compliant_count", 0)
        
        if total_sightings == 0:
            logger.warning("No sightings to process after filtering")
            return "no_sightings"
        
        if fully_compliant == 0:
            logger.warning("No sightings meet all constraints - may need to relax filters")
            return "no_compliant_sightings"
        
        compliance_rate = fully_compliant / total_sightings
        if compliance_rate < 0.1:  # Less than 10% compliance
            logger.warning(f"Low constraint compliance rate: {compliance_rate:.1%}")
            return "low_compliance"
        
        logger.info(f"Constraint filtering successful: {compliance_rate:.1%} compliance rate")
        return "default"