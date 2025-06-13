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