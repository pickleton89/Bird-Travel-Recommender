#!/usr/bin/env python3
"""
Pipeline Handler Module for Bird Travel Recommender MCP Server

Contains handler methods for core birding pipeline processing tools:
- fetch_sightings
- filter_constraints
- cluster_hotspots
- score_locations  
- optimize_route
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Sequence

# Import birding pipeline components
from ...utils.ebird_api import EBirdClient
from ...nodes import (
    ValidateSpeciesNode, 
    FetchSightingsNode, 
    FilterConstraintsNode,
    ClusterHotspotsNode,
    ScoreLocationsNode,
    OptimizeRouteNode,
    GenerateItineraryNode
)
from ...utils.route_optimizer import optimize_birding_route
from ...utils.geo_utils import haversine_distance

# Configure logging
logger = logging.getLogger(__name__)

class PipelineHandlers:
    """Handler methods for core birding pipeline processing MCP tools"""
    
    def __init__(self):
        # Initialize pipeline nodes
        self.fetch_sightings_node = FetchSightingsNode()
        self.filter_constraints_node = FilterConstraintsNode()
        self.cluster_hotspots_node = ClusterHotspotsNode()
        self.score_locations_node = ScoreLocationsNode()
        self.optimize_route_node = OptimizeRouteNode()
    
    async def handle_fetch_sightings(self, validated_species: List, region: str, days_back: int = 14, **kwargs):
        """Handle fetch_sightings tool"""
        try:
            logger.info(f"Fetching sightings for {len(validated_species)} species in {region}")
            
            # Handle case where user passes strings instead of validated species objects
            processed_species = []
            for species in validated_species:
                if isinstance(species, str):
                    # Convert string to basic validated species format
                    processed_species.append({
                        "original_name": species,
                        "common_name": species,
                        "species_code": species.lower().replace(" ", "")[:6],  # Simple code generation
                        "scientific_name": "Unknown",
                        "validation_method": "string_input",
                        "confidence": 0.5
                    })
                else:
                    processed_species.append(species)
            
            # Create mock shared store for node execution
            shared_store = {
                "validated_species": processed_species,
                "input": {
                    "constraints": {
                        "region": region,
                        "days_back": days_back
                    }
                }
            }
            
            # Execute FetchSightingsNode (BatchNode) with correct pattern
            prep_res = self.fetch_sightings_node.prep(shared_store)  # Returns list of species
            
            # For BatchNode, exec is called for each item in prep_res
            exec_results = []
            for species in prep_res:
                exec_res = self.fetch_sightings_node.exec(species)
                exec_results.append(exec_res)
            
            self.fetch_sightings_node.post(shared_store, prep_res, exec_results)
            
            # Return sightings data
            all_sightings = shared_store.get("all_sightings", [])
            sighting_stats = shared_store.get("sighting_statistics", {})
            
            return {
                "success": True,
                "sightings": all_sightings,
                "statistics": sighting_stats,
                "region": region,
                "days_back": days_back
            }
            
        except Exception as e:
            logger.error(f"Error in fetch_sightings: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "sightings": []
            }
    
    async def handle_filter_constraints(self, sightings: List[Dict], start_location: Dict[str, float], 
                                       max_distance_km: float = 100, date_range: Optional[Dict] = None, **kwargs):
        """Handle filter_constraints tool"""
        try:
            logger.info(f"Filtering {len(sightings)} sightings with constraints")
            
            # Create mock shared store for node execution
            shared_store = {
                "all_sightings": sightings,
                "input": {
                    "constraints": {
                        "start_location": start_location,
                        "max_distance_km": max_distance_km,
                        "date_range": date_range
                    }
                }
            }
            
            # Execute FilterConstraintsNode with correct pattern
            prep_res = self.filter_constraints_node.prep(shared_store)
            exec_res = self.filter_constraints_node.exec(prep_res)
            self.filter_constraints_node.post(shared_store, prep_res, exec_res)
            
            # Return filtered sightings data
            filtered_sightings = shared_store.get("all_sightings", [])
            constraint_stats = shared_store.get("filtering_stats", {})
            
            return {
                "success": True,
                "filtered_sightings": filtered_sightings,
                "statistics": constraint_stats,
                "constraints": {
                    "start_location": start_location,
                    "max_distance_km": max_distance_km,
                    "date_range": date_range
                }
            }
            
        except Exception as e:
            logger.error(f"Error in filter_constraints: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "filtered_sightings": []
            }
    
    async def handle_cluster_hotspots(self, filtered_sightings: List[Dict], region: str, 
                                     cluster_radius_km: float = 15, **kwargs):
        """Handle cluster_hotspots tool"""
        try:
            logger.info(f"Clustering hotspots for {len(filtered_sightings)} sightings")
            
            # Create mock shared store for node execution
            shared_store = {
                "all_sightings": filtered_sightings,
                "input": {
                    "constraints": {
                        "region": region,
                        "cluster_radius_km": cluster_radius_km
                    }
                }
            }
            
            # Execute ClusterHotspotsNode with correct pattern
            prep_res = self.cluster_hotspots_node.prep(shared_store)
            exec_res = self.cluster_hotspots_node.exec(prep_res)
            self.cluster_hotspots_node.post(shared_store, prep_res, exec_res)
            
            # Return clustered hotspots data
            hotspot_clusters = shared_store.get("hotspot_clusters", [])
            cluster_stats = shared_store.get("clustering_stats", {})
            
            return {
                "success": True,
                "hotspot_clusters": hotspot_clusters,
                "statistics": cluster_stats,
                "region": region,
                "cluster_radius_km": cluster_radius_km
            }
            
        except Exception as e:
            logger.error(f"Error in cluster_hotspots: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "hotspot_clusters": []
            }
    
    async def handle_score_locations(self, hotspot_clusters: List[Dict], target_species: List[str], 
                                    use_llm_enhancement: bool = True, **kwargs):
        """Handle score_locations tool"""
        try:
            logger.info(f"Scoring {len(hotspot_clusters)} hotspot clusters")
            
            # Create mock shared store for node execution
            shared_store = {
                "hotspot_clusters": hotspot_clusters,
                "input": {
                    "constraints": {
                        "target_species": target_species,
                        "use_llm_enhancement": use_llm_enhancement
                    }
                }
            }
            
            # Execute ScoreLocationsNode with correct pattern
            prep_res = self.score_locations_node.prep(shared_store)
            exec_res = self.score_locations_node.exec(prep_res)
            self.score_locations_node.post(shared_store, prep_res, exec_res)
            
            # Return scored locations data
            scored_locations = shared_store.get("scored_locations", [])
            scoring_stats = shared_store.get("location_scoring_stats", {})
            
            return {
                "success": True,
                "scored_locations": scored_locations,
                "statistics": scoring_stats,
                "target_species": target_species,
                "llm_enhancement_used": use_llm_enhancement
            }
            
        except Exception as e:
            logger.error(f"Error in score_locations: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "scored_locations": []
            }
    
    async def handle_optimize_route(self, scored_locations: List[Dict], start_location: Dict[str, float], 
                                   max_locations: int = 8, **kwargs):
        """Handle optimize_route tool"""
        try:
            logger.info(f"Optimizing route for {len(scored_locations)} locations")
            
            # Create mock shared store for node execution
            shared_store = {
                "scored_locations": scored_locations,
                "input": {
                    "constraints": {
                        "start_location": start_location,
                        "max_locations": max_locations
                    }
                }
            }
            
            # Execute OptimizeRouteNode with correct pattern
            prep_res = self.optimize_route_node.prep(shared_store)
            exec_res = self.optimize_route_node.exec(prep_res)
            self.optimize_route_node.post(shared_store, prep_res, exec_res)
            
            # Return optimized route data
            optimized_route = shared_store.get("optimized_route", {})
            route_stats = shared_store.get("route_optimization_stats", {})
            
            return {
                "success": True,
                "optimized_route": optimized_route,
                "statistics": route_stats,
                "start_location": start_location,
                "max_locations": max_locations
            }
            
        except Exception as e:
            logger.error(f"Error in optimize_route: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "optimized_route": {}
            }
    
    async def handle_get_historic_observations(
        self,
        region: str,
        year: int,
        month: int,
        day: int,
        species_code: str = "",
        locale: str = "en",
        max_results: int = 1000
    ):
        """Handle get_historic_observations tool"""
        try:
            logger.info(f"Getting historical observations for {region} on {year}-{month:02d}-{day:02d}")
            
            # Convert empty string to None for the API call
            species_code_param = species_code if species_code else None
            
            observations = self.ebird_api.get_historic_observations(
                region=region,
                year=year,
                month=month,
                day=day,
                species_code=species_code_param,
                locale=locale,
                max_results=max_results
            )
            
            return {
                "success": True,
                "region": region,
                "date": {
                    "year": year,
                    "month": month,
                    "day": day,
                    "formatted": f"{year}-{month:02d}-{day:02d}"
                },
                "species_code": species_code,
                "search_parameters": {
                    "locale": locale,
                    "max_results": max_results
                },
                "historic_observations": observations,
                "observation_count": len(observations)
            }
            
        except Exception as e:
            logger.error(f"Error in get_historic_observations: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "region": region,
                "historic_observations": []
            }
    
    async def handle_get_seasonal_trends(
        self,
        region: str,
        species_code: str = "",
        start_year: int = 2020,
        end_year: int = None,
        locale: str = "en"
    ):
        """Handle get_seasonal_trends tool"""
        try:
            logger.info(f"Generating seasonal trends for {region}")
            
            # Convert empty string to None for the API call
            species_code_param = species_code if species_code else None
            
            trends = self.ebird_api.get_seasonal_trends(
                region=region,
                species_code=species_code_param,
                start_year=start_year,
                end_year=end_year,
                locale=locale
            )
            
            return {
                "success": True,
                "region": region,
                "species_code": species_code,
                "search_parameters": {
                    "start_year": start_year,
                    "end_year": end_year,
                    "locale": locale
                },
                "seasonal_trends": trends
            }
            
        except Exception as e:
            logger.error(f"Error in get_seasonal_trends: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "region": region,
                "seasonal_trends": {}
            }
    
    async def handle_get_yearly_comparisons(
        self,
        region: str,
        reference_date: str,
        years_to_compare: List[int],
        species_code: str = "",
        locale: str = "en"
    ):
        """Handle get_yearly_comparisons tool"""
        try:
            logger.info(f"Generating yearly comparisons for {region} on {reference_date}")
            
            # Convert empty string to None for the API call
            species_code_param = species_code if species_code else None
            
            comparisons = self.ebird_api.get_yearly_comparisons(
                region=region,
                reference_date=reference_date,
                years_to_compare=years_to_compare,
                species_code=species_code_param,
                locale=locale
            )
            
            return {
                "success": True,
                "region": region,
                "reference_date": reference_date,
                "years_compared": years_to_compare,
                "species_code": species_code,
                "search_parameters": {
                    "locale": locale
                },
                "yearly_comparisons": comparisons
            }
            
        except Exception as e:
            logger.error(f"Error in get_yearly_comparisons: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "region": region,
                "yearly_comparisons": {}
            }
    
    async def handle_get_migration_data(
        self,
        species_code: str,
        region_code: str = "US",
        months: List[int] = None
    ):
        """Handle get_migration_data tool"""
        try:
            logger.info(f"Getting migration data for {species_code} in {region_code}")
            
            migration_data = self.ebird_api.get_migration_data(
                species_code=species_code,
                region_code=region_code,
                months=months
            )
            
            return {
                "success": True,
                "species_code": species_code,
                "region": region_code,
                "search_parameters": {
                    "months": months or list(range(1, 13))
                },
                "migration_analysis": migration_data
            }
            
        except Exception as e:
            logger.error(f"Error in get_migration_data: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "species_code": species_code,
                "migration_analysis": {}
            }
    
    async def handle_get_peak_times(
        self,
        species_code: str,
        latitude: float,
        longitude: float,
        radius_km: int = 25
    ):
        """Handle get_peak_times tool"""
        try:
            logger.info(f"Getting peak times for {species_code} at ({latitude}, {longitude})")
            
            peak_times = self.ebird_api.get_peak_times(
                species_code=species_code,
                lat=latitude,
                lng=longitude,
                radius_km=radius_km
            )
            
            return {
                "success": True,
                "species_code": species_code,
                "coordinates": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "search_radius": radius_km,
                "timing_analysis": peak_times
            }
            
        except Exception as e:
            logger.error(f"Error in get_peak_times: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "species_code": species_code,
                "timing_analysis": {}
            }
    
    async def handle_get_seasonal_hotspots(
        self,
        region_code: str,
        season: str = "spring",
        max_results: int = 20
    ):
        """Handle get_seasonal_hotspots tool"""
        try:
            logger.info(f"Getting seasonal hotspots for {region_code} in {season}")
            
            seasonal_hotspots = self.ebird_api.get_seasonal_hotspots(
                region_code=region_code,
                season=season,
                max_results=max_results
            )
            
            return {
                "success": True,
                "region": region_code,
                "season": season,
                "search_parameters": {
                    "max_results": max_results
                },
                "seasonal_analysis": seasonal_hotspots
            }
            
        except Exception as e:
            logger.error(f"Error in get_seasonal_hotspots: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "region": region_code,
                "seasonal_analysis": {}
            }