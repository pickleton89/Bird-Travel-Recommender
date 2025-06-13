# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **eBird API expansion Phase 4: Comprehensive testing and validation with critical MCP handler fixes**
- **Critical MCP handler signature fix applied to all 4 new eBird API expansion endpoints**
- **Removed problematic **kwargs parameters preventing Claude Desktop integration errors**
- **Unit test suite (test_ebird_api_expansion.py) with 20+ comprehensive test methods**
- **Integration test suite (test_mcp_tools_expansion.py) for MCP tool validation**
- **Manual testing script (test_new_endpoints.py) with CLI interface and performance testing**
- **Complete test coverage for parameter validation, error handling, and response format validation**
- **eBird API expansion Phase 3: Enhanced business logic integration with comprehensive endpoint utilization**
- **Enhanced plan_complete_trip tool with region info for user-friendly region names in trip planning**
- **Regional species list integration for validation and suggestions in trip planning pipeline**
- **Hotspot detail enrichment with comprehensive metadata and statistics for location scoring**
- **Targeted species finding recommendations using nearest observations for each target species**
- **Enhanced get_birding_advice tool with regional species context and nearest observations data**
- **Enriched trip plan responses with region display names, enriched hotspots, and species finding recommendations**
- **Enhanced summary statistics including regional diversity, enriched hotspots, and targeted recommendation counts**
- **eBird API expansion Phase 2: MCP server integration with 4 new tools for Claude Desktop**
- **find_nearest_species MCP tool - Find closest species observations with structured response handling**
- **get_regional_species_list MCP tool - Complete regional species lists via MCP interface**
- **get_region_details MCP tool - Human-readable region metadata through MCP**
- **get_hotspot_details MCP tool - Detailed hotspot information accessible via MCP**
- **Enhanced MCP server with 13 total tools (9 original + 4 new) for comprehensive birding functionality**
- **Tool router updates in handle_call_tool() method with proper error handling and structured responses**
- **eBird API expansion Phase 1: 4 new high-priority endpoints implemented in ebird_api.py**
- **get_nearest_observations() method - Find closest locations where specific species was recently observed**
- **get_species_list() method - Complete species list ever reported in a region**
- **get_region_info() method - Region metadata and human-readable names**
- **get_hotspot_info() method - Detailed hotspot information and activity metrics**
- **Convenience functions for all new endpoints following existing module patterns**
- **eBird API expansion implementation plan (docs/planning/ebird-api-expansion-plan.md) for 4 high-priority endpoints**
- **Comprehensive API gap analysis identifying 19 missing eBird endpoints from technical research documentation**
- **Detailed specifications for get_nearest_observations(), get_species_list(), get_region_info(), get_hotspot_info()**
- **3-week implementation timeline with structured phases for API expansion, MCP integration, and testing**
- **Quality assurance checklist and risk mitigation strategies for eBird API enhancement**
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
- **Phase 1 implementation: Core pipeline foundation with 3 production-ready nodes (June 2025)**
- **Centralized eBird API client (utils/ebird_api.py) with full taxonomy integration (17,415 species)**
- **ValidateSpeciesNode with direct eBird taxonomy lookup and LLM fallback for fuzzy matching**
- **FetchSightingsNode as BatchNode with parallel processing and smart endpoint selection**
- **FilterConstraintsNode with enrichment-in-place strategy and comprehensive constraint validation**
- **Geospatial utility functions (utils/geo_utils.py) with Haversine distance calculations**
- **Comprehensive test suite with mock data and live API validation**
- **requests dependency added for HTTP client functionality**
- **Step 1.5: Modern pytest testing framework with comprehensive mock system and 43 test methods**
- **Production-ready testing infrastructure with unit, integration, and performance tests**
- **pytest, pytest-mock, and pytest-asyncio dependencies for advanced testing capabilities**
- **Complete eBird API mocking system with realistic response data for consistent testing**
- **Test utilities including data generators, validators, and performance measurement tools**
- **Testing documentation (tests/README.md) with usage examples and troubleshooting guide**
- **Phase 2 implementation: Complete data processing pipeline with 4 additional production-ready nodes (June 2025)**
- **ClusterHotspotsNode with dual hotspot discovery and location deduplication using coordinate-based normalization**
- **ScoreLocationsNode with multi-criteria scoring (diversity 40%, recency 25%, hotspot 20%, accessibility 15%)**
- **OptimizeRouteNode with TSP-style algorithms, 2-opt improvement, and nearest neighbor fallbacks**
- **GenerateItineraryNode (AsyncNode) with LLM-enhanced professional birding itinerary generation**
- **Route optimization utility (utils/route_optimizer.py) with traveling salesman algorithms and computational efficiency assessment**
- **Complete 7-node birding pipeline flow with enrichment-in-place data strategy**
- **Enhanced main.py CLI interface with argument parsing, file I/O, debug logging, and statistics reporting**
- **Comprehensive error handling and graceful degradation throughout all pipeline nodes**
- **LLM-enhanced habitat evaluation for top-scoring locations with expert birding guidance**
- **Professional birding itinerary generation with equipment recommendations, timing advice, and field techniques**
- **BatchNode parallel processing for API efficiency and AsyncNode retry logic for LLM reliability**
- **Production-ready pipeline supporting both test data and custom JSON input files**

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
- **Comprehensive error recovery strategy with flow-level retry logic and fallback mechanisms**
- **Node type specifications added (Regular, BatchNode, Async) with performance and retry implications**
- **MCP/Local execution mode parity validation framework for consistency testing**
- **Enhanced testing strategy with unit, integration, and performance testing frameworks**
- **Node ownership markers added for team collaboration and responsibility tracking**
- **Flow retry diagram and error recovery patterns documented for production reliability**

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