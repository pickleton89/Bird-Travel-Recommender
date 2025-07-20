"""
Checklists functionality mixin for eBird API.

This module provides a single checklists implementation that eliminates
the duplication between sync and async clients.
"""

from typing import List, Optional, Dict, Any
from ..models import ChecklistModel
from ...config.logging import get_logger
from ...config.constants import EBIRD_MAX_RESULTS_DEFAULT, EBIRD_BACK_DAYS_DEFAULT


class ChecklistsMixin:
    """
    Mixin providing checklists functionality.
    
    This single implementation replaces both the sync and async
    checklists modules, eliminating ~300 lines of duplication.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
    async def get_recent_checklists(
        self, 
        region_code: str,
        max_results: int = EBIRD_MAX_RESULTS_DEFAULT,
        fmt: str = "json"
    ) -> List[ChecklistModel]:
        """
        Get recent checklists for a region.
        
        Args:
            region_code: eBird region code (e.g., 'US-CA')
            max_results: Maximum number of checklists to return
            fmt: Response format (default: json)
            
        Returns:
            List of recent checklists
            
        Raises:
            EBirdAPIError: For API-related errors
            ValidationError: For invalid parameters
        """
        if not region_code or not region_code.strip():
            from ...exceptions import ValidationError
            raise ValidationError("Region code is required", field="region_code")
            
        if max_results <= 0 or max_results > 200:
            from ...exceptions import ValidationError
            raise ValidationError("Max results must be between 1 and 200", field="max_results")
            
        endpoint = f"/product/lists/{region_code}"
        params = {
            "maxResults": max_results,
            "fmt": fmt
        }
        
        self.logger.debug(f"Fetching recent checklists for region: {region_code}")
        
        try:
            response = await self.request(endpoint, params)
            
            # Convert to Pydantic models for type safety
            checklists = [ChecklistModel(**item) for item in response]
            
            self.logger.info(f"Retrieved {len(checklists)} recent checklists")
            return checklists
            
        except Exception as e:
            self.logger.error(f"Failed to fetch recent checklists for {region_code}: {e}")
            raise
            
    async def get_checklist_details(
        self, 
        checklist_id: str,
        fmt: str = "json"
    ) -> Dict[str, Any]:
        """
        Get detailed information about a specific checklist.
        
        Args:
            checklist_id: eBird checklist identifier
            fmt: Response format (default: json)
            
        Returns:
            Detailed checklist information with species list
            
        Raises:
            EBirdAPIError: For API-related errors
            ValidationError: For invalid checklist ID
        """
        if not checklist_id or not checklist_id.strip():
            from ...exceptions import ValidationError
            raise ValidationError("Checklist ID is required", field="checklist_id")
            
        endpoint = f"/product/checklist/view/{checklist_id}"
        params = {"fmt": fmt}
        
        self.logger.debug(f"Fetching checklist details for: {checklist_id}")
        
        try:
            response = await self.request(endpoint, params)
            
            self.logger.info(f"Retrieved checklist details for {checklist_id}")
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to fetch checklist details for {checklist_id}: {e}")
            raise
            
    async def get_user_stats(
        self, 
        user_id: str,
        region_code: Optional[str] = None,
        year: Optional[int] = None,
        month: Optional[int] = None,
        fmt: str = "json"
    ) -> Dict[str, Any]:
        """
        Get statistics for a specific eBird user.
        
        Args:
            user_id: eBird user identifier
            region_code: Optional region to filter statistics
            year: Optional year filter (4-digit)
            month: Optional month filter (1-12)
            fmt: Response format (default: json)
            
        Returns:
            User statistics including species and checklist counts
            
        Raises:
            EBirdAPIError: For API-related errors
            ValidationError: For invalid parameters
        """
        if not user_id or not user_id.strip():
            from ...exceptions import ValidationError
            raise ValidationError("User ID is required", field="user_id")
            
        # Validate date parameters if provided
        if year is not None and not (1900 <= year <= 2100):
            from ...exceptions import ValidationError
            raise ValidationError("Year must be between 1900 and 2100", field="year")
            
        if month is not None and not (1 <= month <= 12):
            from ...exceptions import ValidationError
            raise ValidationError("Month must be between 1 and 12", field="month")
            
        endpoint = f"/product/stats/{user_id}"
        params = {"fmt": fmt}
        
        if region_code:
            params["r"] = region_code
        if year:
            params["y"] = year
        if month:
            params["m"] = month
            
        self.logger.debug(f"Fetching user stats for: {user_id}")
        
        try:
            response = await self.request(endpoint, params)
            
            self.logger.info(f"Retrieved user statistics for {user_id}")
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to fetch user stats for {user_id}: {e}")
            raise
            
    async def get_top_contributors(
        self, 
        region_code: str,
        year: int,
        month: int,
        max_results: int = 100,
        fmt: str = "json"
    ) -> List[Dict[str, Any]]:
        """
        Get top contributors for a region in a specific month.
        
        Args:
            region_code: eBird region code
            year: Year (4-digit)
            month: Month (1-12)
            max_results: Maximum number of contributors to return
            fmt: Response format (default: json)
            
        Returns:
            List of top contributors with their statistics
            
        Raises:
            EBirdAPIError: For API-related errors
            ValidationError: For invalid parameters
        """
        if not region_code or not region_code.strip():
            from ...exceptions import ValidationError
            raise ValidationError("Region code is required", field="region_code")
            
        # Validate date
        if not (1900 <= year <= 2100):
            from ...exceptions import ValidationError
            raise ValidationError("Year must be between 1900 and 2100", field="year")
            
        if not (1 <= month <= 12):
            from ...exceptions import ValidationError
            raise ValidationError("Month must be between 1 and 12", field="month")
            
        if max_results <= 0 or max_results > 200:
            from ...exceptions import ValidationError
            raise ValidationError("Max results must be between 1 and 200", field="max_results")
            
        endpoint = f"/product/top100/{region_code}/{year}/{month}/contributors"
        params = {
            "maxResults": max_results,
            "fmt": fmt
        }
        
        self.logger.debug(f"Fetching top contributors for {region_code} in {year}-{month:02d}")
        
        try:
            response = await self.request(endpoint, params)
            
            self.logger.info(f"Retrieved {len(response)} top contributors")
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to fetch top contributors: {e}")
            raise
            
    async def get_user_checklists(
        self, 
        user_id: str,
        region_code: Optional[str] = None,
        back: int = EBIRD_BACK_DAYS_DEFAULT,
        max_results: int = EBIRD_MAX_RESULTS_DEFAULT,
        fmt: str = "json"
    ) -> List[ChecklistModel]:
        """
        Get recent checklists submitted by a specific user.
        
        Args:
            user_id: eBird user identifier
            region_code: Optional region filter
            back: Number of days back to search
            max_results: Maximum number of checklists to return
            fmt: Response format (default: json)
            
        Returns:
            List of user's recent checklists
            
        Raises:
            EBirdAPIError: For API-related errors
            ValidationError: For invalid parameters
        """
        if not user_id or not user_id.strip():
            from ...exceptions import ValidationError
            raise ValidationError("User ID is required", field="user_id")
            
        if back <= 0 or back > 30:
            from ...exceptions import ValidationError
            raise ValidationError("Back days must be between 1 and 30", field="back")
            
        if max_results <= 0 or max_results > 200:
            from ...exceptions import ValidationError
            raise ValidationError("Max results must be between 1 and 200", field="max_results")
            
        # Build endpoint based on whether region is specified
        if region_code:
            endpoint = f"/data/obs/{region_code}/recent"
        else:
            endpoint = "/data/obs/recent"
            
        params = {
            "back": back,
            "maxResults": max_results,
            "fmt": fmt,
            "userId": user_id
        }
        
        self.logger.debug(f"Fetching user checklists for: {user_id}")
        
        try:
            response = await self.request(endpoint, params)
            
            # Extract unique checklists from observations
            checklists_map = {}
            for obs in response:
                checklist_id = obs.get("subId")
                if checklist_id and checklist_id not in checklists_map:
                    checklists_map[checklist_id] = {
                        "subId": checklist_id,
                        "userDisplayName": obs.get("userDisplayName"),
                        "obsDt": obs.get("obsDt"),
                        "locId": obs.get("locId"),
                        "locName": obs.get("locName"),
                        "numSpecies": None,  # Will be calculated
                        "allObsReported": None  # Not available from this endpoint
                    }
                    
            # Calculate species count for each checklist
            for obs in response:
                checklist_id = obs.get("subId")
                if checklist_id in checklists_map:
                    current_count = checklists_map[checklist_id].get("numSpecies", 0) or 0
                    checklists_map[checklist_id]["numSpecies"] = current_count + 1
                    
            # Convert to Pydantic models
            checklists = [ChecklistModel(**data) for data in checklists_map.values()]
            
            self.logger.info(f"Retrieved {len(checklists)} user checklists")
            return checklists
            
        except Exception as e:
            self.logger.error(f"Failed to fetch user checklists for {user_id}: {e}")
            raise