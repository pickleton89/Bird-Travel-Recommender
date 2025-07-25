#!/usr/bin/env python3
"""
Advisory Handler Module for Bird Travel Recommender MCP Server

Contains handler methods for LLM-enhanced birding advice tools:
- get_birding_advice
"""

import logging
from typing import Dict, List, Optional

from ...utils.prompt_sanitizer import sanitize_for_birding_advice
from ..auth import require_auth, AuthManager
from ..rate_limiting import rate_limit, RateLimiter

# Configure logging
logger = logging.getLogger(__name__)


class AdvisoryHandlers:
    """Handler methods for LLM-enhanced birding advice MCP tools"""

    def __init__(self):
        # Initialize auth and rate limiting components
        self.auth_manager: Optional[AuthManager] = None
        self.rate_limiter: Optional[RateLimiter] = None

    @require_auth(permissions=["get:advice"])
    @rate_limit("get_birding_advice")
    async def handle_get_birding_advice(
        self,
        handlers_container,
        question: str,
        location: str,
        species_of_interest: Optional[List[str]] = None,
        time_of_year: str = "current",
        experience_level: str = "intermediate",
        session=None,
    ):
        """Handle get_birding_advice tool - Expert birding advice using enhanced LLM prompting"""
        try:
            logger.info(f"Providing birding advice for question: {question[:100]}...")

            # Import LLM function for advice generation
            from ...utils.call_llm import call_llm

            # Build enhanced context-aware prompt using new eBird endpoints
            context_info = ""
            enhanced_data = {}

            # Build context from function parameters - fix undefined 'context' variable
            context = {
                "species": species_of_interest or [],
                "location": location,
                "season": time_of_year,
                "experience_level": experience_level,
            }

            if context:
                species = context.get("species", [])
                location_ctx = context.get("location", "")
                season = context.get("season", "")

                context_parts = []
                if species:
                    context_parts.append(f"Target species: {', '.join(species)}")
                if location_ctx:
                    context_parts.append(f"Location: {location_ctx}")

                    # Enhance with regional species list for habitat recommendations
                    try:
                        regional_species_result = await handlers_container.species_handlers.handle_get_regional_species_list(
                            location
                        )
                        if regional_species_result["success"]:
                            enhanced_data["regional_species_count"] = len(
                                regional_species_result["species_list"]
                            )
                            context_parts.append(
                                f"Regional diversity: {len(regional_species_result['species_list'])} species recorded"
                            )
                    except Exception as e:
                        logger.warning(
                            f"Could not get regional species for advice: {e}"
                        )

                    # Enhance with region details for better location context
                    try:
                        region_info_result = await handlers_container.location_handlers.handle_get_region_details(
                            location
                        )
                        if region_info_result["success"]:
                            region_name = region_info_result["region_info"].get(
                                "name", location
                            )
                            enhanced_data["region_name"] = region_name
                            context_parts.append(f"Region: {region_name}")
                    except Exception as e:
                        logger.warning(f"Could not get region info for advice: {e}")

                if season:
                    context_parts.append(f"Season: {season}")
                if experience_level:
                    context_parts.append(f"Experience level: {experience_level}")

                # Add nearest observations context for species-specific advice
                if species and location and "lat" in context and "lng" in context:
                    try:
                        for species_name in species[
                            :3
                        ]:  # Limit to 3 species for context
                            # Note: This assumes species_name might be a species code
                            nearest_obs_result = await handlers_container.location_handlers.handle_find_nearest_species(
                                species_code=species_name,
                                lat=context["lat"],
                                lng=context["lng"],
                            )
                            if (
                                nearest_obs_result["success"]
                                and nearest_obs_result["observations"]
                            ):
                                obs_count = len(nearest_obs_result["observations"])
                                context_parts.append(
                                    f"{species_name}: {obs_count} recent nearby observations"
                                )
                    except Exception as e:
                        logger.warning(
                            f"Could not get nearest observations for advice: {e}"
                        )

                if context_parts:
                    context_info = f"\n\nEnhanced Context: {'; '.join(context_parts)}"

            # Sanitize inputs for safe LLM prompting
            sanitization_result = sanitize_for_birding_advice(question, context_info)

            if not sanitization_result["is_safe"]:
                logger.warning(
                    f"Potentially unsafe input detected: {sanitization_result['threats_detected']}"
                )
                # In production, you might want to reject the request or apply stricter filtering

            expert_prompt = sanitization_result["safe_prompt"]

            try:
                advice = call_llm(expert_prompt)

                return {
                    "success": True,
                    "advice": advice,
                    "query": question,
                    "context": context,
                    "enhanced_data": enhanced_data,
                    "advice_type": "expert_llm_response_enhanced",
                }

            except Exception as llm_error:
                logger.warning(
                    f"LLM advice generation failed: {str(llm_error)}, using fallback"
                )

                # Fallback advice system
                fallback_advice = self._generate_fallback_advice(question, context)

                return {
                    "success": True,
                    "advice": fallback_advice,
                    "query": question,
                    "context": context,
                    "advice_type": "fallback_response",
                    "llm_error": str(llm_error),
                }

        except Exception as e:
            logger.error(f"Error in get_birding_advice: {str(e)}")
            return {"success": False, "error": str(e), "advice": ""}

    def _generate_fallback_advice(
        self, question: str, context: Optional[Dict] = None
    ) -> str:
        """Generate fallback birding advice when LLM is unavailable"""

        # Basic advice patterns based on common queries
        question_lower = question.lower()

        if "best time" in question_lower or "when" in question_lower:
            return """**General Timing Advice:**
            
            • **Dawn (30 minutes before sunrise to 2 hours after):** Peak bird activity, especially songbirds
            • **Dusk (2 hours before sunset to 30 minutes after):** Second peak activity period
            • **Migration seasons:** Spring (March-May) and Fall (August-October) offer the most species diversity
            • **Weather:** Overcast days often provide better birding than bright sunny conditions
            • **After storms:** Check coastal areas and migrant traps for displaced species
            
            For specific species timing, consult local birding guides or eBird data for your region."""

        elif "equipment" in question_lower or "binoculars" in question_lower:
            return """**Essential Birding Equipment:**
            
            • **Binoculars:** 8x42 recommended for general birding (good balance of magnification and field of view)
            • **Field guide:** Regional guide specific to your area
            • **Notebook/app:** For recording observations and notes
            • **Camera (optional):** For documentation and identification confirmation
            • **Comfortable clothing:** Earth tones, layers for weather changes
            • **Sun protection:** Hat and sunscreen for extended field time
            
            Start with quality binoculars - they make the biggest difference in your birding experience."""

        elif "habitat" in question_lower or "where" in question_lower:
            return """**Habitat-Based Birding Strategy:**
            
            • **Forests:** Dawn chorus offers best songbird activity
            • **Wetlands:** Early morning and late afternoon for waterfowl
            • **Grasslands:** Morning for ground-dwelling species
            • **Coast:** Tide changes bring feeding opportunities
            • **Urban parks:** Surprisingly productive, especially during migration
            
            Edge habitats (where two habitat types meet) are often most productive for bird diversity."""

        else:
            return f"""**General Birding Advice for: "{question}"**
            
            • **Plan your trip:** Check eBird for recent sightings in your target area
            • **Timing matters:** Early morning (dawn + 2 hours) is typically best
            • **Be patient:** Spend time in productive areas rather than constantly moving
            • **Use playback sparingly:** Brief use to attract secretive species, then stop
            • **Record observations:** Use eBird to contribute to citizen science
            • **Join local groups:** Connect with birding clubs for local knowledge
            
            For more specific advice, please provide details about your location, target species, or experience level."""
