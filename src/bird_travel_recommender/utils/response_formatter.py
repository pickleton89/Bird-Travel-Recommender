"""
Enhanced Response Formatting for Bird Travel Recommender

This module provides intelligent response formatting that converts technical
MCP tool outputs into user-friendly, contextual, and engaging responses
tailored to different experience levels and birding interests.
"""

import logging
from typing import Dict, List, Any, Union
from dataclasses import dataclass
from enum import Enum

from .call_llm import call_llm

logger = logging.getLogger(__name__)


class ResponseType(Enum):
    """Types of responses we can generate"""
    TRIP_ITINERARY = "trip_itinerary"
    SPECIES_ADVICE = "species_advice"
    LOCATION_RECOMMENDATIONS = "location_recommendations"
    TIMING_GUIDANCE = "timing_guidance"
    EQUIPMENT_ADVICE = "equipment_advice"
    TECHNIQUE_TIPS = "technique_tips"
    QUICK_SIGHTINGS = "quick_sightings"
    ERROR_GUIDANCE = "error_guidance"
    GENERAL_HELP = "general_help"


class ExperienceLevel(Enum):
    """User experience levels for content adaptation"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class FormattingContext:
    """Context for response formatting"""
    user_request: str
    experience_level: ExperienceLevel
    special_interests: List[str]
    response_type: ResponseType
    intent_confidence: float
    extracted_species: List[str]
    extracted_locations: List[str]
    conversation_history: List[Dict] = None


class EnhancedResponseFormatter:
    """
    Enhanced Response Formatter for birding recommendations
    
    Transforms technical MCP tool outputs into engaging, user-friendly responses
    with appropriate language complexity and birding expertise.
    """
    
    def __init__(self):
        self.formatting_templates = self._load_formatting_templates()
        
    def format_response(self, tool_results: Union[Dict, List[Dict]], 
                       formatting_context: FormattingContext) -> Dict[str, Any]:
        """
        Main entry point for formatting tool results into user-friendly responses
        
        Args:
            tool_results: Raw results from MCP tools
            formatting_context: Context for formatting decisions
            
        Returns:
            Formatted response with markdown, summaries, and user guidance
        """
        try:
            # Determine the best formatting approach
            if isinstance(tool_results, list):
                # Multiple tool results
                formatted_response = self._format_multi_tool_results(tool_results, formatting_context)
            else:
                # Single tool result
                formatted_response = self._format_single_tool_result(tool_results, formatting_context)
            
            # Add metadata and enhancements
            enhanced_response = formatted_response
            enhanced_response["formatting_metadata"] = {
                "experience_level": formatting_context.experience_level.value,
                "response_type": formatting_context.response_type.value,
                "confidence": formatting_context.intent_confidence,
                "formatting_method": "enhanced_llm"
            }
            
            logger.info(f"Response formatted successfully: {formatting_context.response_type.value}")
            
            return enhanced_response
            
        except Exception as e:
            logger.error(f"Error formatting response: {str(e)}")
            return self._create_fallback_response(tool_results, formatting_context, str(e))
    
    def _format_single_tool_result(self, tool_result: Dict[str, Any], 
                                 context: FormattingContext) -> Dict[str, Any]:
        """Format a single tool result based on the tool type and content"""
        
        tool_name = tool_result.get("tool", "unknown")
        success = tool_result.get("success", False)
        result_data = tool_result.get("result", {})
        
        if not success:
            return self._format_error_response(tool_result, context)
        
        # Route to specific formatter based on tool type
        if tool_name == "plan_complete_trip":
            return self._format_complete_trip_response(result_data, context)
        elif tool_name == "get_birding_advice":
            return self._format_advice_response(result_data, context)
        elif tool_name == "validate_species":
            return self._format_species_validation_response(result_data, context)
        elif tool_name == "fetch_sightings":
            return self._format_sightings_response(result_data, context)
        elif tool_name == "cluster_hotspots":
            return self._format_hotspots_response(result_data, context)
        elif tool_name == "score_locations":
            return self._format_location_scores_response(result_data, context)
        elif tool_name == "optimize_route":
            return self._format_route_response(result_data, context)
        elif tool_name == "generate_itinerary":
            return self._format_itinerary_response(result_data, context)
        else:
            return self._format_generic_tool_response(tool_result, context)
    
    def _format_complete_trip_response(self, result_data: Dict[str, Any], 
                                     context: FormattingContext) -> Dict[str, Any]:
        """Format complete trip planning response with rich itinerary"""
        
        trip_plan = result_data.get("trip_plan", {})
        itinerary = trip_plan.get("itinerary", "")
        route = trip_plan.get("route", {})
        locations = trip_plan.get("locations", [])
        
        # Use LLM to enhance the itinerary with user-specific language
        enhanced_itinerary = self._enhance_itinerary_with_llm(itinerary, context)
        
        # Create structured response
        response = {
            "type": "complete_trip_plan",
            "title": self._generate_trip_title(context),
            "summary": self._generate_trip_summary(trip_plan, context),
            "itinerary": enhanced_itinerary,
            "quick_facts": self._extract_quick_facts(trip_plan, context),
            "locations": self._format_location_details(locations, context),
            "route_info": self._format_route_summary(route, context),
            "recommendations": self._generate_personalized_recommendations(trip_plan, context)
        }
        
        return response
    
    def _format_advice_response(self, result_data: Dict[str, Any], 
                              context: FormattingContext) -> Dict[str, Any]:
        """Format birding advice response with appropriate expertise level"""
        
        advice = result_data.get("advice", "")
        query = result_data.get("query", "")
        advice_type = result_data.get("advice_type", "general")
        
        # Enhance advice based on user experience level and interests
        enhanced_advice = self._adapt_advice_to_user_level(advice, context)
        
        response = {
            "type": "birding_advice",
            "title": self._generate_advice_title(query, context),
            "advice": enhanced_advice,
            "experience_level": context.experience_level.value,
            "related_tips": self._generate_related_tips(advice, context),
            "resources": self._generate_relevant_resources(advice_type, context),
            "next_steps": self._suggest_next_steps(advice, context)
        }
        
        return response
    
    def _format_sightings_response(self, result_data: Dict[str, Any], 
                                 context: FormattingContext) -> Dict[str, Any]:
        """Format sightings data into readable location and timing information"""
        
        sightings = result_data.get("sightings", [])
        statistics = result_data.get("statistics", {})
        
        # Group and summarize sightings
        location_summary = self._summarize_sightings_by_location(sightings)
        species_summary = self._summarize_sightings_by_species(sightings, context.extracted_species)
        timing_analysis = self._analyze_sighting_timing(sightings)
        
        response = {
            "type": "sightings_report",
            "title": self._generate_sightings_title(context),
            "summary": self._generate_sightings_summary(statistics, context),
            "by_location": location_summary,
            "by_species": species_summary,
            "timing_insights": timing_analysis,
            "best_opportunities": self._identify_best_sighting_opportunities(sightings, context),
            "data_notes": self._generate_data_interpretation_notes(statistics, context)
        }
        
        return response
    
    def _enhance_itinerary_with_llm(self, base_itinerary: str, context: FormattingContext) -> str:
        """Use LLM to enhance itinerary with user-appropriate language and details"""
        
        try:
            enhancement_prompt = f"""You are an expert birding guide customizing an itinerary for a {context.experience_level.value} birder. 

