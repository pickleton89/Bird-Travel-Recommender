# eBird API Expansion Implementation Plan

## Overview
This document outlines the step-by-step implementation plan for adding 4 high-priority eBird API endpoints to the Bird Travel Recommender system. These endpoints will significantly enhance target species finding, regional analysis, and hotspot-based trip planning capabilities.

## Target Endpoints
1. **`get_nearest_observations()`** - Find closest location where specific species was recently seen
2. **`get_species_list()`** - Complete species list ever reported in a region  
3. **`get_region_info()`** - Region metadata and human-readable names
4. **`get_hotspot_info()`** - Detailed hotspot information and activity metrics

## Current Architecture Analysis

### Existing Implementation Patterns (`ebird_api.py`)
- **Centralized `make_request()` method** for all HTTP interactions
- **Consistent parameter validation** and error handling
- **Rate limiting** with exponential backoff (3 retries, 1s initial delay)
- **Session reuse** for efficient connection management
- **Structured error handling** with descriptive `EBirdAPIError` messages
- **Parameter normalization** (e.g., `min(days_back, 30)` for API limits)

### Existing Error Handling Patterns
```python
# HTTP Status Code Handling
- 200: Success - return response.json()
- 400: Bad request - Invalid parameters 
- 404: Not found - Invalid region/species code
- 429: Rate limit - Exponential backoff retry
- 500+: Server error - Retry with backoff
```

### Current Parameter Patterns
- **Required parameters**: Validated in method signature
- **Optional parameters**: Default values with API limit enforcement
- **Boolean parameters**: Converted to lowercase strings for API compatibility
- **List parameters**: Joined with commas where needed

## Implementation Plan

### Phase 1: Core API Method Implementation

#### 1.1 Add `get_nearest_observations()` Method
**File**: `src/bird_travel_recommender/utils/ebird_api.py`

```python
def get_nearest_observations(
    self,
    species_code: str,
    lat: float,
    lng: float,
    days_back: int = 14,
    distance_km: int = 50,
    hotspot_only: bool = False,
    include_provisional: bool = False,
    max_results: int = 3000,
    locale: str = "en"
) -> List[Dict[str, Any]]:
    """
    Find nearest locations where a specific species was recently observed.
    
    Args:
        species_code: eBird species code (e.g., "norcar")
        lat: Latitude coordinate
        lng: Longitude coordinate
        days_back: Days to look back (default: 14, max: 30)
        distance_km: Maximum search distance (default: 50, max: 50)
        hotspot_only: Restrict to hotspot sightings only
        include_provisional: Include unconfirmed observations
        max_results: Maximum observations to return (default: 3000, max: 3000)
        locale: Language locale for species names
        
    Returns:
        List of nearest observations sorted by distance (closest first)
        
    Raises:
        EBirdAPIError: For API errors with descriptive messages
    """
```

**Implementation Notes**:
- Follow existing parameter validation patterns
- Use centralized `make_request()` method
- Handle empty array response when no species found
- Add appropriate logging statements

#### 1.2 Add `get_species_list()` Method

```python
def get_species_list(
    self,
    region_code: str
) -> List[str]:
    """
    Get complete list of species ever reported in a region.
    
    Args:
        region_code: eBird region code (e.g., "US-MA", "CA-ON")
        
    Returns:
        List of eBird species codes for all species in region
        
    Raises:
        EBirdAPIError: For API errors with descriptive messages
    """
```

**Implementation Notes**:
- Simple endpoint with no optional parameters
- Returns array of species codes only
- May return large lists (1000+ species for countries)

#### 1.3 Add `get_region_info()` Method

```python
def get_region_info(
    self,
    region_code: str,
    name_format: str = "detailed"
) -> Dict[str, Any]:
    """
    Get metadata and human-readable information for a region.
    
    Args:
        region_code: eBird region code to get information about
        name_format: Name format ("detailed" or "short")
        
    Returns:
        Region information including name, type, and hierarchy
        
    Raises:
        EBirdAPIError: For API errors with descriptive messages
    """
```

