# Testing Framework for Bird Travel Recommender

This directory contains a comprehensive pytest-based testing framework for the Bird Travel Recommender system.

## Overview

The testing framework provides:
- **Unit tests** for individual node components
- **Integration tests** for complete pipeline workflows
- **Mock eBird API responses** for consistent testing
- **Performance testing** utilities
- **Data validation** helpers
- **Parametrized tests** for comprehensive coverage

## Quick Start

### Running All Tests
```bash
# Run all tests
uv run pytest

# Run tests with verbose output
uv run pytest -v

# Run tests with coverage
uv run pytest --cov=. --cov-report=html
```

### Running Specific Test Categories
```bash
# Run only unit tests
uv run pytest -m unit

# Run only integration tests  
uv run pytest -m integration

# Run only mock tests (no real API calls)
uv run pytest -m mock

# Run quick tests (exclude slow tests)
uv run pytest -m "not slow"
```

### Running Specific Test Files
```bash
# Test ValidateSpeciesNode only
uv run pytest tests/test_validate_species_node.py

# Test FetchSightingsNode only
uv run pytest tests/test_fetch_sightings_node.py

# Test integration workflows
uv run pytest tests/test_integration.py
```

## Test Structure

### Test Files
- **`conftest.py`** - Shared fixtures and test configuration
- **`test_validate_species_node.py`** - Tests for species validation logic
- **`test_fetch_sightings_node.py`** - Tests for parallel sightings fetching
- **`test_filter_constraints_node.py`** - Tests for constraint filtering
- **`test_integration.py`** - End-to-end pipeline tests
- **`test_utils.py`** - Testing utilities and helpers

### Test Markers
- **`@pytest.mark.unit`** - Unit tests for individual components
- **`@pytest.mark.integration`** - Integration tests for workflows
- **`@pytest.mark.mock`** - Tests using mocked data only
- **`@pytest.mark.api`** - Tests requiring real eBird API access
- **`@pytest.mark.slow`** - Tests that take longer to run

## Mock Data System

### eBird API Mocking
The framework includes comprehensive mocking of eBird API endpoints:

```python
# Fixtures automatically mock eBird API responses
def test_species_validation(mock_ebird_api):
    # Test code here - no real API calls made
    pass
```

### Available Mock Fixtures
- **`mock_ebird_taxonomy`** - Sample eBird taxonomy data
- **`mock_ebird_observations`** - Sample observation data
- **`mock_ebird_hotspots`** - Sample hotspot data
- **`mock_validated_species`** - Pre-validated species for testing
- **`mock_ebird_api`** - Complete API client mocking

## Test Data Generators

### Creating Test Data
```python
from tests.test_utils import TestDataGenerator

generator = TestDataGenerator()

# Generate species lists
species = generator.generate_species_list(10, include_invalid=True)

# Generate geographic coordinates
coords = generator.generate_coordinates_near(42.36, -71.06, count=20)

# Generate mock sightings
sightings = generator.generate_mock_sightings(["norcar", "blujay"], coords)
```

## Data Validation

### Validating Test Results
```python
from tests.test_utils import TestDataValidator

validator = TestDataValidator()

# Validate species data structure
assert validator.validate_species_data(species_result)

# Validate sighting data structure  
assert validator.validate_sighting_data(sighting)

# Validate statistics structure
assert validator.validate_statistics(stats, "validation")
```

## Performance Testing

### Measuring Performance
```python
from tests.test_utils import PerformanceTestHelper

helper = PerformanceTestHelper()

# Time function execution
result, duration = helper.time_function(my_function, arg1, arg2)

# Measure parallel vs sequential performance
speedup, seq_time, par_time = helper.measure_parallel_speedup(
    func, sequential_args, parallel_args
)
```

## Integration Testing

### End-to-End Pipeline Tests
Integration tests verify complete workflows:

```python
def test_full_pipeline(pipeline_nodes, mock_ebird_api):
    # Test validates complete species → fetch → filter pipeline
    # Ensures data consistency across all stages
    # Verifies error handling and recovery
    pass
```

## Common Test Patterns

### Testing Node Lifecycle
```python
def test_node_lifecycle(node, shared_store):
    # Test prep phase
    prep_result = node.prep(shared_store)
    assert prep_result is not None
    
    # Test exec phase
    exec_result = node.exec(prep_result)
    assert exec_result is not None
    
    # Test post phase
    node.post(shared_store, prep_result, exec_result)
    assert "expected_key" in shared_store
```

### Parametrized Testing
```python
@pytest.mark.parametrize("input_data,expected", [
    (["Northern Cardinal"], "direct_common_name"),
    (["Cardinalis cardinalis"], "direct_scientific_name"),
    (["norcar"], "direct_species_code"),
])
def test_validation_methods(input_data, expected):
    # Test multiple scenarios efficiently
    pass
```

## Configuration

### pytest.ini Settings
- **Test discovery** - Automatically finds test files
- **Markers** - Defines custom test categories
- **Output formatting** - Configures verbose output
- **Warning filtering** - Reduces noise in test output

### Environment Setup
Tests automatically configure:
- Mock API keys for testing
- Logging levels for debug output
- Temporary directories for test data

## Troubleshooting

### Common Issues

**Import Errors:**
```bash
# Ensure you're in the project root directory
cd /path/to/Bird-Travel-Recommender
uv run pytest
```

**API Key Warnings:**
```bash
# Tests use mock API keys - warnings are expected
# Real API keys only needed for @pytest.mark.api tests
```

**Slow Tests:**
```bash
# Skip slow tests for faster feedback
uv run pytest -m "not slow"

# Run only fast unit tests
uv run pytest -m "unit and mock"
```

### Debug Mode
```bash
# Run with detailed debug output
uv run pytest -v -s --tb=long

# Run single test with debugging
uv run pytest tests/test_validate_species_node.py::TestValidateSpeciesNode::test_prep_phase -v -s
```

## Contributing

### Adding New Tests
1. Follow the existing naming convention (`test_*.py`)
2. Use appropriate markers (`@pytest.mark.unit`, etc.)
3. Include docstrings explaining test purpose
4. Use fixtures for shared test data
5. Validate test data structure with utilities

### Test Coverage Goals
- **Unit tests** - 90%+ coverage for individual nodes
- **Integration tests** - Cover all major workflows
- **Error handling** - Test failure scenarios
- **Performance** - Validate parallel processing benefits

## Migration from Legacy Tests

The old test files (`test_validate_species.py`, etc.) are being migrated to pytest format:
- Better fixtures and mocking
- Parametrized testing for multiple scenarios
- Comprehensive assertion messages
- Integrated performance testing

Run legacy tests for comparison:
```bash
# Old format (still works)
uv run python test_validate_species.py

# New pytest format (recommended)
uv run pytest tests/test_validate_species_node.py
```