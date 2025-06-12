# Contributing to Bird Travel Recommender

Thank you for your interest in contributing to the Bird Travel Recommender! This guide will help you get started.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Process](#development-process)
- [Code Style](#code-style)
- [Testing Guidelines](#testing-guidelines)
- [Documentation Standards](#documentation-standards)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive criticism
- Respect differing viewpoints and experiences
- Show empathy towards other community members

### Unacceptable Behavior

- Harassment, discrimination, or offensive comments
- Personal attacks or trolling
- Publishing private information without consent
- Other conduct that could be considered inappropriate

## Getting Started

### Prerequisites

1. Python 3.9 or higher
2. `uv` package manager
3. Git
4. API keys for OpenAI and eBird (for testing)

### Setting Up Your Development Environment

```bash
# Fork and clone the repository
git clone https://github.com/YOUR-USERNAME/Bird-Travel-Recommender.git
cd Bird-Travel-Recommender

# Create a new branch for your feature
git checkout -b feature/your-feature-name

# Install dependencies
uv sync

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Run tests to ensure everything works
uv run pytest
```

## Development Process

### 1. Find or Create an Issue

- Check existing issues for something you'd like to work on
- If creating a new issue, provide clear description and context
- Comment on the issue to indicate you're working on it

### 2. Design Your Solution

- For significant changes, discuss your approach in the issue first
- Consider backward compatibility
- Think about performance implications
- Plan your testing strategy

### 3. Implement Your Changes

- Write clean, well-documented code
- Follow the existing code style
- Add tests for new functionality
- Update documentation as needed

### 4. Test Your Changes

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_your_feature.py

# Run with coverage
uv run pytest --cov=. --cov-report=html

# Test against real APIs (requires valid keys)
uv run pytest -m api
```

## Code Style

### Python Style Guide

We follow PEP 8 with some modifications:

```python
# Imports: Standard library, third-party, local
import os
import sys
from typing import Dict, List, Optional

import httpx
from pocketflow import Node

from utils.ebird_api import EBirdClient
from utils.geo_utils import haversine_distance


# Class definitions: Clear docstrings
class BirdingNode(Node):
    """
    A node that processes birding data.
    
    This node validates species and fetches recent observations
    from the eBird API.
    
    Attributes:
        api_client: eBird API client instance
        cache: Optional cache for API responses
    """
    
    def __init__(self, api_client: EBirdClient, cache: Optional[Dict] = None):
        self.api_client = api_client
        self.cache = cache or {}
    
    def prep(self, shared: Dict) -> Dict:
        """Prepare data for processing."""
        return {
            "species": shared.get("species", []),
            "location": shared.get("location")
        }
    
    def exec(self, prep_data: Dict) -> Dict:
        """Execute main processing logic."""
        # Implementation here
        pass


# Function definitions: Type hints and docstrings
def calculate_optimal_route(
    locations: List[Dict],
    start_point: tuple[float, float],
    max_distance: Optional[float] = None
) -> List[Dict]:
    """
    Calculate optimal route between birding locations.
    
    Args:
        locations: List of location dictionaries with lat/lng
        start_point: Starting coordinates (lat, lng)
        max_distance: Maximum total distance in km
        
    Returns:
        Ordered list of locations representing optimal route
        
    Raises:
        ValueError: If locations list is empty
        RouteError: If no valid route can be found
    """
    if not locations:
        raise ValueError("Locations list cannot be empty")
    
    # Implementation here
    return optimized_route
```

### Naming Conventions

```python
# Variables and functions: snake_case
user_location = get_current_location()
species_list = validate_species(input_names)

# Classes: PascalCase
class BirdingRecommender:
    pass

# Constants: UPPER_SNAKE_CASE
MAX_RETRY_ATTEMPTS = 3
DEFAULT_SEARCH_RADIUS_KM = 50

# Private methods: Leading underscore
def _internal_helper(self):
    pass
```

### Import Organization

```python
# Standard library imports
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

# Third-party imports
import httpx
import pytest
from pocketflow import Node, Flow

# Local imports
from utils.ebird_api import EBirdClient
from utils.geo_utils import haversine_distance
from nodes import ValidateSpeciesNode
```

## Testing Guidelines

### Test Structure

```python
# tests/test_feature_name.py

import pytest
from unittest.mock import Mock, patch

from your_module import YourClass


class TestYourClass:
    """Test suite for YourClass."""
    
    @pytest.fixture
    def instance(self):
        """Create instance for testing."""
        return YourClass()
    
    def test_normal_operation(self, instance):
        """Test normal operation with valid input."""
        result = instance.process(valid_input)
        assert result["success"] is True
        assert "data" in result
    
    def test_edge_case(self, instance):
        """Test edge case handling."""
        result = instance.process(edge_case_input)
        assert result["handled_gracefully"] is True
    
    def test_error_handling(self, instance):
        """Test error handling with invalid input."""
        with pytest.raises(ValueError) as exc_info:
            instance.process(invalid_input)
        assert "Expected error message" in str(exc_info.value)
    
    @patch('your_module.external_api_call')
    def test_with_mock(self, mock_api, instance):
        """Test with mocked external dependency."""
        mock_api.return_value = {"mocked": "response"}
        result = instance.process_with_api()
        assert result["source"] == "mocked"
```

### Test Categories

Mark tests appropriately:

```python
@pytest.mark.unit          # Fast, isolated unit tests
@pytest.mark.integration   # Tests involving multiple components
@pytest.mark.api          # Tests requiring real API calls
@pytest.mark.slow         # Tests that take > 1 second
```

### Test Coverage

- Aim for > 80% code coverage
- Test happy paths and error cases
- Include edge cases and boundary conditions
- Test with realistic data

## Documentation Standards

### Code Documentation

```python
def complex_function(
    param1: str,
    param2: List[Dict],
    param3: Optional[int] = None
) -> Dict[str, Any]:
    """
    Brief description of what the function does.
    
    Longer description if needed, explaining the purpose,
    algorithm, or any important details.
    
    Args:
        param1: Description of param1
        param2: Description of param2, including structure
            Example: [{"key": "value"}, ...]
        param3: Optional parameter description
        
    Returns:
        Description of return value structure
        Example: {
            "success": bool,
            "data": list,
            "metadata": dict
        }
        
    Raises:
        ValueError: When param1 is empty
        APIError: When external API call fails
        
    Example:
        >>> result = complex_function("test", [{"id": 1}])
        >>> print(result["success"])
        True
    """
    # Implementation
    pass
```

### Documentation Files

When updating documentation:

1. Use clear, concise language
2. Include practical examples
3. Keep formatting consistent
4. Update the table of contents
5. Check links still work

## Pull Request Process

### 1. Before Creating a PR

- [ ] All tests pass locally
- [ ] Code follows style guidelines
- [ ] New features have tests
- [ ] Documentation is updated
- [ ] Commit messages are clear

### 2. Creating the PR

```bash
# Push your branch
git push origin feature/your-feature-name

# Create PR on GitHub with:
# - Clear title describing the change
# - Description linking to related issue
# - List of changes made
# - Screenshots if UI changes
```

### PR Template

```markdown
## Description
Brief description of changes

## Related Issue
Fixes #123

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Refactoring

## Testing
- [ ] All existing tests pass
- [ ] Added new tests for changes
- [ ] Tested with real API calls

## Checklist
- [ ] Code follows project style
- [ ] Self-reviewed my code
- [ ] Documentation updated
- [ ] No new warnings
```

### 3. PR Review Process

- Respond to review comments promptly
- Make requested changes in new commits
- Re-request review when ready
- Be patient and constructive

### 4. After Merge

- Delete your feature branch
- Update your local main branch
- Close related issues

## Commit Message Guidelines

### Format

```
type(scope): subject

body

footer
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Test additions or changes
- `chore`: Build process or auxiliary tool changes

### Examples

```bash
feat(nlp): add enhanced intent classification

Implement LLM-powered intent classification with 9 specialized
birding intents. Achieves 90-95% accuracy compared to 30% with
previous keyword matching.

Closes #45

---

fix(api): handle rate limit errors gracefully

Add exponential backoff when eBird API rate limit is reached.
Prevents cascade failures and provides better user experience.

---

docs(api): add examples for all MCP tools

Add comprehensive examples for each of the 9 MCP tools,
including request/response formats and error handling.
```

## Getting Help

### Resources

- Check existing documentation
- Review test files for examples
- Look at similar PRs
- Ask in issue discussions

### Communication Channels

- GitHub Issues: Bug reports and feature requests
- GitHub Discussions: General questions and ideas
- Pull Request comments: Code-specific discussions

## Recognition

Contributors will be:
- Listed in the project README
- Acknowledged in release notes
- Credited in relevant documentation

Thank you for contributing to make birding more accessible through technology! 🐦