Base itinerary:
{base_itinerary}

User context:
- Experience level: {context.experience_level.value}
- Interests: {', '.join(context.special_interests) if context.special_interests else 'general birding'}
- Target species: {', '.join(context.extracted_species) if context.extracted_species else 'various'}
- Locations: {', '.join(context.extracted_locations) if context.extracted_locations else 'various'}

Please enhance this itinerary by:

1. **Language Adaptation**: Use appropriate terminology for {context.experience_level.value} level
   - Beginner: Simple terms, basic techniques, safety reminders
   - Intermediate: Standard birding terminology, moderate techniques
   - Advanced/Expert: Technical terms, advanced techniques, field research aspects

2. **Interest-Specific Content**: Add relevant details for {', '.join(context.special_interests) if context.special_interests else 'general birding'}
   - Photography: Camera settings, lighting, approach techniques
   - Migration: Timing patterns, weather factors, peak activity
   - Rare birds: Identification tips, behavior patterns, ethics

3. **Practical Enhancements**:
   - Specific timing recommendations with reasons
   - Equipment suggestions appropriate to experience level
   - Field technique tips for target species
   - Weather and seasonal considerations
   - Local birding etiquette and access notes

4. **Engagement Elements**:
   - What to expect at each location
   - Alternative plans if species aren't present
   - Learning opportunities during the trip
   - How to maximize the experience

