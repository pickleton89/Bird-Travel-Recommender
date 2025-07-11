# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

- **Install dependencies**: `uv sync`
- **Run the application**: `uv run python main.py` (from root) or `uv run python -m bird_travel_recommender`
- **Run individual modules**: `uv run python -m <module_name>`
- **Add new dependencies**: `uv add <package_name>`
- **Activate environment**: `source .venv/bin/activate` (or use `uv run` prefix)
- **Run tests**: `uv run pytest` (tests in `tests/` directory)

## Project Structure

The project follows modern Python packaging standards with a clean `src/` layout:

```
Bird-Travel-Recommender/
├── src/bird_travel_recommender/    # Main package
│   ├── main.py                     # Application entry point
│   ├── flow.py                     # PocketFlow workflow definition  
│   ├── nodes.py                    # Node imports (modularized)
│   ├── nodes/                      # Modularized node implementations
│   │   ├── validation/            # Species validation nodes
│   │   ├── fetching/              # Data fetching nodes
│   │   ├── processing/            # Data processing nodes
│   │   └── ...                     # Other node categories
│   ├── utils/                      # Utility modules
│   │   ├── call_llm.py            # OpenAI API integration
│   │   ├── ebird_api.py           # eBird API client
│   │   └── ...                     # Other utilities
│   └── mcp/                        # MCP server integration
│       ├── server.py              # MCP server implementation
│       └── config/                # MCP configuration files
├── tests/                          # Test suite
│   ├── unit/                      # Unit tests
│   ├── integration/               # Integration tests
│   └── fixtures/                  # Test fixtures
├── scripts/                       # Utility scripts
├── config/                        # Configuration files
├── docs/                          # Documentation
└── main.py                        # Development convenience entry point
```

## Architecture Overview

This is a sophisticated PocketFlow-based Bird Travel Recommender system that leverages eBird API integration and expert birding knowledge. The architecture has evolved from a simple Q&A flow to a comprehensive birding travel planning system with 30 MCP tools and robust error handling.

### Enhanced Flow Architecture

The system now features a comprehensive MCP tool architecture with:

#### Core Node Architecture (Modularized)
- **FetchSightingsNode** - Retrieves recent bird sightings data (nodes/fetching/)
- **ClusterHotspotsNode** - Identifies optimal birding locations (nodes/processing/)
- **ValidateSpeciesNode** - Validates bird species with taxonomic lookup (nodes/validation/)
- **FilterConstraintsNode** - Filters data based on user constraints (nodes/processing/)
- **ScoreLocationsNode** - Scores birding locations (nodes/processing/)
- **OptimizeRouteNode** - Optimizes travel routes (nodes/processing/)
- **GenerateItineraryNode** - Creates detailed itineraries (nodes/processing/)

#### Business Logic Tools
- **DecideBirdingToolNode** - Enhanced with expert birding knowledge for species-specific advice, habitat assessment, and optimal observation timing
- **Location Scoring** - Evaluates birding potential of destinations
- **Itinerary Generation** - Creates detailed birding trip plans
- **Species Validation** - Prioritizes direct taxonomy lookup over external dependencies

#### Data Flow & Error Handling
- **Enrichment-in-Place Strategy** - Embeds validation flags within original data structures
- **Dual Discovery Methods** - Smart endpoint selection for optimal API performance  
- **Bootstrap Statistical Models** - Negative binomial models for handling data overdispersion
- **Comprehensive Schema Validation** - JSON schemas ensure data integrity

The architecture leverages proven patterns from the moonbirdai/ebird-mcp-server JavaScript implementation, providing production-level reliability and scalability.

## Environment Requirements

### API Keys Setup
1. Copy `.env.example` to `.env`: `cp .env.example .env`
2. Fill in your actual API keys in the `.env` file:
   - **OPENAI_API_KEY**: Get from https://platform.openai.com/api-keys
   - **EBIRD_API_KEY**: Get from https://ebird.org/api/keygen

### Configuration
- Uses GPT-4o model by default (configurable in `src/bird_travel_recommender/utils/call_llm.py`)
- Environment variables loaded automatically via python-dotenv
- Default settings can be configured in `.env` file
- MCP configurations available in `src/bird_travel_recommender/mcp/config/`

## Memory Notes
- When asked where we left off, check changelog, memory, and git commit
- Always check changelog when asked "where did we leave off"