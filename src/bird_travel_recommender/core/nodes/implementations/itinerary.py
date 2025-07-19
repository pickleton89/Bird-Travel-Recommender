"""
UnifiedGenerateItineraryNode - Generate detailed markdown itinerary with expert birding guidance.

This module provides the unified implementation for creating comprehensive birding
itineraries using LLM enhancement with fallback template-based generation.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

from ..base import BaseNode, NodeInput, NodeOutput
from ..factory import register_node
from ..mixins import ValidationMixin, LoggingMixin, ErrorHandlingMixin

logger = logging.getLogger(__name__)


class ItineraryInput(NodeInput):
    """Input validation for itinerary generation node."""
    max_retries: int = Field(default=3, ge=1, le=10)
    enable_llm_generation: bool = Field(default=True)
    template_fallback: bool = Field(default=True)
    include_metadata: bool = Field(default=True)


class ItineraryOutput(NodeOutput):
    """Output model for itinerary generation node."""
    itinerary_method: str = "none"
    llm_attempts: int = 0
    fallback_used: bool = False
    total_locations: int = 0
    total_species: int = 0
    content_sections_generated: int = 0


@register_node("generate_itinerary")
class UnifiedGenerateItineraryNode(BaseNode, ValidationMixin, LoggingMixin, ErrorHandlingMixin):
    """
    Unified implementation for generating detailed markdown itinerary with expert birding guidance 
    using LLM enhancement.

    Features:
    - Professional birding guide prompting for detailed itineraries
    - Species-specific advice on timing, habitat, and field techniques
    - Route segment integration with travel times and directions
    - Fallback template-based generation if LLM fails
    - Comprehensive birding trip planning with equipment and etiquette advice
    - Unified sync/async execution through dependency injection
    """

    def __init__(self, dependencies, max_retries: int = 3):
        super().__init__(dependencies)
        self.max_retries = max_retries
        
        # Initialize mixins
        ValidationMixin.__init__(self)
        LoggingMixin.__init__(self)
        ErrorHandlingMixin.__init__(self)

    def validate_input(self, data: Dict[str, Any]) -> ItineraryInput:
        """Validate itinerary generation input."""
        constraints = data.get("constraints", {})
        
        return ItineraryInput(
            max_retries=constraints.get("max_retries", self.max_retries),
            enable_llm_generation=constraints.get("enable_llm_generation", True),
            template_fallback=constraints.get("template_fallback", True),
            include_metadata=constraints.get("include_metadata", True)
        )

    async def process(self, shared_store: Dict[str, Any]) -> ItineraryOutput:
        """
        Core itinerary generation processing logic.

        Args:
            shared_store: Shared data store containing all pipeline data

        Returns:
            ItineraryOutput with generated itinerary and statistics
        """
        try:
            # Get validated input
            input_data = self.validate_input(shared_store.get("input", {}))
            
            # Extract all pipeline data needed for itinerary generation
            optimized_route = shared_store.get("optimized_route", [])
            route_segments = shared_store.get("route_segments", [])
            validated_species = shared_store.get("validated_species", [])
            constraints = shared_store.get("input", {}).get("constraints", {})

            self.log_info(
                f"Generating itinerary for {len(optimized_route)} locations and "
                f"{len(validated_species)} target species"
            )

            # Initialize generation statistics
            generation_stats = {
                "itinerary_method": "none",
                "llm_attempts": 0,
                "fallback_used": False,
                "total_locations": len(optimized_route),
                "total_species": len(validated_species),
                "estimated_trip_duration_hours": sum(
                    seg.get("estimated_drive_time_hours", 0) for seg in route_segments
                ),
                "content_sections_generated": 0,
            }

            if not optimized_route:
                self.log_warning("No optimized route available for itinerary generation")
                empty_itinerary = self._generate_empty_itinerary_message()
                return ItineraryOutput(
                    success=True,
                    data={
                        "itinerary_markdown": empty_itinerary,
                        "generation_stats": generation_stats
                    },
                    itinerary_method="empty",
                    llm_attempts=0,
                    fallback_used=False,
                    total_locations=0,
                    total_species=0,
                    content_sections_generated=1
                )

            # Prepare comprehensive data for itinerary
            prep_data = {
                "optimized_route": optimized_route,
                "route_segments": route_segments,
                "validated_species": validated_species,
                "constraints": constraints,
                "pipeline_stats": self._gather_pipeline_stats(shared_store),
            }

            # Attempt LLM-enhanced itinerary generation
            if input_data.enable_llm_generation:
                llm_itinerary = await self._generate_llm_itinerary(prep_data, input_data, generation_stats)
                
                if llm_itinerary:
                    generation_stats["itinerary_method"] = "llm_enhanced"
                    self.log_info("Successfully generated LLM-enhanced itinerary")
                    
                    return ItineraryOutput(
                        success=True,
                        data={
                            "itinerary_markdown": llm_itinerary,
                            "generation_stats": generation_stats
                        },
                        itinerary_method="llm_enhanced",
                        llm_attempts=generation_stats["llm_attempts"],
                        fallback_used=False,
                        total_locations=len(optimized_route),
                        total_species=len(validated_species),
                        content_sections_generated=generation_stats["content_sections_generated"]
                    )

            # Fallback to template-based generation
            if input_data.template_fallback:
                self.log_warning("LLM itinerary generation failed, using template fallback")
                template_itinerary = self._generate_template_itinerary(prep_data, generation_stats)
                generation_stats["itinerary_method"] = "template_fallback"
                generation_stats["fallback_used"] = True

                return ItineraryOutput(
                    success=True,
                    data={
                        "itinerary_markdown": template_itinerary,
                        "generation_stats": generation_stats
                    },
                    itinerary_method="template_fallback",
                    llm_attempts=generation_stats["llm_attempts"],
                    fallback_used=True,
                    total_locations=len(optimized_route),
                    total_species=len(validated_species),
                    content_sections_generated=generation_stats["content_sections_generated"]
                )
            else:
                return ItineraryOutput(
                    success=False,
                    error="LLM generation failed and template fallback disabled"
                )

        except Exception as e:
            error_msg = f"Itinerary generation failed: {str(e)}"
            self.log_error(error_msg)
            return ItineraryOutput(
                success=False,
                error=error_msg
            )

    def _gather_pipeline_stats(self, shared_store: Dict[str, Any]) -> Dict[str, Any]:
        """Gather statistics from all pipeline stages."""
        return {
            "validation_stats": shared_store.get("validation_stats", {}),
            "fetch_stats": shared_store.get("fetch_stats", {}),
            "filtering_stats": shared_store.get("filtering_stats", {}),
            "clustering_stats": shared_store.get("clustering_stats", {}),
            "scoring_stats": shared_store.get("location_scoring_stats", {}),
            "route_stats": shared_store.get("route_optimization_stats", {}),
        }

    async def _generate_llm_itinerary(
        self, prep_data: Dict[str, Any], input_data: ItineraryInput, stats: Dict
    ) -> Optional[str]:
        """Generate professional birding itinerary using LLM."""
        for attempt in range(input_data.max_retries):
            stats["llm_attempts"] = attempt + 1

            try:
                itinerary_prompt = self._create_itinerary_prompt(prep_data)

                # Use LLM through dependency injection if available
                if hasattr(self.deps, 'llm_client'):
                    llm_response = await self.deps.llm_client.call(itinerary_prompt)
                else:
                    # Fallback to legacy call_llm
                    from ....utils.call_llm import call_llm
                    llm_response = call_llm(itinerary_prompt)

                # Validate and enhance the response
                if self._validate_itinerary_response(llm_response):
                    enhanced_itinerary = self._enhance_itinerary_with_metadata(
                        llm_response, prep_data
                    )
                    stats["content_sections_generated"] = len(enhanced_itinerary.split("##"))
                    return enhanced_itinerary
                else:
                    self.log_warning(f"LLM itinerary validation failed on attempt {attempt + 1}")

            except Exception as e:
                self.log_error(f"LLM itinerary generation attempt {attempt + 1} failed: {e}")

        return None

    def _create_itinerary_prompt(self, prep_data: Dict[str, Any]) -> str:
        """Create comprehensive LLM prompt for itinerary generation."""
        optimized_route = prep_data["optimized_route"]
        route_segments = prep_data["route_segments"]
        validated_species = prep_data["validated_species"]
        constraints = prep_data["constraints"]
        pipeline_stats = prep_data["pipeline_stats"]

        # Prepare trip overview
        trip_overview = self._format_trip_overview(constraints, pipeline_stats)

        # Prepare target species information
        species_info = self._format_species_for_itinerary(validated_species)

        # Prepare location details
        location_details = self._format_locations_for_itinerary(optimized_route, route_segments)

        itinerary_prompt = f"""
