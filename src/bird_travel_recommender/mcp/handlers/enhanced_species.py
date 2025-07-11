#!/usr/bin/env python3
"""
Enhanced Species Handler with Comprehensive Error Handling

Demonstrates the improved error handling framework applied to species tools.
This serves as a template for enhancing all other handler categories.
"""

import asyncio
import logging
from typing import Any, Dict, List

# Import dependencies
from ...utils.ebird_api import EBirdClient, EBirdAPIError
from ...nodes import ValidateSpeciesNode

# Import enhanced error handling framework
from ..utils.error_handling import (
    handle_errors_gracefully,
    validate_parameters,
    with_timeout,
    with_retry,
    with_circuit_breaker,
    APIError,
    ValidationError,
    get_validation_schema,
)

# Configure logging
logger = logging.getLogger(__name__)


class EnhancedSpeciesHandlers:
    """Enhanced species handlers with comprehensive error handling"""

    def __init__(self):
        self.ebird_api = EBirdClient()
        self.validate_species_node = ValidateSpeciesNode()

    @handle_errors_gracefully(fallback_value=[])
    @validate_parameters(get_validation_schema("validate_species"))
    @with_timeout(60)  # 1 minute timeout for validation
    async def handle_validate_species(
        self, species_names: List[str], **kwargs
    ) -> Dict[str, Any]:
        """Enhanced validate_species handler with comprehensive error handling"""
        logger.info(
            f"Validating {len(species_names)} species with enhanced error handling"
        )

        # Additional input validation
        if not species_names:
            raise ValidationError(
                "Species list cannot be empty", "species_names", species_names
            )

        # Filter out obviously invalid inputs
        valid_species_names = []
        for name in species_names:
            if not isinstance(name, str):
                logger.warning(f"Skipping non-string species name: {name}")
                continue
            if len(name.strip()) == 0:
                logger.warning("Skipping empty species name")
                continue
            if len(name) > 100:  # Reasonable limit for species names
                logger.warning(f"Skipping overly long species name: {name[:50]}...")
                continue
            valid_species_names.append(name.strip())

        if not valid_species_names:
            raise ValidationError(
                "No valid species names found after filtering",
                "species_names",
                species_names,
            )

        # Create shared store for node execution
        shared_store = {"input": {"species_list": valid_species_names}}

        try:
            # Execute ValidateSpeciesNode with PocketFlow pattern
            prep_res = self.validate_species_node.prep(shared_store)
            exec_res = self.validate_species_node.exec(prep_res)
            self.validate_species_node.post(shared_store, prep_res, exec_res)

            # Extract results with error checking
            validated_species = shared_store.get("validated_species", [])
            validation_stats = shared_store.get("validation_stats", {})

            # Validate that we got reasonable results
            if not validated_species and valid_species_names:
                logger.warning("Validation returned no results despite valid input")

            return {
                "success": True,
                "validated_species": validated_species,
                "statistics": validation_stats,
                "input_count": len(species_names),
                "processed_count": len(valid_species_names),
                "validated_count": len(validated_species),
            }

        except Exception as e:
            # Convert to more specific error types
            if "taxonomy" in str(e).lower() or "species" in str(e).lower():
                raise APIError(
                    f"Species validation failed: {str(e)}", endpoint="taxonomy"
                )
            else:
                raise  # Re-raise as is for other errors

    @handle_errors_gracefully(fallback_value={"species_list": [], "species_count": 0})
    @validate_parameters(get_validation_schema("get_regional_species_list"))
    @with_retry(max_retries=3, delay=1.0)
    @with_circuit_breaker()
    @with_timeout(30)
    async def handle_get_regional_species_list(
        self, region: str, **kwargs
    ) -> Dict[str, Any]:
        """Enhanced regional species list handler with error handling and retry logic"""
        logger.info(
            f"Getting species list for region {region} with enhanced error handling"
        )

        # Additional region code validation
        if not region or not isinstance(region, str):
            raise ValidationError(
                "Region code must be a non-empty string", "region", region
            )

        # Basic region code format validation
        region = region.strip().upper()
        if len(region) < 2 or len(region) > 10:
            raise ValidationError(
                "Region code length must be between 2 and 10 characters",
                "region",
                region,
            )

        try:
            # Call eBird API with enhanced error handling
            species_list = self.ebird_api.get_species_list(region_code=region)

            # Validate API response
            if not isinstance(species_list, list):
                raise APIError(
                    "Invalid response format from eBird API", endpoint="species_list"
                )

            # Log statistics for monitoring
            logger.info(
                f"Successfully retrieved {len(species_list)} species for region {region}"
            )

            return {
                "success": True,
                "region_code": region,
                "species_list": species_list,
                "species_count": len(species_list),
                "data_quality": {
                    "has_species_codes": any(
                        isinstance(s, dict) and "speciesCode" in s
                        for s in species_list[:5]
                    ),
                    "response_size": len(species_list),
                },
            }

        except EBirdAPIError as e:
            # Convert eBird API errors to our error types
            if "not found" in str(e).lower() or "invalid" in str(e).lower():
                raise ValidationError(
                    f"Invalid region code: {region}", "region", region
                )
            elif "rate limit" in str(e).lower():
                from ..utils.error_handling import RateLimitError

                raise RateLimitError("eBird API rate limit exceeded for region query")
            else:
                raise APIError(f"eBird API error: {str(e)}", endpoint="species_list")

    async def validate_multiple_regions(self, regions: List[str]) -> Dict[str, Any]:
        """
        Example of batch processing with error handling.
        Validates species lists for multiple regions concurrently.
        """
        logger.info(f"Validating species lists for {len(regions)} regions")

        # Validate input
        if not regions or not isinstance(regions, list):
            raise ValidationError(
                "Regions must be a non-empty list", "regions", regions
            )

        if len(regions) > 10:  # Reasonable limit for batch processing
            raise ValidationError(
                "Too many regions requested (max 10)", "regions", regions
            )

        # Process regions concurrently with error handling
        tasks = []
        for region in regions:
            task = self.handle_get_regional_species_list(region)
            tasks.append(task)

        # Gather results, continuing on individual failures
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and separate successes from failures
        successful_results = []
        failed_results = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_results.append(
                    {
                        "region": regions[i],
                        "error": str(result),
                        "error_type": type(result).__name__,
                    }
                )
            elif isinstance(result, dict) and result.get("success"):
                successful_results.append(result)
            else:
                failed_results.append(
                    {"region": regions[i], "error": "Unknown failure", "result": result}
                )

        return {
            "success": len(successful_results) > 0,
            "total_regions": len(regions),
            "successful_regions": len(successful_results),
            "failed_regions": len(failed_results),
            "results": successful_results,
            "failures": failed_results,
            "partial_success": len(successful_results) > 0 and len(failed_results) > 0,
        }


# Example usage and testing
async def test_enhanced_error_handling():
    """Test the enhanced error handling features"""
    handler = EnhancedSpeciesHandlers()

    # Test cases for different error scenarios
    test_cases = [
        # Valid case
        (["Northern Cardinal", "Blue Jay"], "should succeed"),
        # Invalid input cases
        ([], "empty list should fail"),
        ([""], "empty string should be filtered"),
        ([None, 123, "Valid Bird"], "mixed types should be filtered"),
        (["A" * 200], "overly long name should be filtered"),
        # Edge cases
        (["Northern Cardinal"] * 100, "large list should be handled"),
    ]

    for species_list, description in test_cases:
        try:
            result = await handler.handle_validate_species(species_list)
            logger.info(f"✅ {description}: {result['success']}")
        except Exception as e:
            logger.error(f"❌ {description}: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(test_enhanced_error_handling())
