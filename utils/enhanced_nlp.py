"""
Enhanced Natural Language Processing for Bird Travel Recommender

This module provides LLM-powered intent classification and parameter extraction
for improved understanding of user birding requests.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from utils.call_llm import call_llm

logger = logging.getLogger(__name__)


class BirdingIntent(Enum):
    """Enumeration of user intent types for birding requests"""
    COMPLETE_TRIP_PLANNING = "complete_trip_planning"
    SPECIES_ADVICE = "species_advice"
    LOCATION_DISCOVERY = "location_discovery"
    TIMING_ADVICE = "timing_advice"
    EQUIPMENT_ADVICE = "equipment_advice"
    TECHNIQUE_ADVICE = "technique_advice"
    QUICK_LOOKUP = "quick_lookup"
    ROUTE_OPTIMIZATION = "route_optimization"
    GENERAL_ADVICE = "general_advice"


@dataclass
class ExtractedParameters:
    """Container for extracted birding parameters"""
    species: List[str]
    locations: List[str]
    region_codes: List[str]
    coordinates: List[Dict[str, float]]
    timeframes: List[str]
    duration_days: Optional[int]
    max_distance_km: Optional[int]
    experience_level: Optional[str]
    special_interests: List[str]  # photography, migration, rare birds, etc.
    season: Optional[str]
    confidence_score: float


@dataclass
class IntentAnalysis:
    """Container for intent analysis results"""
    primary_intent: BirdingIntent
    secondary_intents: List[BirdingIntent]
    parameters: ExtractedParameters
    strategy_recommendation: str
    confidence_score: float
    reasoning: str


class EnhancedNLPProcessor:
    """
    Enhanced Natural Language Processor for birding requests
    
    Uses LLM to understand user intent and extract relevant parameters
    with semantic understanding of birding terminology and context.
    """
    
    def __init__(self):
        self.conversation_history = []
        
    def analyze_birding_request(self, user_request: str, context: Dict[str, Any] = None) -> IntentAnalysis:
        """
        Analyze user request using LLM to understand intent and extract parameters
        
        Args:
            user_request: Raw user input
            context: Previous conversation context
            
        Returns:
            Comprehensive intent analysis with extracted parameters
        """
        try:
            # Build context-aware prompt
            analysis_prompt = self._build_analysis_prompt(user_request, context)
            
            # Get LLM analysis
            llm_response = call_llm(analysis_prompt)
            
            # Parse LLM response into structured format
            intent_analysis = self._parse_llm_analysis(llm_response, user_request)
            
            # Update conversation history
            self._update_conversation_history(user_request, intent_analysis)
            
            logger.info(f"Intent analysis complete: {intent_analysis.primary_intent.value} with confidence {intent_analysis.confidence_score}")
            
            return intent_analysis
            
        except Exception as e:
            logger.error(f"Error in LLM intent analysis: {str(e)}, falling back to rule-based")
            return self._fallback_rule_based_analysis(user_request, context)
    
    def _build_analysis_prompt(self, user_request: str, context: Dict[str, Any] = None) -> str:
        """Build comprehensive analysis prompt for LLM"""
        
        # Get conversation context
        conversation_context = ""
        if self.conversation_history:
            recent_history = self.conversation_history[-3:]  # Last 3 interactions
            conversation_context = f"\nRecent conversation:\n{self._format_conversation_history(recent_history)}"
        
        # Get external context
        external_context = ""
        if context:
            external_context = f"\nProvided context: {json.dumps(context, indent=2)}"
        
        return f"""You are an expert birding guide and trip planner with deep knowledge of bird behavior, habitats, and observation techniques. Analyze the following user request to understand their intent and extract relevant parameters.

User Request: "{user_request}"{conversation_context}{external_context}

Please provide a comprehensive analysis in the following JSON format:

{{
    "primary_intent": "one of: complete_trip_planning, species_advice, location_discovery, timing_advice, equipment_advice, technique_advice, quick_lookup, route_optimization, general_advice",
    "secondary_intents": ["list of other relevant intents"],
    "extracted_parameters": {{
        "species": ["list of bird species mentioned (use full common names like 'Northern Cardinal')"],
        "locations": ["list of locations, landmarks, or geographic references"],
        "region_codes": ["eBird region codes if determinable (e.g., 'US-MA', 'CA-ON')"],
        "coordinates": [{{ "lat": 42.3601, "lng": -71.0589, "description": "Boston area" }}],
        "timeframes": ["temporal references like 'next weekend', 'spring migration', 'early morning'"],
        "duration_days": 1,
        "max_distance_km": 100,
        "experience_level": "beginner/intermediate/advanced/expert",
        "special_interests": ["photography", "migration", "rare birds", "life list", "habitat", "behavior"],
        "season": "spring/summer/fall/winter"
    }},
    "strategy_recommendation": "monolithic/sequential/parallel - based on complexity and user needs",
    "confidence_score": 0.85,
    "reasoning": "Detailed explanation of why you classified this intent and extracted these parameters"
}}

