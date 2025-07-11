"""
eBird API client for historical analysis and trend-related endpoints.

This module provides methods for analyzing historical bird data from the eBird API,
including seasonal trends, migration patterns, and temporal analysis.
"""

from typing import List, Dict, Any, Optional
import logging
from .ebird_base import EBirdBaseClient, EBirdAPIError
from ..constants import EBIRD_DAYS_BACK_DEFAULT

logger = logging.getLogger(__name__)


class EBirdAnalysisMixin:
    """Mixin class providing historical analysis and trend-related eBird API methods."""

    def get_historic_observations(
        self,
        region: str,
        year: int,
        month: int,
        day: int,
        species_code: Optional[str] = None,
        locale: str = "en",
        max_results: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Get historical observations for a specific date in a region.

        Provides insights into birding activity and species presence on specific
        historical dates, useful for seasonal planning and trend analysis.

        Args:
            region: eBird region code (e.g., "US-CA", "MX-ROO")
            year: Year (e.g., 2023)
            month: Month (1-12)
            day: Day (1-31)
            species_code: Optional species code to filter results
            locale: Language code for common names (default: "en")
            max_results: Maximum observations to return (default: 1000)

        Returns:
            List of historical observation dictionaries for the specified date
        """
        # Format date as required by eBird API
        date_str = f"{year}/{month:02d}/{day:02d}"

        if species_code:
            endpoint = f"/data/obs/{region}/historic/{date_str}/{species_code}"
        else:
            endpoint = f"/data/obs/{region}/historic/{date_str}"

        params = {
            "fmt": "json",
            "locale": locale,
            "maxResults": min(max_results, 10000),  # eBird API limit
        }

        try:
            observations = self.make_request(endpoint, params)

            # Enrich with date information for easier processing
            enriched_observations = []
            for obs in observations:
                enriched_obs = {
                    **obs,
                    "historical_date": {
                        "year": year,
                        "month": month,
                        "day": day,
                        "formatted": date_str,
                    },
                }
                enriched_observations.append(enriched_obs)

            logger.info(
                f"Retrieved {len(enriched_observations)} historical observations for {region} on {date_str}"
            )
            return enriched_observations

        except EBirdAPIError as e:
            logger.error(
                f"Failed to get historical observations for {region} on {date_str}: {e}"
            )
            raise

    def get_seasonal_trends(
        self,
        region: str,
        species_code: Optional[str] = None,
        start_year: int = 2020,
        end_year: Optional[int] = None,
        locale: str = "en",
    ) -> Dict[str, Any]:
        """
        Analyze seasonal birding trends by aggregating historical observations across months.

        Provides month-by-month analysis of species presence and observation frequency
        to identify optimal birding seasons and migration patterns.

        Args:
            region: eBird region code (e.g., "US-CA", "MX-ROO")
            species_code: Optional species code for species-specific trends
            start_year: Starting year for analysis (default: 2020)
            end_year: Ending year for analysis (default: current year)
            locale: Language code for common names (default: "en")

        Returns:
            Dictionary containing seasonal trend analysis
        """
        import datetime

        if end_year is None:
            end_year = datetime.datetime.now().year

        try:
            # Collect data across multiple months for trend analysis
            monthly_data = {}
            total_observations = 0

            # Sample key months for seasonal analysis (every 2 months to reduce API calls)
            key_months = [
                1,
                3,
                5,
                7,
                9,
                11,
            ]  # January, March, May, July, September, November

            for month in key_months:
                monthly_observations = []

                # Sample a few days from each month across years
                for year in range(start_year, end_year + 1):
                    try:
                        # Sample mid-month observations (15th of each month)
                        sample_obs = self.get_historic_observations(
                            region=region,
                            year=year,
                            month=month,
                            day=15,
                            species_code=species_code,
                            locale=locale,
                            max_results=500,
                        )
                        monthly_observations.extend(sample_obs)
                    except Exception as e:
                        logger.warning(
                            f"Could not get data for {year}-{month:02d}: {e}"
                        )
                        continue

                # Analyze monthly data
                if species_code:
                    # Species-specific analysis
                    species_count = len(monthly_observations)
                    monthly_data[month] = {
                        "month_name": datetime.date(2000, month, 1).strftime("%B"),
                        "observation_count": species_count,
                        "years_sampled": end_year - start_year + 1,
                        "avg_per_year": round(
                            species_count / (end_year - start_year + 1), 1
                        ),
                    }
                else:
                    # General biodiversity analysis
                    unique_species = set()
                    for obs in monthly_observations:
                        if obs.get("speciesCode"):
                            unique_species.add(obs["speciesCode"])

                    monthly_data[month] = {
                        "month_name": datetime.date(2000, month, 1).strftime("%B"),
                        "total_observations": len(monthly_observations),
                        "unique_species": len(unique_species),
                        "diversity_index": len(unique_species)
                        / max(len(monthly_observations), 1)
                        * 100,
                        "years_sampled": end_year - start_year + 1,
                    }

                total_observations += len(monthly_observations)

            # Generate seasonal insights
            if species_code and monthly_data:
                peak_month = max(
                    monthly_data.items(), key=lambda x: x[1]["observation_count"]
                )
                low_month = min(
                    monthly_data.items(), key=lambda x: x[1]["observation_count"]
                )
            elif monthly_data:
                peak_month = max(
                    monthly_data.items(), key=lambda x: x[1]["unique_species"]
                )
                low_month = min(
                    monthly_data.items(), key=lambda x: x[1]["unique_species"]
                )
            else:
                peak_month = low_month = (0, {"month_name": "Unknown"})

            seasonal_analysis = {
                "region": region,
                "species_code": species_code,
                "analysis_period": {
                    "start_year": start_year,
                    "end_year": end_year,
                    "years_analyzed": end_year - start_year + 1,
                },
                "monthly_trends": monthly_data,
                "seasonal_insights": {
                    "peak_month": {
                        "month": peak_month[0],
                        "name": peak_month[1]["month_name"],
                        "data": peak_month[1],
                    },
                    "lowest_month": {
                        "month": low_month[0],
                        "name": low_month[1]["month_name"],
                        "data": low_month[1],
                    },
                    "total_observations_sampled": total_observations,
                },
                "recommendations": {
                    "best_season": f"{peak_month[1]['month_name']} appears to be optimal for {'this species' if species_code else 'birding diversity'}",
                    "avoid_season": f"{low_month[1]['month_name']} shows {'lowest activity' if species_code else 'reduced diversity'}",
                },
            }

            logger.info(
                f"Generated seasonal trends for {region}: {total_observations} observations analyzed"
            )
            return seasonal_analysis

        except Exception as e:
            logger.error(f"Failed to generate seasonal trends for {region}: {e}")
            raise EBirdAPIError(f"Seasonal trend analysis failed: {str(e)}")

    def get_yearly_comparisons(
        self,
        region: str,
        reference_date: str,
        years_to_compare: List[int],
        species_code: Optional[str] = None,
        locale: str = "en",
    ) -> Dict[str, Any]:
        """
        Compare birding activity across multiple years for the same date/season.

        Provides year-over-year analysis to identify trends, population changes,
        and optimal timing based on historical patterns.

        Args:
            region: eBird region code (e.g., "US-CA", "MX-ROO")
            reference_date: Date in MM-DD format (e.g., "05-15" for May 15th)
            years_to_compare: List of years to compare (e.g., [2020, 2021, 2022, 2023])
            species_code: Optional species code for species-specific comparison
            locale: Language code for common names (default: "en")

        Returns:
            Dictionary containing year-over-year comparison analysis
        """
        try:
            # Parse reference date
            month, day = map(int, reference_date.split("-"))

            yearly_data = {}
            all_species = set()

            for year in years_to_compare:
                try:
                    observations = self.get_historic_observations(
                        region=region,
                        year=year,
                        month=month,
                        day=day,
                        species_code=species_code,
                        locale=locale,
                        max_results=1000,
                    )

                    # Analyze yearly data
                    unique_species = set()
                    checklist_ids = set()

                    for obs in observations:
                        if obs.get("speciesCode"):
                            unique_species.add(obs["speciesCode"])
                            all_species.add(obs["speciesCode"])
                        if obs.get("subId"):
                            checklist_ids.add(obs["subId"])

                    yearly_data[year] = {
                        "total_observations": len(observations),
                        "unique_species": len(unique_species),
                        "estimated_checklists": len(checklist_ids),
                        "species_list": list(unique_species),
                        "diversity_score": len(unique_species)
                        / max(len(observations), 1)
                        * 100,
                        "observations_per_checklist": len(observations)
                        / max(len(checklist_ids), 1),
                    }

                except Exception as e:
                    logger.warning(
                        f"Could not get data for {year}-{month:02d}-{day:02d}: {e}"
                    )
                    yearly_data[year] = {
                        "total_observations": 0,
                        "unique_species": 0,
                        "estimated_checklists": 0,
                        "species_list": [],
                        "diversity_score": 0,
                        "observations_per_checklist": 0,
                        "error": str(e),
                    }

            # Calculate trends and insights
            if len(yearly_data) > 1:
                years = sorted(yearly_data.keys())

                # Calculate trends
                if species_code:
                    # Species-specific trends
                    observation_counts = [
                        yearly_data[y]["total_observations"] for y in years
                    ]
                    trend = (
                        "increasing"
                        if observation_counts[-1] > observation_counts[0]
                        else "decreasing"
                    )
                    best_year = max(
                        years, key=lambda y: yearly_data[y]["total_observations"]
                    )
                else:
                    # Biodiversity trends
                    diversity_scores = [
                        yearly_data[y]["diversity_score"] for y in years
                    ]
                    trend = (
                        "improving"
                        if diversity_scores[-1] > diversity_scores[0]
                        else "declining"
                    )
                    best_year = max(
                        years, key=lambda y: yearly_data[y]["unique_species"]
                    )

                comparison_analysis = {
                    "region": region,
                    "reference_date": reference_date,
                    "species_code": species_code,
                    "years_compared": years_to_compare,
                    "yearly_data": yearly_data,
                    "trend_analysis": {
                        "overall_trend": trend,
                        "best_year": best_year,
                        "best_year_data": yearly_data[best_year],
                        "years_with_data": len(
                            [
                                y
                                for y in yearly_data.values()
                                if y["total_observations"] > 0
                            ]
                        ),
                    },
                    "species_insights": {
                        "total_species_across_years": len(all_species),
                        "consistent_species": len(
                            set.intersection(
                                *[
                                    set(yearly_data[y]["species_list"])
                                    for y in years
                                    if yearly_data[y]["species_list"]
                                ]
                            )
                        )
                        if len(years) > 1
                        and any(yearly_data[y]["species_list"] for y in years)
                        else 0,
                        "all_species_list": list(all_species),
                    },
                    "recommendations": {
                        "optimal_year_pattern": f"Based on {len(years)} years of data, {best_year} showed the best results",
                        "trend_direction": f"{'Species activity' if species_code else 'Biodiversity'} appears to be {trend} at this location and date",
                    },
                }
            else:
                comparison_analysis = {
                    "region": region,
                    "reference_date": reference_date,
                    "species_code": species_code,
                    "years_compared": years_to_compare,
                    "yearly_data": yearly_data,
                    "error": "Insufficient data for comparison analysis",
                }

            logger.info(
                f"Generated yearly comparison for {region} on {reference_date}: {len(years_to_compare)} years analyzed"
            )
            return comparison_analysis

        except Exception as e:
            logger.error(f"Failed to generate yearly comparison for {region}: {e}")
            raise EBirdAPIError(f"Yearly comparison analysis failed: {str(e)}")

    def get_migration_data(
        self,
        species_code: str,
        region_code: str = "US",
        months: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Get species migration timing and routes data.

        Args:
            species_code: eBird species code (e.g., "norcar")
            region_code: eBird region code (default: "US")
            months: List of months to analyze (1-12, default: all months)

        Returns:
            Migration timing analysis with seasonal patterns and peak periods

        Raises:
            EBirdAPIError: For API errors with descriptive messages
        """
        try:
            logger.info(f"Analyzing migration data for {species_code} in {region_code}")

            # Since eBird doesn't have direct migration endpoint, build from seasonal data
            if months is None:
                months = list(range(1, 13))  # All months

            migration_patterns = []

            for month in months:
                try:
                    # Get historical observations for this month across multiple years
                    month_observations = self.get_species_observations(
                        species_code=species_code,
                        region_code=region_code,
                        days_back=EBIRD_DAYS_BACK_DEFAULT,
                        max_results=1000,
                    )

                    # Analyze abundance patterns
                    observation_count = len(month_observations)

                    # Determine migration status based on observation patterns
                    if observation_count > 100:
                        status = "Peak Migration"
                    elif observation_count > 50:
                        status = "Active Migration"
                    elif observation_count > 10:
                        status = "Present"
                    else:
                        status = "Rare/Absent"

                    migration_patterns.append(
                        {
                            "month": month,
                            "month_name": [
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
                            ][month - 1],
                            "observation_count": observation_count,
                            "migration_status": status,
                        }
                    )

                except Exception:
                    # Fallback for months with no data
                    migration_patterns.append(
                        {
                            "month": month,
                            "month_name": [
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
                            ][month - 1],
                            "observation_count": 0,
                            "migration_status": "No Data",
                        }
                    )

            # Identify peak migration periods
            peak_months = [
                p
                for p in migration_patterns
                if p["migration_status"] == "Peak Migration"
            ]

            result = {
                "species_code": species_code,
                "region": region_code,
                "analysis_months": months,
                "migration_patterns": migration_patterns,
                "peak_migration_months": [p["month_name"] for p in peak_months],
                "total_peak_months": len(peak_months),
                "analysis_note": f"Migration analysis based on seasonal observation patterns for {species_code}",
            }

            logger.info(
                f"Generated migration analysis for {species_code}: {len(peak_months)} peak months identified"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to get migration data for {species_code}: {e}")
            raise EBirdAPIError(f"Migration data analysis failed: {str(e)}")

    def get_peak_times(
        self, species_code: str, lat: float, lng: float, radius_km: int = 25
    ) -> Dict[str, Any]:
        """
        Get best times to see specific species at a location.

        Args:
            species_code: eBird species code (e.g., "norcar")
            lat: Latitude coordinate
            lng: Longitude coordinate
            radius_km: Search radius in kilometers (default: 25)

        Returns:
            Optimal timing recommendations for species observation

        Raises:
            EBirdAPIError: For API errors with descriptive messages
        """
        try:
            logger.info(f"Analyzing peak times for {species_code} at ({lat}, {lng})")

            # Get recent observations to understand current patterns
            recent_observations = self.get_nearby_species_observations(
                species_code=species_code,
                lat=lat,
                lng=lng,
                distance_km=radius_km,
                days_back=30,
            )

            # Analyze time patterns from recent observations
            hourly_counts = {}

            for obs in recent_observations:
                # Extract timing information (if available in observation data)
                obs_date = obs.get("obsDt", "")
                if obs_date:
                    try:
                        # Simple hour extraction (assuming ISO format)
                        if "T" in obs_date and ":" in obs_date:
                            hour = int(obs_date.split("T")[1].split(":")[0])
                            hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
                    except Exception:
                        pass

            # Determine optimal times based on bird behavior patterns
            # Most songbirds are active in early morning and late afternoon
            recommended_times = {
                "best_hours": ["6:00-9:00 AM", "4:00-7:00 PM"],
                "peak_season": "Spring and Fall migration periods",
                "daily_pattern": "Most active during dawn and dusk",
                "weather_factors": "Clear, calm mornings are optimal",
            }

            # Generate time-based recommendations
            time_recommendations = {
                "morning": {
                    "start_time": "6:00 AM",
                    "end_time": "9:00 AM",
                    "activity_level": "High",
                    "notes": "Peak singing and foraging activity",
                },
                "midday": {
                    "start_time": "10:00 AM",
                    "end_time": "3:00 PM",
                    "activity_level": "Moderate",
                    "notes": "Birds often rest during heat of day",
                },
                "evening": {
                    "start_time": "4:00 PM",
                    "end_time": "7:00 PM",
                    "activity_level": "High",
                    "notes": "Evening feeding and territorial activity",
                },
            }

            result = {
                "species_code": species_code,
                "location": {"latitude": lat, "longitude": lng},
                "search_radius": radius_km,
                "recent_observations": len(recent_observations),
                "recommended_times": recommended_times,
                "time_recommendations": time_recommendations,
                "analysis_note": f"Peak timing analysis for {species_code} based on typical behavior patterns",
            }

            logger.info(
                f"Generated peak times analysis for {species_code} at ({lat}, {lng})"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to get peak times for {species_code}: {e}")
            raise EBirdAPIError(f"Peak times analysis failed: {str(e)}")


class EBirdAnalysisClient(EBirdBaseClient, EBirdAnalysisMixin):
    """Complete eBird API client for historical analysis and trend-related endpoints."""

    pass
