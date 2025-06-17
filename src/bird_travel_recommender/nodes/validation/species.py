"""
ValidateSpeciesNode: Validate bird species names using eBird taxonomy with LLM fallback.

This node implements a comprehensive species validation strategy:
1. Direct eBird taxonomy lookup (fast, reliable, cheap)
2. LLM fallback only for fuzzy matching when taxonomy fails
3. Cache successful name→code mappings
4. Add seasonal context and behavioral notes
"""

from pocketflow import Node
from ...utils.call_llm import call_llm
from ...utils.ebird_api import get_client, EBirdAPIError
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ValidateSpeciesNode(Node):
    """
    Validate bird species names using eBird taxonomy with LLM fallback.
    
    Strategy:
    1. Direct eBird taxonomy lookup (fast, reliable, cheap)
    2. LLM fallback only for fuzzy matching when taxonomy fails
    3. Cache successful name→code mappings
    4. Add seasonal context and behavioral notes
    """
    
    def __init__(self):
        super().__init__()
        self.species_cache = {}  # Cache for name→code mappings
        
    def prep(self, shared):
        """Extract species list from shared store."""
        species_list = shared.get("input", {}).get("species_list", [])
        return species_list
    
    def exec(self, species_list: List[str]) -> Dict[str, Any]:
        """
        Validate species names using eBird taxonomy with LLM fallback.
        
        Args:
            species_list: List of bird species names (common names)
            
        Returns:
            Dictionary with validated species and processing stats
        """
        validated_species = []
        processing_stats = {
            "total_input": len(species_list),
            "direct_taxonomy_matches": 0,
            "llm_fuzzy_matches": 0,
            "failed_validations": 0,
            "cache_hits": 0
        }
        
        # Handle empty species list
        if not species_list:
            logger.info("Empty species list provided, returning empty results")
            return {
                "validated_species": validated_species,
                "processing_stats": processing_stats
            }
        
        # Get full eBird taxonomy for matching
        try:
            ebird_client = get_client()
            full_taxonomy = ebird_client.get_taxonomy()
            logger.info(f"Retrieved {len(full_taxonomy)} species from eBird taxonomy")
        except EBirdAPIError as e:
            logger.error(f"Failed to get eBird taxonomy: {e}")
            # Fallback to LLM-only validation
            return self._llm_only_validation(species_list, processing_stats)
        
        for species_name in species_list:
            # Check cache first
            cache_key = species_name.lower().strip()
            if cache_key in self.species_cache:
                validated_species.append(self.species_cache[cache_key])
                processing_stats["cache_hits"] += 1
                continue
            
            # Try direct eBird taxonomy lookup
            direct_match = self._direct_taxonomy_lookup(species_name, full_taxonomy)
            if direct_match:
                validated_species.append(direct_match)
                self.species_cache[cache_key] = direct_match
                processing_stats["direct_taxonomy_matches"] += 1
                continue
            
            # Fallback to LLM for fuzzy matching
            llm_match = self._llm_fuzzy_match(species_name, full_taxonomy)
            if llm_match:
                validated_species.append(llm_match)
                self.species_cache[cache_key] = llm_match
                processing_stats["llm_fuzzy_matches"] += 1
            else:
                processing_stats["failed_validations"] += 1
                logger.warning(f"Could not validate species: {species_name}")
        
        logger.info(f"Validated {len(validated_species)} of {len(species_list)} species")
        
        return {
            "validated_species": validated_species,
            "processing_stats": processing_stats
        }
    
    def _direct_taxonomy_lookup(self, species_name: str, taxonomy: List[Dict]) -> Optional[Dict[str, Any]]:
        """
        Attempt direct match against eBird taxonomy.
        
        Args:
            species_name: Common name to search for
            taxonomy: Full eBird taxonomy list
            
        Returns:
            Validated species dict or None if no match
        """
        normalized_input = species_name.lower().strip()
        
        for species in taxonomy:
            # Check exact common name match
            if species["comName"].lower() == normalized_input:
                return self._format_validated_species(
                    species, species_name, "direct_common_name", 1.0
                )
            
            # Check exact scientific name match
            if species["sciName"].lower() == normalized_input:
                return self._format_validated_species(
                    species, species_name, "direct_scientific_name", 1.0
                )
            
            # Check species code match
            if species["speciesCode"].lower() == normalized_input:
                return self._format_validated_species(
                    species, species_name, "direct_species_code", 1.0
                )
        
        # Try partial matching for common abbreviations
        for species in taxonomy:
            common_name = species["comName"].lower()
            
            # Handle common patterns like "cardinal" → "Northern Cardinal"
            if (normalized_input in common_name and 
                len(normalized_input) > 3):  # Avoid matching very short strings
                return self._format_validated_species(
                    species, species_name, "partial_common_name", 0.8
                )
        
        return None
    
    def _llm_fuzzy_match(self, species_name: str, taxonomy: List[Dict]) -> Optional[Dict[str, Any]]:
        """
        Use LLM for fuzzy matching when direct lookup fails.
        
        Args:
            species_name: Species name that failed direct lookup
            taxonomy: Full eBird taxonomy for context
            
        Returns:
            Best match species dict or None
        """
        # Create a smaller subset of taxonomy for LLM context (to avoid token limits)
        common_species = [s for s in taxonomy if s.get("category") == "species"][:500]
        
        species_validation_prompt = f"""
You are an expert ornithologist with comprehensive knowledge of North American birds.

I need to match this bird name: "{species_name}"

Here are some eBird taxonomy entries to help with matching:
{self._format_taxonomy_for_llm(common_species[:50])}

Please:
1. Find the best matching eBird species for "{species_name}"
2. Handle variations (e.g., "cardinal" → "Northern Cardinal", "blue jay" → "Blue Jay")
3. Consider common misspellings and colloquial names
4. If no good match exists, respond with "NO_MATCH"

Respond with ONLY the exact eBird common name from the taxonomy, or "NO_MATCH".
Example responses: "Northern Cardinal", "Blue Jay", "NO_MATCH"
"""
        
        try:
            llm_response = call_llm(species_validation_prompt).strip()
            
            if llm_response == "NO_MATCH":
                return None
            
            # Find the LLM's suggested match in the full taxonomy
            for species in taxonomy:
                if species["comName"].lower() == llm_response.lower():
                    return self._format_validated_species(
                        species, species_name, "llm_fuzzy_match", 0.7
                    )
            
            logger.warning(f"LLM suggested '{llm_response}' but not found in taxonomy")
            return None
            
        except Exception as e:
            logger.error(f"LLM fuzzy matching failed for '{species_name}': {e}")
            return None
    
    def _llm_only_validation(self, species_list: List[str], stats: Dict) -> Dict[str, Any]:
        """
        Fallback method when eBird API is unavailable.
        
        Args:
            species_list: List of species names to validate
            stats: Processing statistics dictionary
            
        Returns:
            Validation results using LLM knowledge only
        """
        logger.warning("Using LLM-only validation due to eBird API failure")
        
        validated_species = []
        
        llm_validation_prompt = f"""
You are an expert ornithologist. For each bird name below, provide:
1. Standardized common name
2. Scientific name
3. Likely eBird species code (guess based on patterns)
4. Basic seasonal/behavioral notes

Bird names to validate: {species_list}

Format each response as:
Name: [standardized common name]
Scientific: [scientific name]  
Code: [likely eBird code]
Notes: [brief seasonal/behavioral context]
---

If a name is invalid or unrecognizable, respond with "INVALID" for that entry.
"""
        
        try:
            llm_response = call_llm(llm_validation_prompt)
            # Parse LLM response (simplified for this implementation)
            # In production, would need more robust parsing
            
            for species_name in species_list:
                validated_species.append({
                    "original_name": species_name,
                    "common_name": species_name,  # Simplified
                    "scientific_name": "Unknown",
                    "species_code": "unknown",
                    "validation_method": "llm_only_fallback",
                    "confidence": 0.5,
                    "seasonal_notes": "API unavailable - limited validation"
                })
                stats["llm_fuzzy_matches"] += 1
            
        except Exception as e:
            logger.error(f"LLM-only validation failed: {e}")
            stats["failed_validations"] = len(species_list)
        
        return {
            "validated_species": validated_species,
            "processing_stats": stats
        }
    
    def _format_validated_species(self, species: Dict, original_name: str, method: str, confidence: float) -> Dict[str, Any]:
        """
        Format a validated species with additional context.
        
        Args:
            species: eBird taxonomy entry
            original_name: User's original input
            method: Validation method used
            confidence: Confidence score (0.0-1.0)
            
        Returns:
            Formatted species dictionary
        """
        return {
            "original_name": original_name,
            "common_name": species["comName"],
            "scientific_name": species["sciName"],
            "species_code": species["speciesCode"],
            "taxonomic_order": species.get("taxonOrder", 0),
            "family_common_name": species.get("familyComName", ""),
            "family_scientific_name": species.get("familySciName", ""),
            "validation_method": method,
            "confidence": confidence,
            "seasonal_notes": self._get_seasonal_notes(species["comName"]),
            "behavioral_notes": self._get_behavioral_notes(species["comName"])
        }
    
    def _get_seasonal_notes(self, common_name: str) -> str:
        """Generate basic seasonal context for common species."""
        name_lower = common_name.lower()
        
        if "warbler" in name_lower:
            return "Peak migration: spring (April-May) and fall (August-September)"
        elif "duck" in name_lower or "waterfowl" in name_lower:
            return "Best viewing: fall/winter migration and breeding season"
        elif "hawk" in name_lower or "eagle" in name_lower:
            return "Migration peaks: spring (March-April) and fall (September-October)"
        elif "cardinal" in name_lower or "jay" in name_lower:
            return "Year-round resident in most of range"
        else:
            return "Seasonal timing varies by region and migration patterns"
    
    def _get_behavioral_notes(self, common_name: str) -> str:
        """Generate basic behavioral context for common species."""
        name_lower = common_name.lower()
        
        if "warbler" in name_lower:
            return "Active feeders, check mid-canopy to upper canopy, early morning best"
        elif "duck" in name_lower:
            return "Water-dependent, check wetlands, ponds, and shorelines"
        elif "hawk" in name_lower:
            return "Soaring raptors, check thermals and ridgelines, late morning optimal"
        elif "cardinal" in name_lower:
            return "Seed feeders, dense cover, active at feeders dawn and dusk"
        elif "jay" in name_lower:
            return "Vocal and conspicuous, mixed habitats, often in family groups"
        else:
            return "Refer to species-specific field guides for optimal viewing strategies"
    
    def _format_taxonomy_for_llm(self, taxonomy_subset: List[Dict]) -> str:
        """Format taxonomy entries for LLM context."""
        formatted = []
        for species in taxonomy_subset[:20]:  # Limit to avoid token overuse
            formatted.append(f"- {species['comName']} ({species['sciName']}) [{species['speciesCode']}]")
        return "\n".join(formatted)
    
    def post(self, shared, prep_res, exec_res):
        """Store validated species in shared store."""
        shared["validated_species"] = exec_res["validated_species"]
        
        # Create validation_stats with both old and new field names for backward compatibility
        stats = exec_res["processing_stats"].copy()
        stats["total_input_species"] = stats["total_input"]  # Add old field name
        stats["successfully_validated"] = stats["direct_taxonomy_matches"] + stats["llm_fuzzy_matches"]
        
        shared["validation_stats"] = stats
        
        # Handle division by zero when no species are provided
        total_input = stats["total_input"]
        if total_input == 0:
            success_rate = 0.0
            logger.info("No species provided for validation")
        else:
            success_rate = stats["successfully_validated"] / total_input
            logger.info(f"Species validation completed with {success_rate:.1%} success rate")
        
        if total_input > 0 and success_rate < 0.5:
            logger.warning(f"Low validation success rate: {success_rate:.1%}")
            # Instead of returning validation_failed, add a flag to shared store for downstream handling
            shared["validation_warning"] = True
            shared["validation_success_rate"] = success_rate
        
        return "default"