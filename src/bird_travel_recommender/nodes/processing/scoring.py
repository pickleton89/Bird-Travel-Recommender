"""
ScoreLocationsNode - Rank clustered locations by species diversity and sighting frequency.

This module contains the ScoreLocationsNode which scores and ranks hotspot clusters
using multiple criteria including species diversity, observation recency, hotspot
popularity, and LLM-enhanced habitat evaluation.
"""

from pocketflow import Node
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ScoreLocationsNode(Node):
    """
    Rank clustered locations by species diversity and sighting frequency with LLM-enhanced habitat evaluation.

    Features:
    - Species diversity scoring with target species prioritization
    - Observation recency and frequency weighting
    - eBird hotspot popularity and accessibility scoring
    - LLM-enhanced habitat suitability evaluation
    - User preference weighting (photography, rarity, accessibility)
    """

    def __init__(self):
        super().__init__()
        from datetime import datetime, timedelta
        from ...utils.geo_utils import parse_ebird_datetime

        self.datetime = datetime
        self.timedelta = timedelta
        self.parse_ebird_datetime = parse_ebird_datetime

    def prep(self, shared):
        """Extract hotspot clusters and user constraints from shared store."""
        hotspot_clusters = shared.get("hotspot_clusters", [])
        constraints = shared.get("input", {}).get("constraints", {})
        validated_species = shared.get("validated_species", [])

        if not hotspot_clusters:
            logger.warning("No hotspot clusters found in shared store")

        return {
            "hotspot_clusters": hotspot_clusters,
            "constraints": constraints,
            "validated_species": validated_species,
        }

    def exec(self, prep_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score and rank hotspot clusters based on multiple criteria.

        Args:
            prep_data: Dictionary with hotspot clusters, constraints, and validated species

        Returns:
            Dictionary with scored locations and scoring statistics
        """
        hotspot_clusters = prep_data["hotspot_clusters"]
        constraints = prep_data["constraints"]
        validated_species = prep_data["validated_species"]

        scoring_stats = {
            "total_clusters_scored": len(hotspot_clusters),
            "target_species_count": len(validated_species),
            "average_diversity_score": 0.0,
            "average_recency_score": 0.0,
            "average_hotspot_score": 0.0,
            "average_accessibility_score": 0.0,
            "llm_enhanced_clusters": 0,
            "scoring_method_distribution": {},
        }

        if not hotspot_clusters:
            logger.info("No hotspot clusters to score")
            return {"scored_locations": [], "scoring_stats": scoring_stats}

        logger.info(f"Scoring {len(hotspot_clusters)} hotspot clusters")

        # Create target species lookup for prioritization
        target_species_codes = {
            species["species_code"] for species in validated_species
        }

        # Score each cluster
        scored_clusters = []
        for cluster in hotspot_clusters:
            cluster_score = self._score_cluster(
                cluster, target_species_codes, constraints, scoring_stats
            )
            scored_clusters.append(cluster_score)

        # Apply LLM enhancement for top clusters
        enhanced_clusters = self._apply_llm_enhancement(
            scored_clusters, validated_species, constraints, scoring_stats
        )

        # Sort by final score (descending)
        enhanced_clusters.sort(key=lambda c: c["final_score"], reverse=True)

        # Calculate summary statistics
        if enhanced_clusters:
            scoring_stats["average_diversity_score"] = sum(
                c["scoring"]["diversity_score"] for c in enhanced_clusters
            ) / len(enhanced_clusters)
            scoring_stats["average_recency_score"] = sum(
                c["scoring"]["recency_score"] for c in enhanced_clusters
            ) / len(enhanced_clusters)
            scoring_stats["average_hotspot_score"] = sum(
                c["scoring"]["hotspot_score"] for c in enhanced_clusters
            ) / len(enhanced_clusters)
            scoring_stats["average_accessibility_score"] = sum(
                c["scoring"]["accessibility_score"] for c in enhanced_clusters
            ) / len(enhanced_clusters)

        logger.info(
            f"Location scoring completed: {len(enhanced_clusters)} clusters ranked"
        )

        return {"scored_locations": enhanced_clusters, "scoring_stats": scoring_stats}

    def _score_cluster(
        self, cluster: Dict, target_species_codes: set, constraints: Dict, stats: Dict
    ) -> Dict:
        """
        Score a single cluster based on multiple criteria.

        Args:
            cluster: Hotspot cluster dictionary
            target_species_codes: Set of target species codes
            constraints: User constraints
            stats: Statistics dictionary to update

        Returns:
            Cluster dictionary with scoring information added
        """
        scored_cluster = dict(cluster)  # Copy original cluster

        # 1. Species Diversity Score (40% weight)
        diversity_score = self._calculate_diversity_score(cluster, target_species_codes)

        # 2. Observation Recency Score (25% weight)
        recency_score = self._calculate_recency_score(cluster)

        # 3. eBird Hotspot Score (20% weight)
        hotspot_score = self._calculate_hotspot_score(cluster)

        # 4. Accessibility Score (15% weight)
        accessibility_score = self._calculate_accessibility_score(cluster, constraints)

        # Calculate weighted base score
        base_score = (
            diversity_score * 0.40
            + recency_score * 0.25
            + hotspot_score * 0.20
            + accessibility_score * 0.15
        )

        # Store detailed scoring breakdown
        scored_cluster["scoring"] = {
            "diversity_score": diversity_score,
            "recency_score": recency_score,
            "hotspot_score": hotspot_score,
            "accessibility_score": accessibility_score,
            "base_score": base_score,
            "target_species_found": len(
                set(cluster["statistics"]["species_codes"]) & target_species_codes
            ),
            "total_species_found": cluster["statistics"]["species_diversity"],
            "scoring_method": "algorithmic",
        }

        scored_cluster["base_score"] = base_score
        scored_cluster["final_score"] = base_score  # Will be enhanced later

        return scored_cluster

    def _calculate_diversity_score(
        self, cluster: Dict, target_species_codes: set
    ) -> float:
        """
        Calculate species diversity score with target species prioritization.

        Args:
            cluster: Hotspot cluster dictionary
            target_species_codes: Set of target species codes

        Returns:
            Diversity score (0.0-1.0)
        """
        cluster_species = set(cluster["statistics"]["species_codes"])
        total_species = len(cluster_species)
        target_species_found = len(cluster_species & target_species_codes)

        if not target_species_codes:
            # No target species specified, use total diversity
            return min(total_species / 50.0, 1.0)  # Normalize to max 50 species

        # Prioritize target species coverage
        target_coverage = target_species_found / len(target_species_codes)
        diversity_bonus = min(
            total_species / 30.0, 0.5
        )  # Up to 0.5 bonus for diversity

        return min(target_coverage + diversity_bonus, 1.0)

    def _calculate_recency_score(self, cluster: Dict) -> float:
        """
        Calculate observation recency score.

        Args:
            cluster: Hotspot cluster dictionary

        Returns:
            Recency score (0.0-1.0)
        """
        try:
            most_recent = cluster["statistics"]["most_recent_observation"]
            if most_recent == "Unknown":
                return 0.3  # Default score for unknown dates

            recent_date = self.parse_ebird_datetime(most_recent)
            if not recent_date:
                return 0.3

            now = self.datetime.now()
            days_ago = (now - recent_date).days

            # Score based on how recent the observations are
            if days_ago <= 3:
                return 1.0  # Very recent
            elif days_ago <= 7:
                return 0.8  # Within a week
            elif days_ago <= 14:
                return 0.6  # Within two weeks
            elif days_ago <= 30:
                return 0.4  # Within a month
            else:
                return 0.2  # Older than a month

        except Exception as e:
            logger.debug(f"Error calculating recency score: {e}")
            return 0.3  # Default fallback

    def _calculate_hotspot_score(self, cluster: Dict) -> float:
        """
        Calculate eBird hotspot score based on popularity and metadata.

        Args:
            cluster: Hotspot cluster dictionary

        Returns:
            Hotspot score (0.0-1.0)
        """
        accessibility = cluster.get("accessibility", {})

        # Base score for having hotspot status
        if not accessibility.get("has_hotspot", False):
            return 0.2  # Non-hotspot locations get low score

        hotspot_score = 0.6  # Base score for being a hotspot

        # Check hotspot metadata for additional scoring
        for location in cluster.get("locations", []):
            hotspot_metadata = location.get("hotspot_metadata", {})

            # Score based on all-time species count
            species_all_time = hotspot_metadata.get("num_species_all_time", 0)
            if species_all_time > 200:
                hotspot_score += 0.3
            elif species_all_time > 100:
                hotspot_score += 0.2
            elif species_all_time > 50:
                hotspot_score += 0.1

            # Prefer official eBird hotspots over nearby locations
            if hotspot_metadata.get("distance_to_hotspot_km", 0) == 0:
                hotspot_score += 0.1

            break  # Only score based on first hotspot location

        return min(hotspot_score, 1.0)

    def _calculate_accessibility_score(self, cluster: Dict, constraints: Dict) -> float:
        """
        Calculate accessibility score based on travel constraints and location quality.

        Args:
            cluster: Hotspot cluster dictionary
            constraints: User constraints

        Returns:
            Accessibility score (0.0-1.0)
        """
        accessibility = cluster.get("accessibility", {})

        # Base score from coordinate quality
        base_score = 0.7 if accessibility.get("coordinate_quality") == "high" else 0.5

        # Travel time considerations
        avg_travel_time = accessibility.get("avg_travel_time_estimate")
        if avg_travel_time is not None:
            # Prefer closer locations
            if avg_travel_time <= 1.0:  # Within 1 hour
                base_score += 0.2
            elif avg_travel_time <= 2.0:  # Within 2 hours
                base_score += 0.1
            elif avg_travel_time > 4.0:  # More than 4 hours
                base_score -= 0.2

        # Cluster size and sighting density
        location_count = cluster["statistics"]["location_count"]
        sighting_count = cluster["statistics"]["sighting_count"]

        if location_count > 1 and sighting_count > 5:
            base_score += 0.1  # Bonus for rich clusters

        return max(min(base_score, 1.0), 0.0)

    def _apply_llm_enhancement(
        self,
        scored_clusters: List[Dict],
        validated_species: List[Dict],
        constraints: Dict,
        stats: Dict,
    ) -> List[Dict]:
        """
        Apply LLM enhancement to top scoring clusters for habitat suitability evaluation.

        Args:
            scored_clusters: List of scored cluster dictionaries
            validated_species: List of validated species
            constraints: User constraints
            stats: Statistics dictionary to update

        Returns:
            List of enhanced cluster dictionaries
        """
        # Enhance top 10 clusters or all if fewer than 10
        clusters_to_enhance = min(10, len(scored_clusters))
        top_clusters = sorted(
            scored_clusters, key=lambda c: c["base_score"], reverse=True
        )[:clusters_to_enhance]

        enhanced_clusters = scored_clusters.copy()

        for i, cluster in enumerate(top_clusters):
            try:
                llm_enhancement = self._get_llm_habitat_evaluation(
                    cluster, validated_species, constraints
                )

                # Find the cluster in the full list and update it
                cluster_id = cluster["cluster_id"]
                for j, full_cluster in enumerate(enhanced_clusters):
                    if full_cluster["cluster_id"] == cluster_id:
                        enhanced_clusters[j] = self._apply_llm_scoring(
                            full_cluster, llm_enhancement
                        )
                        stats["llm_enhanced_clusters"] += 1
                        break

            except Exception as e:
                logger.warning(
                    f"LLM enhancement failed for cluster {cluster['cluster_id']}: {e}"
                )
                # Keep original scoring if LLM fails

        stats["scoring_method_distribution"] = {
            "algorithmic_only": len(enhanced_clusters) - stats["llm_enhanced_clusters"],
            "llm_enhanced": stats["llm_enhanced_clusters"],
        }

        return enhanced_clusters

    def _get_llm_habitat_evaluation(
        self, cluster: Dict, validated_species: List[Dict], constraints: Dict
    ) -> Dict:
        """
        Get LLM-based habitat suitability evaluation for a cluster.

        Args:
            cluster: Hotspot cluster dictionary
            validated_species: List of validated species
            constraints: User constraints

        Returns:
            Dictionary with LLM evaluation results
        """
        # Prepare species information for LLM
        target_species_info = []
        cluster_species_codes = set(cluster["statistics"]["species_codes"])

        for species in validated_species:
            if species["species_code"] in cluster_species_codes:
                target_species_info.append(
                    {
                        "common_name": species["common_name"],
                        "scientific_name": species["scientific_name"],
                        "seasonal_notes": species.get("seasonal_notes", ""),
                        "behavioral_notes": species.get("behavioral_notes", ""),
                    }
                )

        # Create LLM prompt for habitat evaluation
        location_scoring_prompt = f"""
You are an expert birder evaluating locations for observing specific bird species.

LOCATION: {cluster["cluster_name"]}
COORDINATES: {cluster["center_lat"]:.4f}, {cluster["center_lng"]:.4f}
RECENT SIGHTINGS: {cluster["statistics"]["sighting_count"]} observations
SPECIES DIVERSITY: {cluster["statistics"]["species_diversity"]} species total

TARGET SPECIES FOUND AT THIS LOCATION:
{self._format_species_for_llm(target_species_info)}

LOCATION CHARACTERISTICS:
- eBird Hotspot: {"Yes" if cluster["accessibility"]["has_hotspot"] else "No"}
- Number of sub-locations: {cluster["statistics"]["location_count"]}
- Most recent observation: {cluster["statistics"]["most_recent_observation"]}

Please evaluate this location for birding success considering:
1. Habitat suitability for the target species
2. Seasonal timing and migration patterns
3. Time of day effectiveness for observations
4. Weather condition preferences
5. Accessibility and birding logistics

Provide a habitat suitability score from 0.0 to 1.0 and brief reasoning.
Respond in this format:
SCORE: 0.8
REASONING: [2-3 sentences explaining the score]
BEST_TIME: [optimal timing advice]
TIPS: [specific observation tips for this location]
"""

        from ...utils.call_llm import call_llm

        llm_response = call_llm(location_scoring_prompt)

        return self._parse_llm_evaluation(llm_response)

    def _format_species_for_llm(self, species_info: List[Dict]) -> str:
        """Format species information for LLM prompt."""
        if not species_info:
            return "No target species recently observed at this location."

        formatted = []
        for species in species_info[:5]:  # Limit to 5 species to avoid token overuse
            formatted.append(
                f"- {species['common_name']} ({species['scientific_name']})"
            )
            if species.get("seasonal_notes"):
                formatted.append(f"  Seasonal: {species['seasonal_notes']}")
            if species.get("behavioral_notes"):
                formatted.append(f"  Behavior: {species['behavioral_notes']}")

        return "\n".join(formatted)

    def _parse_llm_evaluation(self, llm_response: str) -> Dict:
        """
        Parse LLM evaluation response.

        Args:
            llm_response: Raw LLM response text

        Returns:
            Dictionary with parsed evaluation data
        """
        evaluation = {
            "habitat_score": 0.5,  # Default fallback
            "reasoning": "LLM evaluation parsing failed",
            "best_time": "Timing varies by species",
            "tips": "Refer to field guides for specific advice",
        }

        try:
            lines = llm_response.strip().split("\n")

            for line in lines:
                line = line.strip()
                if line.startswith("SCORE:"):
                    try:
                        score_str = line.replace("SCORE:", "").strip()
                        score = float(score_str)
                        evaluation["habitat_score"] = max(0.0, min(1.0, score))
                    except ValueError:
                        pass
                elif line.startswith("REASONING:"):
                    evaluation["reasoning"] = line.replace("REASONING:", "").strip()
                elif line.startswith("BEST_TIME:"):
                    evaluation["best_time"] = line.replace("BEST_TIME:", "").strip()
                elif line.startswith("TIPS:"):
                    evaluation["tips"] = line.replace("TIPS:", "").strip()

        except Exception as e:
            logger.debug(f"Error parsing LLM evaluation: {e}")

        return evaluation

    def _apply_llm_scoring(self, cluster: Dict, llm_evaluation: Dict) -> Dict:
        """
        Apply LLM evaluation to cluster scoring.

        Args:
            cluster: Original cluster dictionary
            llm_evaluation: LLM evaluation results

        Returns:
            Enhanced cluster dictionary
        """
        enhanced_cluster = dict(cluster)

        # Add LLM evaluation data
        enhanced_cluster["llm_evaluation"] = llm_evaluation
        enhanced_cluster["scoring"]["scoring_method"] = "llm_enhanced"

        # Calculate enhanced final score
        base_score = cluster["base_score"]
        habitat_score = llm_evaluation["habitat_score"]

        # Blend algorithmic and LLM scores (70% base, 30% habitat)
        enhanced_final_score = (base_score * 0.7) + (habitat_score * 0.3)
        enhanced_cluster["final_score"] = enhanced_final_score

        enhanced_cluster["scoring"]["habitat_score"] = habitat_score
        enhanced_cluster["scoring"]["enhanced_final_score"] = enhanced_final_score

        return enhanced_cluster

    def post(self, shared, prep_res, exec_res):
        """Store scored locations in shared store."""
        shared["scored_locations"] = exec_res["scored_locations"]
        shared["location_scoring_stats"] = exec_res["scoring_stats"]

        # Check if scoring was successful
        scored_count = len(exec_res["scored_locations"])

        if scored_count == 0:
            logger.warning("No locations were scored")
            return "no_scored_locations"

        # Check if we have good scoring diversity
        top_score = (
            exec_res["scored_locations"][0]["final_score"] if scored_count > 0 else 0
        )
        if top_score < 0.3:
            logger.warning(f"Low top location score: {top_score:.2f}")
            return "low_scoring_locations"

        # Report LLM enhancement success
        llm_enhanced = exec_res["scoring_stats"]["llm_enhanced_clusters"]
        if llm_enhanced > 0:
            logger.info(
                f"Location scoring successful: {scored_count} locations ranked, "
                f"{llm_enhanced} enhanced with LLM habitat evaluation"
            )
        else:
            logger.info(
                f"Location scoring successful: {scored_count} locations ranked using algorithmic scoring"
            )

        return "default"
