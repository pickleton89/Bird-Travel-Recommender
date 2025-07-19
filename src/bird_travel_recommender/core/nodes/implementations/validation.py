"""
Unified Species Validation Node.

This node provides species validation functionality in a unified architecture,
supporting both sync and async execution modes.
"""

from typing import Dict, Any, List, Optional
import time
from pydantic import BaseModel, Field

from ..base import BaseNode, NodeInput, NodeOutput
from ..factory import register_node
from ..mixins import LoggingMixin, ValidationMixin, CachingMixin, MetricsMixin, ErrorHandlingMixin
from ...ebird.client import EBirdClient
from ...exceptions.ebird import EBirdAPIError


class SpeciesValidationInput(NodeInput):
    """Input validation for species validation node."""
    
    species_names: List[str] = Field(..., description="List of species names to validate")
    region_code: Optional[str] = Field("US", description="Region code for validation context")
    fuzzy_matching: bool = Field(True, description="Enable fuzzy matching for species names")
    confidence_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Minimum confidence for matches")


class SpeciesValidationOutput(NodeOutput):
    """Output model for species validation node."""
    
    total_species: Optional[int] = Field(None, description="Total number of species processed")
    validated_count: Optional[int] = Field(None, description="Number of successfully validated species")
    validation_rate: Optional[float] = Field(None, description="Percentage of species validated")
    unrecognized_species: Optional[List[str]] = Field(None, description="List of unrecognized species names")


