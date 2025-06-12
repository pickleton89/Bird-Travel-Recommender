# Bird Travel Recommender API Reference

This document provides a comprehensive reference for all 9 MCP tools available in the Bird Travel Recommender system.

## Table of Contents

- [Core eBird Tools](#core-ebird-tools)
  - [validate_species](#validate_species)
  - [fetch_sightings](#fetch_sightings)
  - [filter_constraints](#filter_constraints)
  - [cluster_hotspots](#cluster_hotspots)
  - [score_locations](#score_locations)
  - [optimize_route](#optimize_route)
  - [generate_itinerary](#generate_itinerary)
- [Business Logic Tools](#business-logic-tools)
  - [plan_complete_trip](#plan_complete_trip)
  - [get_birding_advice](#get_birding_advice)
- [Error Handling](#error-handling)
- [Rate Limits](#rate-limits)

## Core eBird Tools

These tools provide direct access to eBird data and core birding functionality.

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

#### Error Codes

- `INVALID_INPUT`: Empty or invalid species names array
- `TAXONOMY_ERROR`: Failed to load eBird taxonomy
- `VALIDATION_FAILED`: All species failed validation

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

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| validated_species | array[object] | Yes | - | List of validated species from validate_species tool |
| region | string | Yes | - | Region code (e.g., 'US-MA', 'CA-ON') or location name |
| days_back | integer | No | 14 | Number of days to look back for sightings (1-30) |

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
    "date_range": {
      "start": "2024-03-01",
      "end": "2024-03-15"
    },
    "fetch_time_seconds": 1.234
  }
}
```

#### Error Codes

- `INVALID_REGION`: Invalid region code or location
- `API_ERROR`: eBird API request failed
- `NO_SIGHTINGS`: No sightings found for specified criteria
- `RATE_LIMIT_EXCEEDED`: eBird API rate limit reached

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

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| sightings | array | Yes | - | Sightings data from fetch_sightings tool |
| start_location | object | Yes | - | Starting location coordinates (lat, lng) |
| max_distance_km | number | No | 100 | Maximum travel distance in kilometers |
| date_range | object | No | - | Optional date range filter (start, end) |

#### Response

```json
{
  "success": true,
  "filtered_observations": [
    {
      "...existing_fields...": "...",
      "meets_geographic_constraint": true,
      "meets_temporal_constraint": true,
      "distance_km": 23.5
    }
  ],
  "statistics": {
    "input_count": 47,
    "passed_geographic": 32,
    "passed_temporal": 47,
    "passed_all": 32,
    "filter_time_seconds": 0.123
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

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| filtered_sightings | array | Yes | - | Filtered sightings from filter_constraints tool |
| region | string | Yes | - | Region code for hotspot discovery |
| cluster_radius_km | number | No | 15 | Clustering radius in kilometers |

#### Response

```json
{
  "success": true,
  "hotspot_clusters": [
    {
      "cluster_id": "cluster_0",
      "center_lat": 42.3736,
      "center_lng": -71.1106,
      "location_count": 5,
      "species_count": 12,
      "notable_species": ["Wood Duck", "Barred Owl"],
      "is_hotspot": true,
      "hotspot_name": "Fresh Pond",
      "recent_checklists": 45,
      "species_total": 187
    }
  ],
  "statistics": {
    "input_locations": 32,
    "clusters_created": 8,
    "hotspots_integrated": 5,
    "clustering_time_seconds": 0.456
  }
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

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| hotspot_clusters | array | Yes | - | Hotspot clusters from cluster_hotspots tool |
| target_species | array[string] | Yes | - | Priority species codes for scoring |
| use_llm_enhancement | boolean | No | true | Enable LLM habitat evaluation |

#### Response

```json
{
  "success": true,
  "scored_locations": [
    {
      "...cluster_fields...": "...",
      "overall_score": 0.875,
      "score_components": {
        "species_diversity": 0.90,
        "recency": 0.85,
        "hotspot_quality": 0.80,
        "accessibility": 0.95
      },
      "recommendation": "Excellent location for target species with recent activity"
    }
  ],
  "statistics": {
    "locations_scored": 8,
    "average_score": 0.72,
    "scoring_time_seconds": 1.234
  }
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

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| scored_locations | array | Yes | - | Scored locations from score_locations tool |
| start_location | object | Yes | - | Starting location coordinates |
| max_locations | integer | No | 8 | Maximum number of locations to include |

#### Response

```json
{
  "success": true,
  "optimized_route": {
    "ordered_locations": [
      {
        "order": 1,
        "location": {...},
        "travel_time_minutes": 0,
        "distance_km": 0
      },
      {
        "order": 2,
        "location": {...},
        "travel_time_minutes": 15,
        "distance_km": 12.3
      }
    ],
    "total_distance_km": 87.5,
    "total_time_hours": 2.3,
    "optimization_method": "2-opt"
  },
  "statistics": {
    "input_locations": 8,
    "selected_locations": 6,
    "optimization_time_seconds": 0.234
  }
}
```

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

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| optimized_route | object | Yes | - | Optimized route from optimize_route tool |
| target_species | array[string] | Yes | - | Target species for the trip |
| trip_duration_days | integer | No | 1 | Duration of the birding trip in days |

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
  },
  "metadata": {
    "generation_method": "llm_enhanced",
    "total_distance_km": 87.5,
    "locations_count": 6,
    "target_species_count": 2
  }
}
```

## Business Logic Tools

These tools provide high-level orchestration and expert advice.

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

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| species_names | array[string] | Yes | - | Target bird species names |
| region | string | Yes | - | Region code or location name |
| start_location | object | Yes | - | Starting coordinates (lat, lng) |
| max_distance_km | number | No | 100 | Maximum travel distance |
| trip_duration_days | integer | No | 1 | Trip duration in days |
| days_back | integer | No | 14 | Days to look back for sightings |

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
    "total_time_seconds": 4.567,
    "warnings": []
  }
}
```

#### Stage-Specific Errors

The tool provides detailed error information for each pipeline stage:

```json
{
  "success": false,
  "error": "Pipeline failed at stage: sightings_fetch",
  "stage_errors": {
    "species_validation": null,
    "sightings_fetch": "API rate limit exceeded",
    "constraint_filtering": "Not attempted"
  },
  "partial_results": {
    "validated_species": [...]
  }
}
```

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

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| query | string | Yes | - | Birding question or advice request |
| context | object | No | - | Optional context for personalized advice |
| context.species | array[string] | No | - | Relevant species names |
| context.location | string | No | - | Geographic location |
| context.season | string | No | - | Season (spring, summer, fall, winter) |
| context.experience_level | string | No | - | Birding experience (beginner, intermediate, advanced, expert) |

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
  },
  "metadata": {
    "advice_type": "timing_migration",
    "confidence": 0.95,
    "sources": ["expert_knowledge", "seasonal_patterns"]
  }
}
```

#### Fallback Behavior

If LLM is unavailable, the tool provides rule-based advice:

```json
{
  "success": true,
  "advice": {
    "main_response": "General birding advice based on your query...",
    "fallback_used": true,
    "metadata": {
      "advice_type": "rule_based",
      "reason": "LLM unavailable"
    }
  }
}
```

## Error Handling

All tools follow a consistent error response format:

```json
{
  "success": false,
  "error": "Error message describing what went wrong",
  "error_code": "SPECIFIC_ERROR_CODE",
  "details": {
    "additional": "context-specific error information"
  }
}
```

### Common Error Codes

| Code | Description | Recovery Action |
|------|-------------|-----------------|
| `INVALID_INPUT` | Request parameters are invalid | Check parameter types and requirements |
| `API_ERROR` | External API request failed | Retry with exponential backoff |
| `RATE_LIMIT_EXCEEDED` | API rate limit reached | Wait before retrying |
| `TIMEOUT` | Request timed out | Retry with smaller data set |
| `INSUFFICIENT_DATA` | Not enough data to process | Adjust search criteria |
| `LLM_ERROR` | LLM enhancement failed | Tool continues with fallback |

## Rate Limits

The system implements respectful rate limiting for external APIs:

### eBird API Limits
- **Requests per hour**: 750 (authenticated)
- **Requests per day**: 10,000 (authenticated)
- **Concurrent requests**: 5 (self-imposed)
- **Retry strategy**: Exponential backoff with jitter

### LLM API Limits
- **Tokens per minute**: Based on OpenAI tier
- **Requests per minute**: Based on OpenAI tier
- **Fallback behavior**: Graceful degradation to non-LLM features

### Best Practices

1. **Batch Operations**: Use `plan_complete_trip` for multiple related queries
2. **Cache Results**: Results are cached for 15 minutes
3. **Progressive Enhancement**: Start with basic queries, add detail as needed
4. **Error Recovery**: All tools provide partial results when possible
5. **Rate Awareness**: Monitor rate limit headers in responses

## Tool Chaining Examples

### Complete Trip Planning
```
validate_species → fetch_sightings → filter_constraints → 
cluster_hotspots → score_locations → optimize_route → generate_itinerary
```

### Quick Species Lookup
```
validate_species → fetch_sightings → filter_constraints
```

### Hotspot Discovery
```
cluster_hotspots (with region only) → score_locations
```

### Expert Advice Flow
```
get_birding_advice → validate_species → plan_complete_trip
```