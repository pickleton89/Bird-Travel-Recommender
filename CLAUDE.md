# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

- **Install dependencies**: `uv sync`
- **Run the application**: `uv run python main.py`
- **Run individual modules**: `uv run python -m <module_name>`
- **Add new dependencies**: `uv add <package_name>`
- **Activate environment**: `source .venv/bin/activate` (or use `uv run` prefix)

## Architecture Overview

This is a sophisticated PocketFlow-based Bird Travel Recommender system that leverages eBird API integration and expert birding knowledge. The architecture has evolved from a simple Q&A flow to a comprehensive birding travel planning system with 9 MCP tools and robust error handling.

- **Main Entry Point**: `main.py` - Creates and runs the birding recommendation flow
- **Flow Definition**: `flow.py` - Defines the workflow using PocketFlow nodes with enhanced birding logic
- **Node Implementation**: `nodes.py` - Contains custom node classes including DecideBirdingToolNode with expert birding knowledge
- **Utilities**: `utils/call_llm.py` - OpenAI API integration optimized for birding domain expertise

### Enhanced Flow Architecture

The system now features a comprehensive MCP tool architecture with:

#### Core eBird Data Tools
- **FetchSightingsNode** - Retrieves recent bird sightings data
- **ClusterHotspotsNode** - Identifies optimal birding locations
- **ValidateSpeciesNode** - Validates bird species with taxonomic lookup
- **makeRequest() Pattern** - Centralized API request handling with robust error management

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
- Uses GPT-4o model by default (configurable in `utils/call_llm.py`)
- Environment variables loaded automatically via python-dotenv
- Default settings can be configured in `.env` file

## Memory Notes
- When asked where we left off, check changelog, memory, and git commit
- Always check changelog when asked "where did we leave off"