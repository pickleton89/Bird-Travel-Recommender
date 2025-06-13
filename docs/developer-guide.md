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
uv run python scripts/deploy_mcp.py development
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
│           ├── server.py      # MCP server with 32 tools
│           ├── tools/         # Tool definitions (6 categories)
│           ├── handlers/      # Business logic implementations
│           ├── utils/         # Error handling framework
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

#### MCP Tools Architecture

The system now uses a modular architecture with 32 tools across 6 categories:

```python
# Tools are organized by category in tools/ directory
tools/
├── species.py      # Species validation tools (2)
├── location.py     # Location discovery tools (12)
├── pipeline.py     # Data processing tools (12)
├── planning.py     # Trip planning tools (2)
├── advisory.py     # Expert advice tools (1)
└── community.py    # Social features tools (3)

# Handlers implement business logic in handlers/ directory
handlers/
├── species.py
├── enhanced_species.py  # With comprehensive error handling
├── location.py
├── pipeline.py
├── planning.py
├── advisory.py
└── community.py
```

Tool definitions use enhanced schemas with validation:

```python
@validate_parameters
@handle_errors
@circuit_breaker
async def get_region_details(self, region: str) -> Dict:
    """Get detailed region information with error handling."""
    try:
        # Validation
        if not region or len(region) < 2:
            raise ValidationError("Region must be at least 2 characters")
        
        # Business logic with error handling
        region_data = await self.ebird_api.get_region_info(region)
        enriched_data = self._enrich_region_data(region_data)
        
        return {"success": True, "region_info": enriched_data}
        
    except ValidationError as e:
        return self.error_handler.handle_validation_error(e)
    except APIError as e:
        return self.error_handler.handle_api_error(e)
    except Exception as e:
        return self.error_handler.handle_unexpected_error(e)
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
- `BirdingIntent`: Enum of 9 intent types mapped to 32 tools
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

Multiple execution patterns based on query complexity:

- **Monolithic**: Single tool for complete workflows (`plan_complete_trip`)
- **Sequential**: Step-by-step tool execution across categories
- **Parallel**: Concurrent independent operations within categories
- **Category-Based**: Tools organized by function (Species, Location, Pipeline, Planning, Advisory, Community)

### 4. Experience Level Adaptation

Responses adapt to four experience levels:
- Beginner: Simple language, safety focus
- Intermediate: Standard terminology
- Advanced: Technical details
- Expert: Research context

## Adding New Features

### Adding a New MCP Tool

The modular architecture makes adding tools straightforward:

1. **Choose the appropriate category** (Species, Location, Pipeline, Planning, Advisory, Community)

2. **Define the tool in the relevant tools file** (e.g., `tools/location.py`):

```python
# In tools/pipeline.py (since this is data analysis)
get_migration_analysis_tool = Tool(
    name="get_migration_analysis",
    description="Analyze bird migration patterns and timing for species in regions",
    inputSchema={
        "type": "object",
        "properties": {
            "species_codes": {
                "type": "array", 
                "items": {"type": "string"},
                "description": "List of eBird species codes to analyze"
            },
            "region": {
                "type": "string",
                "description": "Region code (e.g., 'US-MA', 'CA-ON')"
            },
            "migration_season": {
                "type": "string", 
                "enum": ["spring", "fall", "both"],
                "default": "both",
                "description": "Which migration season to analyze"
            },
            "years_back": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "default": 3,
                "description": "Number of years of historical data to analyze"
            }
        },
        "required": ["species_codes", "region"]
    }
)

PIPELINE_TOOLS = [
    # ... existing tools
    get_migration_analysis_tool
]
```

3. **Implement the handler in `handlers/pipeline.py`**:

```python
class PipelineHandlers:
    def __init__(self):
        self.ebird_api = EBirdClient()
        self.error_handler = ErrorHandler()
    
    @validate_parameters
    @handle_errors
    @circuit_breaker
    async def get_migration_analysis(self, species_codes: List[str], region: str, 
                                   migration_season: str = "both", years_back: int = 3) -> Dict:
        """Analyze migration patterns with comprehensive error handling."""
        try:
            # Input validation
            if not species_codes:
                raise ValidationError("At least one species code required")
            if not region:
                raise ValidationError("Region parameter is required")
            
            # Get historical data with retry logic
            migration_data = await self._fetch_migration_data_with_retry(
                species_codes, region, migration_season, years_back
            )
            
            # Analyze patterns with fallback
            analysis = self._analyze_migration_patterns(migration_data)
            
            # Enrich with additional insights
            enriched_analysis = await self._enrich_migration_analysis(analysis)
            
            return {
                "success": True,
                "migration_analysis": enriched_analysis,
                "peak_periods": self._calculate_peak_periods(analysis),
                "confidence_metrics": self._calculate_confidence(migration_data)
            }
            
        except ValidationError as e:
            return self.error_handler.handle_validation_error(e)
        except APIError as e:
            return self.error_handler.handle_api_error(e)
        except Exception as e:
            return self.error_handler.handle_unexpected_error(e)
    
    async def _fetch_migration_data_with_retry(self, species_codes, region, season, years):
        """Fetch migration data with exponential backoff retry."""
        for attempt in range(self.error_handler.max_retries):
            try:
                return await self.ebird_api.get_historical_observations(
                    species_codes, region, years_back=years, migration_season=season
                )
            except RateLimitError:
                if attempt < self.error_handler.max_retries - 1:
                    await asyncio.sleep(self.error_handler.calculate_backoff(attempt))
                else:
                    raise
