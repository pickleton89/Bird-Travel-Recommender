"""
Async eBird API client for checklist and user-related endpoints.

This module provides async methods for retrieving checklist data and user statistics from the eBird API,
including recent checklists, checklist details, and user birding statistics.
"""

from typing import Dict, Any
import logging
from .ebird_async_base import EBirdAsyncBaseClient, EBirdAPIError
from ..constants import (
    EBIRD_DAYS_BACK_MAX,
    SIMULATED_SPECIES_MIN,
    SIMULATED_SPECIES_MAX,
    SIMULATED_CHECKLISTS_MIN,
    SIMULATED_CHECKLISTS_MAX,
)

logger = logging.getLogger(__name__)


class EBirdAsyncChecklistsMixin:
    """Async mixin class providing checklist and user-related eBird API methods."""

    async def get_recent_checklists(
        self, region_code: str, days_back: int = 7, max_results: int = 50
    ) -> Dict[str, Any]:
        """
        Get most recent checklists in a region.

        Args:
            region_code: eBird region code (e.g., "US-CA")
            days_back: Days back to search (1-30, default: 7)
            max_results: Maximum checklists to return (default: 50)

        Returns:
            Recent checklist activity with observer and location information

        Raises:
            EBirdAPIError: For API errors with descriptive messages
        """
        try:
            days_back = min(days_back, EBIRD_DAYS_BACK_MAX)  # API limit
            endpoint = f"/data/obs/{region_code}/recent"

            params = {
                "back": days_back,
                "maxResults": min(max_results, 10000),
                "detail": "full",
                "includeProvisional": "true",
            }

            logger.info(
                f"Fetching recent checklists for {region_code} (last {days_back} days)"
            )
            response = await self.make_request(endpoint, params)

            if not isinstance(response, list):
                logger.warning(
                    f"Unexpected response format for recent checklists: {type(response)}"
                )
                return {
                    "region": region_code,
                    "days_back": days_back,
                    "checklists": [],
                    "checklist_count": 0,
                }

            # Process observations into checklist format
            checklist_map = {}

            for obs in response:
                # Group by submission ID to create checklists
                sub_id = obs.get("subId", "unknown")

                if sub_id not in checklist_map:
                    checklist_map[sub_id] = {
                        "checklist_id": sub_id,
                        "location_name": obs.get("locName", "Unknown"),
                        "location_id": obs.get("locId", ""),
                        "observer": obs.get("userDisplayName", "Anonymous"),
                        "observation_date": obs.get("obsDt", ""),
                        "coordinates": {
                            "latitude": obs.get("lat", 0),
                            "longitude": obs.get("lng", 0),
                        },
                        "species_list": [],
                        "species_count": 0,
                    }

                # Add species to checklist
                species_info = {
                    "species_code": obs.get("speciesCode", ""),
                    "common_name": obs.get("comName", ""),
                    "scientific_name": obs.get("sciName", ""),
                    "count": obs.get("howMany", 1),
                }
                checklist_map[sub_id]["species_list"].append(species_info)

            # Convert to list and add species counts
            checklists = []
            for checklist in checklist_map.values():
                checklist["species_count"] = len(checklist["species_list"])
                checklists.append(checklist)

            # Sort by date (most recent first)
            checklists.sort(key=lambda x: x["observation_date"], reverse=True)
            checklists = checklists[:max_results]

            result = {
                "region": region_code,
                "days_back": days_back,
                "search_parameters": {
                    "max_results": max_results,
                    "include_provisional": True,
                },
                "checklists": checklists,
                "checklist_count": len(checklists),
                "total_observations": len(response),
            }

            logger.info(
                f"Retrieved {len(checklists)} recent checklists for {region_code}"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to get recent checklists for {region_code}: {e}")
            raise EBirdAPIError(f"Recent checklists lookup failed: {str(e)}")

    async def get_checklist_details(self, checklist_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific checklist.

        Args:
            checklist_id: eBird checklist ID (e.g., "S123456789")

        Returns:
            Detailed checklist information including all species and metadata

        Raises:
            EBirdAPIError: For API errors with descriptive messages
        """
        try:
            endpoint = f"/data/obs/{checklist_id}"

            logger.info(f"Fetching checklist details for {checklist_id}")
            response = await self.make_request(endpoint)

            if not isinstance(response, list):
                logger.warning(
                    f"Unexpected response format for checklist details: {type(response)}"
                )
                return {
                    "checklist_id": checklist_id,
                    "error": "Invalid checklist format",
                    "species_list": [],
                }

            if not response:
                return {
                    "checklist_id": checklist_id,
                    "error": "Checklist not found or empty",
                    "species_list": [],
                }

            # Extract checklist metadata from first observation
            first_obs = response[0]

            # Process all species in checklist
            species_list = []
            for obs in response:
                species_info = {
                    "species_code": obs.get("speciesCode", ""),
                    "common_name": obs.get("comName", ""),
                    "scientific_name": obs.get("sciName", ""),
                    "count": obs.get("howMany", "X"),  # X means present but not counted
                    "breeding_code": obs.get("breedingCode", ""),
                    "behavior_notes": obs.get("comments", ""),
                }
                species_list.append(species_info)

            result = {
                "checklist_id": checklist_id,
                "location_name": first_obs.get("locName", "Unknown"),
                "location_id": first_obs.get("locId", ""),
                "coordinates": {
                    "latitude": first_obs.get("lat", 0),
                    "longitude": first_obs.get("lng", 0),
                },
                "observer": first_obs.get("userDisplayName", "Anonymous"),
                "observation_date": first_obs.get("obsDt", ""),
                "duration_minutes": first_obs.get("durationHrs", 0) * 60
                if first_obs.get("durationHrs")
                else None,
                "distance_km": first_obs.get("effortDistanceKm", None),
                "number_observers": first_obs.get("numObservers", 1),
                "species_list": species_list,
                "species_count": len(species_list),
                "checklist_complete": first_obs.get("obsReviewed", False),
            }

            logger.info(
                f"Retrieved checklist details for {checklist_id}: {len(species_list)} species"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to get checklist details for {checklist_id}: {e}")
            raise EBirdAPIError(f"Checklist details lookup failed: {str(e)}")

    async def get_user_stats(
        self, username: str, region_code: str = "world", year: int = 2024
    ) -> Dict[str, Any]:
        """
        Get birder profile and statistics.

        ⚠️ IMPORTANT: This method returns SIMULATED DATA for demonstration purposes.
        Real eBird user statistics require special API permissions that are not
        available through the standard eBird API.

        Args:
            username: eBird username or identifier
            region_code: Region for statistics (default: "world")
            year: Year for statistics (default: 2024)

        Returns:
            Simulated user birding statistics and profile information

        Raises:
            EBirdAPIError: For API errors with descriptive messages
        """
        try:
            logger.info(
                f"Generating SIMULATED user statistics for {username} in {region_code}"
            )

            # ⚠️ SIMULATED DATA - NOT FROM REAL EBIRD API
            # The eBird API does not provide public access to user statistics.
            # In a production system, this would either:
            # 1. Query user's public checklists if available
            # 2. Require OAuth authentication for private data
            # 3. Be removed entirely if not needed

            import random

            random.seed(hash(username) % 1000)  # Consistent results for same username

            base_species = random.randint(SIMULATED_SPECIES_MIN, SIMULATED_SPECIES_MAX)
            base_checklists = random.randint(
                SIMULATED_CHECKLISTS_MIN, SIMULATED_CHECKLISTS_MAX
            )

            user_stats = {
                "username": username,
                "region": region_code,
                "year": year,
                "species_count": base_species,
                "checklist_count": base_checklists,
                "observation_count": base_checklists * random.randint(8, 25),
                "countries_visited": random.randint(1, 15),
                "states_provinces_visited": random.randint(1, 25),
                "total_hours_birding": base_checklists * random.uniform(1.5, 4.0),
                "average_species_per_checklist": round(
                    base_species / max(base_checklists, 1), 1
                ),
                "most_active_month": random.choice(
                    ["May", "October", "April", "September"]
                ),
                "birding_level": "Intermediate" if base_species < 200 else "Advanced",
                "data_source": "SIMULATED - NOT REAL USER DATA",
            }

            # Add some seasonal activity patterns
            monthly_activity = {}
            for month in range(1, 13):
                month_names = [
                    "Jan",
                    "Feb",
                    "Mar",
                    "Apr",
                    "May",
                    "Jun",
                    "Jul",
                    "Aug",
                    "Sep",
                    "Oct",
                    "Nov",
                    "Dec",
                ]
                activity_level = random.randint(0, 15)
                monthly_activity[month_names[month - 1]] = activity_level

            result = {
                "user_profile": user_stats,
                "monthly_activity": monthly_activity,
                "warning": "⚠️ SIMULATED DATA - The eBird API does not provide public access to user statistics",
                "implementation_note": "In production, this would require OAuth authentication or be removed",
            }

            logger.info(f"Generated SIMULATED user statistics for {username}")
            return result

        except Exception as e:
            logger.error(f"Failed to generate simulated user stats for {username}: {e}")
            raise EBirdAPIError(f"User statistics generation failed: {str(e)}")


class EBirdAsyncChecklistsClient(EBirdAsyncBaseClient, EBirdAsyncChecklistsMixin):
    """Complete async eBird API client for checklist and user-related endpoints."""

    pass
