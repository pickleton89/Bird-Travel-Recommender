#!/usr/bin/env python3
"""
Advisory Handler Module for Bird Travel Recommender MCP Server

Contains handler methods for LLM-enhanced birding advice tools:
- get_birding_advice
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Sequence

# Configure logging
logger = logging.getLogger(__name__)

class AdvisoryHandlers:
    """Handler methods for LLM-enhanced birding advice MCP tools"""
    
    def __init__(self):
        pass
    
    async def handle_get_birding_advice(self, handlers_container, query: str, context: Optional[Dict] = None, **kwargs):
        """Handle get_birding_advice tool - Expert birding advice using enhanced LLM prompting"""
        try:
            logger.info(f"Providing birding advice for query: {query[:100]}...")
            
            # Import LLM function for advice generation
            from ...utils.call_llm import call_llm
            
            # Build enhanced context-aware prompt using new eBird endpoints
            context_info = ""
            enhanced_data = {}
            
            if context:
                species = context.get("species", [])
                location = context.get("location", "")
                season = context.get("season", "")
                experience_level = context.get("experience_level", "")
                
                context_parts = []
                if species:
                    context_parts.append(f"Target species: {', '.join(species)}")
                if location:
                    context_parts.append(f"Location: {location}")
                    
                    # Enhance with regional species list for habitat recommendations
                    try:
                        regional_species_result = await handlers_container.species_handlers.handle_get_regional_species_list(location)
                        if regional_species_result["success"]:
                            enhanced_data["regional_species_count"] = len(regional_species_result["species_list"])
                            context_parts.append(f"Regional diversity: {len(regional_species_result['species_list'])} species recorded")
                    except Exception as e:
                        logger.warning(f"Could not get regional species for advice: {e}")
                    
                    # Enhance with region details for better location context
                    try:
                        region_info_result = await handlers_container.location_handlers.handle_get_region_details(location)
                        if region_info_result["success"]:
                            region_name = region_info_result["region_info"].get("name", location)
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
                        for species_name in species[:3]:  # Limit to 3 species for context
                            # Note: This assumes species_name might be a species code
                            nearest_obs_result = await handlers_container.location_handlers.handle_find_nearest_species(
                                species_code=species_name,
                                lat=context["lat"],
                                lng=context["lng"]
                            )
                            if nearest_obs_result["success"] and nearest_obs_result["observations"]:
                                obs_count = len(nearest_obs_result["observations"])
                                context_parts.append(f"{species_name}: {obs_count} recent nearby observations")
                    except Exception as e:
                        logger.warning(f"Could not get nearest observations for advice: {e}")
                
                if context_parts:
                    context_info = f"\n\nEnhanced Context: {'; '.join(context_parts)}"
            
            expert_prompt = f"""You are an expert birding guide with decades of field experience and deep knowledge of bird behavior, habitats, and identification techniques. 
            
            Please provide professional birding advice for the following query: {query}{context_info}
            
            Your response should include:
            1. Direct answer to the specific question
            2. Relevant species-specific behavior and habitat information
            3. Practical field techniques and timing recommendations
            4. Equipment suggestions if applicable
            5. Seasonal considerations and migration patterns
            6. Safety and ethical birding practices
            
            Be specific, practical, and draw from ornithological knowledge and field experience. 
            Provide actionable advice that will help the birder succeed."""
            
            try:
                advice = call_llm(expert_prompt)
                
                return {
                    "success": True,
                    "advice": advice,
                    "query": query,
                    "context": context,
                    "enhanced_data": enhanced_data,
                    "advice_type": "expert_llm_response_enhanced"
                }
                
            except Exception as llm_error:
                logger.warning(f"LLM advice generation failed: {str(llm_error)}, using fallback")
                
                # Fallback advice system
                fallback_advice = self._generate_fallback_advice(query, context)
                
                return {
                    "success": True,
                    "advice": fallback_advice,
                    "query": query,
                    "context": context,
                    "advice_type": "fallback_response",
                    "llm_error": str(llm_error)
                }
                
        except Exception as e:
            logger.error(f"Error in get_birding_advice: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "advice": ""
            }

    def _generate_fallback_advice(self, query: str, context: Optional[Dict] = None) -> str:
        """Generate fallback birding advice when LLM is unavailable"""
        
        # Basic advice patterns based on common queries
        query_lower = query.lower()
        
        if "best time" in query_lower or "when" in query_lower:
            return """**General Timing Advice:**
            
            • **Dawn (30 minutes before sunrise to 2 hours after):** Peak bird activity, especially songbirds
            • **Dusk (2 hours before sunset to 30 minutes after):** Second peak activity period
            • **Migration seasons:** Spring (March-May) and Fall (August-October) offer the most species diversity
            • **Weather:** Overcast days often provide better birding than bright sunny conditions
            • **After storms:** Check coastal areas and migrant traps for displaced species
            
            For specific species timing, consult local birding guides or eBird data for your region."""
            
        elif "equipment" in query_lower or "binoculars" in query_lower:
            return """**Essential Birding Equipment:**
            
            • **Binoculars:** 8x42 recommended for general birding (good balance of magnification and field of view)
            • **Field guide:** Regional guide specific to your area
            • **Notebook/app:** For recording observations and notes
            • **Camera (optional):** For documentation and identification confirmation
            • **Comfortable clothing:** Earth tones, layers for weather changes
            • **Sun protection:** Hat and sunscreen for extended field time
            
            Start with quality binoculars - they make the biggest difference in your birding experience."""
            
        elif "habitat" in query_lower or "where" in query_lower:
            return """**Habitat-Based Birding Strategy:**
            
            • **Forests:** Dawn chorus offers best songbird activity
            • **Wetlands:** Early morning and late afternoon for waterfowl
            • **Grasslands:** Morning for ground-dwelling species
            • **Coast:** Tide changes bring feeding opportunities
            • **Urban parks:** Surprisingly productive, especially during migration
            
            Edge habitats (where two habitat types meet) are often most productive for bird diversity."""
            
        else:
            return f"""**General Birding Advice for: "{query}"**
            
            • **Plan your trip:** Check eBird for recent sightings in your target area
            • **Timing matters:** Early morning (dawn + 2 hours) is typically best
            • **Be patient:** Spend time in productive areas rather than constantly moving
            • **Use playback sparingly:** Brief use to attract secretive species, then stop
            • **Record observations:** Use eBird to contribute to citizen science
            • **Join local groups:** Connect with birding clubs for local knowledge
            
            For more specific advice, please provide details about your location, target species, or experience level."""