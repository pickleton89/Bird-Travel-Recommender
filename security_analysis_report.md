# Security Analysis Report: Input Validation and Sanitization
## Bird Travel Recommender

### Executive Summary

The comprehensive security analysis of the Bird Travel Recommender codebase reveals **significant input validation vulnerabilities** across all major modules. The application lacks systematic input validation, with no validation decorator or middleware in place. This creates multiple attack vectors for malicious users.

### Critical Findings

#### 1. **No Input Validation Framework**
- **Finding**: No validation decorator (`@validation_decorator`) exists in the codebase
- **Impact**: All handlers accept raw user input without validation
- **Risk Level**: CRITICAL
- **Affected Files**: All handler modules in `/src/bird_travel_recommender/mcp/handlers/`

#### 2. **Unvalidated Coordinate Inputs**
- **Finding**: Latitude/longitude values are passed directly to APIs without bounds checking
- **Location**: `location.py` handlers (lines 78-79, 119-120, 172-173)
- **Risk**: 
  - Potential for invalid coordinates causing API errors
  - No validation that lat is between -90 and 90
  - No validation that lng is between -180 and 180
- **Example**:
  ```python
  # In handle_find_nearest_species
  lat: float,  # No validation
  lng: float,  # No validation
  ```

#### 3. **Unvalidated String Inputs**
- **Finding**: Region codes, species codes, and location IDs are not validated
- **Location**: Throughout all handlers
- **Risk**: 
  - Invalid region codes could cause API failures
  - Malformed species codes could bypass taxonomy lookup
  - No format validation for location IDs (e.g., "L123456" pattern)
- **Example**:
  ```python
  # In handle_get_region_details
  region_code: str  # No format validation
  ```

#### 4. **No Array Size Limits**
- **Finding**: Arrays like `species_names` have no size limits
- **Location**: `species.py`, `planning.py`
- **Risk**: 
  - DoS attacks by passing extremely large arrays
  - Memory exhaustion
  - API rate limit exhaustion
- **Example**:
  ```python
  async def handle_validate_species(self, species_names: List[str]):
      # No check on len(species_names)
  ```

#### 5. **Direct String Interpolation in API Endpoints**
- **Finding**: User input is directly interpolated into API endpoint URLs
- **Location**: `ebird_api.py` (lines 150-152, 188-190, 224, 257, 286, 398, 434)
- **Risk**: 
  - Path traversal attacks
  - API endpoint manipulation
- **Example**:
  ```python
  endpoint = f"/data/obs/{region_code}/recent"  # Direct interpolation
  if species_code:
      endpoint += f"/{species_code}"  # More direct interpolation
  ```

#### 6. **No Date Format Validation**
- **Finding**: Date inputs in temporal tools are not validated
- **Location**: `pipeline.py` temporal handlers
- **Risk**: 
  - Invalid date formats could cause crashes
  - No validation of date ranges
  - No prevention of future dates

#### 7. **Unvalidated Numeric Ranges**
- **Finding**: While some limits exist in `ebird_api.py`, they're not consistently applied
- **Location**: Various handlers
- **Issues**:
  - `days_back` could be negative
  - `distance_km` could be negative or extremely large
  - `max_results` has no upper bound in handlers
- **Partial Protection Found**:
  ```python
  # In ebird_api.py
  "back": min(days_back, 30),  # Good, but no negative check
  "dist": min(distance_km, 50),  # Good, but no negative check
  ```

#### 8. **LLM Prompt Injection Vulnerabilities**
- **Finding**: User input is directly embedded in LLM prompts without sanitization
- **Location**: `call_llm.py`, `advisory.py`, `nodes.py`
- **Risk**: 
  - Prompt injection attacks
  - LLM jailbreaking
  - Unintended behavior
- **Example**:
  ```python
  # In advisory.py
  expert_prompt = f"""...following query: {query}{context_info}"""  # Direct injection
  ```

#### 9. **No Input Sanitization Before External API Calls**
- **Finding**: Raw user input is passed to both eBird API and OpenAI API
- **Risk**: 
  - Potential for crafted inputs to exploit API vulnerabilities
  - No escaping of special characters
  - No prevention of control characters

