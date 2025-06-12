# Bird Travel Recommender Troubleshooting Guide

This guide helps diagnose and resolve common issues with the Bird Travel Recommender system.

## Table of Contents

- [Common Issues](#common-issues)
- [API Key Problems](#api-key-problems)
- [Installation Issues](#installation-issues)
- [Runtime Errors](#runtime-errors)
- [Performance Issues](#performance-issues)
- [MCP Server Issues](#mcp-server-issues)
- [Testing Problems](#testing-problems)
- [Debug Strategies](#debug-strategies)

## Common Issues

### System Won't Start

**Symptom**: Application crashes on startup

**Solutions**:

1. **Check Python version**:
```bash
python --version  # Should be 3.9 or higher
```

2. **Verify dependencies**:
```bash
uv sync
uv pip list  # Check all packages installed
```

3. **Check environment variables**:
```bash
python check_api_keys.py
```

4. **Look for error messages**:
```bash
uv run python main.py --debug
```

### No Results Returned

**Symptom**: Queries return empty results

**Possible Causes**:
- Invalid species names
- No recent sightings in area
- API rate limits reached
- Network connectivity issues

**Debug Steps**:
```python
# Enable debug logging
import os
os.environ["LOG_LEVEL"] = "DEBUG"

# Check API responses
from bird_travel_recommender.utils.ebird_api import EBirdClient
client = EBirdClient()
response = client.get_recent_observations("US-MA")
print(f"API Response: {response}")
```

## API Key Problems

### Invalid API Key Errors

**OpenAI API Key Issues**:
```
Error: Invalid API key provided: sk-...
```

**Solutions**:
1. Verify key format (should start with `sk-`)
2. Check key hasn't expired
3. Ensure key has proper permissions
4. Test directly:
```python
import openai
openai.api_key = "your-key"
response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "test"}]
)
```

**eBird API Key Issues**:
```
Error: 403 Forbidden - Invalid eBird API key
```

**Solutions**:
1. Get new key from https://ebird.org/api/keygen
2. Check for extra spaces in .env file
3. Test with curl:
```bash
curl -H "X-eBirdApiToken: YOUR_KEY" \
  "https://api.ebird.org/v2/data/obs/US-MA/recent"
```

### Environment Variable Not Loading

**Symptom**: "API key not found" despite .env file

**Solutions**:

1. **Check file location**:
```bash
ls -la .env  # Should be in project root
cat .env     # Verify contents
```

2. **Check file format**:
```bash
# Correct format (no spaces around =)
OPENAI_API_KEY=sk-...
EBIRD_API_KEY=...

# Wrong format
OPENAI_API_KEY = sk-...  # Spaces cause issues
```

3. **Force reload**:
```python
from dotenv import load_dotenv
load_dotenv(override=True)
```

## Installation Issues

### UV Package Manager Problems

**Symptom**: `uv: command not found`

**Solution**:
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv
```

### Dependency Conflicts

**Symptom**: Package version conflicts

**Solutions**:

1. **Clean install**:
```bash
rm -rf .venv
rm uv.lock
uv venv
uv sync
```

2. **Check Python version compatibility**:
```bash
uv venv --python 3.9  # Specify Python version
```

3. **Update dependencies**:
```bash
uv update
```

### Import Errors

**Symptom**: `ModuleNotFoundError`

**Solutions**:

1. **Ensure virtual environment is activated**:
```bash
source .venv/bin/activate  # Unix/macOS
# or
.venv\Scripts\activate  # Windows
```

2. **Check PYTHONPATH**:
```python
import sys
print(sys.path)  # Should include project directory
```

3. **Add project to path**:
```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
```

## Runtime Errors

### LLM Timeout Errors

**Symptom**: "OpenAI API request timed out"

**Solutions**:

1. **Increase timeout**:
```python
# In src/bird_travel_recommender/utils/call_llm.py or environment
os.environ["OPENAI_TIMEOUT"] = "60"  # 60 seconds
```

2. **Use simpler model**:
```python
response = call_llm(prompt, model="gpt-3.5-turbo")  # Faster
```

3. **Implement retry logic**:
```python
import time

for attempt in range(3):
    try:
        response = call_llm(prompt)
        break
    except TimeoutError:
        if attempt < 2:
            time.sleep(2 ** attempt)  # Exponential backoff
            continue
        raise
```

### Memory Errors

**Symptom**: "MemoryError" or system becomes unresponsive

**Solutions**:

1. **Process in batches**:
```python
def process_large_dataset(items, batch_size=100):
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        process_batch(batch)
        
        # Force garbage collection
        import gc
        gc.collect()
```

2. **Limit concurrent operations**:
```python
# In BatchNode
max_workers = 3  # Reduce from default 5
```

3. **Stream data**:
```python
# Instead of loading all data
all_data = fetch_all_observations()  # Bad

# Stream data
for observation in stream_observations():  # Good
    process(observation)
```

### Geocoding Errors

**Symptom**: "Invalid coordinates" or distance calculation fails

**Solutions**:

1. **Validate coordinates**:
```python
def validate_coordinates(lat: float, lng: float) -> bool:
    return -90 <= lat <= 90 and -180 <= lng <= 180

# Usage
if not validate_coordinates(lat, lng):
    raise ValueError(f"Invalid coordinates: {lat}, {lng}")
```

2. **Handle missing coordinates**:
```python
def safe_distance(lat1, lng1, lat2, lng2):
    try:
        return haversine_distance(lat1, lng1, lat2, lng2)
    except (TypeError, ValueError):
        logger.warning(f"Invalid coordinates for distance calculation")
        return float('inf')  # Treat as very far
```

## Performance Issues

### Slow Response Times

**Symptom**: Requests take > 10 seconds

**Diagnosis**:
```python
# Enable performance profiling
os.environ["PROFILE_PERFORMANCE"] = "true"
os.environ["LOG_LEVEL"] = "DEBUG"

# Add timing logs
import time
start = time.time()
result = expensive_operation()
print(f"Operation took {time.time() - start:.2f}s")
```

**Solutions**:

1. **Enable caching**:
```python
os.environ["ENABLE_CACHE"] = "true"
os.environ["CACHE_TTL_SECONDS"] = "1800"  # 30 minutes
```

2. **Reduce API calls**:
```python
# Batch species validation
species_list = ["cardinal", "blue jay", "robin"]
validated = validate_species_batch(species_list)  # One call
```

3. **Optimize data processing**:
```python
# Use set for lookups instead of list
target_species = set(["norcar", "blujay"])  # O(1) lookup
if observation["species_code"] in target_species:
    process(observation)
```

### High Memory Usage

**Symptom**: System using > 1GB RAM

**Solutions**:

1. **Monitor memory usage**:
```python
import psutil
import os

process = psutil.Process(os.getpid())
print(f"Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB")
```

2. **Clear caches periodically**:
```python
# Add cache size limits
from functools import lru_cache

@lru_cache(maxsize=100)  # Limit cache size
def expensive_function(param):
    return compute(param)

# Clear cache when needed
expensive_function.cache_clear()
```

## MCP Server Issues

### Server Won't Start

**Symptom**: "Failed to start MCP server"

**Solutions**:

1. **Check port availability**:
```bash
lsof -i :3000  # Check if port is in use
```

2. **Validate configuration**:
```bash
python deploy_mcp.py development --validate-only
```

3. **Test server directly**:
```bash
uv run python src/bird_travel_recommender/mcp/server.py
```

### Claude Can't Connect

**Symptom**: "MCP server not found" in Claude

**Solutions**:

1. **Check configuration location**:
```bash
cat ~/.claude/mcp_servers.json
```

2. **Verify server is running**:
```bash
ps aux | grep mcp_server
```

3. **Check logs**:
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
uv run python src/bird_travel_recommender/mcp/server.py
```

### Tool Execution Failures

**Symptom**: "Tool execution failed" errors

**Debug Steps**:

1. **Test tool directly**:
```python
from bird_travel_recommender.mcp.server import BirdTravelMCPServer
server = BirdTravelMCPServer()

# Test specific tool
result = await server._handle_validate_species(
    species_names=["Northern Cardinal"]
)
print(result)
```

2. **Check tool registration**:
```python
# List registered tools
tools = await server.handle_list_tools()
for tool in tools:
    print(f"Tool: {tool.name}")
```

## Testing Problems

### Tests Failing

**Symptom**: pytest reports failures

**Solutions**:

1. **Run specific test**:
```bash
# Run single test for debugging
uv run pytest tests/test_validate_species_node.py -v -s
```

2. **Check test environment**:
```bash
# Use test environment variables
export MOCK_API_CALLS=true
export TEST_ENV=true
uv run pytest
```

3. **Update test data**:
```python
# Regenerate mock data if needed
from tests.conftest import generate_mock_data
generate_mock_data()
```

### Coverage Issues

**Symptom**: Low test coverage

**Solutions**:

1. **Generate coverage report**:
```bash
uv run pytest --cov=. --cov-report=html
open htmlcov/index.html  # View report
```

2. **Identify untested code**:
```bash
uv run pytest --cov=. --cov-report=term-missing
```

## Debug Strategies

### Enable Comprehensive Logging

```python
# debug_config.py
import logging
import sys

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('debug.log')
    ]
)

# Set specific module levels
logging.getLogger('bird_travel_recommender.utils.ebird_api').setLevel(logging.DEBUG)
logging.getLogger('httpx').setLevel(logging.INFO)  # Reduce noise
```

### Interactive Debugging

```python
# Add breakpoints
import pdb

def problematic_function(data):
    # ... some code ...
    pdb.set_trace()  # Debugger will stop here
    # ... more code ...

# Or use IPython for better experience
from IPython import embed

def debug_here():
    local_vars = locals()
    embed()  # Drops into IPython shell
```

### Request/Response Logging

```python
# Log all API interactions
import json

class DebugAPIClient(EBirdClient):
    def make_request(self, endpoint: str, params: dict = None):
        print(f"\n=== API Request ===")
        print(f"Endpoint: {endpoint}")
        print(f"Params: {json.dumps(params, indent=2)}")
        
        response = super().make_request(endpoint, params)
        
        print(f"\n=== API Response ===")
        print(f"Status: {response.status_code}")
        print(f"Body: {json.dumps(response.json(), indent=2)[:500]}...")
        
        return response
```

### Error Context Collection

```python
import traceback
import sys

def debug_wrapper(func):
    """Wrapper that captures full error context."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print("\n=== ERROR CONTEXT ===")
            print(f"Function: {func.__name__}")
            print(f"Args: {args}")
            print(f"Kwargs: {kwargs}")
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Message: {str(e)}")
            print("\n=== TRACEBACK ===")
            traceback.print_exc()
            print("\n=== LOCAL VARIABLES ===")
            frame = sys.exc_info()[2].tb_frame
            print(frame.f_locals)
            raise
    return wrapper
```

### Health Check Endpoint

```python
# Add health check for monitoring
from datetime import datetime

class HealthCheck:
    def __init__(self):
        self.start_time = datetime.now()
        self.request_count = 0
        self.error_count = 0
    
    def check(self) -> dict:
        """Return system health status."""
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        # Check critical components
        checks = {
            "uptime_seconds": uptime,
            "requests_processed": self.request_count,
            "errors": self.error_count,
            "api_keys_valid": self._check_api_keys(),
            "ebird_api_accessible": self._check_ebird_api(),
            "llm_accessible": self._check_llm(),
            "cache_working": self._check_cache()
        }
        
        checks["status"] = "healthy" if all(
            v for k, v in checks.items() 
            if k.endswith("_valid") or k.endswith("_accessible") or k.endswith("_working")
        ) else "degraded"
        
        return checks
```

## Getting Additional Help

1. **Check logs**: Always check debug.log and error messages
2. **Search issues**: Look for similar problems in GitHub issues
3. **Minimal reproduction**: Create smallest example that shows the problem
4. **System information**: Include Python version, OS, and package versions
5. **Ask for help**: Provide error messages, code snippets, and what you've tried

Remember: Most issues are related to API keys, dependencies, or network connectivity. Start with these common causes before diving deeper!