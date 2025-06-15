# Bird Travel Recommender MCP Server Deployment Guide

This guide covers deploying the Bird Travel Recommender MCP server for use with Claude CLI and Claude Desktop.

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

# Generate the authentication secret
mkdir -p config
openssl rand -hex 32 > config/.auth_secret
```

### 2. Deploy MCP Server

Choose your deployment environment:

```bash
# Development deployment (with debug logging)
uv run python scripts/deploy_mcp.py development

# Production deployment (optimized settings)
uv run python scripts/deploy_mcp.py production

# Local deployment (current configuration)
uv run python scripts/deploy_mcp.py local
```

### 3. Configure Claude Desktop or Claude CLI

#### Option A: Claude Desktop (Recommended)

Use the safe merge script to add the MCP server to Claude Desktop:

```bash
# Preview changes without applying
uv run python scripts/merge_mcp_config.py --dry-run

# Apply changes with automatic backup
uv run python scripts/merge_mcp_config.py --yes
```

The script will:
- Automatically backup your existing configuration
- Merge the bird-travel-recommender server with your existing MCP servers
- Use the correct `uv` configuration with `--directory` flag
- Preserve all your existing settings

#### Option B: Claude CLI

Copy the configuration to Claude CLI:

```bash
# For development
cp scripts/mcp_config_development.json ~/.claude/mcp_servers.json

# For production  
cp mcp_config_production.json ~/.claude/mcp_servers.json
```

### 4. Restart Claude

#### For Claude Desktop:
1. Quit Claude Desktop completely
2. Restart Claude Desktop
3. The bird-travel-recommender server should appear in your MCP servers list

#### For Claude CLI:
```bash
# Restart Claude CLI service (if running as daemon)
claude restart

# Or start a new session
claude chat --server bird-travel-recommender
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

The Bird Travel Recommender MCP server provides 32 specialized birding tools across 6 categories:

### Species Tools (2)
- **validate_species** - Validate bird species names using eBird taxonomy
- **get_regional_species_list** - Get comprehensive species list for regions

### Location Tools (12)
- **get_region_details** - Geographic region information and statistics
- **get_hotspot_details** - Detailed birding hotspot information
- **find_nearest_species** - Find closest observations of specific species
- **get_nearby_notable_observations** - Rare/notable observations near coordinates
- **get_nearby_species_observations** - Recent species observations near coordinates
- **get_top_locations** - Most active birding locations in regions
- **get_regional_statistics** - Species counts and activity statistics
- **get_location_species_list** - Complete species lists for locations
- **get_subregions** - Subregions within geographic areas
- **get_adjacent_regions** - Neighboring regions for cross-border planning
- **get_elevation_data** - Elevation and habitat zone analysis

### Pipeline Tools (12)
- **fetch_sightings** - Retrieve recent bird sightings data
- **filter_constraints** - Apply geographic and temporal filters
- **cluster_hotspots** - Identify optimal birding locations
- **score_locations** - Evaluate birding potential of destinations
- **optimize_route** - Calculate optimal travel routes
- **get_historic_observations** - Historical observations for temporal analysis
- **get_seasonal_trends** - Seasonal birding patterns and trends
- **get_yearly_comparisons** - Multi-year activity comparisons
- **get_migration_data** - Species migration timing and routes
- **get_peak_times** - Optimal daily timing recommendations
- **get_seasonal_hotspots** - Season-optimized location rankings

### Planning Tools (2)
- **generate_itinerary** - Create detailed birding trip plans
- **plan_complete_trip** - End-to-end trip planning orchestration

### Advisory Tools (1)
- **get_birding_advice** - Expert birding advice and recommendations

### Community Tools (3)
- **get_recent_checklists** - Recent birding checklists in regions
- **get_checklist_details** - Detailed checklist information
- **get_user_stats** - Birder profiles and statistics

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

## Claude Desktop Configuration

### Safe Configuration Merging

The project includes a safe merge script (`scripts/merge_mcp_config.py`) that preserves your existing Claude Desktop configuration:

```bash
# Preview what changes will be made
uv run python scripts/merge_mcp_config.py --dry-run

# Apply changes with automatic backup
uv run python scripts/merge_mcp_config.py --yes

# Apply without backup (not recommended)
uv run python scripts/merge_mcp_config.py --no-backup
```

### Features:
- **Automatic backup**: Creates timestamped backups in `~/Library/Application Support/Claude/claude_config_backups/`
- **Conflict detection**: Warns if server names already exist
- **Preview mode**: Shows exactly what will change before applying
- **Safe merging**: Only adds new servers, never overwrites existing ones

### Manual Configuration

If you prefer to manually edit your Claude Desktop configuration:

1. Open: `~/Library/Application Support/Claude/claude_desktop_config.json`
2. Add the bird-travel-recommender server to the `mcpServers` section:

```json
{
  "mcpServers": {
    "bird-travel-recommender": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/Users/your-username/path/to/Bird-Travel-Recommender",
        "python",
        "scripts/mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "src"
      }
    }
  }
}
```

**Important**: Use the `--directory` flag to ensure `uv` finds the correct project dependencies.

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
   uv run --directory /path/to/Bird-Travel-Recommender python scripts/mcp_server.py
   
   # Check dependencies
   uv sync
   ```

3. **"Module not found" errors (pocketflow, mcp)**
   This occurs when `uv` can't find the project dependencies. Fix with:
   ```bash
   # Use --directory flag to specify project path
   # Update your Claude Desktop config to use:
   "command": "uv",
   "args": [
     "run",
     "--directory",
     "/full/path/to/Bird-Travel-Recommender",
     "python",
     "scripts/mcp_server.py"
   ]
   ```

4. **"name 'true' is not defined" error**
   This is a Python syntax error. Ensure all JSON boolean values use Python syntax:
   ```python
   # Wrong (JSON syntax)
   "default": true
   
   # Correct (Python syntax) 
   "default": True
   ```

5. **MCP Server Disabled in Claude Desktop**
   Check the Claude Desktop logs for errors. Common causes:
   - Import errors (see #3 above)
   - Syntax errors (see #4 above)
   - Missing dependencies (`uv sync`)

6. **Claude CLI Can't Find Server**
   ```bash
   # Verify configuration
   cat ~/.claude/mcp_servers.json
   
   # Test configuration
   uv run python scripts/deploy_mcp.py development --validate-only
   ```

### Deployment Validation

Use the deployment script to validate your environment:

```bash
# Validate environment only
uv run python scripts/deploy_mcp.py development --validate-only

# Test MCP server
uv run python scripts/deploy_mcp.py development --test-only

# Update configuration paths
uv run python scripts/deploy_mcp.py production --update-path /path/to/project
```

### Debug Mode

Enable debug mode for troubleshooting:

```bash
# Deploy with debug settings
uv run python scripts/deploy_mcp.py development

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
uv run python scripts/deploy_mcp.py production
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

1. Use development environment: `uv run python scripts/deploy_mcp.py development`
2. Run tests: `uv run pytest`
3. Check code quality: `uv run ruff check`
4. Follow the established patterns in the codebase

## License

This project is licensed under the MIT License. See LICENSE file for details.