"""
Enhanced ProcessResultsNode with Advanced Response Formatting

This module provides an enhanced version of ProcessResultsNode that uses
the new response formatting system to create user-friendly, contextual responses.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from pocketflow import Node

# Import enhanced formatting components
from utils.response_formatter import (
    EnhancedResponseFormatter,
    FormattingContext,
    ResponseType,
    ExperienceLevel,
    format_tool_response
)
from utils.enhanced_nlp import IntentAnalysis, BirdingIntent

logger = logging.getLogger(__name__)


class EnhancedProcessResultsNode(Node):
    """
    Enhanced Node 3: Advanced Result Processing and Response Formatting
    
    Processes tool execution results and formats them into engaging,
    user-friendly responses with appropriate language complexity and
    birding expertise context.
    """
    
    def __init__(self):
        super().__init__()
        self.name = "EnhancedProcessResultsNode"
        self.response_formatter = EnhancedResponseFormatter()
    
    def prep(self, shared_store: Dict[str, Any]) -> None:
        """Prepare enhanced result processing"""
        results = shared_store.get("tool_execution_results", [])
        intent_analysis = shared_store.get("intent_analysis")
        
        logger.info(f"Preparing enhanced processing for {len(results)} tool results")
        if intent_analysis:
            logger.info(f"Intent: {intent_analysis.primary_intent.value}, Confidence: {intent_analysis.confidence_score:.2f}")
    
    def exec(self, shared_store: Dict[str, Any]) -> Dict[str, Any]:
        """Execute enhanced result processing with intelligent formatting"""
        try:
            # Extract data from shared store
            results = shared_store.get("tool_execution_results", [])
            execution_plan = shared_store.get("tool_execution_plan")
            intent_analysis = shared_store.get("intent_analysis")
            enhanced_parameters = shared_store.get("enhanced_parameters", {})
            metadata = shared_store.get("execution_metadata", {})
            
            # Create formatting context from available data
            formatting_context = self._create_formatting_context(
                shared_store, intent_analysis, enhanced_parameters
            )
            
            # Process results with enhanced formatting
            if not results:
                processed_response = self._handle_no_results(formatting_context)
            elif len(results) == 1:
                processed_response = self._process_single_result(results[0], formatting_context)
            else:
                processed_response = self._process_multiple_results(results, formatting_context, execution_plan)
            
            # Add enhanced metadata and user guidance
            enhanced_response = self._enhance_response_with_guidance(
                processed_response, formatting_context, metadata
            )
            
            # Store final response
            shared_store["final_response"] = enhanced_response
            shared_store["processing_metadata"] = {
                "results_processed": len(results),
                "response_type": enhanced_response.get("type", "unknown"),
                "formatting_method": "enhanced_llm_formatting",
                "user_experience_level": formatting_context.experience_level.value if formatting_context else "unknown",
                "success_rate": metadata.get("successful_executions", 0) / max(len(results), 1)
            }
            
            logger.info(f"Enhanced processing complete: {enhanced_response.get('type', 'unknown')} response")
            
            return {
                "success": True,
                "response": enhanced_response,
                "metadata": shared_store["processing_metadata"]
            }
            
        except Exception as e:
            logger.error(f"Error in enhanced result processing: {str(e)}")
            
            # Enhanced fallback response with user guidance
            fallback_response = self._create_enhanced_fallback_response(
                shared_store, str(e)
            )
            
            shared_store["final_response"] = fallback_response
            shared_store["processing_error"] = str(e)
            
            return {
                "success": True,  # Still provide response
                "response": fallback_response,
                "error": str(e)
            }
    
    def post(self, shared_store: Dict[str, Any]) -> None:
        """Post-process enhanced final response"""
        response = shared_store.get("final_response", {})
        metadata = shared_store.get("processing_metadata", {})
        
        logger.info(f"Enhanced response processing complete: {response.get('type', 'unknown')} "
                   f"for {metadata.get('user_experience_level', 'unknown')} user")
    
    def _create_formatting_context(self, shared_store: Dict[str, Any], 
                                 intent_analysis: Optional[IntentAnalysis],
                                 enhanced_parameters: Dict[str, Any]) -> FormattingContext:
        """Create comprehensive formatting context from available data"""
        
        # Extract user request
        user_request = shared_store.get("user_request", "")
        
        # Determine experience level
        experience_level = ExperienceLevel.INTERMEDIATE  # Default
        if enhanced_parameters.get("experience_level"):
            try:
                experience_level = ExperienceLevel(enhanced_parameters["experience_level"])
            except ValueError:
                pass
        
        # Extract special interests
        special_interests = enhanced_parameters.get("special_interests", [])
        
        # Determine response type from intent
        response_type = self._map_intent_to_response_type(intent_analysis)
        
        # Extract species and locations
        extracted_species = []
        extracted_locations = []
        
        if intent_analysis:
            extracted_species = intent_analysis.parameters.species
            extracted_locations = intent_analysis.parameters.locations
        
        # Get conversation history
        conversation_history = shared_store.get("conversation_history", [])
        
        return FormattingContext(
            user_request=user_request,
            experience_level=experience_level,
            special_interests=special_interests,
            response_type=response_type,
            intent_confidence=intent_analysis.confidence_score if intent_analysis else 0.5,
            extracted_species=extracted_species,
            extracted_locations=extracted_locations,
            conversation_history=conversation_history
        )
    
    def _map_intent_to_response_type(self, intent_analysis: Optional[IntentAnalysis]) -> ResponseType:
        """Map intent analysis to appropriate response type"""
        
        if not intent_analysis:
            return ResponseType.GENERAL_HELP
        
        intent_map = {
            BirdingIntent.COMPLETE_TRIP_PLANNING: ResponseType.TRIP_ITINERARY,
            BirdingIntent.SPECIES_ADVICE: ResponseType.SPECIES_ADVICE,
            BirdingIntent.LOCATION_DISCOVERY: ResponseType.LOCATION_RECOMMENDATIONS,
            BirdingIntent.TIMING_ADVICE: ResponseType.TIMING_GUIDANCE,
            BirdingIntent.EQUIPMENT_ADVICE: ResponseType.EQUIPMENT_ADVICE,
            BirdingIntent.TECHNIQUE_ADVICE: ResponseType.TECHNIQUE_TIPS,
            BirdingIntent.QUICK_LOOKUP: ResponseType.QUICK_SIGHTINGS,
            BirdingIntent.ROUTE_OPTIMIZATION: ResponseType.TRIP_ITINERARY,
            BirdingIntent.GENERAL_ADVICE: ResponseType.GENERAL_HELP
        }
        
        return intent_map.get(intent_analysis.primary_intent, ResponseType.GENERAL_HELP)
    
    def _process_single_result(self, result: Dict[str, Any], 
                             context: FormattingContext) -> Dict[str, Any]:
        """Process single tool result with enhanced formatting"""
        
        try:
            # Use the enhanced response formatter
            formatted_response = self.response_formatter.format_response(result, context)
            
            # Add success indicators and metadata
            formatted_response.update({
                "execution_success": result.get("success", False),
                "tool_used": result.get("tool", "unknown"),
                "confidence_level": context.intent_confidence,
                "user_experience_level": context.experience_level.value
            })
            
            return formatted_response
            
        except Exception as e:
            logger.error(f"Error in single result formatting: {str(e)}")
            return self._create_simple_formatted_response(result, context)
    
    def _process_multiple_results(self, results: List[Dict[str, Any]], 
                                context: FormattingContext,
                                execution_plan: Any) -> Dict[str, Any]:
        """Process multiple tool results with intelligent aggregation"""
        
        successful_results = [r for r in results if r.get("success", False)]
        failed_results = [r for r in results if not r.get("success", False)]
        
        if not successful_results:
            return self._handle_all_failed_results(results, context)
        
        # If we have multiple successful results, aggregate them intelligently
        if len(successful_results) > 1:
            return self._aggregate_multiple_successful_results(successful_results, context, execution_plan)
        else:
            # Single successful result with some failures
            return self._process_partial_success(successful_results[0], failed_results, context)
    
    def _aggregate_multiple_successful_results(self, results: List[Dict[str, Any]], 
                                             context: FormattingContext,
                                             execution_plan: Any) -> Dict[str, Any]:
        """Aggregate multiple successful results into cohesive response"""
        
        try:
            # Determine if this is a sequential pipeline or parallel execution
            strategy = execution_plan.strategy if execution_plan else "unknown"
            
            if strategy == "sequential":
                # Sequential results build on each other - use the final result
                final_result = results[-1]
                return self._process_single_result(final_result, context)
            else:
                # Parallel or mixed results - aggregate intelligently
                aggregated_data = self._aggregate_parallel_results(results)
                return self.response_formatter.format_response(aggregated_data, context)
                
        except Exception as e:
            logger.error(f"Error aggregating multiple results: {str(e)}")
            # Fallback to processing the best single result
            best_result = max(results, key=lambda r: len(str(r.get("result", ""))))
            return self._process_single_result(best_result, context)
    
    def _aggregate_parallel_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate parallel tool results into unified data structure"""
        
        aggregated = {
            "success": True,
            "tool": "multiple_tools",
            "result": {
                "aggregated_data": {},
                "individual_results": results,
                "summary": {
                    "total_tools": len(results),
                    "successful_tools": len([r for r in results if r.get("success", False)]),
                    "data_sources": [r.get("tool", "unknown") for r in results]
                }
            }
        }
        
        # Merge result data intelligently
        for result in results:
            tool_name = result.get("tool", "unknown")
            tool_data = result.get("result", {})
            aggregated["result"]["aggregated_data"][tool_name] = tool_data
        
        return aggregated
    
    def _enhance_response_with_guidance(self, base_response: Dict[str, Any], 
                                      context: FormattingContext,
                                      metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance response with user guidance and next steps"""
        
        # Add user-appropriate guidance
        guidance = self._generate_user_guidance(base_response, context, metadata)
        
        # Add follow-up suggestions
        follow_ups = self._generate_follow_up_suggestions(base_response, context)
        
        # Add technical metadata for advanced users
        tech_info = self._generate_technical_info(metadata, context)
        
        enhanced_response = base_response.copy()
        enhanced_response.update({
            "user_guidance": guidance,
            "follow_up_suggestions": follow_ups,
            "response_metadata": {
                "intent_confidence": context.intent_confidence,
                "experience_level": context.experience_level.value,
                "response_type": context.response_type.value,
                "formatting_method": "enhanced_llm",
                "execution_stats": metadata
            }
        })
        
        # Add technical info for advanced users
        if context.experience_level in [ExperienceLevel.ADVANCED, ExperienceLevel.EXPERT]:
            enhanced_response["technical_details"] = tech_info
        
        return enhanced_response
    
    def _generate_user_guidance(self, response: Dict[str, Any], 
                              context: FormattingContext,
                              metadata: Dict[str, Any]) -> List[str]:
        """Generate appropriate user guidance based on response and user level"""
        
        guidance = []
        
        # Experience-level specific guidance
        if context.experience_level == ExperienceLevel.BEGINNER:
            guidance.extend([
                "📱 Consider downloading the Merlin Bird ID app for field identification help",
                "🎧 Listen to bird calls before your trip to familiarize yourself with target species",
                "👥 Consider joining local birding groups for guided experience"
            ])
        elif context.experience_level == ExperienceLevel.EXPERT:
            guidance.extend([
                "📊 Remember to contribute your observations to eBird for citizen science",
                "🔍 Document any unusual behaviors or rare species encounters",
                "📍 Consider sharing exceptional hotspot discoveries with the birding community"
            ])
        
        # Response-type specific guidance
        if context.response_type == ResponseType.TRIP_ITINERARY:
            guidance.extend([
                "🌤️ Check weather conditions before departing - they significantly affect bird activity",
                "⏰ Plan to arrive at locations 30 minutes before sunrise for peak activity",
                "🔋 Ensure your devices are charged and bring backup power for long trips"
            ])
        elif context.response_type == ResponseType.QUICK_SIGHTINGS:
            guidance.extend([
                "📍 Recent sightings don't guarantee current presence - birds are mobile!",
                "🕐 Timing matters - early morning is typically most productive",
                "📱 Check eBird alerts for real-time updates from other birders"
            ])
        
        # Success rate specific guidance
        success_rate = metadata.get("successful_executions", 0) / max(metadata.get("tools_executed", 1), 1)
        if success_rate < 0.8:
            guidance.append("⚠️ Some data sources had limited information - consider expanding your search area or timeframe")
        
        return guidance
    
    def _generate_follow_up_suggestions(self, response: Dict[str, Any], 
                                      context: FormattingContext) -> List[str]:
        """Generate relevant follow-up suggestions"""
        
        suggestions = []
        
        # Intent-based follow-ups
        if context.response_type == ResponseType.TRIP_ITINERARY:
            suggestions.extend([
                "Ask about specific equipment recommendations for your trip",
                "Get timing advice for individual species you're targeting",
                "Request alternative locations if weather affects your planned route"
            ])
        elif context.response_type == ResponseType.SPECIES_ADVICE:
            suggestions.extend([
                "Plan a trip to see these species in their optimal habitat",
                "Ask about identification tips for similar-looking species",
                "Get seasonal timing recommendations for better sighting chances"
            ])
        elif context.response_type == ResponseType.QUICK_SIGHTINGS:
            suggestions.extend([
                "Plan a complete birding itinerary for these locations",
                "Ask about the best times to visit for each species",
                "Get equipment recommendations for photographing these birds"
            ])
        
        # Experience-level based follow-ups
        if context.experience_level == ExperienceLevel.BEGINNER:
            suggestions.append("Ask for basic field techniques and identification tips")
        elif context.experience_level == ExperienceLevel.EXPERT:
            suggestions.append("Request detailed habitat analysis and conservation status information")
        
        return suggestions
    
    def _generate_technical_info(self, metadata: Dict[str, Any], 
                               context: FormattingContext) -> Dict[str, Any]:
        """Generate technical information for advanced users"""
        
        return {
            "execution_summary": {
                "tools_executed": metadata.get("tools_executed", 0),
                "success_rate": metadata.get("successful_executions", 0) / max(metadata.get("tools_executed", 1), 1),
                "strategy_used": metadata.get("strategy_used", "unknown"),
                "processing_method": "enhanced_llm_formatting"
            },
            "data_sources": {
                "ebird_api": "Recent observations and hotspot data",
                "llm_enhancement": "GPT-4o for intent analysis and response formatting",
                "routing_algorithm": "TSP-based optimization for location ordering"
            },
            "confidence_metrics": {
                "intent_confidence": context.intent_confidence,
                "parameter_extraction_score": len(context.extracted_species) + len(context.extracted_locations),
                "response_completeness": "high" if metadata.get("successful_executions", 0) > 0 else "low"
            }
        }
    
    def _handle_no_results(self, context: FormattingContext) -> Dict[str, Any]:
        """Handle case where no results were generated"""
        
        return {
            "type": "no_results",
            "title": "No Birding Information Available",
            "message": self._generate_no_results_message(context),
            "user_guidance": [
                "Try expanding your search area or time range",
                "Check if your target species are currently in season for your region",
                "Consider asking for alternative species that are more commonly observed"
            ],
            "follow_up_suggestions": [
                "Ask for general birding advice for your area",
                "Request information about common species in your region",
                "Get seasonal birding recommendations for your location"
            ]
        }
    
    def _generate_no_results_message(self, context: FormattingContext) -> str:
        """Generate appropriate message when no results available"""
        
        if context.extracted_species and context.extracted_locations:
            return f"I couldn't find recent information about {', '.join(context.extracted_species)} in {', '.join(context.extracted_locations)}. This might be due to seasonal timing, limited recent observations, or the species being uncommon in that area."
        elif context.extracted_species:
            return f"I couldn't find recent observations for {', '.join(context.extracted_species)}. These species might be out of season or uncommon in the search area."
        elif context.extracted_locations:
            return f"I couldn't retrieve birding information for {', '.join(context.extracted_locations)}. Try expanding your search area or checking for alternative location names."
        else:
            return "I wasn't able to generate birding information based on your request. Please provide more specific details about the species or locations you're interested in."
    
    def _create_enhanced_fallback_response(self, shared_store: Dict[str, Any], 
                                         error: str) -> Dict[str, Any]:
        """Create enhanced fallback response with helpful guidance"""
        
        user_request = shared_store.get("user_request", "")
        
        return {
            "type": "enhanced_fallback",
            "title": "Birding Information Response",
            "message": "I encountered an issue while processing your birding request, but I'm here to help you get the information you need.",
            "user_guidance": [
                "🔄 Try rephrasing your request with more specific details",
                "📍 Include specific locations (city, state, or coordinates) for better results",
                "🐦 Mention specific bird species you're interested in seeing",
                "📅 Add timing information (season, dates, or time of day)"
            ],
            "alternative_approaches": [
                "Ask for general birding advice for your area",
                "Request recent sightings for common species",
                "Get equipment or technique recommendations",
                "Ask about seasonal birding opportunities"
            ],
            "example_requests": [
                "\"Recent cardinal sightings near Boston\"",
                "\"Plan a birding trip for warblers in Massachusetts\"", 
                "\"What equipment do I need for hawk watching?\"",
                "\"Best time to see migrants during spring?\""
            ],
            "technical_note": f"Error details: {error}" if error else None,
            "user_request": user_request
        }
    
    def _create_simple_formatted_response(self, result: Dict[str, Any], 
                                        context: FormattingContext) -> Dict[str, Any]:
        """Create simple formatted response when advanced formatting fails"""
        
        tool_name = result.get("tool", "unknown")
        success = result.get("success", False)
        result_data = result.get("result", {})
        
        if success:
            return {
                "type": "simple_tool_result",
                "title": f"{tool_name.replace('_', ' ').title()} Results",
                "message": f"Here are the results from the {tool_name} tool.",
                "data": result_data,
                "user_guidance": [
                    "The data above contains the requested birding information",
                    "Look for coordinates, species names, and location details",
                    "Consider asking follow-up questions for specific aspects"
                ]
            }
        else:
            return {
                "type": "tool_error",
                "title": f"{tool_name.replace('_', ' ').title()} Error",
                "message": f"The {tool_name} tool encountered an issue.",
                "error": result.get("error", "Unknown error"),
                "user_guidance": [
                    "Try rephrasing your request with different parameters",
                    "Check if your target species or locations are spelled correctly",
                    "Consider using broader search criteria"
                ]
            }


# Convenience function for creating enhanced process results node
def create_enhanced_process_results_node() -> EnhancedProcessResultsNode:
    """Create an enhanced process results node with advanced formatting"""
    return EnhancedProcessResultsNode()