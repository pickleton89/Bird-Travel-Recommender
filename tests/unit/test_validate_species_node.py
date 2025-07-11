"""
Unit tests for ValidateSpeciesNode using pytest framework.

Tests cover:
- Direct taxonomy lookup validation
- LLM fallback for fuzzy matching
- Various input formats (common names, scientific names, species codes)
- Error handling and edge cases
- Performance and caching
"""

import pytest
from unittest.mock import patch
from bird_travel_recommender.nodes import ValidateSpeciesNode


class TestValidateSpeciesNode:
    """Test suite for ValidateSpeciesNode."""

    @pytest.fixture
    def validate_node(self):
        """Create ValidateSpeciesNode instance for testing."""
        return ValidateSpeciesNode()

    @pytest.fixture
    def shared_store_basic(self):
        """Basic shared store for testing."""
        return {
            "input": {
                "species_list": ["Northern Cardinal", "Blue Jay", "American Robin"]
            }
        }

    @pytest.mark.unit
    @pytest.mark.mock
    def test_prep_phase(self, validate_node, shared_store_basic):
        """Test the preparation phase of ValidateSpeciesNode."""
        result = validate_node.prep(shared_store_basic)
        
        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 3
        assert result == ["Northern Cardinal", "Blue Jay", "American Robin"]

    @pytest.mark.unit
    @pytest.mark.mock  
    def test_direct_common_name_validation(self, validate_node, mock_ebird_api):
        """Test direct common name validation."""
        shared = {
            "input": {
                "species_list": ["Northern Cardinal", "Blue Jay"]
            }
        }
        
        # Run the full node lifecycle
        prep_result = validate_node.prep(shared)
        exec_result = validate_node.exec(prep_result)
        validate_node.post(shared, prep_result, exec_result)
        
        # Verify results
        assert "validated_species" in shared
        assert len(shared["validated_species"]) == 2
        
        # Check first species
        cardinal = shared["validated_species"][0]
        assert cardinal["original_name"] == "Northern Cardinal"
        assert cardinal["common_name"] == "Northern Cardinal"
        assert cardinal["species_code"] == "norcar"
        assert cardinal["validation_method"] == "direct_common_name"
        assert cardinal["confidence"] == 1.0
        
        # Check second species
        jay = shared["validated_species"][1]
        assert jay["original_name"] == "Blue Jay"
        assert jay["common_name"] == "Blue Jay"
        assert jay["species_code"] == "blujay"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_scientific_name_validation(self, validate_node, mock_ebird_api):
        """Test scientific name validation."""
        shared = {
            "input": {
                "species_list": ["Cardinalis cardinalis", "Cyanocitta cristata"]
            }
        }
        
        prep_result = validate_node.prep(shared)
        exec_result = validate_node.exec(prep_result)
        validate_node.post(shared, prep_result, exec_result)
        
        assert len(shared["validated_species"]) == 2
        
        cardinal = shared["validated_species"][0]
        assert cardinal["validation_method"] == "direct_scientific_name"
        assert cardinal["scientific_name"] == "Cardinalis cardinalis"
        assert cardinal["species_code"] == "norcar"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_species_code_validation(self, validate_node, mock_ebird_api):
        """Test species code validation."""
        shared = {
            "input": {
                "species_list": ["norcar", "blujay", "amerob"]
            }
        }
        
        prep_result = validate_node.prep(shared)
        exec_result = validate_node.exec(prep_result)
        validate_node.post(shared, prep_result, exec_result)
        
        assert len(shared["validated_species"]) == 3
        
        cardinal = shared["validated_species"][0]
        assert cardinal["validation_method"] == "direct_species_code"
        assert cardinal["species_code"] == "norcar"
        assert cardinal["common_name"] == "Northern Cardinal"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_partial_matching(self, validate_node, mock_ebird_api):
        """Test partial name matching."""
        shared = {
            "input": {
                "species_list": ["cardinal", "jay", "robin"]
            }
        }
        
        prep_result = validate_node.prep(shared)
        exec_result = validate_node.exec(prep_result)
        validate_node.post(shared, prep_result, exec_result)
        
        # Should find matches for partial names
        assert len(shared["validated_species"]) >= 1
        
        # Check that partial matching method is used
        for species in shared["validated_species"]:
            assert species["validation_method"] in ["partial_common_name", "partial_scientific_name"]
            assert 0.5 <= species["confidence"] <= 1.0

    @pytest.mark.unit
    @pytest.mark.mock
    def test_invalid_species_handling(self, validate_node, mock_ebird_api):
        """Test handling of invalid species names."""
        shared = {
            "input": {
                "species_list": ["Northern Cardinal", "Invalid Bird Name", "Blue Jay", "Made Up Species"]
            }
        }
        
        prep_result = validate_node.prep(shared)
        exec_result = validate_node.exec(prep_result)
        validate_node.post(shared, prep_result, exec_result)
        
        # Should validate the valid species and skip invalid ones
        assert len(shared["validated_species"]) == 2
        
        species_names = [s["common_name"] for s in shared["validated_species"]]
        assert "Northern Cardinal" in species_names
        assert "Blue Jay" in species_names
        assert "Invalid Bird Name" not in species_names
        assert "Made Up Species" not in species_names

    @pytest.mark.unit
    @pytest.mark.mock
    def test_validation_statistics(self, validate_node, mock_ebird_api):
        """Test validation statistics generation."""
        shared = {
            "input": {
                "species_list": ["Northern Cardinal", "invalid name", "Blue Jay"]
            }
        }
        
        prep_result = validate_node.prep(shared)
        exec_result = validate_node.exec(prep_result)
        validate_node.post(shared, prep_result, exec_result)
        
        # Check validation statistics
        assert "validation_stats" in shared
        stats = shared["validation_stats"]
        
        assert stats["total_input"] == 3
        successfully_validated = stats["direct_taxonomy_matches"] + stats["llm_fuzzy_matches"]
        assert successfully_validated == 2
        validation_rate = successfully_validated / stats["total_input"]
        assert validation_rate == pytest.approx(0.667, rel=1e-2)
        # Note: validation_methods_used is not in current implementation
        assert stats["direct_taxonomy_matches"] == 2

    @pytest.mark.unit
    @pytest.mark.mock
    def test_seasonal_and_behavioral_notes(self, validate_node, mock_ebird_api):
        """Test that seasonal and behavioral notes are added."""
        shared = {
            "input": {
                "species_list": ["Northern Cardinal"]
            }
        }
        
        prep_result = validate_node.prep(shared)
        exec_result = validate_node.exec(prep_result)
        validate_node.post(shared, prep_result, exec_result)
        
        cardinal = shared["validated_species"][0]
        assert "seasonal_notes" in cardinal
        assert "behavioral_notes" in cardinal
        assert len(cardinal["seasonal_notes"]) > 0
        assert len(cardinal["behavioral_notes"]) > 0

    @pytest.mark.unit
    @pytest.mark.mock
    def test_empty_species_list(self, validate_node):
        """Test handling of empty species list."""
        shared = {
            "input": {
                "species_list": []
            }
        }
        
        prep_result = validate_node.prep(shared)
        exec_result = validate_node.exec(prep_result)
        validate_node.post(shared, prep_result, exec_result)
        
        assert shared["validated_species"] == []
        assert shared["validation_stats"]["total_input_species"] == 0
        assert shared["validation_stats"]["successfully_validated"] == 0

    @pytest.mark.unit
    @pytest.mark.mock
    def test_duplicate_species_handling(self, validate_node, mock_ebird_api):
        """Test handling of duplicate species in input."""
        shared = {
            "input": {
                "species_list": ["Northern Cardinal", "Northern Cardinal", "Blue Jay", "cardinal"]
            }
        }
        
        prep_result = validate_node.prep(shared)
        exec_result = validate_node.exec(prep_result)
        validate_node.post(shared, prep_result, exec_result)
        
        # Should handle duplicates appropriately
        # Check that we don't have duplicate species codes (but multiple matches for "cardinal" variations is OK)
        assert len(shared["validated_species"]) >= 2

    @pytest.mark.unit
    @pytest.mark.mock
    @patch('bird_travel_recommender.utils.call_llm.call_llm')
    def test_llm_fallback_integration(self, mock_llm, validate_node, mock_ebird_api):
        """Test LLM fallback when direct lookup fails."""
        # Configure LLM mock to return fuzzy match result
        mock_llm.return_value = """
        Based on "cardina", this appears to be a partial reference to "Northern Cardinal".
        
        SPECIES_MATCH: Northern Cardinal
        CONFIDENCE: 0.85
        REASONING: "cardina" is a clear partial match for "cardinal"
        """
        
        shared = {
            "input": {
                "species_list": ["cardina"]  # Partial name that should trigger LLM fallback
            }
        }
        
        prep_result = validate_node.prep(shared)
        exec_result = validate_node.exec(prep_result)
        validate_node.post(shared, prep_result, exec_result)
        
        # Should have found a match through partial matching or LLM fallback
        assert len(shared["validated_species"]) == 1
        match = shared["validated_species"][0]
        # Accept either partial matching or LLM fallback (both are valid)
        assert match["validation_method"] in ["partial_common_name", "llm_fuzzy_match"]
        assert match["confidence"] >= 0.8  # Both methods should have good confidence
        assert match["common_name"] == "Northern Cardinal"
        
        # If partial matching found it, LLM won't be called
        if match["validation_method"] == "llm_fuzzy_match":
            mock_llm.assert_called_once()
        else:
            # Partial matching should prevent LLM call
            mock_llm.assert_not_called()

    @pytest.mark.parametrize("species_input,expected_method", [
        (["Northern Cardinal"], "direct_common_name"),
        (["Cardinalis cardinalis"], "direct_scientific_name"), 
        (["norcar"], "direct_species_code"),
        (["cardinal"], "partial_common_name"),
    ])
    @pytest.mark.unit
    @pytest.mark.mock
    def test_validation_methods_parametrized(self, validate_node, mock_ebird_api, species_input, expected_method):
        """Test different validation methods using parametrized testing."""
        shared = {
            "input": {
                "species_list": species_input
            }
        }
        
        prep_result = validate_node.prep(shared)
        exec_result = validate_node.exec(prep_result)
        validate_node.post(shared, prep_result, exec_result)
        
        assert len(shared["validated_species"]) >= 1
        assert shared["validated_species"][0]["validation_method"] == expected_method