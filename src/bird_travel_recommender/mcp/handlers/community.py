#!/usr/bin/env python3
"""
Community Handler Module for Bird Travel Recommender MCP Server

Contains handler methods for community and checklist tools:
- get_recent_checklists
- get_checklist_details
- get_user_stats
"""

import logging

# Import eBird API client
from ...utils.ebird_api import EBirdClient

# Configure logging
logger = logging.getLogger(__name__)


class CommunityHandlers:
    """Handler class for community and checklist tools"""
    
    def __init__(self):
        """Initialize community handlers with eBird API client"""
        self.ebird_api = EBirdClient()
        logger.info("Initialized CommunityHandlers")
    
    async def handle_get_recent_checklists(
        self,
        region_code: str,
        days_back: int = 7,
        max_results: int = 50
    ):
        """Handle get_recent_checklists tool"""
        try:
            logger.info(f"Getting recent checklists for {region_code} (last {days_back} days)")
            
            checklists = self.ebird_api.get_recent_checklists(
                region_code=region_code,
                days_back=days_back,
                max_results=max_results
            )
            
            return {
                "success": True,
                "region": region_code,
                "search_parameters": {
                    "days_back": days_back,
                    "max_results": max_results
                },
                "checklist_activity": checklists
            }
            
        except Exception as e:
            logger.error(f"Error in get_recent_checklists: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "region": region_code,
                "checklist_activity": {}
            }
    
    async def handle_get_checklist_details(
        self,
        checklist_id: str
    ):
        """Handle get_checklist_details tool"""
        try:
            logger.info(f"Getting checklist details for {checklist_id}")
            
            checklist_details = self.ebird_api.get_checklist_details(
                checklist_id=checklist_id
            )
            
            return {
                "success": True,
                "checklist_id": checklist_id,
                "checklist_data": checklist_details
            }
            
        except Exception as e:
            logger.error(f"Error in get_checklist_details: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "checklist_id": checklist_id,
                "checklist_data": {}
            }
    
    async def handle_get_user_stats(
        self,
        username: str,
        region_code: str = "world",
        year: int = 2024
    ):
        """Handle get_user_stats tool"""
        try:
            logger.info(f"Getting user statistics for {username} in {region_code}")
            
            user_stats = self.ebird_api.get_user_stats(
                username=username,
                region_code=region_code,
                year=year
            )
            
            return {
                "success": True,
                "username": username,
                "search_parameters": {
                    "region": region_code,
                    "year": year
                },
                "user_statistics": user_stats
            }
            
        except Exception as e:
            logger.error(f"Error in get_user_stats: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "username": username,
                "user_statistics": {}
            }