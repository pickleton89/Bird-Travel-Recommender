"""
UnifiedFilterConstraintsNode - Apply user constraints to sightings using enrichment-in-place strategy.

This module provides the unified implementation for applying geographic, temporal, and quality
filtering to bird sightings while preserving original data through enrichment-in-place.
"""

from typing import Dict, Any, List, Set
from pydantic import Field
import logging

from ..base import BaseNode, NodeInput, NodeOutput
from ..factory import register_node
from ..mixins import ValidationMixin, LoggingMixin, ErrorHandlingMixin

logger = logging.getLogger(__name__)


class ConstraintsInput(NodeInput):
    """Input validation for constraints filtering node."""
    max_daily_distance_km: float = Field(default=200, ge=10, le=1000)
    max_travel_radius_km: float = Field(default=200, ge=10, le=1000)
    days_back: int = Field(default=30, ge=1, le=365)
    min_observation_quality: str = Field(default="any", pattern="^(any|valid|reviewed)$")


class ConstraintsOutput(NodeOutput):
    """Output model for constraints filtering node."""
    total_input_sightings: int = 0
    total_enriched_sightings: int = 0
    fully_compliant_count: int = 0
    compliance_rate: float = 0.0


@register_node("filter_constraints")
class UnifiedFilterConstraintsNode(BaseNode, ValidationMixin, LoggingMixin, ErrorHandlingMixin):
    """
    Unified implementation for applying user constraints to sightings using enrichment-in-place strategy.

    Features:
    - Enrichment-in-place: adds constraint flags to original sighting records
    - Geographic filtering: distance calculations from start location
    - Temporal filtering: observation dates within travel window
    - Data quality filtering: valid GPS coordinates, duplicate handling
    - Travel feasibility: daily distance compliance
    - Unified sync/async execution through dependency injection
    """

    def __init__(self, dependencies):
        super().__init__(dependencies)
        
        # Initialize mixins
        ValidationMixin.__init__(self)
        LoggingMixin.__init__(self)
        ErrorHandlingMixin.__init__(self)

    def validate_input(self, data: Dict[str, Any]) -> ConstraintsInput:
        """Validate constraints-specific input."""
        constraints = data.get("constraints", {})
        
        return ConstraintsInput(
            max_daily_distance_km=constraints.get("max_daily_distance_km", 200),
            max_travel_radius_km=constraints.get("max_travel_radius_km", 200),
            days_back=constraints.get("days_back", 30),
            min_observation_quality=constraints.get("min_observation_quality", "any")
        )

    async def process(self, shared_store: Dict[str, Any]) -> ConstraintsOutput:
        """
        Core constraints filtering processing logic.

        Args:
            shared_store: Shared data store containing sightings

        Returns:
            ConstraintsOutput with enriched sightings and statistics
        """
        try:
            # Get validated input
            input_data = self.validate_input(shared_store.get("input", {}))
            
            # Extract sightings and constraints from shared store
            all_sightings = shared_store.get("all_sightings", [])
            constraints = shared_store.get("input", {}).get("constraints", {})

            self.log_info(f"Applying constraints to {len(all_sightings)} sightings")

            # Initialize filtering statistics
            filtering_stats = {
                "total_input_sightings": len(all_sightings),
                "valid_coordinates": 0,
                "within_travel_radius": 0,
                "within_date_range": 0,
                "within_region": 0,
                "high_quality_observations": 0,
                "duplicates_flagged": 0,
                "travel_feasible": 0,
                "constraint_compliance_summary": {},
            }

            if not all_sightings:
                self.log_warning("No sightings to filter")
                return ConstraintsOutput(
                    success=True,
                    data={
                        "enriched_sightings": [],
                        "filtering_stats": filtering_stats
                    },
                    total_input_sightings=0,
                    total_enriched_sightings=0,
                    fully_compliant_count=0,
                    compliance_rate=0.0
                )

            # Extract constraint parameters
            start_location = constraints.get("start_location")
            # max_daily_distance_km = input_data.max_daily_distance_km  # Currently unused
            max_travel_radius_km = input_data.max_travel_radius_km
            date_range_start = constraints.get("date_range", {}).get("start")
            date_range_end = constraints.get("date_range", {}).get("end")
            days_back = input_data.days_back
            region_code = constraints.get("region")
            min_observation_quality = input_data.min_observation_quality

            # Track seen observations for duplicate detection
            seen_observations: Set[tuple] = set()

            # Enrich each sighting with constraint compliance flags
            enriched_sightings = []
            for sighting in all_sightings:
                enriched_sighting = await self._enrich_sighting_with_constraints(
                    sighting,
                    start_location,
                    max_travel_radius_km,
                    date_range_start,
                    date_range_end,
                    days_back,
                    region_code,
                    min_observation_quality,
                    seen_observations,
                    filtering_stats
                )
                enriched_sightings.append(enriched_sighting)

            # Calculate constraint compliance summary
            total_sightings = len(enriched_sightings)
            if total_sightings > 0:
                filtering_stats["constraint_compliance_summary"] = self._calculate_compliance_summary(
                    enriched_sightings, filtering_stats, total_sightings
                )

            fully_compliant_count = filtering_stats["constraint_compliance_summary"].get("fully_compliant_count", 0)
            compliance_rate = fully_compliant_count / total_sightings if total_sightings > 0 else 0.0

            self.log_info(
                f"Constraint filtering completed: {total_sightings} sightings enriched, "
                f"{fully_compliant_count} fully compliant ({compliance_rate:.1%})"
            )

            return ConstraintsOutput(
                success=True,
                data={
                    "enriched_sightings": enriched_sightings,
                    "filtering_stats": filtering_stats
                },
                total_input_sightings=len(all_sightings),
                total_enriched_sightings=total_sightings,
                fully_compliant_count=fully_compliant_count,
                compliance_rate=compliance_rate
            )

        except Exception as e:
            error_msg = f"Constraints filtering failed: {str(e)}"
            self.log_error(error_msg)
            return ConstraintsOutput(
                success=False,
                error=error_msg
            )

    async def _enrich_sighting_with_constraints(
        self,
        sighting: Dict[str, Any],
        start_location: Dict[str, Any],
        max_travel_radius_km: float,
        date_range_start: str,
        date_range_end: str,
        days_back: int,
        region_code: str,
        min_observation_quality: str,
        seen_observations: Set[tuple],
        filtering_stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enrich a single sighting with constraint compliance flags.
        """
        enriched_sighting = dict(sighting)  # Copy original sighting

        # 1. Geographic filtering
        lat, lng = sighting.get("lat"), sighting.get("lng")
        has_valid_gps = self._validate_coordinates(lat, lng)
        enriched_sighting["has_valid_gps"] = has_valid_gps

        if has_valid_gps:
            filtering_stats["valid_coordinates"] += 1

            # Distance from start location
            if (
                start_location
                and start_location.get("lat")
                and start_location.get("lng")
            ):
                distance_from_start = self._haversine_distance(
                    start_location["lat"], start_location["lng"], lat, lng
                )
                enriched_sighting["distance_from_start_km"] = distance_from_start
                enriched_sighting["within_travel_radius"] = (
                    distance_from_start <= max_travel_radius_km
                )

                if enriched_sighting["within_travel_radius"]:
                    filtering_stats["within_travel_radius"] += 1

                # Travel time estimate
                enriched_sighting["estimated_travel_time_hours"] = (
                    self._calculate_travel_time_estimate(distance_from_start)
                )
            else:
                enriched_sighting["distance_from_start_km"] = None
                enriched_sighting["within_travel_radius"] = True  # No start location = no distance constraint
                enriched_sighting["estimated_travel_time_hours"] = None

            # Region compliance
            if region_code:
                within_region = await self._is_within_region(lat, lng, region_code)
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
        within_date_range = await self._is_within_date_range(
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
        duplicate_key = (
            sighting.get("locId", "unknown"),
            sighting.get("speciesCode", "unknown"),
            sighting.get("obsDt", "unknown"),
        )

        is_duplicate = duplicate_key in seen_observations
        enriched_sighting["is_duplicate"] = is_duplicate

        if not is_duplicate:
            seen_observations.add(duplicate_key)
        else:
            filtering_stats["duplicates_flagged"] += 1

        # 5. Travel feasibility (daily distance compliance)
        travel_feasible = True
        if enriched_sighting.get("estimated_travel_time_hours"):
            # Assume max 8 hours driving per day
            max_daily_travel_hours = 8
            travel_feasible = (
                enriched_sighting["estimated_travel_time_hours"] <= max_daily_travel_hours
            )

        enriched_sighting["daily_distance_compliant"] = travel_feasible
        if travel_feasible:
            filtering_stats["travel_feasible"] += 1

        # 6. Overall constraint compliance
        all_constraints_met = (
            enriched_sighting.get("has_valid_gps", False)
            and enriched_sighting.get("within_travel_radius", False)
            and enriched_sighting.get("within_date_range", False)
            and enriched_sighting.get("within_region", False)
            and enriched_sighting.get("quality_compliant", False)
            and not enriched_sighting.get("is_duplicate", True)
            and enriched_sighting.get("daily_distance_compliant", False)
        )

        enriched_sighting["meets_all_constraints"] = all_constraints_met

        return enriched_sighting

    def _calculate_compliance_summary(
        self, enriched_sightings: List[Dict], filtering_stats: Dict, total_sightings: int
    ) -> Dict[str, Any]:
        """Calculate constraint compliance summary statistics."""
        return {
            "valid_coordinates_pct": (filtering_stats["valid_coordinates"] / total_sightings) * 100,
            "within_travel_radius_pct": (filtering_stats["within_travel_radius"] / total_sightings) * 100,
            "within_date_range_pct": (filtering_stats["within_date_range"] / total_sightings) * 100,
            "high_quality_pct": (filtering_stats["high_quality_observations"] / total_sightings) * 100,
            "duplicate_rate_pct": (filtering_stats["duplicates_flagged"] / total_sightings) * 100,
            "travel_feasible_pct": (filtering_stats["travel_feasible"] / total_sightings) * 100,
            "fully_compliant_count": sum(
                1 for s in enriched_sightings if s.get("meets_all_constraints", False)
            ),
        }

    def _validate_coordinates(self, lat: Any, lng: Any) -> bool:
        """Validate GPS coordinates."""
        try:
            lat_f = float(lat) if lat is not None else None
            lng_f = float(lng) if lng is not None else None
            
            if lat_f is None or lng_f is None:
                return False
                
            return -90 <= lat_f <= 90 and -180 <= lng_f <= 180
        except (TypeError, ValueError):
            return False

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

    def _calculate_travel_time_estimate(self, distance_km: float) -> float:
        """Calculate travel time estimate in hours."""
        # Assume average speed of 60 km/h for road travel
        avg_speed_kmh = 60
        return distance_km / avg_speed_kmh

    async def _is_within_region(self, lat: float, lng: float, region_code: str) -> bool:
        """Check if coordinates are within specified region."""
        # Simplified implementation - in practice would use geographic boundaries
        # For now, just return True as the region filtering is handled elsewhere
        return True

    async def _is_within_date_range(
        self, obs_date: str, start_date: str, end_date: str, days_back: int
    ) -> bool:
        """Check if observation date is within specified date range."""
        if not obs_date:
            return False
            
        try:
            from datetime import datetime, timedelta
            
            # Parse observation date
            obs_dt = self._parse_ebird_datetime(obs_date)
            if not obs_dt:
                return False
                
            now = datetime.now()
            
            # If specific date range provided, use it
            if start_date and end_date:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                return start_dt <= obs_dt <= end_dt
            
            # Otherwise use days_back
            cutoff_date = now - timedelta(days=days_back)
            return obs_dt >= cutoff_date
            
        except Exception as e:
            self.log_debug(f"Date range validation error: {e}")
            return False

    def _parse_ebird_datetime(self, date_str: str) -> Any:
        """Parse eBird datetime string."""
        from datetime import datetime
        
        try:
            # Handle various eBird date formats
            formats = [
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d",
                "%Y-%m-%d %H:%M:%S",
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
                    
            return None
        except Exception:
            return None