Format as clean markdown with clear sections, bullet points, and practical advice. Keep the enthusiastic but professional tone of an experienced guide."""

            enhanced_content = call_llm(enhancement_prompt)
            return enhanced_content
            
        except Exception as e:
            logger.error(f"Error enhancing itinerary with LLM: {str(e)}")
            return base_itinerary  # Return original if enhancement fails
    
    def _adapt_advice_to_user_level(self, advice: str, context: FormattingContext) -> str:
        """Adapt advice language and complexity to user experience level"""
        
        try:
            adaptation_prompt = f"""You are an expert birding instructor adapting advice for different skill levels.

Original advice:
{advice}

Target audience: {context.experience_level.value} birder
User interests: {', '.join(context.special_interests) if context.special_interests else 'general birding'}
Request context: {context.user_request}

Please adapt this advice by:

**For {context.experience_level.value} level:**
- Beginner: Use simple language, explain basic terms, include safety tips, focus on common species
- Intermediate: Standard birding terminology, practical field techniques, species identification tips  
- Advanced: Technical details, advanced techniques, habitat analysis, research aspects
- Expert: Scientific terminology, cutting-edge techniques, conservation insights, data analysis

**Content adjustments:**
1. **Language complexity**: Match vocabulary to skill level
2. **Detail level**: Appropriate depth of information
3. **Practical focus**: Most relevant techniques for their level
4. **Learning progression**: Build on assumed knowledge base
5. **Interest alignment**: Emphasize {', '.join(context.special_interests) if context.special_interests else 'general aspects'}

**Format requirements:**
- Clear markdown formatting
- Actionable bullet points
- Logical organization
- Encouraging and supportive tone
- Include "why" explanations appropriate to level

