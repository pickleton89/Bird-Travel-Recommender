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

### Changed
- Migrated from requirements.txt to UV package management
- **Updated project scope from simple Q&A to specialized birding travel planning application**

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