# Bird Travel Recommender

An advanced birding travel planning system with enhanced natural language understanding. Features intelligent trip planning, species identification, and personalized recommendations through Claude Desktop integration.

## 🌟 Key Features

- **Enhanced Natural Language Understanding**: Semantic intent recognition with 90-95% accuracy
- **Intelligent Trip Planning**: Optimized routes based on recent eBird sightings
- **Experience-Level Adaptation**: Responses tailored from beginner to expert birders
- **9 Specialized MCP Tools**: Comprehensive birding functionality via Model Context Protocol
- **Real-time eBird Integration**: Access to 600M+ observations and 10,000+ hotspots

## 📚 Documentation

### For Users
- **[User Guide](docs/user-guide.md)** - Complete guide to using the enhanced birding assistant
- **[Examples](docs/examples-enhanced.md)** - Real-world usage examples with natural language queries
- **[API Reference](docs/api-reference.md)** - Detailed documentation of all 9 MCP tools

### For Developers
- **[Architecture](docs/architecture.md)** - System design, data flows, and component details
- **[Developer Guide](docs/developer-guide.md)** - Extending the system and adding features
- **[Configuration](docs/configuration.md)** - Environment variables and settings reference
- **[Deployment Guide](DEPLOYMENT.md)** - MCP server deployment and configuration
- **[Development Guide](CLAUDE.md)** - Development commands and project structure

### Additional Resources
- **[Performance Guide](docs/performance.md)** - Optimization strategies and best practices
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions
- **[Contributing](CONTRIBUTING.md)** - How to contribute to the project
- **[Changelog](CHANGELOG.md)** - Detailed project history and updates
- **[Testing Guide](tests/README.md)** - Comprehensive testing framework documentation
- **[Design Document](docs/design.md)** - Original system design and requirements

## 🚀 Quick Start

1. **Install dependencies**: `uv sync`
2. **Set up API keys**: Copy `.env.example` to `.env` and add your keys
3. **Run the application**: `uv run python main.py`

For Claude Desktop integration:
```bash
python deploy_mcp.py development
```

## API Keys Required

- **OPENAI_API_KEY**: Get from https://platform.openai.com/api-keys
- **EBIRD_API_KEY**: Get from https://ebird.org/api/keygen

## Acknowledgments

This project's MCP tool architecture and eBird API integration patterns were significantly influenced by the [ebird-mcp-server](https://github.com/moonbirdai/ebird-mcp-server) by moonbirdai. Their working JavaScript implementation provided proven patterns for MCP tool schemas, eBird API endpoint strategies, and error handling approaches that we adapted for our Python-based PocketFlow architecture.

We also reference the [ebird-api](https://github.com/ProjectBabbler/ebird-api) Python wrapper by ProjectBabbler, distributed under the MIT License. While we implement our own custom eBird API utilities following the hybrid approach outlined in our design documentation, both projects provided valuable insights into best practices for eBird API integration.

Additional thanks to Eric Nost from the University of Guelph's Digital Conservation project for the comprehensive eBird API tutorial, which provided detailed implementation guidance and real-world usage patterns.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