Maintain accuracy while making the content engaging and accessible."""

            adapted_advice = call_llm(adaptation_prompt)
            return adapted_advice
            
        except Exception as e:
            logger.error(f"Error adapting advice: {str(e)}")
            return advice  # Return original if adaptation fails
    
    def _generate_trip_title(self, context: FormattingContext) -> str:
        """Generate an engaging title for the trip plan"""
        
        species_part = ""
        if context.extracted_species:
            if len(context.extracted_species) == 1:
                species_part = f"for {context.extracted_species[0]}"
            elif len(context.extracted_species) <= 3:
                species_part = f"for {', '.join(context.extracted_species[:-1])} and {context.extracted_species[-1]}"
            else:
                species_part = f"for {len(context.extracted_species)} Target Species"
        
        location_part = ""
        if context.extracted_locations:
            location_part = f"in {context.extracted_locations[0]}"
        
        return f"Birding Adventure {species_part} {location_part}".strip()
    
    def _generate_trip_summary(self, trip_plan: Dict[str, Any], context: FormattingContext) -> str:
        """Generate a compelling trip summary"""
        
        duration = trip_plan.get("trip_duration_days", 1)
        species_count = len(context.extracted_species) if context.extracted_species else "several"
        location_count = len(trip_plan.get("locations", []))
        
        duration_text = "day" if duration == 1 else f"{duration}-day"
        species_text = f"{species_count} species" if isinstance(species_count, int) else f"{species_count} target species"
        location_text = f"{location_count} location" + ("s" if location_count != 1 else "")
        
        return f"A {duration_text} birding adventure targeting {species_text} across {location_text}, optimized for your {context.experience_level.value} level experience."
    
    def _extract_quick_facts(self, trip_plan: Dict[str, Any], context: FormattingContext) -> List[str]:
        """Extract key facts for quick reference"""
        
        facts = []
        
        if trip_plan.get("trip_duration_days"):
            duration = trip_plan["trip_duration_days"]
            facts.append(f"📅 Duration: {duration} day{'s' if duration > 1 else ''}")
        
        if context.extracted_species:
            facts.append(f"🐦 Target Species: {len(context.extracted_species)}")
        
        locations = trip_plan.get("locations", [])
        if locations:
            facts.append(f"📍 Locations: {len(locations)} birding spots")
        
        route = trip_plan.get("route", {})
        if route.get("total_distance_km"):
            distance = route["total_distance_km"]
            facts.append(f"🚗 Total Distance: {distance:.1f} km")
        
        if context.experience_level:
            facts.append(f"🎯 Level: {context.experience_level.value.title()}")
        
        return facts
    
    def _format_location_details(self, locations: List[Dict], context: FormattingContext) -> List[Dict[str, Any]]:
        """Format location information with user-appropriate details"""
        
        formatted_locations = []
        
        for i, location in enumerate(locations[:8]):  # Limit to top 8 locations
            formatted_loc = {
                "rank": i + 1,
                "name": location.get("name", f"Location {i+1}"),
                "coordinates": location.get("coordinates", {}),
                "score": location.get("final_score", 0),
                "species_expected": location.get("species_diversity", 0),
                "recent_activity": location.get("observation_recency", 0),
                "accessibility": self._assess_location_accessibility(location, context),
                "best_time": self._suggest_best_visiting_time(location, context),
                "highlights": self._extract_location_highlights(location, context)
            }
            formatted_locations.append(formatted_loc)
        
        return formatted_locations
    
    def _summarize_sightings_by_location(self, sightings: List[Dict]) -> Dict[str, Any]:
        """Summarize sightings data by location for easy reading"""
        
        location_groups = {}
        
        for sighting in sightings:
            loc_name = sighting.get("locName", "Unknown Location")
            if loc_name not in location_groups:
                location_groups[loc_name] = {
                    "location": loc_name,
                    "coordinates": {"lat": sighting.get("lat"), "lng": sighting.get("lng")},
                    "species_count": 0,
                    "species_list": [],
                    "most_recent": None,
                    "total_observations": 0
                }
            
            location_groups[loc_name]["species_count"] += 1
            location_groups[loc_name]["species_list"].append(sighting.get("comName", "Unknown"))
            location_groups[loc_name]["total_observations"] += sighting.get("howMany", 1) if isinstance(sighting.get("howMany"), int) else 1
            
            # Track most recent observation
            obs_date = sighting.get("obsDt")
            if obs_date and (not location_groups[loc_name]["most_recent"] or obs_date > location_groups[loc_name]["most_recent"]):
                location_groups[loc_name]["most_recent"] = obs_date
        
        # Sort by species diversity
        sorted_locations = sorted(location_groups.values(), key=lambda x: x["species_count"], reverse=True)
        
        return {
            "total_locations": len(sorted_locations),
            "top_locations": sorted_locations[:10],  # Top 10 most diverse
            "summary": f"Found sightings across {len(sorted_locations)} locations"
        }
    
    def _generate_personalized_recommendations(self, trip_plan: Dict[str, Any], context: FormattingContext) -> List[str]:
        """Generate personalized recommendations based on user profile"""
        
        recommendations = []
        
        # Experience-based recommendations
        if context.experience_level == ExperienceLevel.BEGINNER:
            recommendations.extend([
                "📱 Download a bird identification app like Merlin Bird ID before your trip",
                "🎧 Bring headphones to listen to bird calls for identification practice",
                "📋 Consider joining a local birding group for your first few outings"
            ])
        elif context.experience_level == ExperienceLevel.EXPERT:
            recommendations.extend([
                "📊 Consider contributing your sightings to eBird for citizen science",
                "🔬 Document any unusual behavior or rare species observations",
                "📍 Share hotspot information with the local birding community"
            ])
        
        # Interest-based recommendations
        if "photography" in context.special_interests:
            recommendations.extend([
                "📷 Golden hour (first hour after sunrise) offers the best lighting",
                "🤫 Move slowly and let birds come to you for better photo opportunities",
                "📱 Consider a smartphone scope adapter for distant subjects"
            ])
        
        if "migration" in context.special_interests:
            recommendations.extend([
                "🌤️ Check weather patterns - following cold fronts often bring waves of migrants",
                "⏰ Peak migration activity usually occurs in early morning hours",
                "📊 Monitor eBird alerts for unusual species reports in your area"
            ])
        
        return recommendations
    
    def _create_fallback_response(self, tool_results: Union[Dict, List], 
                                context: FormattingContext, error: str) -> Dict[str, Any]:
        """Create a fallback response when formatting fails"""
        
        return {
            "type": "fallback_response",
            "title": "Birding Information",
            "message": "I've gathered some birding information for you, though the formatting encountered an issue.",
            "raw_data": tool_results,
            "user_guidance": [
                "The technical data above contains your birding information",
                "You can still use the coordinates and location names for your trip",
                "Consider rephrasing your request for a better formatted response"
            ],
            "error_note": f"Formatting error: {error}",
            "next_steps": [
                "Try asking for specific information (e.g., 'best locations' or 'timing advice')",
                "Check the raw data above for coordinates and species information",
                "Contact support if this error persists"
            ]
        }
    
    def _load_formatting_templates(self) -> Dict[str, str]:
        """Load formatting templates for different response types"""
        
        return {
            "trip_itinerary": """