You are a professional birding guide with extensive field experience creating detailed trip itineraries.

TRIP OVERVIEW:
{trip_overview}

TARGET SPECIES:
{species_info}

OPTIMIZED ROUTE:
{location_details}

Create a comprehensive birding itinerary with expert guidance. Include:

1. **Executive Summary**: Brief overview of the trip highlights and expectations
2. **Species Target List**: Priority species with specific timing and habitat advice
3. **Detailed Location Guide**: For each location, provide:
   - Optimal arrival time and duration
   - Habitat characteristics and target species
   - Specific observation tips and techniques
   - Weather and seasonal considerations
   - Equipment recommendations
4. **Travel Schedule**: Driving directions and timing between locations
5. **Field Tips**: Professional advice on field techniques, birding ethics, and photography
6. **Contingency Plans**: Alternative locations or activities if target species aren't found

Format as clean markdown with proper headers. Focus on actionable field guidance that maximizes observation success. Include specific coordinates where helpful.

Make this sound like a professional birding guide's detailed trip plan, not a generic travel itinerary.
"""

        return itinerary_prompt

    def _format_trip_overview(self, constraints: Dict, stats: Dict) -> str:
        """Format trip overview section for LLM prompt."""
        total_distance = stats.get("route_stats", {}).get("total_route_distance_km", 0)
        estimated_time = stats.get("route_stats", {}).get("estimated_total_drive_time_hours", 0)
        locations_count = stats.get("route_stats", {}).get("locations_optimized", 0)

        start_location = constraints.get("start_location", {})
        start_coords = f"({start_location.get('lat', 'unknown')}, {start_location.get('lng', 'unknown')})"

        overview = f"""
