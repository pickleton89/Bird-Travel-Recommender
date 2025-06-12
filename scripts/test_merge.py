#!/usr/bin/env python3
import json
from pathlib import Path

# Load existing config
config_path = Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"
with open(config_path) as f:
    config = json.load(f)

# Check if bird-travel-recommender exists
servers = config.get('mcpServers', {})
print("Total servers in config:", len(servers))
print("Server names:", sorted(servers.keys()))
print("\n'bird-travel-recommender' exists:", 'bird-travel-recommender' in servers)

# Check for similar names
for server in servers:
    if 'bird' in server.lower() or 'travel' in server.lower():
        print("Found similar server:", server)