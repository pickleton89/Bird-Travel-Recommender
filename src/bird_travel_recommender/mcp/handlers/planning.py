#!/usr/bin/env python3
"""
Planning Handler Module for Bird Travel Recommender MCP Server

Contains handler methods for itinerary generation and trip planning tools:
- generate_itinerary
- plan_complete_trip
"""

import logging
from typing import Dict, List

# Import birding pipeline components
from ...nodes import (
    GenerateItineraryNode
)

# Configure logging
logger = logging.getLogger(__name__)

class PlanningHandlers:
    """Handler methods for itinerary generation and trip planning MCP tools"""
    
    def __init__(self):
        # Initialize pipeline nodes
        self.generate_itinerary_node = GenerateItineraryNode()
        # Note: plan_complete_trip will need access to other handlers
        # This will be handled via composition in the main server class
    
    async def handle_generate_itinerary(self, optimized_route: Dict, target_species: List[str], 
                                       trip_duration_days: int = 1, **kwargs):
        """Handle generate_itinerary tool"""
        try:
            logger.info(f"Generating itinerary for {trip_duration_days}-day trip")
            
            # Create mock shared store for node execution
            shared_store = {
                "optimized_route": optimized_route,
                "input": {
                    "constraints": {
                        "target_species": target_species,
                        "trip_duration_days": trip_duration_days
                    }
                }
            }
            
            # Execute GenerateItineraryNode with correct pattern
            prep_res = self.generate_itinerary_node.prep(shared_store)
            exec_res = self.generate_itinerary_node.exec(prep_res)
            self.generate_itinerary_node.post(shared_store, prep_res, exec_res)
            
            # Return itinerary data
            itinerary = shared_store.get("itinerary_markdown", "")
            itinerary_stats = shared_store.get("itinerary_generation_stats", {})
            
            return {
                "success": True,
                "itinerary": itinerary,
                "statistics": itinerary_stats,
                "target_species": target_species,
                "trip_duration_days": trip_duration_days
            }
            
        except Exception as e:
            logger.error(f"Error in generate_itinerary: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "itinerary": ""
            }
    
    async def handle_plan_complete_trip(self, handlers_container, target_species: List[str], regions: List[str], 
                                       trip_duration_days: int, max_daily_driving_hours: float = 4,
                                       birding_skill_level: str = "intermediate", start_location: dict = None,
                                       max_distance_km: float = 150, days_back: int = 30):
        """Handle plan_complete_trip tool - End-to-end birding trip planning"""
        try:
            logger.info(f"Planning complete trip for {len(target_species)} species in {regions}")
            
            pipeline_results = {}
            
            # Step 0: Get Region Information for user-friendly display
            primary_region = regions[0] if regions else "US"
            try:
                region_info_result = await handlers_container.location_handlers.handle_get_region_details(primary_region)
                if region_info_result["success"]:
                    pipeline_results["region_info"] = region_info_result
                    region_display_name = region_info_result["region_info"].get("name", primary_region)
                    logger.info(f"Trip planning for region: {region_display_name}")
                else:
                    region_display_name = primary_region
                    logger.warning(f"Could not get region info for {primary_region}, using code as display name")
            except Exception as e:
                region_display_name = primary_region
                logger.warning(f"Error getting region info: {e}")
            
            # Step 0.5: Get Regional Species List for validation and suggestions
            try:
                regional_species_result = await handlers_container.species_handlers.handle_get_regional_species_list(primary_region)
                if regional_species_result["success"]:
                    pipeline_results["regional_species"] = regional_species_result
                    regional_species_codes = regional_species_result["species_list"]
                    logger.info(f"Found {len(regional_species_codes)} species ever reported in {region_display_name}")
                else:
                    regional_species_codes = []
                    logger.warning(f"Could not get species list for {primary_region}")
            except Exception as e:
                regional_species_codes = []
                logger.warning(f"Error getting regional species list: {e}")
            
            # Step 1: Validate Species
            validate_result = await handlers_container.species_handlers.handle_validate_species(target_species)
            if not validate_result["success"]:
                return {
                    "success": False,
                    "error": f"Species validation failed: {validate_result.get('error', 'Unknown error')}",
                    "stage": "validate_species"
                }
            pipeline_results["species_validation"] = validate_result
            validated_species = validate_result["validated_species"]
            
            # Step 2: Fetch Sightings
            validated_species_codes = [species["species_code"] for species in validated_species]
            fetch_result = await handlers_container.pipeline_handlers.handle_fetch_sightings(validated_species_codes, regions, days_back)
            if not fetch_result["success"]:
                return {
                    "success": False,
                    "error": f"Sightings fetch failed: {fetch_result.get('error', 'Unknown error')}",
                    "stage": "fetch_sightings",
                    "pipeline_results": pipeline_results
                }
            pipeline_results["sightings_fetch"] = fetch_result
            sightings = fetch_result["sightings"]
            
            # Step 3: Filter Constraints
            filter_result = await handlers_container.pipeline_handlers.handle_filter_constraints(sightings, start_location, max_distance_km)
            if not filter_result["success"]:
                return {
                    "success": False,
                    "error": f"Constraint filtering failed: {filter_result.get('error', 'Unknown error')}",
                    "stage": "filter_constraints",
                    "pipeline_results": pipeline_results
                }
            pipeline_results["constraint_filtering"] = filter_result
            filtered_sightings = filter_result["filtered_sightings"]
            
            # Step 4: Cluster Hotspots
            cluster_result = await handlers_container.pipeline_handlers.handle_cluster_hotspots(filtered_sightings, primary_region)
            if not cluster_result["success"]:
                return {
                    "success": False,
                    "error": f"Hotspot clustering failed: {cluster_result.get('error', 'Unknown error')}",
                    "stage": "cluster_hotspots",
                    "pipeline_results": pipeline_results
                }
            pipeline_results["hotspot_clustering"] = cluster_result
            hotspot_clusters = cluster_result["hotspot_clusters"]
            
            # Step 4.5: Enrich hotspot clusters with detailed information
            enriched_clusters = []
            for cluster in hotspot_clusters:
                enriched_cluster = cluster.copy()
                hotspot_details = []
                
                # Get detailed info for each hotspot in the cluster
                for hotspot in cluster.get("hotspots", []):
                    location_id = hotspot.get("locId", "")
                    if location_id:
                        try:
                            hotspot_detail_result = await handlers_container.location_handlers.handle_get_hotspot_details(location_id)
                            if hotspot_detail_result["success"]:
                                hotspot_details.append({
                                    "location_id": location_id,
                                    "basic_info": hotspot,
                                    "detailed_info": hotspot_detail_result["hotspot_info"]
                                })
                            else:
                                hotspot_details.append({
                                    "location_id": location_id, 
                                    "basic_info": hotspot,
                                    "detailed_info": {}
                                })
                        except Exception as e:
                            logger.warning(f"Could not get details for hotspot {location_id}: {e}")
                            hotspot_details.append({
                                "location_id": location_id,
                                "basic_info": hotspot, 
                                "detailed_info": {}
                            })
                
                enriched_cluster["enriched_hotspots"] = hotspot_details
                enriched_clusters.append(enriched_cluster)
            
            pipeline_results["enriched_hotspot_clustering"] = {
                "success": True,
                "enriched_clusters": enriched_clusters,
                "enrichment_count": len([h for c in enriched_clusters for h in c.get("enriched_hotspots", [])])
            }
            logger.info(f"Enriched {len(enriched_clusters)} hotspot clusters with detailed information")
            
            # Step 5: Score Locations
            score_result = await handlers_container.pipeline_handlers.handle_score_locations(hotspot_clusters, target_species)
            if not score_result["success"]:
                return {
                    "success": False,
                    "error": f"Location scoring failed: {score_result.get('error', 'Unknown error')}",
                    "stage": "score_locations",
                    "pipeline_results": pipeline_results
                }
            pipeline_results["location_scoring"] = score_result
            scored_locations = score_result["scored_locations"]
            
            # Step 6: Optimize Route
            route_result = await handlers_container.pipeline_handlers.handle_optimize_route(scored_locations, start_location)
            if not route_result["success"]:
                return {
                    "success": False,
                    "error": f"Route optimization failed: {route_result.get('error', 'Unknown error')}",
                    "stage": "optimize_route",
                    "pipeline_results": pipeline_results
                }
            pipeline_results["route_optimization"] = route_result
            optimized_route = route_result["optimized_route"]
            
            # Step 7: Generate Itinerary
            itinerary_result = await self.handle_generate_itinerary(optimized_route, target_species, trip_duration_days)
            if not itinerary_result["success"]:
                return {
                    "success": False,
                    "error": f"Itinerary generation failed: {itinerary_result.get('error', 'Unknown error')}",
                    "stage": "generate_itinerary",
                    "pipeline_results": pipeline_results
                }
            pipeline_results["itinerary_generation"] = itinerary_result
            
            # Step 7.5: Generate targeted species finding recommendations
            species_finding_recommendations = []
            for species in validated_species:
                species_code = species.get("species_code", "")
                if species_code:
                    try:
                        if start_location:
                            nearest_obs_result = await handlers_container.location_handlers.handle_find_nearest_species(
                                species_code=species_code,
                                lat=start_location["lat"],
                                lng=start_location["lng"],
                                days_back=days_back,
                                distance_km=max_distance_km
                            )
                        else:
                            nearest_obs_result = {"success": False, "observations": []}
                        if nearest_obs_result["success"] and nearest_obs_result["observations"]:
                            species_finding_recommendations.append({
                                "species": species,
                                "nearest_observations": nearest_obs_result["observations"][:3],  # Top 3 closest
                                "total_nearby": len(nearest_obs_result["observations"])
                            })
                    except Exception as e:
                        logger.warning(f"Could not get nearest observations for {species_code}: {e}")
            
            pipeline_results["species_finding_recommendations"] = {
                "success": True,
                "recommendations": species_finding_recommendations,
                "species_count": len(species_finding_recommendations)
            }
            logger.info(f"Generated targeted finding recommendations for {len(species_finding_recommendations)} species")
            
            # Return complete trip plan
            return {
                "success": True,
                "trip_plan": {
                    "species_names": target_species,
                    "region": primary_region,
                    "region_display_name": region_display_name,
                    "start_location": start_location,
                    "trip_duration_days": trip_duration_days,
                    "itinerary": itinerary_result["itinerary"],
                    "route": optimized_route,
                    "locations": scored_locations[:8],  # Top locations
                    "enriched_hotspots": enriched_clusters,
                    "species_finding_recommendations": species_finding_recommendations
                },
                "pipeline_results": pipeline_results,
                "summary": {
                    "total_species_validated": len(validated_species),
                    "regional_species_available": len(regional_species_codes),
                    "total_sightings_found": len(sightings),
                    "sightings_after_filtering": len(filtered_sightings),
                    "hotspot_clusters": len(hotspot_clusters),
                    "enriched_hotspots": len([h for c in enriched_clusters for h in c.get("enriched_hotspots", [])]),
                    "species_with_targeted_recommendations": len(species_finding_recommendations),
                    "route_distance_km": optimized_route.get("total_distance_km", 0),
                    "estimated_travel_time": optimized_route.get("total_travel_time_hours", 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Error in plan_complete_trip: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "stage": "pipeline_execution"
            }