- Starting Point: {start_coords}
- Total Locations: {locations_count}
- Total Distance: {total_distance:.1f} km
- Estimated Driving Time: {estimated_time:.1f} hours
- Region: {constraints.get("region", "Not specified")}
- Date Range: {constraints.get("date_range", {}).get("start", "Flexible")} to {constraints.get("date_range", {}).get("end", "Flexible")}
- Max Daily Distance: {constraints.get("max_daily_distance_km", "Not specified")} km
"""

        return overview.strip()

    def _format_species_for_itinerary(self, validated_species: List[Dict]) -> str:
        """Format target species information for LLM prompt."""
        if not validated_species:
            return "No specific target species identified."

        species_sections = []
        for species in validated_species[:10]:  # Limit to prevent prompt overflow
            section = f"""
**{species["common_name"]}** (*{species["scientific_name"]}*)
- eBird Code: {species["species_code"]}
- Validation: {species["validation_method"]} (confidence: {species["confidence"]:.1f})
- Seasonal Notes: {species.get("seasonal_notes", "No specific timing noted")}
- Behavioral Notes: {species.get("behavioral_notes", "Standard observation approaches")}
"""
            species_sections.append(section.strip())

        if len(validated_species) > 10:
            species_sections.append(f"... and {len(validated_species) - 10} additional species")

        return "\n\n".join(species_sections)

    def _format_locations_for_itinerary(self, route: List[Dict], segments: List[Dict]) -> str:
        """Format location and route information for LLM prompt."""
        if not route:
            return "No locations in optimized route."

        location_sections = []
        for i, location in enumerate(route):
            # Find corresponding route segment
            segment = next(
                (seg for seg in segments if seg.get("segment_number") == i + 1), {}
            )

            section = f"""