Key considerations:
1. **Bird Species Recognition**: Understand colloquial names (cardinal = Northern Cardinal), scientific names, and family references
2. **Location Intelligence**: Parse GPS coordinates, city names, landmarks, habitats, and regional birding areas
3. **Temporal Understanding**: Interpret relative dates, seasons, migration periods, and optimal birding times
4. **Birding Context**: Understand equipment needs, skill levels, birding techniques, and special interests
5. **Intent Nuance**: Distinguish between planning trips vs seeking advice vs quick information lookups

Examples of intent classification:
- "Plan a birding trip to see warblers" → complete_trip_planning
- "What equipment do I need for hawk watching?" → equipment_advice  
- "When is the best time to see cardinals?" → timing_advice
- "Recent cardinal sightings near Boston" → quick_lookup
- "How do I identify different warbler songs?" → technique_advice

Be thorough in parameter extraction and provide high confidence scores only when information is clearly stated."""

    def _parse_llm_analysis(self, llm_response: str, original_request: str) -> IntentAnalysis:
        """Parse LLM response into structured IntentAnalysis object"""
        try:
            # Try to extract JSON from response
            json_start = llm_response.find('{')
            json_end = llm_response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = llm_response[json_start:json_end]
                analysis_data = json.loads(json_str)
            else:
                raise ValueError("No valid JSON found in LLM response")
            
            # Parse primary intent
            primary_intent = BirdingIntent(analysis_data.get("primary_intent", "general_advice"))
            
            # Parse secondary intents
            secondary_intents = []
            for intent_str in analysis_data.get("secondary_intents", []):
                try:
                    secondary_intents.append(BirdingIntent(intent_str))
                except ValueError:
                    logger.warning(f"Unknown secondary intent: {intent_str}")
            
            # Parse extracted parameters
            params_data = analysis_data.get("extracted_parameters", {})
            parameters = ExtractedParameters(
                species=params_data.get("species", []),
                locations=params_data.get("locations", []),
                region_codes=params_data.get("region_codes", []),
                coordinates=params_data.get("coordinates", []),
                timeframes=params_data.get("timeframes", []),
                duration_days=params_data.get("duration_days"),
                max_distance_km=params_data.get("max_distance_km"),
                experience_level=params_data.get("experience_level"),
                special_interests=params_data.get("special_interests", []),
                season=params_data.get("season"),
                confidence_score=analysis_data.get("confidence_score", 0.5)
            )
            
            return IntentAnalysis(
                primary_intent=primary_intent,
                secondary_intents=secondary_intents,
                parameters=parameters,
                strategy_recommendation=analysis_data.get("strategy_recommendation", "monolithic"),
                confidence_score=analysis_data.get("confidence_score", 0.5),
                reasoning=analysis_data.get("reasoning", "LLM analysis completed")
            )
            
        except Exception as e:
            logger.error(f"Error parsing LLM analysis: {str(e)}")
            return self._fallback_rule_based_analysis(original_request, {})
    
    def _fallback_rule_based_analysis(self, user_request: str, context: Dict[str, Any] = None) -> IntentAnalysis:
        """Fallback to rule-based analysis if LLM fails"""
        logger.info("Using fallback rule-based analysis")
        
        request_lower = user_request.lower()
        
        # Simple intent classification
        if any(phrase in request_lower for phrase in ["plan", "trip", "itinerary", "route"]):
            primary_intent = BirdingIntent.COMPLETE_TRIP_PLANNING
            strategy = "monolithic"
        elif any(phrase in request_lower for phrase in ["advice", "help", "how", "recommend"]):
            primary_intent = BirdingIntent.GENERAL_ADVICE
            strategy = "monolithic"
        elif any(phrase in request_lower for phrase in ["when", "time", "season", "timing"]):
            primary_intent = BirdingIntent.TIMING_ADVICE
            strategy = "monolithic"
        elif any(phrase in request_lower for phrase in ["where", "location", "spot", "place"]):
            primary_intent = BirdingIntent.LOCATION_DISCOVERY
            strategy = "monolithic"
        else:
            primary_intent = BirdingIntent.QUICK_LOOKUP
            strategy = "monolithic"
        
        # Basic parameter extraction
        species = self._extract_species_fallback(user_request)
        locations = self._extract_locations_fallback(user_request)
        
        parameters = ExtractedParameters(
            species=species,
            locations=locations,
            region_codes=[],
            coordinates=[],
            timeframes=[],
            duration_days=None,
            max_distance_km=None,
            experience_level=None,
            special_interests=[],
            season=None,
            confidence_score=0.3  # Lower confidence for fallback
        )
        
        return IntentAnalysis(
            primary_intent=primary_intent,
            secondary_intents=[],
            parameters=parameters,
            strategy_recommendation=strategy,
            confidence_score=0.3,
            reasoning="Fallback rule-based analysis due to LLM failure"
        )
    
    def _extract_species_fallback(self, user_request: str) -> List[str]:
        """Fallback species extraction using common patterns"""
        common_birds = [
            "Northern Cardinal", "Blue Jay", "American Robin", "House Sparrow",
            "European Starling", "Red-winged Blackbird", "Common Grackle",
            "Mourning Dove", "American Goldfinch", "House Finch", "Song Sparrow",
            "White-breasted Nuthatch", "Downy Woodpecker"
        ]
        
        found_species = []
        request_lower = user_request.lower()
        
        # Check for common names
        for bird in common_birds:
            if bird.lower() in request_lower:
                found_species.append(bird)
        
        # Check for family/group names
        if "warbler" in request_lower:
            found_species.extend(["Yellow Warbler", "Black-throated Blue Warbler"])
        if "hawk" in request_lower:
            found_species.extend(["Red-tailed Hawk", "Sharp-shinned Hawk"])
        if "cardinal" in request_lower and "Northern Cardinal" not in found_species:
            found_species.append("Northern Cardinal")
        
        return list(set(found_species)) if found_species else ["Northern Cardinal"]
    
    def _extract_locations_fallback(self, user_request: str) -> List[str]:
        """Fallback location extraction using common patterns"""
        locations = []
        request_lower = user_request.lower()
        
        # Common location patterns
        location_patterns = {
            "boston": "Boston, MA",
            "massachusetts": "Massachusetts",
            "new york": "New York",
            "california": "California",
            "texas": "Texas",
            "florida": "Florida"
        }
        
        for pattern, location in location_patterns.items():
            if pattern in request_lower:
                locations.append(location)
        
        return locations
    
    def _update_conversation_history(self, user_request: str, intent_analysis: IntentAnalysis):
        """Update conversation history for context awareness"""
        self.conversation_history.append({
            "request": user_request,
            "intent": intent_analysis.primary_intent.value,
            "parameters": intent_analysis.parameters,
            "timestamp": "now"  # Would use actual timestamp in production
        })
        
        # Keep only last 5 interactions
        if len(self.conversation_history) > 5:
            self.conversation_history = self.conversation_history[-5:]
    
    def _format_conversation_history(self, history: List[Dict]) -> str:
        """Format conversation history for prompt context"""
        formatted = []
        for interaction in history:
            formatted.append(f"User: {interaction['request']}")
            formatted.append(f"Intent: {interaction['intent']}")
            if interaction['parameters'].species:
                formatted.append(f"Species: {', '.join(interaction['parameters'].species)}")
        return "\n".join(formatted)
    
    def get_enhanced_parameters_for_tool(self, intent_analysis: IntentAnalysis, 
                                       context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Convert extracted parameters into tool-ready format
        
        Args:
            intent_analysis: Results from analyze_birding_request
            context: Additional context to merge
            
        Returns:
            Dictionary ready for tool execution
        """
        params = intent_analysis.parameters
        tool_params = {}
        
        # Species parameters
        if params.species:
            tool_params["species_names"] = params.species
            tool_params["target_species"] = params.species
        
        # Location parameters
        if params.coordinates:
            tool_params["start_location"] = params.coordinates[0]
        elif params.locations and context and context.get("default_coordinates"):
            tool_params["start_location"] = context["default_coordinates"]
        else:
            # Default to Boston area
            tool_params["start_location"] = {"lat": 42.3601, "lng": -71.0589}
        
        # Region parameters
        if params.region_codes:
            tool_params["region"] = params.region_codes[0]
        elif params.locations:
            # Try to infer region from location names
            location = params.locations[0].lower()
            if "massachusetts" in location or "boston" in location:
                tool_params["region"] = "US-MA"
            elif "california" in location:
                tool_params["region"] = "US-CA"
            elif "texas" in location:
                tool_params["region"] = "US-TX"
            else:
                tool_params["region"] = "US-MA"  # Default
        else:
            tool_params["region"] = "US-MA"  # Default
        
        # Trip parameters
        if params.duration_days:
            tool_params["trip_duration_days"] = params.duration_days
        else:
            tool_params["trip_duration_days"] = 1  # Default
        
        if params.max_distance_km:
            tool_params["max_distance_km"] = params.max_distance_km
        else:
            tool_params["max_distance_km"] = 100  # Default
        
        # Additional context
        tool_params["experience_level"] = params.experience_level or "intermediate"
        tool_params["special_interests"] = params.special_interests
        tool_params["season"] = params.season
        tool_params["timeframes"] = params.timeframes
        
        # Merge with provided context
        if context:
            tool_params.update(context)
        
        return tool_params