**Implementation Notes**:
- Returns single JSON object (not array)
- Provides hierarchical region context
- Essential for user-friendly region display

#### 1.4 Add `get_hotspot_info()` Method

```python
def get_hotspot_info(
    self,
    location_id: str
) -> Dict[str, Any]:
    """
    Get detailed information about a specific birding hotspot.
    
    Args:
        location_id: eBird location ID (e.g., "L123456")
        
    Returns:
        Hotspot details including coordinates, statistics, and metadata
        
    Raises:
        EBirdAPIError: For API errors with descriptive messages
    """
```

**Implementation Notes**:
- Returns single JSON object with comprehensive hotspot data
- Only works with official hotspot IDs
- Provides species counts and activity metrics

### Phase 2: Convenience Function Integration

#### 2.1 Add Global Convenience Functions
Add convenience functions at module level following existing pattern:

```python
# Add to end of ebird_api.py
def get_nearest_observations(*args, **kwargs):
    """Convenience function for getting nearest observations."""
    return get_client().get_nearest_observations(*args, **kwargs)

def get_species_list(*args, **kwargs):
    """Convenience function for getting species list."""
    return get_client().get_species_list(*args, **kwargs)

def get_region_info(*args, **kwargs):
    """Convenience function for getting region info."""
    return get_client().get_region_info(*args, **kwargs)

def get_hotspot_info(*args, **kwargs):
    """Convenience function for getting hotspot info."""
    return get_client().get_hotspot_info(*args, **kwargs)
```

### Phase 3: MCP Server Tool Integration

#### 3.1 Add New MCP Tools
**File**: `src/bird_travel_recommender/mcp/server.py`

Add 4 new tools to the `handle_list_tools()` method:

1. **`find_nearest_species`** - Wrapper for `get_nearest_observations()`
2. **`get_regional_species_list`** - Wrapper for `get_species_list()`
3. **`get_region_details`** - Wrapper for `get_region_info()`
4. **`get_hotspot_details`** - Wrapper for `get_hotspot_info()`

#### 3.2 Add Tool Handler Methods

```python
async def _handle_find_nearest_species(self, species_code: str, lat: float, lng: float, **kwargs):
    """Handle find_nearest_species tool"""
    
async def _handle_get_regional_species_list(self, region_code: str, **kwargs):
    """Handle get_regional_species_list tool"""
    
async def _handle_get_region_details(self, region_code: str, **kwargs):
    """Handle get_region_details tool"""
    
async def _handle_get_hotspot_details(self, location_id: str, **kwargs):
    """Handle get_hotspot_details tool"""
```

#### 3.3 Update Tool Router
Add new tool cases to the `handle_call_tool()` method.

### Phase 4: Enhanced Business Logic Integration

#### 4.1 Enhance `plan_complete_trip` Tool
Integrate new endpoints into the end-to-end trip planning pipeline:

- **Use `get_region_info()`** to display user-friendly region names
- **Use `get_species_list()`** for regional species validation and suggestions
- **Use `get_hotspot_info()`** to enrich hotspot cluster data with detailed metrics
- **Use `get_nearest_observations()`** for targeted species finding recommendations

#### 4.2 Enhance `get_birding_advice` Tool
Incorporate new data sources into expert advice generation:

- Reference regional species lists for habitat recommendations
- Use nearest observations for species-specific location advice
- Include hotspot information in location recommendations

### Phase 5: Testing and Validation

#### 5.1 Unit Tests
**File**: `tests/unit/test_ebird_api_expansion.py`

Create comprehensive test suite covering:
- Parameter validation for all new methods
- Error handling scenarios (404, 400, 429, 500+ responses)
- Response format validation
- Rate limiting behavior
- Mock API responses for consistent testing

#### 5.2 Integration Tests
**File**: `tests/integration/test_mcp_tools_expansion.py`

Test MCP tool integration:
- Tool registration and discovery
- End-to-end tool execution
- Error propagation through MCP layer
- JSON schema validation for tool responses

