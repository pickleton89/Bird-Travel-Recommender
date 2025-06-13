# Bird Travel Recommender Configuration Guide

This guide covers all configuration options for the Bird Travel Recommender system.

## Table of Contents

- [Environment Variables](#environment-variables)
- [Configuration Files](#configuration-files)
- [API Configuration](#api-configuration)
- [Performance Tuning](#performance-tuning)
- [Logging Configuration](#logging-configuration)
- [MCP Server Configuration](#mcp-server-configuration)

## Environment Variables

### Required API Keys

Create a `.env` file in the project root with these required keys:

```bash
# OpenAI API Configuration
OPENAI_API_KEY=sk-...your-key-here...

# eBird API Configuration  
EBIRD_API_KEY=...your-key-here...
```

### Optional Configuration

```bash
# Model Configuration
OPENAI_MODEL=gpt-4o-mini          # Default: gpt-4o-mini
OPENAI_TEMPERATURE=0.7            # Default: 0.7 (0.0-2.0)
OPENAI_MAX_TOKENS=2000            # Default: 2000

# API Timeouts (seconds)
OPENAI_TIMEOUT=30                 # Default: 30
EBIRD_TIMEOUT=20                  # Default: 20
DEFAULT_REQUEST_TIMEOUT=15        # Default: 15

# Performance Settings
MAX_CONCURRENT_REQUESTS=5         # Default: 5
BATCH_SIZE=10                     # Default: 10
CACHE_TTL_SECONDS=900            # Default: 900 (15 minutes)

# Logging
LOG_LEVEL=INFO                    # Default: INFO (DEBUG|INFO|WARNING|ERROR)
LOG_FORMAT=simple                 # Default: simple (simple|detailed|json)
LOG_FILE=bird_travel.log         # Default: None (console only)

# Geographic Defaults
DEFAULT_SEARCH_RADIUS_KM=50       # Default: 50
DEFAULT_CLUSTER_RADIUS_KM=15      # Default: 15
MAX_ROUTE_LOCATIONS=8             # Default: 8

# Data Settings
EBIRD_DAYS_BACK=14               # Default: 14 (max: 30)
MIN_OBSERVATION_COUNT=1          # Default: 1
INCLUDE_PROVISIONAL=true         # Default: true

# Development
DEBUG_MODE=false                 # Default: false
MOCK_API_CALLS=false            # Default: false
PROFILE_PERFORMANCE=false        # Default: false
```

## Configuration Files

### Main Configuration Files

1. **`.env`** - Environment variables (git-ignored)
2. **`.env.example`** - Template for environment variables
3. **`pyproject.toml`** - Project dependencies and metadata
4. **`pytest.ini`** - Test configuration
5. **`mcp_config.json`** - MCP server configuration

### MCP Configuration Files

Different configurations for different environments:

```bash
src/bird_travel_recommender/mcp/config/
├── base.json        # Local/default configuration
├── development.json # Development with debug logging
└── production.json  # Production optimized settings
```

## API Configuration

### OpenAI API Settings

Configure OpenAI behavior in `src/bird_travel_recommender/utils/call_llm.py`:

```python
# Model selection
model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Temperature (creativity)
# 0.0 = Deterministic, 2.0 = Very creative
temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))

# Response length
max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "2000"))

# Timeout settings
timeout = int(os.getenv("OPENAI_TIMEOUT", "30"))
```

### eBird API Settings

Configure eBird API in `src/bird_travel_recommender/utils/ebird_api.py`:

```python
# Base configuration
EBIRD_BASE_URL = "https://api.ebird.org/v2"
DEFAULT_TIMEOUT = int(os.getenv("EBIRD_TIMEOUT", "20"))

# Request defaults
DEFAULT_DAYS_BACK = int(os.getenv("EBIRD_DAYS_BACK", "14"))
INCLUDE_PROVISIONAL = os.getenv("INCLUDE_PROVISIONAL", "true").lower() == "true"

# Rate limiting
RATE_LIMIT_REQUESTS = 750  # Per hour with auth
RATE_LIMIT_WINDOW = 3600   # 1 hour in seconds
```

### API Rate Limiting

```python
# Configure rate limiting behavior
RATE_LIMIT_STRATEGY = os.getenv("RATE_LIMIT_STRATEGY", "exponential_backoff")
# Options: exponential_backoff, fixed_delay, adaptive

INITIAL_RETRY_DELAY = float(os.getenv("INITIAL_RETRY_DELAY", "1.0"))
MAX_RETRY_DELAY = float(os.getenv("MAX_RETRY_DELAY", "60.0"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
```

## Performance Tuning

### Parallel Processing

```bash
# BatchNode configuration
MAX_WORKERS=5                    # Concurrent API calls
CHUNK_SIZE=50                    # Items per batch

# ThreadPoolExecutor settings
THREAD_POOL_SIZE=10              # Thread pool size
QUEUE_SIZE=100                   # Task queue limit
```

### Caching Configuration

```bash
# Cache settings
ENABLE_CACHE=true                # Enable/disable caching
CACHE_BACKEND=memory             # Options: memory, redis, file
CACHE_SIZE_MB=100                # Maximum cache size

# Cache TTL by data type (seconds)
TAXONOMY_CACHE_TTL=86400         # 24 hours
OBSERVATION_CACHE_TTL=900        # 15 minutes  
HOTSPOT_CACHE_TTL=3600          # 1 hour
```

### Memory Management

```bash
# Memory limits
MAX_MEMORY_MB=2048               # Maximum memory usage
GC_THRESHOLD=1000                # Garbage collection threshold

# Data limits
MAX_OBSERVATIONS_PER_SPECIES=1000
MAX_HOTSPOTS_PER_REGION=500
MAX_ROUTE_COMPUTATION_TIME=30    # seconds
```

## Logging Configuration

### Log Levels

```python
# Set via LOG_LEVEL environment variable
DEBUG     # Detailed debugging information
INFO      # General information and progress
WARNING   # Warning messages
ERROR     # Error messages only
CRITICAL  # Critical errors only
```

### Log Formats

```bash
# Simple format (default)
2024-03-15 10:30:45 INFO: Processing 5 species...

# Detailed format
2024-03-15 10:30:45.123 [MainThread] INFO utils.ebird_api:123 - Processing 5 species...

# JSON format (for log aggregation)
{"timestamp": "2024-03-15T10:30:45.123Z", "level": "INFO", "message": "Processing 5 species..."}
```

### Custom Logging Configuration

Create `logging_config.py`:

```python
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
        'detailed': {
            'format': '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'standard',
            'stream': 'ext://sys.stdout'
        },
        'file': {
            'class': 'logging.FileHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'filename': 'bird_travel.log'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'file']
    }
}
```

## MCP Server Configuration

### Development Configuration

`src/bird_travel_recommender/mcp/config/development.json`:

```json
{
  "mcpServers": {
    "bird-travel-recommender": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "src/bird_travel_recommender/mcp/server.py"
      ],
      "env": {
        "LOG_LEVEL": "DEBUG",
        "CACHE_TTL_SECONDS": "300",
        "MOCK_API_CALLS": "false",
        "PROFILE_PERFORMANCE": "true"
      }
    }
  }
}
```

### Production Configuration

`src/bird_travel_recommender/mcp/config/production.json`:

```json
{
  "mcpServers": {
    "bird-travel-recommender": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "src/bird_travel_recommender/mcp/server.py"
      ],
      "env": {
        "LOG_LEVEL": "WARNING",
        "CACHE_TTL_SECONDS": "900",
        "MAX_CONCURRENT_REQUESTS": "10",
        "ENABLE_CACHE": "true",
        "PROFILE_PERFORMANCE": "false"
      }
    }
  }
}
```

### Local Configuration

`src/bird_travel_recommender/mcp/config/base.json`:

```json
{
  "mcpServers": {
    "bird-travel-recommender": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "src/bird_travel_recommender/mcp/server.py"
      ],
      "env": {
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

## MCP Tools Configuration

### Tool Category Settings

Configure behavior for the 32 MCP tools across 6 categories:

```bash
# Species Tools (2 tools)
SPECIES_VALIDATION_TIMEOUT=10        # Species name validation timeout
ENABLE_FUZZY_SPECIES_MATCHING=true   # Allow approximate name matching
MAX_SPECIES_PER_REQUEST=50           # Maximum species to validate at once

# Location Tools (12 tools)  
LOCATION_SEARCH_RADIUS_MAX=200       # Maximum search radius (km)
ELEVATION_DATA_PRECISION=10          # Elevation data accuracy (meters)
ADJACENT_REGIONS_LIMIT=10            # Max neighboring regions to return
HOTSPOT_RANKING_ALGORITHM=weighted   # Options: weighted, simple, ml_based

# Pipeline Tools (12 tools)
PIPELINE_BATCH_SIZE=100              # Items processed per batch
TEMPORAL_ANALYSIS_YEARS_MAX=10       # Maximum years for trend analysis
MIGRATION_DATA_CACHE_HOURS=24        # Cache migration patterns (hours)
SEASONAL_TRENDS_SMOOTHING=0.3        # Smoothing factor for trend analysis

# Planning Tools (2 tools)
MAX_TRIP_DURATION_DAYS=30           # Maximum trip length
ITINERARY_DETAIL_LEVEL=standard     # Options: minimal, standard, detailed
ROUTE_OPTIMIZATION_ALGORITHM=2opt   # Options: 2opt, genetic, greedy

# Advisory Tools (1 tool)
ADVISORY_LLM_FALLBACK=true          # Use rule-based advice if LLM fails
ADVISORY_RESPONSE_LENGTH=medium     # Options: short, medium, long, adaptive

# Community Tools (3 tools)
COMMUNITY_DATA_FRESHNESS_HOURS=6    # How fresh community data must be
USER_STATS_PRIVACY_LEVEL=public     # Options: private, friends, public
CHECKLIST_DETAILS_LIMIT=100         # Max checklists to analyze
```

### Enhanced Error Handling Configuration

Configure the comprehensive error handling framework:

```bash
# Circuit Breaker Settings
CIRCUIT_BREAKER_ENABLED=true        # Enable circuit breaker pattern
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5 # Failures before opening circuit
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60 # Seconds before attempting recovery
CIRCUIT_BREAKER_HALF_OPEN_CALLS=3   # Test calls in half-open state

# Retry Logic Configuration
RETRY_ENABLED=true                   # Enable automatic retries
RETRY_MAX_ATTEMPTS=3                # Maximum retry attempts
RETRY_INITIAL_DELAY=1.0             # Initial retry delay (seconds)
RETRY_MAX_DELAY=16.0                # Maximum retry delay (seconds)  
RETRY_BACKOFF_FACTOR=2.0            # Exponential backoff multiplier
RETRY_JITTER=true                   # Add randomness to delays

# Graceful Degradation
ENABLE_FALLBACK_RESPONSES=true      # Use fallback data when APIs fail
FALLBACK_TO_CACHE=true              # Use stale cache on API failures
FALLBACK_TO_MOCK_DATA=false         # Use mock data in emergencies
PARTIAL_RESULTS_ACCEPTABLE=true     # Return partial results on errors

# Error Response Configuration
ERROR_INCLUDE_RETRY_INFO=true       # Include retry attempt info in errors
ERROR_INCLUDE_SUGGESTIONS=true      # Include suggested fixes in errors
ERROR_INCLUDE_TIMESTAMP=true        # Include error timestamp
ERROR_MASK_SENSITIVE_DATA=true      # Hide sensitive info in error messages
```

### Tool Performance Configuration

Configure performance settings for all 32 tools:

```bash
# Concurrent Tool Execution
TOOL_EXECUTION_MODE=smart            # Options: sequential, parallel, smart
MAX_CONCURRENT_TOOLS=8               # Max tools running simultaneously
TOOL_EXECUTION_TIMEOUT=120           # Default tool timeout (seconds)
TOOL_QUEUE_SIZE=50                   # Maximum queued tool requests

# Category-Specific Timeouts
SPECIES_TOOLS_TIMEOUT=15             # Species validation timeout
LOCATION_TOOLS_TIMEOUT=30            # Location analysis timeout  
PIPELINE_TOOLS_TIMEOUT=45            # Data processing timeout
PLANNING_TOOLS_TIMEOUT=60            # Trip planning timeout
ADVISORY_TOOLS_TIMEOUT=25            # LLM advice timeout
COMMUNITY_TOOLS_TIMEOUT=20           # Community data timeout

# Tool Caching Strategy
ENABLE_TOOL_RESULT_CACHING=true      # Cache tool results
TOOL_CACHE_SIZE_MB=250               # Tool cache size limit
TOOL_CACHE_TTL_STRATEGY=adaptive     # Options: fixed, adaptive, category_based

# Category-Specific Cache TTL (seconds)
SPECIES_CACHE_TTL=86400              # 24 hours (stable data)
LOCATION_CACHE_TTL=3600              # 1 hour (semi-stable)
PIPELINE_CACHE_TTL=900               # 15 minutes (dynamic data)
PLANNING_CACHE_TTL=1800              # 30 minutes (personalized)
ADVISORY_CACHE_TTL=7200              # 2 hours (advice patterns)
COMMUNITY_CACHE_TTL=300              # 5 minutes (real-time data)
```

## Advanced Configuration

### Tool Orchestration Settings

Configure how the 32 tools work together:

```bash
# Smart Tool Selection
ENABLE_INTELLIGENT_TOOL_SELECTION=true  # AI-powered tool selection
TOOL_SELECTION_CONFIDENCE_THRESHOLD=0.8 # Minimum confidence for tool selection
TOOL_DEPENDENCY_CHECKING=true           # Verify tool dependencies

# Cross-Category Workflows
ENABLE_CROSS_CATEGORY_WORKFLOWS=true    # Allow multi-category operations
WORKFLOW_OPTIMIZATION=true              # Optimize tool execution order
WORKFLOW_PARALLELIZATION=smart          # Options: none, aggressive, smart

# Tool Result Integration
RESULT_MERGING_STRATEGY=intelligent     # Options: simple, weighted, intelligent
RESULT_CONFLICT_RESOLUTION=llm_mediated # Options: first_wins, voting, llm_mediated
ENABLE_RESULT_VALIDATION=true           # Validate tool result consistency
```

### Custom Model Configuration

For different OpenAI models:

```bash
# GPT-4 (higher quality, slower, more expensive)
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=4000

# GPT-3.5 (faster, cheaper)
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_MAX_TOKENS=1000

# GPT-4o (multimodal, balanced)
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=2000
```

### Regional Configuration

```bash
# eBird regional settings
DEFAULT_REGION=US                # Default country code
REGION_FORMAT=subnational1       # Options: country, subnational1, subnational2
ACCEPT_LANG=en                   # Language for location names

# Coordinate system
COORDINATE_SYSTEM=WGS84          # GPS standard
DISTANCE_UNITS=km                # Options: km, mi
```

### Feature Flags

```bash
# Enable/disable features
ENABLE_LLM_ENHANCEMENT=true      # LLM-powered enhancements
ENABLE_HOTSPOT_INTEGRATION=true  # eBird hotspot data
ENABLE_ROUTE_OPTIMIZATION=true   # TSP route optimization
ENABLE_WEATHER_INTEGRATION=false # Future feature
ENABLE_PHOTO_INTEGRATION=false   # Future feature

# Experimental features
ENABLE_MIGRATION_PREDICTION=false
ENABLE_RARITY_SCORING=false
ENABLE_SOCIAL_FEATURES=false
```

### Error Handling Configuration

```bash
# Error behavior
ON_API_ERROR=fallback            # Options: fallback, retry, fail
ON_LLM_ERROR=use_template        # Options: use_template, retry, fail
ON_RATE_LIMIT=wait               # Options: wait, queue, fail

# Fallback behavior
USE_MOCK_DATA_ON_ERROR=false     # Use mock data when APIs fail
USE_CACHED_ON_ERROR=true         # Use stale cache on errors
PARTIAL_RESULTS_ON_ERROR=true    # Return partial results
```

## Security Configuration

### API Key Security

```bash
# Never commit these to version control!
# Use environment variables or secure key management

# Key rotation reminder (days)
API_KEY_ROTATION_REMINDER=90

# Key validation on startup
VALIDATE_KEYS_ON_START=true

# Mask keys in logs
MASK_SENSITIVE_DATA=true
```

### Request Security

```bash
# Input validation
MAX_INPUT_LENGTH=1000            # Maximum query length
SANITIZE_USER_INPUT=true         # Clean user input
VALIDATE_COORDINATES=true        # Verify GPS coordinates

# Output filtering
FILTER_SENSITIVE_LOCATIONS=true  # Hide sensitive bird locations
HIDE_EXACT_COORDINATES=false     # Round coordinates
```

## Deployment-Specific Configuration

### Docker Configuration

```dockerfile
# Environment variables in Docker
ENV LOG_LEVEL=INFO
ENV OPENAI_TIMEOUT=45
ENV MAX_CONCURRENT_REQUESTS=10
```

### Kubernetes ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: bird-travel-config
data:
  LOG_LEVEL: "INFO"
  CACHE_TTL_SECONDS: "900"
  MAX_CONCURRENT_REQUESTS: "10"
```

### Cloud Platform Variables

```bash
# AWS
AWS_REGION=us-east-1
AWS_LAMBDA_TIMEOUT=300

# Google Cloud
GCP_PROJECT_ID=bird-travel-project
GCP_REGION=us-central1

# Azure
AZURE_REGION=eastus
AZURE_FUNCTION_TIMEOUT=300
```

## Monitoring Configuration

```bash
# Metrics collection
ENABLE_METRICS=true
METRICS_ENDPOINT=http://localhost:9090
METRICS_INTERVAL=60              # seconds

# Health checks
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_PORT=8080
HEALTH_CHECK_PATH=/health

# Performance monitoring
TRACK_API_LATENCY=true
TRACK_MEMORY_USAGE=true
TRACK_ERROR_RATES=true
```

## Troubleshooting Configuration

### Debug Settings

```bash
# Enhanced debugging
DEBUG_MODE=true
TRACE_API_CALLS=true
LOG_REQUEST_BODIES=true
LOG_RESPONSE_BODIES=true
SAVE_DEBUG_FILES=true
DEBUG_OUTPUT_DIR=./debug

# Performance profiling
PROFILE_PERFORMANCE=true
PROFILE_OUTPUT_DIR=./profiles
PROFILE_TOP_FUNCTIONS=20
```

### Testing Configuration

```bash
# Test environment
TEST_ENV=true
USE_TEST_DATABASE=true
MOCK_EXTERNAL_APIS=true
TEST_API_KEY=test-key-123

# Test data
TEST_DATA_DIR=./tests/data
GENERATE_TEST_REPORTS=true
TEST_COVERAGE_THRESHOLD=80
```

Remember to restart the application after changing configuration values for them to take effect.