"""
UnifiedClusterHotspotsNode - Group nearby locations using dual hotspot discovery patterns.

This module provides the unified implementation for clustering birding locations using the modern
Node Factory Pattern with dependency injection and sync/async transparency.
"""

from typing import List, Dict, Any, Optional
from pydantic import Field
import logging

from ..base import BaseNode, NodeInput, NodeOutput
from ..factory import register_node
from ..mixins import ValidationMixin, LoggingMixin, ErrorHandlingMixin

logger = logging.getLogger(__name__)


class ClusteringInput(NodeInput):
    """Input validation for clustering node."""
    cluster_radius_km: float = Field(default=15.0, ge=0.1, le=100.0)
    max_clusters: Optional[int] = Field(default=None, ge=1, le=50)
    min_sightings_per_cluster: int = Field(default=1, ge=1)


class ClusteringOutput(NodeOutput):
    """Output model for clustering node."""
    clusters_created: Optional[int] = None
    unique_locations_found: Optional[int] = None
    hotspots_discovered: Optional[int] = None
    sightings_in_clusters: Optional[int] = None


@register_node("cluster_hotspots")
class UnifiedClusterHotspotsNode(BaseNode, ValidationMixin, LoggingMixin, ErrorHandlingMixin):
    """
    Unified implementation for grouping nearby locations using dual hotspot discovery patterns.

    Features:
    - Dual hotspot discovery: regional hotspots + coordinate-based hotspots
    - Location deduplication handling eBird's multiple identifiers
    - Distance-based clustering with travel time optimization
    - Full data preservation: each cluster contains complete sighting records
    - Unified sync/async execution through dependency injection
    """

    def __init__(self, dependencies, cluster_radius_km: float = 15.0):
        super().__init__(dependencies)
        self.cluster_radius_km = cluster_radius_km
        
        # Initialize mixins
        ValidationMixin.__init__(self)
        LoggingMixin.__init__(self)
        ErrorHandlingMixin.__init__(self)

    def validate_input(self, data: Dict[str, Any]) -> ClusteringInput:
        """Validate clustering-specific input."""
        # Extract clustering parameters from constraints
        constraints = data.get("constraints", {})
        
        return ClusteringInput(
            cluster_radius_km=constraints.get("cluster_radius_km", self.cluster_radius_km),
            max_clusters=constraints.get("max_clusters"),
            min_sightings_per_cluster=constraints.get("min_sightings_per_cluster", 1)
        )

    async def process(self, shared_store: Dict[str, Any]) -> ClusteringOutput:
        """
        Core clustering processing logic.

        Args:
            shared_store: Shared data store containing enriched sightings

        Returns:
            ClusteringOutput with hotspot clusters and statistics
        """
        try:
            # Get validated input
            input_data = self.validate_input(shared_store.get("input", {}))
            
            # Extract enriched sightings and constraints
            enriched_sightings = shared_store.get("all_sightings", [])
            constraints = shared_store.get("input", {}).get("constraints", {})

            self.log_info(f"Clustering {len(enriched_sightings)} sightings with {input_data.cluster_radius_km}km radius")

            # Initialize clustering statistics
            clustering_stats = {
                "total_input_sightings": len(enriched_sightings),
                "unique_locations_found": 0,
                "hotspots_discovered": 0,
                "clusters_created": 0,
                "sightings_in_clusters": 0,
                "isolated_locations": 0,
                "duplicate_locations_merged": 0,
            }

            if not enriched_sightings:
                self.log_warning("No enriched sightings to cluster")
                return ClusteringOutput(
                    success=True,
                    data={
                        "hotspot_clusters": [],
                        "clustering_stats": clustering_stats
                    },
                    clusters_created=0,
                    unique_locations_found=0,
                    hotspots_discovered=0,
                    sightings_in_clusters=0
                )

            # Step 1: Extract unique locations from sightings
            unique_locations = await self._extract_unique_locations(
                enriched_sightings, clustering_stats
            )

            # Step 2: Discover eBird hotspots for the region
            region_hotspots = await self._discover_regional_hotspots(
                constraints, clustering_stats
            )

            # Step 3: Merge sighting locations with discovered hotspots
            merged_locations = self._merge_locations_with_hotspots(
                unique_locations, region_hotspots, clustering_stats
            )

            # Step 4: Apply distance-based clustering
            location_clusters = self._apply_distance_clustering(
                merged_locations, input_data.cluster_radius_km, clustering_stats
            )

            # Step 5: Build final hotspot clusters with full sighting data
            hotspot_clusters = self._build_hotspot_clusters(
                location_clusters, enriched_sightings, clustering_stats
            )

            # Apply cluster filtering if specified
            if input_data.max_clusters and len(hotspot_clusters) > input_data.max_clusters:
                hotspot_clusters = hotspot_clusters[:input_data.max_clusters]
                clustering_stats["clusters_created"] = len(hotspot_clusters)

            self.log_info(
                f"Clustering completed: {clustering_stats['clusters_created']} clusters from "
                f"{clustering_stats['unique_locations_found']} unique locations"
            )

            return ClusteringOutput(
                success=True,
                data={
                    "hotspot_clusters": hotspot_clusters,
                    "clustering_stats": clustering_stats
                },
                clusters_created=clustering_stats["clusters_created"],
                unique_locations_found=clustering_stats["unique_locations_found"],
                hotspots_discovered=clustering_stats["hotspots_discovered"],
                sightings_in_clusters=clustering_stats["sightings_in_clusters"]
            )

        except Exception as e:
            error_msg = f"Clustering failed: {str(e)}"
            self.log_error(error_msg)
            return ClusteringOutput(
                success=False,
                error=error_msg
            )

    async def _extract_unique_locations(
        self, sightings: List[Dict], stats: Dict
    ) -> List[Dict[str, Any]]:
        """
        Extract unique locations from sightings, handling eBird location identifier variations.
        """
        location_map = {}  # Key: normalized location identifier

        for sighting in sightings:
            lat, lng = sighting.get("lat"), sighting.get("lng")
            loc_id = sighting.get("locId")
            loc_name = sighting.get("locName", "Unknown Location")

            # Skip sightings without valid coordinates
            if not self._validate_coordinates(lat, lng):
                continue

            # Create normalized location key
            coord_key = f"{lat:.4f},{lng:.4f}"  # 4 decimal places ≈ 11m precision

            if coord_key not in location_map:
                location_map[coord_key] = {
                    "coord_key": coord_key,
                    "lat": lat,
                    "lng": lng,
                    "primary_loc_id": loc_id,
                    "primary_loc_name": loc_name,
                    "alternate_loc_ids": set(),
                    "alternate_loc_names": set(),
                    "sighting_count": 0,
                    "species_codes": set(),
                    "observation_dates": set(),
                    "is_hotspot": False,
                    "hotspot_metadata": {},
                }
            else:
                # Merge alternate identifiers
                if loc_id and loc_id != location_map[coord_key]["primary_loc_id"]:
                    location_map[coord_key]["alternate_loc_ids"].add(loc_id)
                if loc_name and loc_name != location_map[coord_key]["primary_loc_name"]:
                    location_map[coord_key]["alternate_loc_names"].add(loc_name)

            # Update location statistics
            location_map[coord_key]["sighting_count"] += 1
            if sighting.get("speciesCode"):
                location_map[coord_key]["species_codes"].add(sighting["speciesCode"])
            if sighting.get("obsDt"):
                location_map[coord_key]["observation_dates"].add(sighting["obsDt"])

        # Convert sets to lists for JSON serialization
        unique_locations = []
        for location in location_map.values():
            location["alternate_loc_ids"] = list(location["alternate_loc_ids"])
            location["alternate_loc_names"] = list(location["alternate_loc_names"])
            location["species_codes"] = list(location["species_codes"])
            location["observation_dates"] = list(location["observation_dates"])
            location["species_diversity"] = len(location["species_codes"])
            unique_locations.append(location)

        stats["unique_locations_found"] = len(unique_locations)
        stats["duplicate_locations_merged"] = len(
            [loc for loc in unique_locations if loc["alternate_loc_ids"]]
        )

        self.log_debug(f"Extracted {len(unique_locations)} unique locations from sightings")
        return unique_locations

    async def _discover_regional_hotspots(
        self, constraints: Dict, stats: Dict
    ) -> List[Dict[str, Any]]:
        """
        Discover eBird hotspots for the region using dual discovery methods.
        """
        hotspots = []

        try:
            # Get eBird client from dependencies
            ebird_client = self.deps.ebird_client

            # Method 1: Regional hotspots
            region_code = constraints.get("region")
            if region_code:
                try:
                    if hasattr(ebird_client, 'get_hotspots'):
                        regional_hotspots = await ebird_client.get_hotspots(region_code)
                        hotspots.extend(regional_hotspots)
                        self.log_debug(
                            f"Found {len(regional_hotspots)} regional hotspots for {region_code}"
                        )
                except Exception as e:
                    self.log_warning(
                        f"Failed to get regional hotspots for {region_code}: {e}"
                    )

            # Method 2: Coordinate-based hotspots (if start location available)
            start_location = constraints.get("start_location")
            if (
                start_location
                and start_location.get("lat")
                and start_location.get("lng")
            ):
                try:
                    max_distance = min(
                        constraints.get("max_daily_distance_km", 200) // 2, 50
                    )  # Half travel distance, eBird max 50km
                    
                    if hasattr(ebird_client, 'get_nearby_hotspots'):
                        nearby_hotspots = await ebird_client.get_nearby_hotspots(
                            lat=start_location["lat"],
                            lng=start_location["lng"],
                            distance_km=max_distance,
                        )

                        # Deduplicate by locId
                        existing_loc_ids = {h.get("locId") for h in hotspots}
                        new_hotspots = [
                            h
                            for h in nearby_hotspots
                            if h.get("locId") not in existing_loc_ids
                        ]
                        hotspots.extend(new_hotspots)

                        self.log_debug(f"Found {len(new_hotspots)} additional nearby hotspots")
                except Exception as e:
                    self.log_warning(f"Failed to get nearby hotspots: {e}")

        except Exception as e:
            self.log_error(f"Failed to discover hotspots: {e}")

        stats["hotspots_discovered"] = len(hotspots)
        self.log_info(f"Discovered {len(hotspots)} eBird hotspots")
        return hotspots

    def _merge_locations_with_hotspots(
        self, locations: List[Dict], hotspots: List[Dict], stats: Dict
    ) -> List[Dict]:
        """
        Merge sighting locations with discovered hotspots.
        """
        # Create coordinate-based lookup for hotspots
        hotspot_lookup = {}
        for hotspot in hotspots:
            if self._validate_coordinates(hotspot.get("lat"), hotspot.get("lng")):
                coord_key = f"{hotspot['lat']:.4f},{hotspot['lng']:.4f}"
                hotspot_lookup[coord_key] = hotspot

        # Merge hotspot data into locations
        merged_locations = []
        hotspot_matches = 0

        for location in locations:
            coord_key = location["coord_key"]

            # Check for exact coordinate match
            if coord_key in hotspot_lookup:
                hotspot = hotspot_lookup[coord_key]
                location["is_hotspot"] = True
                location["hotspot_metadata"] = {
                    "hotspot_loc_id": hotspot.get("locId"),
                    "hotspot_name": hotspot.get("locName"),
                    "country_code": hotspot.get("countryCode"),
                    "subnational1_code": hotspot.get("subnational1Code"),
                    "subnational2_code": hotspot.get("subnational2Code"),
                    "latest_obs_date": hotspot.get("latestObsDt"),
                    "num_species_all_time": hotspot.get("numSpeciesAllTime", 0),
                }
                hotspot_matches += 1
            else:
                # Check for nearby hotspots (within 500m)
                nearby_hotspot = self._find_nearby_hotspot(
                    location, hotspots, max_distance_km=0.5
                )
                if nearby_hotspot:
                    location["is_hotspot"] = True
                    location["hotspot_metadata"] = {
                        "hotspot_loc_id": nearby_hotspot.get("locId"),
                        "hotspot_name": nearby_hotspot.get("locName"),
                        "distance_to_hotspot_km": self._haversine_distance(
                            location["lat"],
                            location["lng"],
                            nearby_hotspot["lat"],
                            nearby_hotspot["lng"],
                        ),
                        "country_code": nearby_hotspot.get("countryCode"),
                        "subnational1_code": nearby_hotspot.get("subnational1Code"),
                        "num_species_all_time": nearby_hotspot.get("numSpeciesAllTime", 0),
                    }
                    hotspot_matches += 1

            merged_locations.append(location)

        # Add hotspots that don't have sighting locations
        sighting_coords = {loc["coord_key"] for loc in locations}
        for hotspot in hotspots:
            if self._validate_coordinates(hotspot.get("lat"), hotspot.get("lng")):
                coord_key = f"{hotspot['lat']:.4f},{hotspot['lng']:.4f}"
                if coord_key not in sighting_coords:
                    # Add hotspot as potential location even without current sightings
                    merged_locations.append({
                        "coord_key": coord_key,
                        "lat": hotspot["lat"],
                        "lng": hotspot["lng"],
                        "primary_loc_id": hotspot.get("locId"),
                        "primary_loc_name": hotspot.get("locName"),
                        "alternate_loc_ids": [],
                        "alternate_loc_names": [],
                        "sighting_count": 0,
                        "species_codes": [],
                        "observation_dates": [],
                        "species_diversity": 0,
                        "is_hotspot": True,
                        "hotspot_metadata": {
                            "hotspot_loc_id": hotspot.get("locId"),
                            "hotspot_name": hotspot.get("locName"),
                            "country_code": hotspot.get("countryCode"),
                            "subnational1_code": hotspot.get("subnational1Code"),
                            "num_species_all_time": hotspot.get("numSpeciesAllTime", 0),
                        },
                    })

        self.log_debug(
            f"Merged {hotspot_matches} sighting locations with hotspots, "
            f"added {len(merged_locations) - len(locations)} hotspot-only locations"
        )

        return merged_locations

    def _find_nearby_hotspot(
        self, location: Dict, hotspots: List[Dict], max_distance_km: float
    ) -> Optional[Dict]:
        """Find the closest hotspot within max_distance_km."""
        closest_hotspot = None
        min_distance = float("inf")

        for hotspot in hotspots:
            if self._validate_coordinates(hotspot.get("lat"), hotspot.get("lng")):
                distance = self._haversine_distance(
                    location["lat"], location["lng"], hotspot["lat"], hotspot["lng"]
                )
                if distance <= max_distance_km and distance < min_distance:
                    min_distance = distance
                    closest_hotspot = hotspot

        return closest_hotspot

    def _apply_distance_clustering(
        self, locations: List[Dict], cluster_radius_km: float, stats: Dict
    ) -> List[List[Dict]]:
        """
        Apply distance-based clustering to group nearby locations.
        """
        if not locations:
            return []

        # Simple greedy clustering algorithm
        clusters = []
        unassigned = locations.copy()

        while unassigned:
            # Start new cluster with first unassigned location
            seed_location = unassigned.pop(0)
            current_cluster = [seed_location]

            # Find all locations within cluster radius of any location in current cluster
            changed = True
            while changed:
                changed = False
                remaining = []

                for candidate in unassigned:
                    # Check if candidate is close to any location in current cluster
                    min_distance = min(
                        self._haversine_distance(
                            candidate["lat"],
                            candidate["lng"],
                            cluster_loc["lat"],
                            cluster_loc["lng"],
                        )
                        for cluster_loc in current_cluster
                    )

                    if min_distance <= cluster_radius_km:
                        current_cluster.append(candidate)
                        changed = True
                    else:
                        remaining.append(candidate)

                unassigned = remaining

            clusters.append(current_cluster)

        # Sort clusters by total sighting count (descending)
        clusters.sort(
            key=lambda cluster: sum(loc["sighting_count"] for loc in cluster),
            reverse=True,
        )

        stats["clusters_created"] = len(clusters)
        stats["isolated_locations"] = len([c for c in clusters if len(c) == 1])

        self.log_debug(
            f"Created {len(clusters)} location clusters using {cluster_radius_km}km radius"
        )
        return clusters

    def _build_hotspot_clusters(
        self, location_clusters: List[List[Dict]], sightings: List[Dict], stats: Dict
    ) -> List[Dict]:
        """
        Build final hotspot clusters with complete sighting data.
        """
        hotspot_clusters = []
        total_sightings_in_clusters = 0

        for i, location_cluster in enumerate(location_clusters):
            if not location_cluster:
                continue

            # Find all sightings that belong to this cluster
            cluster_sightings = []
            cluster_coord_keys = {loc["coord_key"] for loc in location_cluster}

            for sighting in sightings:
                if self._validate_coordinates(sighting.get("lat"), sighting.get("lng")):
                    sighting_coord_key = f"{sighting['lat']:.4f},{sighting['lng']:.4f}"
                    if sighting_coord_key in cluster_coord_keys:
                        cluster_sightings.append(sighting)

            # Calculate cluster center (centroid)
            cluster_center_lat = sum(loc["lat"] for loc in location_cluster) / len(location_cluster)
            cluster_center_lng = sum(loc["lng"] for loc in location_cluster) / len(location_cluster)

            # Determine cluster name (prefer hotspot names)
            hotspot_locations = [loc for loc in location_cluster if loc["is_hotspot"]]
            if hotspot_locations:
                # Use most diverse hotspot name
                best_hotspot = max(
                    hotspot_locations, key=lambda loc: loc.get("species_diversity", 0)
                )
                cluster_name = (
                    best_hotspot.get("hotspot_metadata", {}).get("hotspot_name")
                    or best_hotspot["primary_loc_name"]
                )
            else:
                # Use location with most sightings
                best_location = max(location_cluster, key=lambda loc: loc["sighting_count"])
                cluster_name = best_location["primary_loc_name"]

            # Calculate cluster statistics
            total_species = len(
                set(
                    sighting.get("speciesCode")
                    for sighting in cluster_sightings
                    if sighting.get("speciesCode")
                )
            )

            hotspot_cluster = {
                "cluster_id": f"cluster_{i + 1}",
                "cluster_name": cluster_name,
                "center_lat": cluster_center_lat,
                "center_lng": cluster_center_lng,
                "locations": location_cluster,
                "sightings": cluster_sightings,
                "statistics": {
                    "location_count": len(location_cluster),
                    "sighting_count": len(cluster_sightings),
                    "species_diversity": total_species,
                    "hotspot_count": len(hotspot_locations),
                    "cluster_radius_km": self._calculate_cluster_radius(location_cluster),
                    "most_recent_observation": max(
                        (s.get("obsDt") for s in cluster_sightings if s.get("obsDt")),
                        default="Unknown",
                    ),
                    "species_codes": sorted(
                        list(
                            set(
                                s.get("speciesCode")
                                for s in cluster_sightings
                                if s.get("speciesCode")
                            )
                        )
                    ),
                },
                "accessibility": {
                    "has_hotspot": len(hotspot_locations) > 0,
                    "avg_travel_time_estimate": self._calculate_avg_travel_time(cluster_sightings),
                    "coordinate_quality": "high"
                    if all(loc.get("sighting_count", 0) > 0 for loc in location_cluster)
                    else "medium",
                },
            }

            hotspot_clusters.append(hotspot_cluster)
            total_sightings_in_clusters += len(cluster_sightings)

        stats["sightings_in_clusters"] = total_sightings_in_clusters

        self.log_info(
            f"Built {len(hotspot_clusters)} hotspot clusters containing "
            f"{total_sightings_in_clusters} sightings"
        )

        return hotspot_clusters

    def _calculate_cluster_radius(self, locations: List[Dict]) -> float:
        """Calculate the radius of a cluster (max distance from centroid)."""
        if len(locations) <= 1:
            return 0.0

        # Calculate centroid
        center_lat = sum(loc["lat"] for loc in locations) / len(locations)
        center_lng = sum(loc["lng"] for loc in locations) / len(locations)

        # Find max distance from centroid
        max_distance = max(
            self._haversine_distance(center_lat, center_lng, loc["lat"], loc["lng"])
            for loc in locations
        )

        return max_distance

    def _calculate_avg_travel_time(self, sightings: List[Dict]) -> Optional[float]:
        """Calculate average travel time estimate for cluster sightings."""
        travel_times = [
            s.get("estimated_travel_time_hours")
            for s in sightings
            if s.get("estimated_travel_time_hours") is not None
        ]

        if not travel_times:
            return None

        return sum(travel_times) / len(travel_times)

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