#### 10. **Missing Type Validation at Runtime**
- **Finding**: While type hints exist, no runtime type validation occurs
- **Risk**: 
  - Type confusion attacks
  - Unexpected behavior with wrong types
  - No validation that numeric inputs are actually numbers

### Specific Vulnerable Code Examples

#### Example 1: Location Handler
```python
async def handle_get_nearby_notable_observations(
    self,
    lat: float,  # No validation
    lng: float,  # No validation
    distance_km: int = 25,  # No validation for negative/large values
    days_back: int = 7,  # No validation for negative/large values
    # ... more unvalidated params
):
    observations = self.ebird_api.get_nearby_notable_observations(
        lat=lat,  # Passed directly
        lng=lng,  # Passed directly
        # ...
    )
```

#### Example 2: Species Validation
```python
async def handle_validate_species(self, species_names: List[str]):
    # No check on:
    # - List size
    # - String lengths
    # - Special characters
    # - Empty strings
    shared_store = {"input": {"species_list": species_names}}
```

#### Example 3: Direct Endpoint Construction
```python
def get_recent_observations(self, region_code: str, ...):
    endpoint = f"/data/obs/{region_code}/recent"  # Injection risk
```

### Recommendations

#### 1. **Implement Input Validation Middleware**
Create a validation decorator that checks all inputs before handler execution:
```python
from functools import wraps
import re

def validate_inputs(schema):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Validate against schema
            # Check types, ranges, formats
            # Sanitize strings
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

#### 2. **Add Coordinate Validation**
```python
def validate_coordinates(lat: float, lng: float):
    if not -90 <= lat <= 90:
        raise ValueError(f"Invalid latitude: {lat}")
    if not -180 <= lng <= 180:
        raise ValueError(f"Invalid longitude: {lng}")
```

#### 3. **Implement String Format Validation**
```python
REGION_CODE_PATTERN = re.compile(r'^[A-Z]{2}(-[A-Z0-9]{1,3})?$')
SPECIES_CODE_PATTERN = re.compile(r'^[a-z]{3,6}\d{0,2}$')
LOCATION_ID_PATTERN = re.compile(r'^L\d+$')

def validate_region_code(code: str):
    if not REGION_CODE_PATTERN.match(code):
        raise ValueError(f"Invalid region code format: {code}")
```

#### 4. **Add Array Size Limits**
```python
MAX_SPECIES_LIST_SIZE = 100
MAX_RESULTS_LIMIT = 1000

def validate_array_size(arr: List, max_size: int, name: str):
    if len(arr) > max_size:
        raise ValueError(f"{name} exceeds maximum size of {max_size}")
```

#### 5. **Sanitize LLM Inputs**
```python
def sanitize_for_llm(text: str) -> str:
    # Remove potential prompt injection patterns
    # Escape special characters
    # Limit length
    return cleaned_text
```

#### 6. **Use Parameterized API Calls**
Instead of string interpolation, use a safe endpoint builder:
```python
def build_endpoint(base: str, *parts: str) -> str:
    # Validate each part
    # Safely construct endpoint
    return safe_endpoint
```

### Immediate Actions Required

1. **Create validation module** at `/src/bird_travel_recommender/mcp/validation.py`
2. **Add input validation to all handlers** before any processing
3. **Implement rate limiting** to prevent abuse
4. **Add logging for invalid inputs** for security monitoring
5. **Create security tests** to verify validation works correctly

### Risk Assessment

- **Overall Risk Level**: HIGH
- **Exploitation Difficulty**: LOW (no protections in place)
- **Potential Impact**: 
  - Service disruption (DoS)
  - Data corruption
  - Unauthorized API usage
  - Potential for chained attacks

### Conclusion

The Bird Travel Recommender currently operates with minimal input validation, creating significant security vulnerabilities. Immediate implementation of comprehensive input validation is critical to protect against both accidental misuse and malicious attacks. The recommendations provided should be implemented as a priority before any production deployment.