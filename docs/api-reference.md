# Bird Travel Recommender API Reference

This document provides a comprehensive reference for all 30 MCP tools available in the Bird Travel Recommender system, organized into 6 specialized categories.

## Table of Contents

- [Species Tools (2)](#species-tools)
  - [validate_species](#validate_species)
  - [get_regional_species_list](#get_regional_species_list)
- [Location Tools (11)](#location-tools)
  - [get_region_details](#get_region_details)
  - [get_hotspot_details](#get_hotspot_details)
  - [find_nearest_species](#find_nearest_species)
  - [get_nearby_notable_observations](#get_nearby_notable_observations)
  - [get_nearby_species_observations](#get_nearby_species_observations)
  - [get_top_locations](#get_top_locations)
  - [get_regional_statistics](#get_regional_statistics)
  - [get_location_species_list](#get_location_species_list)
  - [get_subregions](#get_subregions)
  - [get_adjacent_regions](#get_adjacent_regions)
  - [get_elevation_data](#get_elevation_data)
- [Pipeline Tools (11)](#pipeline-tools)
  - [fetch_sightings](#fetch_sightings)
  - [filter_constraints](#filter_constraints)
  - [cluster_hotspots](#cluster_hotspots)
  - [score_locations](#score_locations)
  - [optimize_route](#optimize_route)
  - [get_historic_observations](#get_historic_observations)
  - [get_seasonal_trends](#get_seasonal_trends)
  - [get_yearly_comparisons](#get_yearly_comparisons)
  - [get_migration_data](#get_migration_data)
  - [get_peak_times](#get_peak_times)
  - [get_seasonal_hotspots](#get_seasonal_hotspots)
- [Planning Tools (2)](#planning-tools)
  - [generate_itinerary](#generate_itinerary)
  - [plan_complete_trip](#plan_complete_trip)
- [Advisory Tools (1)](#advisory-tools)
  - [get_birding_advice](#get_birding_advice)
- [Community Tools (3)](#community-tools)
  - [get_recent_checklists](#get_recent_checklists)
  - [get_checklist_details](#get_checklist_details)
  - [get_user_stats](#get_user_stats)
- [Error Handling](#error-handling)
- [Rate Limits](#rate-limits)

## Species Tools

Tools for species validation, identification, and regional species information.

### validate_species

Validate bird species names using eBird taxonomy with LLM fallback for fuzzy matching.

#### Request Schema

```json
{
  "species_names": ["Northern Cardinal", "Blue Jay", "American Robin"]
}
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| species_names | array[string] | Yes | List of bird species names to validate (common names, scientific names, or species codes) |

#### Response

```json
{
  "success": true,
  "validated_species": [
    {
      "input": "Northern Cardinal",
      "species_code": "norcar",
      "common_name": "Northern Cardinal",
      "scientific_name": "Cardinalis cardinalis",
      "method": "direct_common_name",
      "confidence": 1.0
    }
  ],
  "statistics": {
    "input_count": 3,
    "validated_count": 3,
    "failed_count": 0,
    "validation_time_seconds": 0.245
  }
}
```

### get_regional_species_list

Get comprehensive species list for a specific region with recent activity data.

#### Request Schema

```json
{
  "region": "US-MA",
  "days_back": 30
}
```

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| region | string | Yes | - | Region code (e.g., 'US-MA', 'CA-ON') |
| days_back | integer | No | 30 | Number of days to analyze for recent activity |

#### Response

```json
{
  "success": true,
  "region_species": [
    {
      "species_code": "norcar",
      "common_name": "Northern Cardinal",
      "scientific_name": "Cardinalis cardinalis",
      "recent_observations": 45,
      "last_seen": "2024-03-15",
      "frequency": 0.85
    }
  ],
  "total_species": 187,
  "recent_activity_species": 156
}
```

## Location Tools

Tools for discovering, analyzing, and getting detailed information about birding locations.

### get_region_details

Get detailed information about a geographic region including birding statistics and characteristics.

#### Request Schema

```json
{
  "region": "US-MA"
}
```

#### Response

```json
{
  "success": true,
  "region_info": {
    "region_code": "US-MA",
    "region_name": "Massachusetts",
    "total_species": 425,
    "total_hotspots": 1247,
    "recent_checklists": 15420,
    "top_birding_months": ["May", "September", "October"]
  }
}
```

### get_hotspot_details

Get comprehensive information about a specific birding hotspot.

#### Request Schema

```json
{
  "hotspot_id": "L123456"
}
```

#### Response

```json
{
  "success": true,
  "hotspot": {
    "hotspot_id": "L123456",
    "name": "Fresh Pond",
    "location": {"lat": 42.3736, "lng": -71.1106},
    "total_species": 187,
    "recent_checklists": 45,
    "best_time": "early_morning",
    "habitat_types": ["pond", "woodland", "grassland"]
  }
}
```

### find_nearest_species

Find closest recent observations of specific species to given coordinates.

#### Request Schema

```json
{
  "species_code": "norcar",
  "lat": 42.3601,
  "lng": -71.0589,
  "max_distance_km": 50
}
```

### get_nearby_notable_observations

Get rare or notable bird observations near specific coordinates.

#### Request Schema

```json
{
  "lat": 42.3601,
  "lng": -71.0589,
  "radius_km": 25,
  "days_back": 7
}
```

### get_nearby_species_observations

Get recent observations of specific species near coordinates.

#### Request Schema

```json
{
  "species_codes": ["norcar", "blujay"],
  "lat": 42.3601,
  "lng": -71.0589,
  "radius_km": 25
}
```

### get_top_locations

Get most active birding locations in a region based on recent activity.

#### Request Schema

```json
{
  "region": "US-MA",
  "limit": 10,
  "min_species": 20
}
```

### get_regional_statistics

Get species counts and birding activity statistics for a region.

#### Request Schema

```json
{
  "region": "US-MA",
  "days_back": 30
}
```

### get_location_species_list

Get complete species list for a specific location or hotspot.

#### Request Schema

```json
{
  "location_id": "L123456",
  "days_back": 365
}
```

### get_subregions

Get subregions within a geographic region for detailed area exploration.

#### Request Schema

```json
{
  "region": "US-MA"
}
```

### get_adjacent_regions

Get neighboring regions for cross-border birding trip planning.

#### Request Schema

```json
{
  "region": "US-MA"
}
```

### get_elevation_data

Get elevation information and habitat zone analysis for locations.

#### Request Schema

```json
{
  "lat": 42.3601,
  "lng": -71.0589,
  "radius_km": 10
}
```

## Pipeline Tools

Core data processing and analysis tools for building comprehensive birding workflows.

### fetch_sightings

Fetch recent bird sightings using parallel eBird API queries with smart endpoint selection.

#### Request Schema

```json
{
  "validated_species": [
    {
      "species_code": "norcar",
      "common_name": "Northern Cardinal"
    }
  ],
  "region": "US-MA",
  "days_back": 14
}
```

#### Response

```json
{
  "success": true,
  "observations": [
    {
      "species_code": "norcar",
      "common_name": "Northern Cardinal",
      "scientific_name": "Cardinalis cardinalis",
      "observation_count": 2,
      "location_name": "Fresh Pond",
      "location_id": "L123456",
      "lat": 42.3736,
      "lng": -71.1106,
      "observation_date": "2024-03-15",
      "observation_time": "08:30",
      "notable": false
    }
  ],
  "statistics": {
    "total_observations": 47,
    "unique_locations": 23,
    "fetch_time_seconds": 1.234
  }
}
```

### filter_constraints

Apply geographic and temporal constraints to sightings using enrichment-in-place strategy.

#### Request Schema

```json
{
  "sightings": [...],
  "start_location": {
    "lat": 42.3601,
    "lng": -71.0589
  },
  "max_distance_km": 50,
  "date_range": {
    "start": "2024-03-01",
    "end": "2024-03-15"
  }
}
```

### cluster_hotspots

Cluster birding locations and integrate with eBird hotspots using dual discovery methods.

#### Request Schema

```json
{
  "filtered_sightings": [...],
  "region": "US-MA",
  "cluster_radius_km": 15
}
```

### score_locations

Score and rank birding locations using multi-criteria analysis with optional LLM enhancement.

#### Request Schema

```json
{
  "hotspot_clusters": [...],
  "target_species": ["norcar", "blujay"],
  "use_llm_enhancement": true
}
```

### optimize_route

Optimize travel route between birding locations using TSP algorithms.

#### Request Schema

```json
{
  "scored_locations": [...],
  "start_location": {
    "lat": 42.3601,
    "lng": -71.0589
  },
  "max_locations": 6
}
```

### get_historic_observations

Get historical bird observations for specific dates and temporal analysis.

#### Request Schema

```json
{
  "region": "US-MA",
  "start_date": "2023-03-01",
  "end_date": "2023-03-31",
  "species_codes": ["norcar"]
}
```

### get_seasonal_trends

Analyze seasonal birding trends and patterns for species or regions.

#### Request Schema

```json
{
  "region": "US-MA",
  "species_codes": ["norcar", "blujay"],
  "years": 3
}
```

### get_yearly_comparisons

Compare birding activity across multiple years for trend analysis.

#### Request Schema

```json
{
  "region": "US-MA",
  "years": [2022, 2023, 2024],
  "species_codes": ["norcar"]
}
```

### get_migration_data

Analyze species migration timing and routes for trip planning.

#### Request Schema

```json
{
  "species_codes": ["yewwar", "btnwar"],
  "region": "US-MA",
  "migration_season": "spring"
}
```

### get_peak_times

Get optimal daily timing recommendations for birding activities.

#### Request Schema

```json
{
  "region": "US-MA",
  "season": "spring",
  "target_species": ["warblers"]
}
```

### get_seasonal_hotspots

Get location rankings optimized for specific seasons and migration periods.

#### Request Schema

```json
{
  "region": "US-MA",
  "season": "spring",
  "habitat_preference": "woodland"
}
```

## Planning Tools

High-level trip planning and itinerary generation tools.

### generate_itinerary

Generate professional birding itinerary with LLM enhancement and template fallback.

#### Request Schema

```json
{
  "optimized_route": {...},
  "target_species": ["Northern Cardinal", "Blue Jay"],
  "trip_duration_days": 2
}
```

#### Response

```json
{
  "success": true,
  "itinerary": {
    "markdown": "# Birding Itinerary: Massachusetts Adventure\n\n## Day 1\n...",
    "summary": "2-day birding trip targeting 2 species across 6 locations",
    "highlights": [
      "Fresh Pond - High probability for Northern Cardinal",
      "Mount Auburn Cemetery - Recent Blue Jay activity"
    ]
  }
}
```

### plan_complete_trip

End-to-end birding trip planning combining all pipeline stages for comprehensive recommendations.

#### Request Schema

```json
{
  "species_names": ["Northern Cardinal", "Blue Jay", "Wood Duck"],
  "region": "US-MA",
  "start_location": {
    "lat": 42.3601,
    "lng": -71.0589
  },
  "max_distance_km": 75,
  "trip_duration_days": 2,
  "days_back": 14
}
```

#### Response

```json
{
  "success": true,
  "trip_plan": {
    "validated_species": [...],
    "total_observations": 234,
    "hotspot_clusters": [...],
    "optimized_route": {...},
    "itinerary": {...}
  },
  "execution_summary": {
    "stages_completed": [
      "species_validation",
      "sightings_fetch",
      "constraint_filtering",
      "hotspot_clustering",
      "location_scoring",
      "route_optimization",
      "itinerary_generation"
    ],
    "total_time_seconds": 4.567
  }
}
```

## Advisory Tools

Expert birding advice and recommendation tools.

### get_birding_advice

Get expert birding advice for species, locations, or techniques using enhanced LLM prompting.

#### Request Schema

```json
{
  "query": "What's the best time to see warblers during spring migration?",
  "context": {
    "species": ["Yellow Warbler", "Black-throated Blue Warbler"],
    "location": "New England",
    "season": "spring",
    "experience_level": "intermediate"
  }
}
```

#### Response

```json
{
  "success": true,
  "advice": {
    "main_response": "Spring warbler migration in New England typically peaks...",
    "key_points": [
      "Peak migration: May 10-25",
      "Best time: Early morning (6-10 AM)",
      "Look for mixed feeding flocks"
    ],
    "species_specific": {
      "Yellow Warbler": "Common in wetland edges...",
      "Black-throated Blue Warbler": "Prefer understory of deciduous forests..."
    },
    "recommended_locations": [
      "Mount Auburn Cemetery, Cambridge",
      "Plum Island, Newburyport"
    ]
  }
}
```

## Community Tools

Social birding features and community interaction tools.

### get_recent_checklists

Get most recent birding checklists submitted in a region.

#### Request Schema

```json
{
  "region": "US-MA",
  "days_back": 7,
  "limit": 20
}
```

#### Response

```json
{
  "success": true,
  "checklists": [
    {
      "checklist_id": "S123456789",
      "location_name": "Fresh Pond",
      "observer": "John Birder",
      "date": "2024-03-15",
      "species_count": 23,
      "duration_minutes": 120
    }
  ]
}
```

### get_checklist_details

Get detailed information about a specific birding checklist.

#### Request Schema

```json
{
  "checklist_id": "S123456789"
}
```

### get_user_stats

Get birder profile and statistics for community features.

#### Request Schema

```json
{
  "user_id": "usr123",
  "region": "US-MA"
}
```

## Error Handling

All tools follow a consistent error response format with enhanced error handling framework including circuit breakers, retry logic, and graceful degradation.

```json
{
  "success": false,
  "error": "Error message describing what went wrong",
  "error_code": "SPECIFIC_ERROR_CODE",
  "details": {
    "stage": "validation",
    "retry_count": 2,
    "fallback_available": true
  }
}
```

### Common Error Codes

| Code | Description | Recovery Action |
|------|-------------|-----------------|
| `INVALID_INPUT` | Request parameters are invalid | Check parameter types and requirements |
| `API_ERROR` | External API request failed | Automatic retry with exponential backoff |
| `RATE_LIMIT_EXCEEDED` | API rate limit reached | Circuit breaker activates, retry after delay |
| `TIMEOUT` | Request timed out | Retry with smaller data set |
| `INSUFFICIENT_DATA` | Not enough data to process | Adjust search criteria |
| `LLM_ERROR` | LLM enhancement failed | Automatic fallback to rule-based responses |

## Rate Limits

The system implements comprehensive rate limiting and error recovery:

### eBird API Limits
- **Requests per hour**: 750 (authenticated)
- **Concurrent requests**: 5 (self-imposed)
- **Retry strategy**: Exponential backoff with jitter
- **Circuit breaker**: Activates after 5 consecutive failures

### LLM API Limits
- **Tokens per minute**: Based on OpenAI tier
- **Fallback behavior**: Graceful degradation to non-LLM features

### Best Practices

1. **Use Complete Trip Planning**: `plan_complete_trip` orchestrates multiple tools efficiently
2. **Leverage Caching**: Results cached for 15 minutes
3. **Handle Partial Failures**: Tools provide partial results when possible
4. **Monitor Error Rates**: Built-in error tracking and circuit breakers
5. **Progressive Enhancement**: Start simple, add complexity as needed

## Tool Categories and Workflows

### Complete Trip Planning Workflow
```
plan_complete_trip → [orchestrates all pipeline stages automatically]
```

### Manual Pipeline Workflow
```
validate_species → fetch_sightings → filter_constraints → 
cluster_hotspots → score_locations → optimize_route → generate_itinerary
```

### Location Discovery Workflow
```
get_region_details → get_top_locations → get_hotspot_details → get_location_species_list
```

### Temporal Analysis Workflow
```
get_historic_observations → get_seasonal_trends → get_migration_data → get_peak_times
```

### Community Exploration Workflow
```
get_recent_checklists → get_checklist_details → get_user_stats
```