@register_node("species_validation", aliases=["validate_species", "species_validate"])
class UnifiedSpeciesValidationNode(
    BaseNode,
    LoggingMixin,
    ValidationMixin,
    CachingMixin,
    MetricsMixin,
    ErrorHandlingMixin
):
    """
    Unified species validation node for bird species taxonomic lookup.
    
    This node validates bird species names against the eBird taxonomy with:
    - Exact and fuzzy matching capabilities
    - Confidence scoring for matches
    - Regional species list filtering
    - Caching for performance
    - Comprehensive error handling
    """
    
    def __init__(self, dependencies):
        """
        Initialize the species validation node.
        
        Args:
            dependencies: Injected dependencies
        """
        super().__init__(dependencies)
        self._taxonomy_cache = None
        self._cache_timestamp = None
        self._cache_ttl = 3600  # 1 hour
    
    def validate_input(self, data: Dict[str, Any]) -> SpeciesValidationInput:
        """Validate species validation input."""
        
        # Extract species information from various input formats
        species_names = []
        
        # Handle different input formats
        if "species" in data:
            # Single species string
            if isinstance(data["species"], str):
                species_names = [data["species"]]
            # List of species strings
            elif isinstance(data["species"], list):
                species_names = data["species"]
            # List of species objects with names
            elif isinstance(data["species"], list) and data["species"]:
                if isinstance(data["species"][0], dict):
                    species_names = [s.get("name", s.get("common_name", str(s))) for s in data["species"]]
                else:
                    species_names = [str(s) for s in data["species"]]
        
        # Handle input structure with constraints
        constraints = data.get("input", {}).get("constraints", {})
        if not species_names and "species" in constraints:
            species_names = [constraints["species"]] if isinstance(constraints["species"], str) else constraints["species"]
        
        # Validation
        if not species_names:
            raise ValueError("No species names provided for validation")
        
        self.validate_required_fields({"species_names": species_names}, ["species_names"])
        
        return SpeciesValidationInput(
            species_names=species_names,
            region_code=constraints.get("region", "US"),
            fuzzy_matching=True,
            confidence_threshold=0.7
        )
    
    async def process(self, shared_store: Dict[str, Any]) -> SpeciesValidationOutput:
        """
        Core species validation processing logic.
        
        Args:
            shared_store: Shared data store containing species information
            
        Returns:
            SpeciesValidationOutput with validation results
        """
        self.log_execution_start("species_validation")
        start_time = time.time()
        
        try:
            # Get validated input
            input_data = self.validate_input(shared_store)
            
            self.increment_counter("species_validation_requests_total", 
                                 {"species_count": str(len(input_data.species_names))})
            
            # Check for cached taxonomy data
            taxonomy = await self._get_taxonomy_data(input_data.region_code)
            
            # Validate each species
            with self.time_operation("species_validation_processing"):
                validated_species = []
                unrecognized_species = []
                
                for species_name in input_data.species_names:
                    validation_result = await self._validate_single_species(
                        species_name, taxonomy, input_data
                    )
                    
                    if validation_result["success"]:
                        validated_species.append(validation_result["species"])
                    else:
                        unrecognized_species.append(species_name)
            
            # Calculate statistics
            validation_rate = len(validated_species) / len(input_data.species_names) if input_data.species_names else 0
            
            # Create output
            output = SpeciesValidationOutput(
                success=True,
                data={
                    "validated_species": validated_species,
                    "unrecognized_species": unrecognized_species
                },
                total_species=len(input_data.species_names),
                validated_count=len(validated_species),
                validation_rate=validation_rate,
                unrecognized_species=unrecognized_species,
                execution_time_ms=(time.time() - start_time) * 1000
            )
            
            # Record metrics
            self.record_gauge("species_validation_rate", validation_rate)
            self.record_gauge("species_validated_total", len(validated_species))
            self.increment_counter("species_validation_completed_total")
            
            self.log_execution_end("species_validation", True, output.execution_time_ms,
                                 validated_count=len(validated_species),
                                 total_species=len(input_data.species_names))
            
            return output
            
        except Exception as e:
            error_response = self.handle_api_error(e, "species_validation")
            
            execution_time = (time.time() - start_time) * 1000
            self.log_execution_end("species_validation", False, execution_time)
            
            return SpeciesValidationOutput(
                success=False,
                error=str(e),
                execution_time_ms=execution_time,
                metadata={"error_type": type(e).__name__}
            )
    
    async def _get_taxonomy_data(self, region_code: str) -> List[Dict[str, Any]]:
        """
        Get eBird taxonomy data with caching.
        
        Args:
            region_code: Region code for regional species lists
            
        Returns:
            List of taxonomy entries
        """
        cache_key = f"taxonomy_{region_code}"
        
        # Check memory cache first
        current_time = time.time()
        if (self._taxonomy_cache and 
            self._cache_timestamp and 
            (current_time - self._cache_timestamp) < self._cache_ttl):
            return self._taxonomy_cache
        
        # Check external cache
        cached_taxonomy = await self.get_cached_result("taxonomy", region_code=region_code)
        if cached_taxonomy:
            self._taxonomy_cache = cached_taxonomy
            self._cache_timestamp = current_time
            return cached_taxonomy
        
        # Fetch fresh taxonomy data
        try:
            client = self.deps.ebird_client
            taxonomy = await client.get_taxonomy()
            
            # Convert to dict format for easier processing
            taxonomy_dict = [
                {
                    "species_code": entry.species_code,
                    "common_name": entry.common_name,
                    "scientific_name": entry.scientific_name,
                    "category": getattr(entry, "category", "species"),
                    "order": getattr(entry, "order", ""),
                    "family": getattr(entry, "family", "")
                }
                for entry in taxonomy
                if hasattr(entry, 'species_code') and hasattr(entry, 'common_name')
            ]
            
            # Cache the results
            await self.set_cached_result("taxonomy", taxonomy_dict, ttl=3600, region_code=region_code)
            
            # Update memory cache
            self._taxonomy_cache = taxonomy_dict
            self._cache_timestamp = current_time
            
            return taxonomy_dict
            
        except EBirdAPIError as e:
            self.logger.error(f"Failed to fetch taxonomy data: {e}")
            raise
    
    async def _validate_single_species(self, species_name: str, taxonomy: List[Dict[str, Any]], 
                                     input_data: SpeciesValidationInput) -> Dict[str, Any]:
        """
        Validate a single species against the taxonomy.
        
        Args:
            species_name: Name of the species to validate
            taxonomy: eBird taxonomy data
            input_data: Validation parameters
            
        Returns:
            Validation result dictionary
        """
        species_name_lower = species_name.lower().strip()
        
        # Try exact match first
        exact_matches = [
            entry for entry in taxonomy 
            if entry["common_name"].lower() == species_name_lower
        ]
        
        if exact_matches:
            return {
                "success": True,
                "species": {
                    "original_name": species_name,
                    "common_name": exact_matches[0]["common_name"],
                    "scientific_name": exact_matches[0]["scientific_name"],
                    "species_code": exact_matches[0]["species_code"],
                    "confidence": 1.0,
                    "validation_method": "exact_match",
                    "category": exact_matches[0].get("category", "species"),
                    "order": exact_matches[0].get("order", ""),
                    "family": exact_matches[0].get("family", "")
                }
            }
        
        # Try fuzzy matching if enabled
        if input_data.fuzzy_matching:
            fuzzy_matches = []
            
            for entry in taxonomy:
                # Simple fuzzy matching - check if species name is contained in common name
                if species_name_lower in entry["common_name"].lower():
                    # Calculate a simple confidence score
                    confidence = len(species_name_lower) / len(entry["common_name"])
                    if confidence >= input_data.confidence_threshold:
                        fuzzy_matches.append({
                            **entry,
                            "confidence": confidence
                        })
            
            # Sort by confidence and take the best match
            if fuzzy_matches:
                best_match = max(fuzzy_matches, key=lambda x: x["confidence"])
                return {
                    "success": True,
                    "species": {
                        "original_name": species_name,
                        "common_name": best_match["common_name"],
                        "scientific_name": best_match["scientific_name"],
                        "species_code": best_match["species_code"],
                        "confidence": best_match["confidence"],
                        "validation_method": "fuzzy_match",
                        "category": best_match.get("category", "species"),
                        "order": best_match.get("order", ""),
                        "family": best_match.get("family", "")
                    }
                }
        
        # No matches found
        self.increment_counter("species_validation_failures_total", {"reason": "no_match"})
        return {
            "success": False,
            "error": f"No match found for species: {species_name}",
            "original_name": species_name
        }