**Stop {i + 1}: {location["cluster_name"]}**
- Coordinates: ({location["center_lat"]:.4f}, {location["center_lng"]:.4f})
- Score: {location.get("final_score", 0):.2f}
- Species Diversity: {location["statistics"]["species_diversity"]} species
- Recent Sightings: {location["statistics"]["sighting_count"]} observations
- Hotspot Status: {"Official eBird Hotspot" if location["accessibility"]["has_hotspot"] else "Sighting Location"}
- Distance from Previous: {segment.get("distance_km", 0):.1f} km
- Estimated Drive Time: {segment.get("estimated_drive_time_hours", 0):.1f} hours
- Target Species Found: {", ".join(location["statistics"]["species_codes"][:5])}
"""

            # Add LLM evaluation if available
            if location.get("llm_evaluation"):
                eval_info = location["llm_evaluation"]
                section += f"""
- Habitat Score: {eval_info.get("habitat_score", 0):.2f}
- Expert Assessment: {eval_info.get("reasoning", "No assessment")}
- Best Timing: {eval_info.get("best_time", "Variable")}
- Field Tips: {eval_info.get("tips", "Standard birding approaches")}
"""

            location_sections.append(section.strip())

        return "\n\n".join(location_sections)

    def _validate_itinerary_response(self, response: str) -> bool:
        """Validate that the LLM response is a reasonable itinerary."""
        if not response or len(response) < 500:
            return False

        # Check for essential sections
        required_elements = [
            "##",  # Markdown headers
            "species",  # Should mention species
            "location",  # Should mention locations
            "time",  # Should mention timing
        ]

        response_lower = response.lower()
        return all(element in response_lower for element in required_elements)

    def _enhance_itinerary_with_metadata(
        self, itinerary: str, prep_data: Dict[str, Any]
    ) -> str:
        """Enhance LLM-generated itinerary with additional metadata."""
        pipeline_stats = prep_data["pipeline_stats"]

        # Add header with generation metadata
        header = f"""# Birding Trip Itinerary
*Generated by Bird Travel Recommender*

---

## Trip Statistics
- **Locations Analyzed**: {pipeline_stats.get("clustering_stats", {}).get("total_input_sightings", 0)} sightings across {pipeline_stats.get("clustering_stats", {}).get("unique_locations_found", 0)} locations
- **Species Validated**: {pipeline_stats.get("validation_stats", {}).get("total_input", 0)} requested, {pipeline_stats.get("validation_stats", {}).get("direct_taxonomy_matches", 0) + pipeline_stats.get("validation_stats", {}).get("llm_fuzzy_matches", 0)} confirmed
- **Route Optimization**: {pipeline_stats.get("route_stats", {}).get("optimization_method", "Unknown")} method
- **Total Trip Distance**: {pipeline_stats.get("route_stats", {}).get("total_route_distance_km", 0):.1f} km

---

"""

        # Add footer with disclaimers
        footer = f"""

---

## Important Notes

### Data Sources
- Bird observations from eBird API (recent {pipeline_stats.get("fetch_stats", {}).get("total_observations", 0)} observations)
- Hotspot data from official eBird hotspot registry
- Route optimization using traveling salesman algorithms

### Disclaimers
- Observation times and locations are based on recent eBird data and may not guarantee current bird presence
- Weather conditions, seasonal timing, and local factors can significantly impact birding success
- Always respect private property, follow local regulations, and practice ethical birding
- Consider checking recent eBird reports before visiting each location

