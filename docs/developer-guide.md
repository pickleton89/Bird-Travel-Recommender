# Bird Travel Recommender Developer Guide

This guide helps developers understand, extend, and contribute to the Bird Travel Recommender system.

## Table of Contents

- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Core Concepts](#core-concepts)
- [Adding New Features](#adding-new-features)
- [Testing Strategy](#testing-strategy)
- [Debugging](#debugging)
- [Performance Considerations](#performance-considerations)

## Development Setup

### Prerequisites

- Python 3.9 or higher
- `uv` package manager
- API keys for OpenAI and eBird

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/your-org/Bird-Travel-Recommender.git
cd Bird-Travel-Recommender

# Install dependencies using uv
uv sync

# Copy environment template
cp config/.env.example .env

# Edit .env with your API keys
# OPENAI_API_KEY=your_key_here
# EBIRD_API_KEY=your_key_here

# Verify setup
uv run python scripts/check_api_keys.py
```

### Development Workflow

```bash
# Run tests
uv run pytest

# Run specific test file
uv run pytest tests/test_validate_species_node.py

# Run with coverage
uv run pytest --cov=. --cov-report=html

# Run the main application
uv run python main.py

# Run the MCP server
uv run python src/bird_travel_recommender/mcp/server.py

# Deploy MCP server for Claude
python scripts/deploy_mcp.py development
```

## Project Structure

```
Bird-Travel-Recommender/
├── main.py                    # Development convenience entry point
├── src/
│   └── bird_travel_recommender/
│       ├── __init__.py        # Package initialization
│       ├── main.py            # Application entry point
│       ├── flow.py            # PocketFlow pipeline definition
│       ├── nodes.py           # Core pipeline nodes
│       ├── utils/
│       │   ├── __init__.py
│       │   ├── ebird_api.py          # eBird API client
│       │   ├── call_llm.py           # OpenAI integration
│       │   ├── enhanced_nlp.py       # NLP processing
│       │   ├── response_formatter.py  # Response formatting
│       │   ├── geo_utils.py          # Geographic utilities
│       │   └── route_optimizer.py    # Route optimization
│       └── mcp/
│           ├── __init__.py
│           ├── server.py      # MCP server with 9 tools
│           └── config/
│               ├── base.json
│               ├── development.json
│               └── production.json
├── tests/
│   ├── __init__.py
│   ├── conftest.py           # Test fixtures
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   ├── fixtures/             # Test fixtures
│   └── README.md             # Testing guide
├── scripts/
│   ├── check_api_keys.py     # API key validation
│   └── deploy_mcp.py         # MCP deployment script
├── config/
│   └── .env.example          # Environment template
└── docs/
    └── *.md                  # Documentation files
```

### Key Components

#### Pipeline Nodes (`nodes.py`)

Each node follows the PocketFlow pattern:

```python
class MyNode(Node):
    def prep(self, shared: Dict) -> Any:
        """Prepare data for processing"""
        return prepared_data
    
    def exec(self, data: Any) -> Any:
        """Execute main logic"""
        return processed_data
    
    def post(self, shared: Dict, prep_data: Any, exec_data: Any):
        """Store results in shared store"""
        shared["my_results"] = exec_data
```

#### MCP Tools (`src/bird_travel_recommender/mcp/server.py`)

Tools are defined with JSON schemas:

```python
Tool(
    name="my_tool",
    description="Tool description",
    inputSchema={
        "type": "object",
        "properties": {
            "param1": {"type": "string"},
            "param2": {"type": "number"}
        },
        "required": ["param1"]
    }
)
```

## Core Concepts

### 1. Enhanced NLP Processing

The system uses LLM-powered intent classification:

```python
# Enhanced NLP flow
User Query → Enhanced NLP → Intent + Parameters → Tool Selection → Execution → Formatting
```

Key classes:
- `EnhancedNLPProcessor`: Intent classification and parameter extraction
- `BirdingIntent`: Enum of 9 intent types
- `ExtractedParameters`: Structured parameter storage

### 2. Shared Store Pattern

All nodes communicate through a shared dictionary:

```python
shared_store = {
    "user_request": "original query",
    "intent_analysis": {...},
    "validated_species": [...],
    "observations": [...],
    # ... more results
}
```

### 3. Tool Execution Strategies

Three execution patterns based on query complexity:

- **Monolithic**: Single tool for complete workflows
- **Sequential**: Step-by-step tool execution
- **Parallel**: Concurrent independent operations

### 4. Experience Level Adaptation

Responses adapt to four experience levels:
- Beginner: Simple language, safety focus
- Intermediate: Standard terminology
- Advanced: Technical details
- Expert: Research context

## Adding New Features

### Adding a New MCP Tool

1. **Define the tool in `src/bird_travel_recommender/mcp/server.py`**:

```python
Tool(
    name="analyze_migration",
    description="Analyze bird migration patterns",
    inputSchema={
        "type": "object",
        "properties": {
            "species": {"type": "array", "items": {"type": "string"}},
            "region": {"type": "string"},
            "season": {"type": "string", "enum": ["spring", "fall"]}
        },
        "required": ["species", "region"]
    }
)
```

2. **Implement the handler**:

```python
async def _handle_analyze_migration(self, species: List[str], region: str, season: str = "spring"):
    """Analyze migration patterns for species"""
    try:
        # Validate species
        validated = await self._validate_species_batch(species)
        
        # Query migration data
        migration_data = await self.ebird_api.get_migration_data(
            validated, region, season
        )
        
        # Analyze patterns
        patterns = self._analyze_patterns(migration_data)
        
        return {
            "success": True,
            "patterns": patterns,
            "peak_dates": self._calculate_peak_dates(patterns)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
```

3. **Add to tool router**:

```python
elif tool_name == "analyze_migration":
    result = await self._handle_analyze_migration(**arguments)
```

### Adding a New Pipeline Node

1. **Create the node class**:

```python
class MigrationAnalysisNode(Node):
    """Analyzes bird migration patterns"""
    
    def prep(self, shared: Dict) -> Dict:
        """Prepare migration analysis data"""
        return {
            "species": shared.get("validated_species", []),
            "region": shared.get("region"),
            "season": shared.get("season", "spring")
        }
    
    def exec(self, prep_data: Dict) -> Dict:
        """Execute migration analysis"""
        # Implementation here
        return migration_analysis
    
    def post(self, shared: Dict, prep_data: Dict, exec_data: Dict):
        """Store migration analysis results"""
        shared["migration_analysis"] = exec_data
```

2. **Integrate into pipeline**:

```python
# In flow.py or agent_flow.py
migration_node = MigrationAnalysisNode()
flow.add_node("migration_analysis", migration_node)
flow.add_edge("validate_species", "migration_analysis")
```

### Adding a New Intent Type

1. **Update the enum in `enhanced_nlp.py`**:

```python
class BirdingIntent(Enum):
    # Existing intents...
    MIGRATION_ANALYSIS = "migration_analysis"
```

2. **Update LLM prompt**:

```python
INTENT_CLASSIFICATION_PROMPT = """
Classify the birding-related intent...

9. migration_analysis - Analyzing bird migration patterns and timing
"""
```

3. **Add parameter extraction**:

```python
def _extract_migration_parameters(self, query: str) -> Dict:
    """Extract migration-specific parameters"""
    return {
        "season": self._extract_season(query),
        "time_period": self._extract_time_period(query),
        "species_group": self._extract_species_group(query)
    }
```

4. **Map to tools in agent**:

```python
elif intent == BirdingIntent.MIGRATION_ANALYSIS:
    return {
        "strategy": "sequential",
        "tools": ["validate_species", "analyze_migration"],
        "confidence": confidence
    }
```

### Adding Response Formatting

1. **Add response type to `response_formatter.py`**:

```python
class ResponseType(Enum):
    # Existing types...
    MIGRATION_ANALYSIS = "migration_analysis"
```

2. **Create formatting function**:

```python
def _format_migration_analysis(self, data: Dict, context: FormattingContext) -> str:
    """Format migration analysis results"""
    if context.experience_level == "beginner":
        return self._format_simple_migration(data)
    else:
        return self._format_detailed_migration(data)
```

3. **Add to response router**:

```python
elif response_type == ResponseType.MIGRATION_ANALYSIS:
    return self._format_migration_analysis(results, context)
```

## Testing Strategy

### Unit Testing

Test individual components in isolation:

```python
def test_migration_analysis_node():
    node = MigrationAnalysisNode()
    shared = {
        "validated_species": [{"species_code": "amro"}],
        "region": "US-MA",
        "season": "spring"
    }
    
    prep_data = node.prep(shared)
    exec_data = node.exec(prep_data)
    
    assert exec_data["success"]
    assert "peak_dates" in exec_data
```

### Integration Testing

Test complete workflows:

```python
@pytest.mark.integration
def test_migration_tool_integration(mcp_server):
    result = await mcp_server._handle_analyze_migration(
        species=["American Robin"],
        region="US-MA",
        season="spring"
    )
    
    assert result["success"]
    assert len(result["patterns"]) > 0
```

### Mock Testing

Use mocks for external APIs:

```python
@patch('bird_travel_recommender.utils.ebird_api.EBirdClient.get_migration_data')
def test_migration_with_mock(mock_migration):
    mock_migration.return_value = sample_migration_data
    # Test implementation
```

## Debugging

### Enable Debug Logging

```python
# In your code
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add debug statements
logger.debug(f"Processing {len(species)} species")
```

### Common Issues

1. **API Rate Limits**
```python
# Check for rate limit errors
if "rate limit" in error_message.lower():
    logger.warning("Rate limit hit, implementing backoff")
    time.sleep(exponential_backoff())
```

2. **LLM Timeouts**
```python
# Set appropriate timeouts
response = await call_llm(prompt, timeout=30)
```

3. **Memory Issues**
```python
# Process in batches for large datasets
for batch in chunks(large_list, size=100):
    process_batch(batch)
```

### Debugging Tools

```bash
# Run with verbose output
uv run python main.py --debug

# Test specific components
uv run python -m bird_travel_recommender.utils.enhanced_nlp "test query"

# Profile performance
uv run python -m cProfile main.py
```

## Performance Considerations

### Parallel Processing

Use `BatchNode` for parallel API calls:

```python
class ParallelFetchNode(BatchNode):
    max_workers = 5  # Concurrent API calls
```

### Caching

Implement caching for expensive operations:

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_species_taxonomy(species_code: str):
    # Expensive lookup
    return taxonomy_data
```

### API Optimization

```python
# Batch API requests
species_batch = ["species1", "species2", "species3"]
results = await self.ebird_api.get_observations_batch(species_batch)

# Use appropriate endpoints
if len(species) == 1:
    # Use species-specific endpoint
    data = await self.get_species_observations(species[0])
else:
    # Use regional endpoint with species filter
    data = await self.get_regional_observations(region, species)
```

### Memory Management

```python
# Clear large objects when done
del large_dataset
gc.collect()

# Use generators for large datasets
def process_observations(observations):
    for obs in observations:
        yield process_single(obs)
```

## Best Practices

### Code Style

- Follow PEP 8 conventions
- Use type hints for clarity
- Document with clear docstrings
- Keep functions focused and small

### Error Handling

```python
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    return fallback_result()
except Exception as e:
    logger.exception("Unexpected error")
    raise
```

### Testing

- Write tests for new features
- Maintain > 80% code coverage
- Use meaningful test names
- Test edge cases and errors

### Documentation

- Update docstrings for new code
- Add examples for complex features
- Keep README current
- Document breaking changes

## Resources

### Internal Documentation
- [Architecture](architecture.md) - System design details
- [API Reference](api-reference.md) - Tool documentation
- [Testing Guide](../tests/README.md) - Testing framework

### External Resources
- [PocketFlow Documentation](https://github.com/PocketFlow/docs)
- [eBird API Documentation](https://documenter.getpostman.com/view/664302/S1ENwy59)
- [MCP Specification](https://modelcontextprotocol.io/docs)

### Getting Help
- Check existing issues on GitHub
- Review test files for examples
- Consult architecture documentation
- Ask in project discussions