```

4. **Register in server.py**:

```python
# Import new tools
from .tools.pipeline import PIPELINE_TOOLS

# In server.py, tools are automatically registered from each category
all_tools = (
    SPECIES_TOOLS + 
    LOCATION_TOOLS + 
    PIPELINE_TOOLS +  # Now includes get_migration_analysis
    PLANNING_TOOLS + 
    ADVISORY_TOOLS + 
    COMMUNITY_TOOLS
)

# Handler routing in call_tool method
elif tool_name == "get_migration_analysis":
    result = await self.handlers_container.pipeline.get_migration_analysis(**arguments)
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
    TEMPORAL_ANALYSIS = "temporal_analysis"  # Maps to multiple pipeline tools
```

2. **Update LLM prompt to map to tool categories**:

```python
INTENT_CLASSIFICATION_PROMPT = """
Classify the birding-related intent and map to our 6 tool categories...

9. temporal_analysis - Analyzing migration, seasonal trends, historical patterns
   → Maps to Pipeline Tools: get_migration_data, get_seasonal_trends, get_historic_observations
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

4. **Map to tool categories in agent**:

```python
elif intent == BirdingIntent.TEMPORAL_ANALYSIS:
    # Determine specific tools based on extracted parameters
    tools = ["validate_species"]  # Species validation first
    
    if "migration" in parameters.get("analysis_type", ""):
        tools.append("get_migration_data")
    if "seasonal" in parameters.get("analysis_type", ""):
        tools.append("get_seasonal_trends")
    if "historical" in parameters.get("analysis_type", ""):
        tools.append("get_historic_observations")
    
    return {
        "strategy": "sequential",
        "tools": tools,
        "categories": ["species", "pipeline"],
        "confidence": confidence
    }
```

### Adding Response Formatting

1. **Add response type to `response_formatter.py`**:

```python
class ResponseType(Enum):
    # Existing types...
    TEMPORAL_ANALYSIS = "temporal_analysis"  # Covers migration, seasonal, historical
```

2. **Create comprehensive formatting function**:

```python
def _format_temporal_analysis(self, data: Dict, context: FormattingContext) -> str:
    """Format temporal analysis results with error handling."""
    try:
        # Determine analysis type from data
        analysis_type = self._detect_analysis_type(data)
        
        if context.experience_level == "beginner":
            return self._format_simple_temporal(data, analysis_type)
        elif context.experience_level == "expert":
            return self._format_expert_temporal(data, analysis_type)
        else:
            return self._format_standard_temporal(data, analysis_type)
            
    except Exception as e:
        logger.error(f"Error formatting temporal analysis: {e}")
        return self._format_fallback_temporal(data)

def _format_simple_temporal(self, data: Dict, analysis_type: str) -> str:
    """Beginner-friendly temporal analysis formatting."""
    if analysis_type == "migration":
        return f"""
🦅 **Migration Timing for {data.get('species_name', 'your species')}**

**Best time to see them:** {data.get('peak_period', 'Spring migration')}
**Where to look:** {data.get('best_locations', 'Various locations')}
**What to expect:** Migration typically lasts {data.get('duration', '2-3 weeks')}

