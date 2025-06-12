#!/usr/bin/env python3
"""
Test script for ValidateSpeciesNode to verify eBird taxonomy integration.
"""

import logging
from nodes import ValidateSpeciesNode

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_validate_species_node():
    """Test ValidateSpeciesNode with various species names."""
    
    # Initialize the node
    validate_node = ValidateSpeciesNode()
    
    # Test data with various types of bird names
    test_species_lists = [
        # Test 1: Common names that should match directly
        ["Northern Cardinal", "Blue Jay", "American Robin"],
        
        # Test 2: Shortened names that need partial matching
        ["cardinal", "blue jay", "robin"],
        
        # Test 3: Mix of valid and invalid names
        ["Northern Cardinal", "invalid bird name", "Blue Jay", "made up species"],
        
        # Test 4: Scientific names
        ["Cardinalis cardinalis", "Cyanocitta cristata"],
        
        # Test 5: eBird species codes
        ["norcar", "blujay", "amerob"]
    ]
    
    for i, species_list in enumerate(test_species_lists, 1):
        print(f"\n{'='*60}")
        print(f"TEST {i}: {species_list}")
        print(f"{'='*60}")
        
        # Create shared store structure as expected by the node
        shared = {
            "input": {
                "species_list": species_list
            }
        }
        
        try:
            # Run the validation node
            prep_result = validate_node.prep(shared)
            exec_result = validate_node.exec(prep_result)
            validate_node.post(shared, prep_result, exec_result)
            
            # Display results
            print(f"Input species: {len(species_list)}")
            print(f"Validated species: {len(shared['validated_species'])}")
            print(f"Validation stats: {shared['validation_stats']}")
            
            print("\nValidated Species Details:")
            for species in shared['validated_species']:
                print(f"  • {species['original_name']} → {species['common_name']}")
                print(f"    Code: {species['species_code']}, Method: {species['validation_method']}")
                print(f"    Confidence: {species['confidence']}, Scientific: {species['scientific_name']}")
                print(f"    Seasonal: {species['seasonal_notes']}")
                print(f"    Behavioral: {species['behavioral_notes']}")
                print()
            
        except Exception as e:
            print(f"ERROR in test {i}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("Testing ValidateSpeciesNode with eBird API integration...")
    test_validate_species_node()
    print("\nValidation testing completed!")