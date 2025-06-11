# Bird Travel Recommender

A PocketFlow-based birding travel planning application that generates optimal routes for bird observation trips using eBird data. The system uses a node-based workflow architecture with MCP integration for natural language interaction through Claude Desktop.

## Features

- **Intelligent Species Validation**: Convert common bird names to eBird species codes
- **Real-time Sighting Data**: Query recent bird observations from eBird API
- **Route Optimization**: Calculate optimal travel routes to maximize species diversity
- **Natural Language Interface**: Accessible through Claude Desktop via Model Context Protocol
- **Local Development Mode**: Test and develop pipeline locally without MCP overhead

## Quick Start

1. **Install dependencies**: `uv sync`
2. **Set up API keys**: Copy `.env.example` to `.env` and add your keys
3. **Run the application**: `uv run python main.py`

See [CLAUDE.md](CLAUDE.md) for detailed development commands and architecture overview.

## Architecture

The application follows a dual-layer architecture:
- **MCP Agent Layer**: Natural language interface for Claude Desktop
- **Birding Pipeline Layer**: Core business logic with 7-node workflow

For detailed design documentation, see [docs/design.md](docs/design.md).

## API Keys Required

- **OPENAI_API_KEY**: Get from https://platform.openai.com/api-keys
- **EBIRD_API_KEY**: Get from https://ebird.org/api/keygen

## Acknowledgments

This project's eBird API integration was developed with reference to the [ebird-api](https://github.com/ProjectBabbler/ebird-api) Python wrapper by ProjectBabbler, distributed under the MIT License. While we implement our own custom eBird API utilities following the hybrid approach outlined in our design documentation, the wrapper provided valuable insights into best practices for eBird API integration.

We also acknowledge the comprehensive eBird API tutorial by Eric Nost from the University of Guelph's Digital Conservation project, which provided detailed implementation guidance and real-world usage patterns.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