💡 **Tip:** Early morning hours (6-10 AM) are usually best for spotting migrating birds!
        """
    # Handle other analysis types...
```

3. **Add to response router with error handling**:

```python
elif response_type == ResponseType.TEMPORAL_ANALYSIS:
    try:
        return self._format_temporal_analysis(results, context)
    except Exception as e:
        logger.error(f"Temporal analysis formatting failed: {e}")
        return self._format_generic_results(results, context)
```

## Testing Strategy

### Unit Testing

Test individual components with comprehensive error scenarios:

```python
def test_migration_analysis_handler():
    """Test migration analysis with various scenarios."""
    handler = PipelineHandlers()
    
    # Test successful case
    result = await handler.get_migration_analysis(
        species_codes=["amro"],
        region="US-MA",
        migration_season="spring"
    )
    
    assert result["success"]
    assert "migration_analysis" in result
    assert "confidence_metrics" in result

def test_migration_analysis_validation_errors():
    """Test validation error handling."""
    handler = PipelineHandlers()
    
    # Test empty species list
    result = await handler.get_migration_analysis(
        species_codes=[],
        region="US-MA"
    )
    
    assert not result["success"]
    assert "error_code" in result
    assert result["error_code"] == "INVALID_INPUT"

def test_migration_analysis_circuit_breaker():
    """Test circuit breaker activation."""
    handler = PipelineHandlers()
    
    # Simulate repeated failures
    with patch.object(handler.ebird_api, 'get_historical_observations', side_effect=APIError):
        for _ in range(6):  # Exceed failure threshold
            await handler.get_migration_analysis(["amro"], "US-MA")
        
        # Next call should trigger circuit breaker
        result = await handler.get_migration_analysis(["amro"], "US-MA")
        assert result["error_code"] == "CIRCUIT_BREAKER_OPEN"
```

### Integration Testing

Test complete workflows across tool categories:

```python
@pytest.mark.integration
async def test_temporal_analysis_workflow(mcp_server):
    """Test complete temporal analysis workflow."""
    # Test species validation → migration analysis chain
    species_result = await mcp_server.call_tool(
        "validate_species", 
        {"species_names": ["American Robin"]}
    )
    
    assert species_result["success"]
    
    # Use validated species for migration analysis
    species_codes = [s["species_code"] for s in species_result["validated_species"]]
    migration_result = await mcp_server.call_tool(
        "get_migration_analysis",
        {
            "species_codes": species_codes,
            "region": "US-MA",
            "migration_season": "spring"
        }
    )
    
    assert migration_result["success"]
    assert "migration_analysis" in migration_result
    assert "confidence_metrics" in migration_result

@pytest.mark.integration
async def test_cross_category_workflow(mcp_server):
    """Test workflow spanning multiple tool categories."""
    # Species (validation) → Location (region details) → Pipeline (temporal analysis)
    workflow_results = {}
    
    # Step 1: Species validation
    workflow_results["species"] = await mcp_server.call_tool(
        "validate_species", {"species_names": ["Yellow Warbler"]}
    )
    
    # Step 2: Region analysis
    workflow_results["region"] = await mcp_server.call_tool(
        "get_region_details", {"region": "US-MA"}
    )
    
    # Step 3: Temporal analysis
    workflow_results["temporal"] = await mcp_server.call_tool(
        "get_seasonal_trends", {
            "region": "US-MA",
            "species_codes": ["yewwar"],
            "years": 3
        }
    )
    
    # Verify all steps succeeded
    for step, result in workflow_results.items():
        assert result["success"], f"Step {step} failed: {result}"
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
- Use descriptive names reflecting tool categories

### Error Handling

Use the comprehensive error handling framework:

```python
@validate_parameters
@handle_errors
@circuit_breaker
async def my_handler_method(self, param1: str, param2: int) -> Dict:
    """Handler with comprehensive error handling."""
    try:
        # Input validation (automatic via decorator)
        
        # Business logic with specific error handling
        result = await self.api_call(param1, param2)
        
        # Data processing with fallback
        processed = self._process_with_fallback(result)
        
        return {"success": True, "data": processed}
        
    except ValidationError as e:
        return self.error_handler.handle_validation_error(e)
    except RateLimitError as e:
        # Automatic retry handled by decorator
        return self.error_handler.handle_rate_limit_error(e)
    except APIError as e:
        return self.error_handler.handle_api_error(e)
    except Exception as e:
        return self.error_handler.handle_unexpected_error(e)
```

### Tool Organization

```python
# Organize tools by logical categories
SPECIES_TOOLS = [...]     # Species validation and info
LOCATION_TOOLS = [...]    # Geographic analysis
PIPELINE_TOOLS = [...]    # Data processing and analysis
PLANNING_TOOLS = [...]    # Trip planning
ADVISORY_TOOLS = [...]    # Expert advice
COMMUNITY_TOOLS = [...]   # Social features

# Use consistent naming conventions
# get_* for data retrieval
# validate_* for validation
# generate_* for creation
# analyze_* for analysis
```

### Testing

- Write tests for new features across all tool categories
- Maintain > 80% code coverage including error paths
- Use meaningful test names describing scenarios
- Test edge cases, validation errors, and API failures
- Test circuit breaker activation and recovery
- Test graceful degradation scenarios
- Include performance tests for batch operations

```python
# Test naming convention examples
def test_get_migration_analysis_success_case():
    pass

def test_get_migration_analysis_validation_error_empty_species():
    pass

def test_get_migration_analysis_api_timeout_with_retry():
    pass

def test_get_migration_analysis_circuit_breaker_activation():
    pass
```

### Documentation

- Update docstrings for new code with error handling details
- Add examples for complex features showing tool category interactions
- Keep README current with accurate tool counts (32 tools, 6 categories)
- Document breaking changes and migration paths
- Update API reference with new tools and enhanced error responses
- Document new error codes and recovery strategies

## Resources

### Internal Documentation
- [Architecture](architecture.md) - System design details
- [API Reference](api-reference.md) - Tool documentation
- [Testing Guide](../tests/README.md) - Testing framework

### External Resources
- [PocketFlow Documentation](https://github.com/PocketFlow/docs)
- [eBird API Documentation](https://documenter.getpostman.com/view/664302/S1ENwy59)
- [MCP Specification](https://modelcontextprotocol.io/docs)
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Error Handling Best Practices](https://docs.python.org/3/tutorial/errors.html)

### Getting Help
- Check existing issues on GitHub
- Review test files for examples
- Consult architecture documentation
- Ask in project discussions