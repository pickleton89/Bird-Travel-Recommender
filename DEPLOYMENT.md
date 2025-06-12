# Bird Travel Recommender MCP Server Deployment Guide

This guide covers deploying the Bird Travel Recommender MCP server for use with Claude CLI.

## Prerequisites

1. **Python Environment**: Python 3.9+ with `uv` package manager
2. **API Keys**: Valid OpenAI and eBird API keys
3. **Claude CLI**: Latest version of Claude CLI installed

## Quick Start

### 1. Environment Setup

```bash
# Clone and setup the project
cd Bird-Travel-Recommender
uv sync

# Copy environment template
cp .env.example .env

# Edit .env file with your API keys
# OPENAI_API_KEY=your_openai_key_here
# EBIRD_API_KEY=your_ebird_key_here
```

### 2. Deploy MCP Server

Choose your deployment environment:

```bash
# Development deployment (with debug logging)
python deploy_mcp.py development

# Production deployment (optimized settings)
python deploy_mcp.py production

# Local deployment (current configuration)
python deploy_mcp.py local
```

### 3. Configure Claude CLI

The deployment script will generate the appropriate configuration. Copy it to Claude CLI:

```bash
# For development
cp mcp_config_development.json ~/.claude/mcp_servers.json

# For production
cp mcp_config_production.json ~/.claude/mcp_servers.json

# For local
cp mcp_config.json ~/.claude/mcp_servers.json
```

### 4. Restart Claude CLI

Restart Claude CLI to load the new MCP server:

```bash
# Restart Claude CLI service (if running as daemon)
claude restart

# Or start a new session
claude chat
```

## Environment Configurations

### Development Environment

- **Purpose**: Development and testing
- **Features**: 
  - Debug logging enabled
  - Extended timeouts
  - Reduced cache size
  - Verbose error reporting

### Production Environment

- **Purpose**: Production use
- **Features**:
  - Optimized performance
  - Reduced logging
  - Caching enabled
  - Higher concurrency limits

### Local Environment

- **Purpose**: Local testing and personal use
- **Features**:
  - Balanced configuration
  - Standard timeouts
  - Moderate logging

## Available MCP Tools

The Bird Travel Recommender MCP server provides 9 specialized birding tools:

### Core eBird Data Tools

1. **validate_species** - Validate bird species names using eBird taxonomy
2. **fetch_sightings** - Retrieve recent bird sightings data
3. **filter_constraints** - Apply geographic and temporal filters
4. **cluster_hotspots** - Identify optimal birding locations
5. **score_locations** - Evaluate birding potential of destinations
6. **optimize_route** - Calculate optimal travel routes
7. **generate_itinerary** - Create detailed birding trip plans

### Business Logic Tools

8. **plan_complete_trip** - End-to-end trip planning orchestration
9. **get_birding_advice** - Expert birding advice and recommendations

## Usage Examples

### Using with Claude CLI

```bash
# Start Claude CLI session
claude chat --server bird-travel-recommender

# Example queries
"Plan a birding trip to see Northern Cardinals in Massachusetts"
"What equipment do I need for winter birding?"
"Find the best birding locations near Boston"
"Create an itinerary for a 3-day birding trip in Texas"
```

### Tool-Specific Queries

```bash
# Species validation
"Validate these bird species: Northern Cardinal, Blue Jay, American Robin"

# Location clustering
"Find birding hotspots within 50km of Boston"

# Route optimization
"Optimize a route between these birding locations: [locations]"
```

## Advanced Configuration

### Custom Environment Variables

Add these to your `.env` file for advanced configuration:

```bash
# Logging
BIRD_TRAVEL_LOG_LEVEL=DEBUG
BIRD_TRAVEL_CACHE_SIZE=1000

# API Settings
BIRD_TRAVEL_REQUEST_TIMEOUT=30
BIRD_TRAVEL_MAX_RETRIES=3

# Performance
BIRD_TRAVEL_MAX_CONCURRENT_REQUESTS=10
```

### Configuration File Customization

Edit the MCP configuration files directly:

- `mcp_config_development.json` - Development settings
- `mcp_config_production.json` - Production settings  
- `mcp_config.json` - Local settings

## Troubleshooting

### Common Issues

1. **API Keys Not Found**
   ```bash
   # Verify environment variables
   echo $OPENAI_API_KEY
   echo $EBIRD_API_KEY
   
   # Check .env file
   cat .env
   ```

2. **MCP Server Won't Start**
   ```bash
   # Test server manually
   uv run python mcp_server.py
   
   # Check dependencies
   uv sync
   ```

3. **Claude CLI Can't Find Server**
   ```bash
   # Verify configuration
   cat ~/.claude/mcp_servers.json
   
   # Test configuration
   python deploy_mcp.py development --validate-only
   ```

### Deployment Validation

Use the deployment script to validate your environment:

```bash
# Validate environment only
python deploy_mcp.py development --validate-only

# Test MCP server
python deploy_mcp.py development --test-only

# Update configuration paths
python deploy_mcp.py production --update-path /path/to/project
```

### Debug Mode

Enable debug mode for troubleshooting:

```bash
# Deploy with debug settings
python deploy_mcp.py development

# Or set environment variable
export BIRD_TRAVEL_LOG_LEVEL=DEBUG
```

## Performance Optimization

### Production Settings

- Enable caching: `BIRD_TRAVEL_CACHE_ENABLED=true`
- Optimize concurrency: `BIRD_TRAVEL_MAX_CONCURRENT_REQUESTS=10`
- Set appropriate timeouts: `BIRD_TRAVEL_REQUEST_TIMEOUT=30`

### Memory Management

- Limit cache size: `BIRD_TRAVEL_CACHE_SIZE=1000`
- Monitor memory usage with system tools
- Restart server periodically for long-running deployments

## Security Considerations

1. **API Key Management**
   - Store API keys in environment variables
   - Never commit API keys to version control
   - Use different keys for development/production

2. **Access Control**
   - MCP server runs locally for security
   - No external network access required
   - API keys are only used for external services

3. **Data Privacy**
   - No user data is stored permanently
   - All processing happens locally
   - External APIs used only for bird data

## Support and Maintenance

### Updating the Server

```bash
# Pull latest changes
git pull origin main

# Sync dependencies
uv sync

# Redeploy
python deploy_mcp.py production
```

### Monitoring

- Check logs for errors: Look for ERROR/WARNING messages
- Monitor API usage: Track API key usage limits
- Performance metrics: Response times and success rates

### Backup Configuration

```bash
# Backup current configuration
cp ~/.claude/mcp_servers.json ~/.claude/mcp_servers.json.backup

# Restore if needed
cp ~/.claude/mcp_servers.json.backup ~/.claude/mcp_servers.json
```

## Contributing

For development and contributions:

1. Use development environment: `python deploy_mcp.py development`
2. Run tests: `uv run pytest`
3. Check code quality: `uv run ruff check`
4. Follow the established patterns in the codebase

## License

This project is licensed under the MIT License. See LICENSE file for details.