# Bird Travel Recommender

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/pickleton89/Bird-Travel-Recommender)

## 🏆 **Production-Ready** | 🚀 **Unified Architecture** | ✅ **Zero Breaking Changes**

An advanced birding travel planning system with enhanced natural language understanding. Features intelligent trip planning, species identification, and personalized recommendations through Claude Desktop integration. **Recently transformed with comprehensive 4-phase refactoring eliminating ~1,750 lines of duplicate code** while maintaining 100% backward compatibility.

## 🌟 Key Features

- **🏆 Unified Architecture**: Single codebase supporting both sync/async execution modes (eliminated ~1,750 lines of duplicate code)
- **✅ Zero Breaking Changes**: Complete backward compatibility maintained throughout architectural transformation
- **⚡ Professional Standards**: Dependency injection, type safety with Pydantic, structured error handling
- **Enhanced Natural Language Understanding**: Semantic intent recognition with increased accuracy
- **Intelligent Trip Planning**: Optimized routes based on recent eBird sightings
- **Experience-Level Adaptation**: Responses tailored from beginner to expert birders
- **30 Specialized MCP Tools**: Comprehensive birding functionality across 6 categories via Model Context Protocol
- **Real-time eBird Integration**: Access to 600M+ observations and 10,000+ hotspots

## 📚 Documentation

### For Users
- **[User Guide](docs/user-guide.md)** - Complete guide to using the enhanced birding assistant
- **[Examples](docs/examples-enhanced.md)** - Real-world usage examples with natural language queries
- **[API Reference](docs/api-reference.md)** - Detailed documentation of all 30 MCP tools

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
- **[Testing Guide](tests/README.md)** - Comprehensive testing framework with unified architecture support
- **[Design Document](docs/design.md)** - Original system design and requirements

## 🚀 Quick Start

### Prerequisites

1. **Install dependencies**: 
   ```bash
   uv sync
   ```

2. **Set up API keys**: 
   ```bash
   cp config/.env.example .env
   # Edit .env and add your API keys
   ```

### Standalone Usage (Without MCP)

The Bird Travel Recommender can be used as a standalone command-line application:

```bash
# Run the main application
uv run python main.py

# Or run as a module
uv run python -m bird_travel_recommender
```

#### Interactive Mode

When you run the application, you'll enter an interactive chat interface where you can:

- Ask about recent bird sightings in specific locations
- Request birding trip recommendations
- Get information about specific bird species
- Plan optimal birding routes

**Example queries:**
```
> What birds have been seen in Central Park this week?
> Plan a weekend birding trip to see warblers near San Francisco
> Is the Painted Bunting found in Texas?
> Find the best spots to see owls within 50 miles of Portland
```

#### Direct API Usage

You can also import and use the components directly in your Python code:

```python
# Recommended: Unified architecture (supports both sync/async)
from bird_travel_recommender.flow import create_unified_birding_flow, ExecutionMode

# Create a unified flow with runtime mode selection
flow = create_unified_birding_flow(ExecutionMode.ASYNC)  # or ExecutionMode.SYNC

# Use the flow to process queries
result = flow.run({
    "query": "Find recent sightings of rare birds near Austin, Texas",
    "location": "Austin, TX",
    "radius": 25
})

# Legacy approach (still supported with deprecation warnings)
from bird_travel_recommender.flow import create_birding_flow
flow = create_birding_flow()
```

## 🤖 Claude Desktop MCP Integration

The Bird Travel Recommender can be integrated with Claude Desktop to provide birding tools directly in your Claude conversations.

### Setup Instructions

1. **Deploy the MCP server**:
   ```bash
   uv run python scripts/deploy_mcp.py development
   ```

2. **Copy the configuration to Claude Desktop**:
   ```bash
   cp scripts/mcp_config_development.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```
   
   Or manually edit `~/Library/Application Support/Claude/claude_desktop_config.json` and add:
   ```json
   {
     "mcpServers": {
       "bird-travel-recommender": {
         "command": "uv",
         "args": ["run", "python", "scripts/mcp_server.py"],
         "cwd": "/path/to/Bird-Travel-Recommender",
         "env": {
           "PYTHONPATH": "src"
         }
       }
     }
   }
   ```

3. **Restart Claude Desktop** to load the new MCP server

4. **Verify the integration**: In Claude Desktop, you should now have access to 30 birding tools across 6 categories:
   - **Species Tools** (2) - Species validation and regional species lists
   - **Location Tools** (11) - Hotspot discovery, regional analysis, and geographic data
   - **Pipeline Tools** (11) - Data processing, temporal analysis, and filtering
   - **Planning Tools** (2) - Trip planning and itinerary generation
   - **Advisory Tools** (1) - Expert birding advice and recommendations
   - **Community Tools** (3) - Social features and birder statistics

### Usage Example

Once integrated, you can ask Claude Desktop questions like:
- "Find recent sightings of Painted Bunting near Austin, Texas"
- "Plan a 3-day birding trip to see warblers in Central Park"
- "What rare birds have been spotted in San Francisco this week?"

## API Keys Required

- **OPENAI_API_KEY**: Get from https://platform.openai.com/api-keys
- **EBIRD_API_KEY**: Get from https://ebird.org/api/keygen

### MCP Server Authentication

The MCP server uses **API key-based authentication**. Generate keys with the
`AuthManager` and include the raw key in the `MCP_API_KEY` environment variable
when making requests. Issued keys can also be converted into signed JWT session
tokens via `AuthManager.issue_token()` if needed.

## Acknowledgments

This project is built using [PocketFlow](https://github.com/The-Pocket/PocketFlow), a minimalist 100-line LLM framework created by Zachary Huang and The Pocket team. PocketFlow provides the core pipeline architecture that enables our node-based bird travel recommendation workflow system. PocketFlow is released under the MIT License and offers a lightweight, dependency-free approach to building AI agent workflows with support for multi-agent coordination and task decomposition.

This project's MCP tool architecture and eBird API integration patterns were significantly influenced by the [ebird-mcp-server](https://github.com/moonbirdai/ebird-mcp-server) by moonbirdai. Their working JavaScript implementation provided proven patterns for MCP tool schemas, eBird API endpoint strategies, and error handling approaches that we adapted for our Python-based PocketFlow architecture.

We also reference the [ebird-api](https://github.com/ProjectBabbler/ebird-api) Python wrapper by ProjectBabbler, distributed under the MIT License. While we implement our own custom eBird API utilities following the hybrid approach outlined in our design documentation, both projects provided valuable insights into best practices for eBird API integration.

Additional thanks to Eric Nost from the University of Guelph's Digital Conservation project for the comprehensive eBird API tutorial, which provided detailed implementation guidance and real-world usage patterns.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