#### 5.3 Manual Testing Script
**File**: `scripts/test_new_endpoints.py`

Create manual testing script for validation:
```python
#!/usr/bin/env python3
"""
Manual testing script for new eBird API endpoints
"""

def test_nearest_observations():
    # Test with common species (Northern Cardinal)
    # Test with rare species (might return empty)
    # Test parameter validation

def test_species_list():
    # Test with different region types (country, state, county)
    # Test with invalid region codes

def test_region_info():
    # Test hierarchical regions
    # Test different name formats

def test_hotspot_info():
    # Test with known hotspot IDs
    # Test with invalid location IDs
```

## Implementation Timeline

### Week 1: Core API Implementation
- **Days 1-2**: Implement `get_nearest_observations()` and `get_species_list()`
- **Days 3-4**: Implement `get_region_info()` and `get_hotspot_info()`
- **Day 5**: Add convenience functions and basic testing

### Week 2: MCP Integration
- **Days 1-2**: Add new MCP tools and handlers
- **Days 3-4**: Update business logic integration
- **Day 5**: Integration testing and debugging

### Week 3: Testing and Documentation
- **Days 1-2**: Comprehensive unit and integration tests
- **Days 3-4**: Manual testing and validation
- **Day 5**: Documentation updates and code review

## Quality Assurance Checklist

### Code Quality
- [ ] Follow existing code patterns and style
- [ ] Consistent error handling with descriptive messages
- [ ] Proper parameter validation and type hints
- [ ] Comprehensive docstrings following existing format
- [ ] Logging statements for debugging and monitoring

### API Integration
- [ ] All endpoints use centralized `make_request()` method
- [ ] Rate limiting and retry logic applied consistently
- [ ] Parameter normalization follows API limits
- [ ] Response format validation and error handling

### MCP Server Integration
- [ ] New tools registered in `handle_list_tools()`
- [ ] Tool handlers follow async pattern
- [ ] JSON schema validation for inputs and outputs
- [ ] Error propagation to MCP client

### Testing Coverage
- [ ] Unit tests for all new methods (>90% coverage)
- [ ] Integration tests for MCP tools
- [ ] Manual testing script validates real API responses
- [ ] Error scenarios tested comprehensively

### Documentation
- [ ] Update API documentation with new endpoints
- [ ] Update MCP tool documentation
- [ ] Add usage examples for new functionality
- [ ] Update CHANGELOG.md with new features

## Risk Mitigation

### API Rate Limiting
- **Risk**: New endpoints may increase API usage
- **Mitigation**: Monitor usage patterns, implement request batching where possible

### Error Handling
- **Risk**: New error scenarios not covered
- **Mitigation**: Comprehensive error testing, graceful degradation

### Data Quality
- **Risk**: API response format changes
- **Mitigation**: Response validation, version-specific handling

### Performance Impact
- **Risk**: Additional API calls may slow down operations
- **Mitigation**: Implement caching for static data (region info, hotspot info)

## Success Metrics

### Functional Metrics
- All 4 endpoints successfully implemented and tested
- MCP tools properly integrated and functional
- Enhanced business logic features working correctly
- Test coverage >90% for new code

### User Experience Metrics
- Improved target species finding accuracy
- Enhanced regional analysis capabilities
- Better hotspot-based recommendations
- Reduced user effort for trip planning

## Next Steps After Implementation

### Future Enhancements
1. **Caching Layer**: Implement Redis/file-based caching for static data
2. **Batch Operations**: Combine multiple API calls for efficiency
3. **Advanced Analytics**: Use new data for enhanced trip optimization
4. **User Interface**: Expose new capabilities through improved UI

### Additional Endpoints (Lower Priority)
- `get_nearby_notable_observations()` - Local rare bird alerts
- `get_recent_checklists()` - Community activity feed
- `get_subregions()` - Geographic navigation
- `get_adjacent_regions()` - Cross-border planning

This implementation plan provides a comprehensive roadmap for adding the 4 high-priority eBird API endpoints while maintaining code quality, test coverage, and integration with the existing system architecture.