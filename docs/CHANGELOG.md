# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure with PocketFlow-based Q&A workflow
- Two-node workflow: GetQuestionNode and AnswerNode
- OpenAI GPT-4o integration for question answering
- UV package manager configuration
- Project documentation (CLAUDE.md)
- **Comprehensive design document (docs/design.md) following PocketFlow methodology**
- **7-node birding travel recommender architecture specification**
- **Complete shared store schema for bird sighting data pipeline**
- **Utility function specifications for eBird API, geospatial calculations, and route optimization**
- **Model Context Protocol (MCP) integration design with dual architecture**
- **3-node MCP agent pattern for natural language interface**
- **5 MCP tools exposed for Claude Desktop integration**
- **Toggle functionality between local development and MCP production modes**
- **4-phase implementation roadmap following PocketFlow iterative approach**
- **Comprehensive eBird API integration strategy and technical documentation**
- **Detailed eBird API 2.0 endpoint specifications and authentication requirements**
- **Enhanced utility function specifications with eBird API client functions**
- **Updated node implementation details with eBird-specific data processing**
- **Error handling and data quality management strategies for eBird data**
- **Performance optimization including caching, rate limiting, and batch processing**
- **Complete testing strategy covering unit, integration, and end-to-end scenarios**
- **Security considerations and development guidelines for API integration**
- **README acknowledgments for eBird API wrapper and tutorial references**
- **5-phase implementation roadmap with specific eBird API development steps**
- **Enhanced MCP tool architecture based on proven ebird-mcp-server patterns**
- **9 comprehensive MCP tools (7 core eBird + 2 business logic) with validated JSON schemas**
- **Centralized eBird API client design with make_request() pattern and consistent error handling**
- **Comprehensive data structure documentation for observations, hotspots, taxonomy, and notable records**
- **Updated node architecture aligned with proven endpoint patterns and dual discovery methods**

### Changed
- Migrated from requirements.txt to UV package management
- **Updated project scope from simple Q&A to specialized birding travel planning application**
- **Enhanced design to include MCP server and agent architecture for Claude Desktop accessibility**
- **Extended user stories from 3 to 5 scenarios including quick lookups and hotspot discovery**
- **Enhanced design.md with comprehensive eBird API integration section (158+ lines)**
- **Updated README.md from minimal greeting to complete project documentation**
- **Expanded utility function definitions to include specific eBird API functions**
- **Updated node specifications to include eBird data processing requirements**
- **Enhanced README acknowledgments to credit moonbirdai/ebird-mcp-server for proven MCP patterns**
- **Updated MCP tool specifications from 5 to 9 tools based on working JavaScript implementation**
- **Revised eBird API integration approach from hybrid strategy to proven pattern adaptation**
- **Enhanced node implementations with smart endpoint selection and dual discovery methods**
- **Enhanced LLM prompting strategies with domain-specific birding expertise context**
- **Professional birding guide prompting for itinerary generation with species-specific advice**
- **Expert ornithologist prompting for species validation with seasonal and behavioral context**
- **Birding expert evaluation prompting for location scoring with habitat and timing considerations**
- **Species validation logic optimization: direct eBird taxonomy lookup first, LLM fallback for fuzzy matching**
- **Data enrichment-in-place strategy replacing separate filtered data lists with constraint flags**
- **Agent orchestration enhanced to default to granular tool chaining over monolithic tool execution**

### Deprecated

### Removed
- requirements.txt (replaced by pyproject.toml)

### Fixed

### Security

## [0.1.0] - 2025-01-11

### Added
- Initial release with basic Q&A functionality
- PocketFlow workflow implementation
- OpenAI API integration
- Command-line question input interface