### Equipment Recommendations
- Binoculars (8x42 or 10x42 recommended)
- Field guide for local region
- eBird mobile app for real-time reporting
- Camera with telephoto lens (optional)
- Weather-appropriate clothing and comfortable walking shoes

*Happy Birding!*

*Generated on {self._get_current_timestamp()}*
"""

        return header + itinerary + footer

    def _generate_template_itinerary(self, prep_data: Dict[str, Any], stats: Dict) -> str:
        """Generate basic template-based itinerary as fallback."""
        optimized_route = prep_data["optimized_route"]
        route_segments = prep_data["route_segments"]
        validated_species = prep_data["validated_species"]
        constraints = prep_data["constraints"]

        stats["content_sections_generated"] = 5  # Fixed sections in template

        itinerary = f"""# Birding Trip Itinerary
*Template-based itinerary (LLM generation unavailable)*

## Trip Overview
- **Starting Point**: {constraints.get("start_location", {}).get("lat", "Not specified")}, {constraints.get("start_location", {}).get("lng", "Not specified")}
- **Total Locations**: {len(optimized_route)}
- **Target Species**: {len(validated_species)}
- **Estimated Distance**: {sum(seg.get("distance_km", 0) for seg in route_segments):.1f} km
- **Estimated Travel Time**: {sum(seg.get("estimated_drive_time_hours", 0) for seg in route_segments):.1f} hours

## Target Species List
"""

        for species in validated_species:
            itinerary += f"- **{species['common_name']}** (*{species['scientific_name']}*) - {species.get('seasonal_notes', 'No timing notes')}\n"

        itinerary += "\n## Location Schedule\n"

        for i, location in enumerate(optimized_route):
            segment = next(
                (seg for seg in route_segments if seg.get("segment_number") == i + 1), {}
            )

            itinerary += f"""
### Stop {i + 1}: {location["cluster_name"]}
- **Coordinates**: {location["center_lat"]:.4f}, {location["center_lng"]:.4f}
- **Species Diversity**: {location["statistics"]["species_diversity"]} species observed
- **Recent Sightings**: {location["statistics"]["sighting_count"]} observations
- **Score**: {location.get("final_score", 0):.2f}
- **Distance from previous**: {segment.get("distance_km", 0):.1f} km ({segment.get("estimated_drive_time_hours", 0):.1f} hours)
- **Hotspot Status**: {"Official eBird Hotspot" if location["accessibility"]["has_hotspot"] else "Regular birding location"}

**Species found here**: {", ".join(location["statistics"]["species_codes"][:8])}

"""

        itinerary += """
## General Birding Tips
- Check eBird for recent sightings before visiting each location
- Early morning (dawn to 10 AM) is typically the most productive time for birding
- Bring appropriate weather gear and comfortable walking shoes
- Respect private property and follow local birding ethics
- Consider joining local birding groups for area-specific knowledge

## Equipment Checklist
- [ ] Binoculars (8x42 or 10x42 recommended)
- [ ] Field guide for the region
- [ ] eBird mobile app
- [ ] Camera (optional)
- [ ] Notebook and pen
- [ ] Snacks and water
- [ ] Weather-appropriate clothing

*This itinerary was generated using automated route optimization and eBird data analysis.*
"""

        return itinerary

    def _generate_empty_itinerary_message(self) -> str:
        """Generate message when no route is available."""
        return """# Birding Trip Itinerary

## No Route Available

Unfortunately, no birding locations could be optimized for your trip parameters. This could be due to:

- No recent bird sightings in the specified region
- All locations filtered out by travel constraints
- API data unavailable

## Suggestions
1. Try expanding your search radius
2. Consider relaxing travel distance constraints
3. Check eBird directly for recent activity in your target region
4. Verify your target species are present in the specified region and season

*Generated by Bird Travel Recommender*
"""

    def _get_current_timestamp(self) -> str:
        """Get current timestamp for itinerary generation."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")