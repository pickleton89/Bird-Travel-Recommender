#!/usr/bin/env python3
"""
Species Handler Module for Bird Travel Recommender MCP Server

Contains handler methods for species-related tools:
- validate_species
- get_regional_species_list
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

# Import dependencies
from ...utils.ebird_api import EBirdClient
from ...nodes import ValidateSpeciesNode

# Configure logging
logger = logging.getLogger(__name__)

class SpeciesHandlers:
    """Handler methods for species-related MCP tools"""
    
    def __init__(self):
        self.ebird_api = EBirdClient()
        self.validate_species_node = ValidateSpeciesNode()
    
    async def handle_validate_species(self, species_names: List[str]):
        """Handle validate_species tool"""
        try:
            logger.info(f"Validating {len(species_names)} species")
            
            # Create mock shared store for node execution
            shared_store = {"input": {"species_list": species_names}}
            
            # Execute ValidateSpeciesNode with correct PocketFlow pattern
            prep_res = self.validate_species_node.prep(shared_store)
            exec_res = self.validate_species_node.exec(prep_res)
            self.validate_species_node.post(shared_store, prep_res, exec_res)
            
            # Return validated species data
            validated_species = shared_store.get("validated_species", [])
            validation_stats = shared_store.get("validation_stats", {})
            
            return {
                "success": True,
                "validated_species": validated_species,
                "statistics": validation_stats
            }
            
        except Exception as e:
            logger.error(f"Error in validate_species: {str(e)}")
            return {
                "success": False, 
                "error": str(e),
                "validated_species": []
            }
    
    async def handle_get_regional_species_list(self, region_code: str):
        """Handle get_regional_species_list tool"""
        try:
            logger.info(f"Getting species list for region {region_code}")
            
            species_list = self.ebird_api.get_species_list(region_code=region_code)
            
            return {
                "success": True,
                "region_code": region_code,
                "species_list": species_list,
                "species_count": len(species_list)
            }
            
        except Exception as e:
            logger.error(f"Error in get_regional_species_list: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "region_code": region_code,
                "species_list": []
            }