# {title}

{summary}

## Quick Facts
{quick_facts}

## Detailed Itinerary
{itinerary}

## Locations
{locations}

## Route Information
{route_info}

## Recommendations
{recommendations}
            """,
            
            "advice_response": """
# {title}

{advice}

## Related Tips
{related_tips}

## Helpful Resources
{resources}

## Next Steps
{next_steps}
            """,
            
            "sightings_report": """
# {title}

{summary}

## Best Opportunities
{best_opportunities}

## By Location
{by_location}

## By Species
{by_species}

## Timing Insights
{timing_insights}

## Data Notes
{data_notes}
            """
        }
    
    # Additional helper methods for specific formatting tasks
    def _assess_location_accessibility(self, location: Dict, context: FormattingContext) -> str:
        """Assess and describe location accessibility"""
        # Implementation would analyze location data and user needs
        return "Good accessibility"  # Placeholder
    
    def _suggest_best_visiting_time(self, location: Dict, context: FormattingContext) -> str:
        """Suggest optimal visiting time for location"""
        # Implementation would consider species behavior, weather, etc.
        return "Early morning (6-9 AM)"  # Placeholder
    
    def _extract_location_highlights(self, location: Dict, context: FormattingContext) -> List[str]:
        """Extract key highlights for a location"""
        # Implementation would identify notable features
        return ["High species diversity", "Recent activity"]  # Placeholder
    
    def _format_route_summary(self, route: Dict, context: FormattingContext) -> Dict[str, Any]:
        """Format route summary information"""
        return {
            "total_distance": route.get("total_distance_km", 0),
            "estimated_time": "Half day",
            "difficulty": "Easy to moderate",
            "transportation": "Car recommended"
        }
    
    def _generate_advice_title(self, query: str, context: FormattingContext) -> str:
        """Generate title for advice response"""
        return f"Birding Advice: {query}"
    
    def _generate_related_tips(self, advice: str, context: FormattingContext) -> List[str]:
        """Generate related tips based on advice"""
        return [
            "Check weather conditions before heading out",
            "Bring appropriate field guides for your region",
            "Consider joining local birding groups"
        ]
    
    def _generate_relevant_resources(self, advice_type: str, context: FormattingContext) -> List[str]:
        """Generate relevant resources"""
        return [
            "eBird mobile app for real-time sightings",
            "Merlin Bird ID for species identification",
            "Local Audubon chapter websites"
        ]
    
    def _suggest_next_steps(self, advice: str, context: FormattingContext) -> List[str]:
        """Suggest next steps based on advice"""
        return [
            "Practice the techniques discussed",
            "Plan a field trip to apply what you've learned",
            "Share your experiences with the birding community"
        ]
    
    def _generate_sightings_title(self, context: FormattingContext) -> str:
        """Generate title for sightings response"""
        species_part = f" for {', '.join(context.extracted_species)}" if context.extracted_species else ""
        location_part = f" near {', '.join(context.extracted_locations)}" if context.extracted_locations else ""
        return f"Recent Bird Sightings{species_part}{location_part}"
    
    def _generate_sightings_summary(self, statistics: Dict, context: FormattingContext) -> str:
        """Generate summary for sightings data"""
        total = statistics.get("total_sightings", 0)
        locations = statistics.get("unique_locations", 0)
        return f"Found {total} recent sightings across {locations} locations"
    
    def _summarize_sightings_by_species(self, sightings: List[Dict], target_species: List[str]) -> Dict[str, Any]:
        """Summarize sightings by species"""
        species_groups = {}
        for sighting in sightings:
            species = sighting.get("comName", "Unknown")
            if species not in species_groups:
                species_groups[species] = {"count": 0, "locations": [], "recent_date": None}
            species_groups[species]["count"] += 1
            species_groups[species]["locations"].append(sighting.get("locName", "Unknown"))
        
        return {
            "species_summary": species_groups,
            "total_species": len(species_groups)
        }
    
    def _analyze_sighting_timing(self, sightings: List[Dict]) -> Dict[str, Any]:
        """Analyze timing patterns in sightings"""
        return {
            "peak_activity": "Early morning (6-9 AM)",
            "recent_activity": "High in last 7 days",
            "seasonal_notes": "Good timing for current season"
        }
    
    def _identify_best_sighting_opportunities(self, sightings: List[Dict], context: FormattingContext) -> List[str]:
        """Identify best sighting opportunities"""
        return [
            "Arnold Arboretum - Multiple species active",
            "Fresh Pond - Good for waterfowl",
            "Mount Auburn Cemetery - Migration hotspot"
        ]
    
    def _generate_data_interpretation_notes(self, statistics: Dict, context: FormattingContext) -> List[str]:
        """Generate notes about data interpretation"""
        return [
            "Recent sightings indicate current bird activity in the area",
            "Multiple sightings suggest reliable locations for target species",
            "Weather and time of day significantly affect bird activity"
        ]
    
    def _format_error_response(self, tool_result: Dict[str, Any], context: FormattingContext) -> Dict[str, Any]:
        """Format error response with helpful guidance"""
        error_msg = tool_result.get("error", "Unknown error")
        tool_name = tool_result.get("tool", "unknown")
        
        return {
            "type": "tool_error",
            "title": f"Issue with {tool_name.replace('_', ' ').title()}",
            "message": f"I encountered an issue while {tool_name.replace('_', ' ')}: {error_msg}",
            "user_guidance": [
                "Try rephrasing your request with different parameters",
                "Check spelling of species names and locations",
                "Consider using broader search criteria"
            ],
            "alternative_suggestions": [
                "Ask for general birding advice for your area",
                "Request information about common species",
                "Try a different approach to your birding question"
            ]
        }
    
    def _format_species_validation_response(self, result_data: Dict[str, Any], context: FormattingContext) -> Dict[str, Any]:
        """Format species validation response"""
        validated_species = result_data.get("validated_species", [])
        statistics = result_data.get("statistics", {})
        
        return {
            "type": "species_validation",
            "title": "Species Validation Results",
            "summary": f"Validated {len(validated_species)} species from your request",
            "validated_species": validated_species,
            "success_rate": statistics.get("success_rate", 0),
            "next_steps": [
                "Use these validated species for sightings lookup",
                "Plan trips to locations where these species are active",
                "Get specific timing advice for each species"
            ]
        }
    
    def _format_hotspots_response(self, result_data: Dict[str, Any], context: FormattingContext) -> Dict[str, Any]:
        """Format hotspots clustering response"""
        clusters = result_data.get("hotspot_clusters", [])
        statistics = result_data.get("statistics", {})
        
        return {
            "type": "hotspot_clusters",
            "title": "Birding Hotspot Recommendations",
            "summary": f"Found {len(clusters)} hotspot clusters in your area",
            "clusters": clusters[:10],  # Top 10 clusters
            "cluster_info": statistics,
            "usage_tips": [
                "Visit multiple locations within each cluster for best results",
                "Early morning typically offers the highest bird activity",
                "Check recent eBird reports before visiting"
            ]
        }
    
    def _format_location_scores_response(self, result_data: Dict[str, Any], context: FormattingContext) -> Dict[str, Any]:
        """Format location scoring response"""
        scored_locations = result_data.get("scored_locations", [])
        statistics = result_data.get("statistics", {})
        
        return {
            "type": "location_scores",
            "title": "Best Birding Locations Ranked",
            "summary": f"Analyzed and ranked {len(scored_locations)} locations for your target species",
            "top_locations": scored_locations[:8],
            "scoring_info": statistics,
            "interpretation": [
                "Higher scores indicate better probability of target species",
                "Recent activity and species diversity factor into scores",
                "Weather and timing can affect actual results"
            ]
        }
    
    def _format_route_response(self, result_data: Dict[str, Any], context: FormattingContext) -> Dict[str, Any]:
        """Format route optimization response"""
        route = result_data.get("optimized_route", {})
        statistics = result_data.get("statistics", {})
        
        return {
            "type": "optimized_route",
            "title": "Optimized Birding Route",
            "summary": f"Created efficient route visiting {len(route.get('locations', []))} locations",
            "route_details": route,
            "optimization_info": statistics,
            "travel_tips": [
                "Allow extra time for birding at each location",
                "Check traffic conditions before departing",
                "Have backup locations in case of poor conditions"
            ]
        }
    
    def _format_itinerary_response(self, result_data: Dict[str, Any], context: FormattingContext) -> Dict[str, Any]:
        """Format itinerary generation response"""
        itinerary = result_data.get("itinerary", "")
        statistics = result_data.get("statistics", {})
        
        return {
            "type": "detailed_itinerary",
            "title": "Your Birding Itinerary",
            "itinerary_content": itinerary,
            "generation_info": statistics,
            "preparation_checklist": [
                "Check weather forecast and dress appropriately",
                "Charge cameras and bring extra batteries",
                "Download offline maps for your locations",
                "Bring water and snacks for longer trips"
            ]
        }
    
    def _format_generic_tool_response(self, tool_result: Dict[str, Any], context: FormattingContext) -> Dict[str, Any]:
        """Format generic tool response when specific formatter not available"""
        tool_name = tool_result.get("tool", "unknown")
        result_data = tool_result.get("result", {})
        
        return {
            "type": "generic_tool_result",
            "title": f"{tool_name.replace('_', ' ').title()} Results",
            "message": f"Results from {tool_name} tool",
            "data": result_data,
            "user_guidance": [
                "Review the data above for relevant birding information",
                "Use coordinates and location names for planning",
                "Ask follow-up questions for specific aspects"
            ]
        }


# Convenience functions for easy integration
def format_tool_response(tool_results: Union[Dict, List[Dict]], user_request: str,
                        experience_level: str = "intermediate", 
                        special_interests: List[str] = None,
                        extracted_species: List[str] = None,
                        extracted_locations: List[str] = None) -> Dict[str, Any]:
    """
    Convenience function to format tool responses with minimal setup
    
    Args:
        tool_results: Raw MCP tool results
        user_request: Original user request
        experience_level: User's birding experience level
        special_interests: User's special interests (photography, migration, etc.)
        extracted_species: Species mentioned in request
        extracted_locations: Locations mentioned in request
    
    Returns:
        Formatted response dictionary
    """
    
    formatter = EnhancedResponseFormatter()
    
    # Determine response type from tool results
    if isinstance(tool_results, dict):
        tool_name = tool_results.get("tool", "unknown")
    elif isinstance(tool_results, list) and tool_results:
        tool_name = tool_results[0].get("tool", "unknown")
    else:
        tool_name = "unknown"
    
    # Map tool names to response types
    response_type_map = {
        "plan_complete_trip": ResponseType.TRIP_ITINERARY,
        "get_birding_advice": ResponseType.SPECIES_ADVICE,
        "fetch_sightings": ResponseType.QUICK_SIGHTINGS,
        "cluster_hotspots": ResponseType.LOCATION_RECOMMENDATIONS,
        "validate_species": ResponseType.SPECIES_ADVICE,
        "optimize_route": ResponseType.TRIP_ITINERARY,
        "generate_itinerary": ResponseType.TRIP_ITINERARY
    }
    
    response_type = response_type_map.get(tool_name, ResponseType.GENERAL_HELP)
    
    # Create formatting context
    context = FormattingContext(
        user_request=user_request,
        experience_level=ExperienceLevel(experience_level),
        special_interests=special_interests or [],
        response_type=response_type,
        intent_confidence=0.8,  # Default confidence
        extracted_species=extracted_species or [],
        extracted_locations=extracted_locations or []
    )
    
    return formatter.format_response(tool_results, context)