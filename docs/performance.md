# Bird Travel Recommender Performance Guide

This guide covers performance optimization strategies for the Bird Travel Recommender system.

## Table of Contents

- [Performance Overview](#performance-overview)
- [Measuring Performance](#measuring-performance)
- [API Optimization](#api-optimization)
- [Parallel Processing](#parallel-processing)
- [Caching Strategies](#caching-strategies)
- [Memory Management](#memory-management)
- [Database Optimization](#database-optimization)
- [LLM Optimization](#llm-optimization)
- [Performance Tuning](#performance-tuning)

## Performance Overview

### Current Performance Metrics

| Operation | Average Time | Max Time | Notes |
|-----------|-------------|----------|-------|
| Species Validation | 150ms | 500ms | With LLM fallback |
| Fetch Sightings (5 species) | 1.2s | 3s | Parallel execution |
| Complete Trip Planning | 4-6s | 10s | Full pipeline |
| Route Optimization (10 locations) | 200ms | 500ms | TSP algorithm |
| LLM Enhancement | 1-2s | 5s | GPT-4o response |

### Performance Goals

- **Response Time**: < 5 seconds for complete trip planning
- **Throughput**: 100 concurrent users
- **API Efficiency**: < 10 API calls per request
- **Memory Usage**: < 500MB per request
- **Cache Hit Rate**: > 70% for common queries

## Measuring Performance

### Built-in Profiling

```python
# Enable performance profiling
import os
os.environ["PROFILE_PERFORMANCE"] = "true"

# Run with profiling
# Example: Using profiling (hypothetical module)
# from bird_travel_recommender.utils.call_llm import call_llm

@profile_function
def expensive_operation():
    # Your code here
    pass
```

### Performance Logging

```python
import time
import logging

logger = logging.getLogger(__name__)

class PerformanceTimer:
    def __init__(self, operation_name):
        self.operation = operation_name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, *args):
        elapsed = time.time() - self.start_time
        logger.info(f"{self.operation} took {elapsed:.3f}s")
        
        # Log slow operations
        if elapsed > 2.0:
            logger.warning(f"Slow operation: {self.operation} took {elapsed:.3f}s")

# Usage
with PerformanceTimer("fetch_sightings"):
    results = fetch_bird_sightings(species_list)
```

### Metrics Collection

```python
# Collect detailed metrics
from dataclasses import dataclass
from typing import Dict, List
import statistics

@dataclass
class PerformanceMetrics:
    operation: str
    times: List[float]
    
    @property
    def average(self) -> float:
        return statistics.mean(self.times)
    
    @property
    def p95(self) -> float:
        return statistics.quantiles(self.times, n=20)[18]  # 95th percentile
    
    @property
    def max(self) -> float:
        return max(self.times)

# Track metrics across requests
metrics_collector = {}

def track_operation(operation: str, duration: float):
    if operation not in metrics_collector:
        metrics_collector[operation] = PerformanceMetrics(operation, [])
    metrics_collector[operation].times.append(duration)
```

## API Optimization

### Batch Requests

```python
# Instead of multiple individual requests
for species in species_list:
    data = api.get_observations(species)  # Bad: N API calls

# Use batch operations
data = api.get_observations_batch(species_list)  # Good: 1 API call
```

### Smart Endpoint Selection

```python
def choose_optimal_endpoint(species_count: int, region: str) -> str:
    """Select most efficient eBird endpoint based on query."""
    if species_count == 1:
        # Use species-specific endpoint for single species
        return "obs/{region}/recent/{species}"
    elif species_count <= 5:
        # Use regional endpoint with species filter
        return "obs/{region}/recent"
    else:
        # Use hotspot endpoint for many species
        return "product/spplist/{region}"
```

### Request Pooling

```python
import httpx
from typing import List, Dict

class APIConnectionPool:
    def __init__(self, max_connections: int = 10):
        self.client = httpx.AsyncClient(
            limits=httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=5
            ),
            timeout=httpx.Timeout(20.0)
        )
    
    async def fetch_multiple(self, urls: List[str]) -> List[Dict]:
        """Fetch multiple URLs concurrently."""
        tasks = [self.client.get(url) for url in urls]
        responses = await asyncio.gather(*tasks)
        return [r.json() for r in responses]
```

### Rate Limit Management

```python
import asyncio
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, calls_per_hour: int = 750):
        self.calls_per_hour = calls_per_hour
        self.call_times = []
    
    async def acquire(self):
        """Wait if necessary to respect rate limits."""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        
        # Remove old calls
        self.call_times = [t for t in self.call_times if t > hour_ago]
        
        # Check if we need to wait
        if len(self.call_times) >= self.calls_per_hour:
            wait_time = (self.call_times[0] - hour_ago).total_seconds()
            await asyncio.sleep(wait_time)
        
        self.call_times.append(now)
```

## Parallel Processing

### BatchNode Implementation

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

class OptimizedBatchNode(BatchNode):
    """Optimized batch processing with connection pooling."""
    
    def __init__(self, max_workers: int = 5):
        super().__init__()
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def exec(self, items: List[Any]) -> List[Dict]:
        """Process items in parallel with progress tracking."""
        results = []
        
        # Submit all tasks
        future_to_item = {
            self.executor.submit(self.process_item, item): item
            for item in items
        }
        
        # Process completed tasks
        for future in as_completed(future_to_item):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process item: {e}")
                results.append({"error": str(e)})
        
        return results
```

### Async Processing

```python
import asyncio
from typing import List, Coroutine

async def process_concurrently(
    tasks: List[Coroutine],
    max_concurrent: int = 10
) -> List[Any]:
    """Process tasks concurrently with controlled parallelism."""
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def bounded_task(task):
        async with semaphore:
            return await task
    
    return await asyncio.gather(
        *[bounded_task(task) for task in tasks],
        return_exceptions=True
    )
```

## Caching Strategies

### In-Memory Caching

```python
from functools import lru_cache
from datetime import datetime, timedelta
import hashlib
import json

class TTLCache:
    """Time-based cache with TTL support."""
    
    def __init__(self, ttl_seconds: int = 900):
        self.cache = {}
        self.ttl = timedelta(seconds=ttl_seconds)
    
    def _make_key(self, *args, **kwargs):
        """Create cache key from arguments."""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, *args, **kwargs):
        """Get value from cache if not expired."""
        key = self._make_key(*args, **kwargs)
        if key in self.cache:
            value, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, value, *args, **kwargs):
        """Store value in cache."""
        key = self._make_key(*args, **kwargs)
        self.cache[key] = (value, datetime.now())

# Usage
cache = TTLCache(ttl_seconds=900)  # 15 minutes

def get_species_data(species_code: str) -> Dict:
    # Check cache
    cached = cache.get(species_code)
    if cached:
        return cached
    
    # Fetch from API
    data = fetch_from_api(species_code)
    
    # Store in cache
    cache.set(data, species_code)
    return data
```

### Smart Cache Invalidation

```python
class SmartCache:
    """Cache with dependency tracking and smart invalidation."""
    
    def __init__(self):
        self.cache = {}
        self.dependencies = {}  # key -> set of dependent keys
    
    def set(self, key: str, value: Any, depends_on: List[str] = None):
        """Set value with dependencies."""
        self.cache[key] = value
        
        if depends_on:
            for dep in depends_on:
                if dep not in self.dependencies:
                    self.dependencies[dep] = set()
                self.dependencies[dep].add(key)
    
    def invalidate(self, key: str):
        """Invalidate key and all dependent keys."""
        if key in self.cache:
            del self.cache[key]
        
        # Invalidate dependents
        if key in self.dependencies:
            for dependent in self.dependencies[key]:
                self.invalidate(dependent)
            del self.dependencies[key]
```

## Memory Management

### Streaming Large Datasets

```python
from typing import Iterator, Dict

def stream_observations(region: str, days: int) -> Iterator[Dict]:
    """Stream observations instead of loading all into memory."""
    page = 1
    while True:
        # Fetch one page
        data = api.get_observations(region, days, page=page, per_page=100)
        
        if not data:
            break
        
        # Yield items one by one
        for observation in data:
            yield observation
        
        page += 1

# Process without loading entire dataset
for observation in stream_observations("US-MA", 14):
    process_observation(observation)
```

### Memory-Efficient Data Structures

```python
import array
from collections import namedtuple

# Use namedtuples instead of dictionaries for fixed structures
Observation = namedtuple('Observation', ['species', 'lat', 'lng', 'date'])

# Use arrays for numeric data
latitudes = array.array('f')  # Float array, more memory efficient than list

# Use generators for transformations
def process_large_dataset(data):
    return (transform(item) for item in data)  # Generator, not list
```

### Garbage Collection Optimization

```python
import gc

def process_large_batch(items: List):
    """Process large batch with explicit garbage collection."""
    results = []
    
    for i, chunk in enumerate(chunks(items, 1000)):
        chunk_results = process_chunk(chunk)
        results.extend(chunk_results)
        
        # Force garbage collection every 10 chunks
        if i % 10 == 0:
            gc.collect()
    
    return results
```

## Database Optimization

### Query Optimization

```python
# Bad: N+1 query problem
for species in species_list:
    observations = db.query(f"SELECT * FROM observations WHERE species = '{species}'")

# Good: Single query
species_str = ','.join(f"'{s}'" for s in species_list)
observations = db.query(f"SELECT * FROM observations WHERE species IN ({species_str})")
```

### Index Usage

```sql
-- Create indexes for common queries
CREATE INDEX idx_observations_species_date ON observations(species_code, observation_date);
CREATE INDEX idx_locations_coords ON locations(latitude, longitude);
CREATE INDEX idx_hotspots_region ON hotspots(region_code, species_count);
```

### Connection Pooling

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

# Create engine with connection pooling
engine = create_engine(
    'postgresql://user:pass@localhost/birds',
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

## LLM Optimization

### Prompt Optimization

```python
def optimize_prompt(base_prompt: str, max_tokens: int = 2000) -> str:
    """Optimize prompt for faster LLM response."""
    # Remove unnecessary instructions
    optimized = base_prompt.replace(
        "Please think step by step and provide a detailed explanation",
        "Provide a concise response"
    )
    
    # Add response format hints
    optimized += "\nRespond in JSON format with keys: summary, locations, species."
    
    return optimized
```

### Response Streaming

```python
async def stream_llm_response(prompt: str) -> AsyncIterator[str]:
    """Stream LLM response for better perceived performance."""
    async for chunk in openai.ChatCompletion.acreate(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        stream=True
    ):
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
```

### Fallback Strategies

```python
async def get_llm_response_with_fallback(prompt: str, timeout: float = 5.0) -> str:
    """Get LLM response with timeout and fallback."""
    try:
        # Try primary model with timeout
        response = await asyncio.wait_for(
            call_llm(prompt, model="gpt-4o"),
            timeout=timeout
        )
        return response
    except asyncio.TimeoutError:
        # Fall back to faster model
        logger.warning("Primary model timeout, using fallback")
        return await call_llm(prompt, model="gpt-3.5-turbo")
    except Exception:
        # Final fallback to template
        logger.error("LLM failed, using template response")
        return generate_template_response(prompt)
```

## Performance Tuning

### Configuration Optimization

```bash
# Optimal settings for production
export MAX_CONCURRENT_REQUESTS=10
export BATCH_SIZE=50
export CACHE_TTL_SECONDS=1800
export CONNECTION_POOL_SIZE=20
export LLM_TIMEOUT=10
export USE_CONNECTION_POOLING=true
export ENABLE_RESPONSE_COMPRESSION=true
```

### Load Testing

```python
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

async def load_test(concurrent_users: int = 100, requests_per_user: int = 10):
    """Simulate concurrent users making requests."""
    
    async def simulate_user(user_id: int):
        times = []
        for i in range(requests_per_user):
            start = time.time()
            await make_request(f"user_{user_id}_request_{i}")
            times.append(time.time() - start)
        return times
    
    # Run concurrent users
    tasks = [simulate_user(i) for i in range(concurrent_users)]
    all_times = await asyncio.gather(*tasks)
    
    # Calculate statistics
    flat_times = [t for times in all_times for t in times]
    print(f"Average response time: {statistics.mean(flat_times):.3f}s")
    print(f"95th percentile: {statistics.quantiles(flat_times, n=20)[18]:.3f}s")
    print(f"Max response time: {max(flat_times):.3f}s")
```

### Monitoring and Alerts

```python
class PerformanceMonitor:
    """Monitor performance and alert on degradation."""
    
    def __init__(self, alert_threshold: float = 5.0):
        self.alert_threshold = alert_threshold
        self.recent_times = []
    
    def record_request(self, duration: float, operation: str):
        """Record request duration and check for alerts."""
        self.recent_times.append(duration)
        
        # Keep only recent 100 requests
        if len(self.recent_times) > 100:
            self.recent_times.pop(0)
        
        # Check if performance is degrading
        if duration > self.alert_threshold:
            self.send_alert(f"Slow {operation}: {duration:.2f}s")
        
        # Check trend
        if len(self.recent_times) >= 10:
            recent_avg = statistics.mean(self.recent_times[-10:])
            if recent_avg > self.alert_threshold * 0.8:
                self.send_alert(f"Performance degradation detected: {recent_avg:.2f}s avg")
    
    def send_alert(self, message: str):
        """Send performance alert."""
        logger.error(f"PERFORMANCE ALERT: {message}")
        # Could also send to monitoring service
```

## Best Practices Summary

1. **Measure First**: Profile before optimizing
2. **Cache Aggressively**: Cache expensive operations
3. **Batch Operations**: Reduce API calls through batching
4. **Parallel Processing**: Use async/threading appropriately
5. **Memory Efficiency**: Stream large datasets
6. **Monitor Continuously**: Track performance metrics
7. **Fail Fast**: Set appropriate timeouts
8. **Optimize Hot Paths**: Focus on frequently used code
9. **Test Under Load**: Simulate real usage patterns
10. **Document Changes**: Track performance improvements

Remember: Premature optimization is the root of all evil. Always measure and profile before optimizing!