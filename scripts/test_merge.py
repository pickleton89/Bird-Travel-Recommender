#!/usr/bin/env python3
import json
from pathlib import Path

# Load existing config with fallback paths
config_paths = [
    Path.home()
    / "Library/Application Support/Claude/claude_desktop_config.json",  # macOS
    Path.home() / ".config/claude/claude_desktop_config.json",  # Linux
    Path.home() / "AppData/Roaming/Claude/claude_desktop_config.json",  # Windows
]

config_path = None
for path in config_paths:
    if path.exists():
        config_path = path
        break

if not config_path:
    print("Error: Could not find Claude config file in any of the standard locations:")
    for path in config_paths:
        print(f"  {path}")
    exit(1)
with open(config_path) as f:
    config = json.load(f)

# Check if bird-travel-recommender exists
servers = config.get("mcpServers", {})
print("Total servers in config:", len(servers))
print("Server names:", sorted(servers.keys()))
print("\n'bird-travel-recommender' exists:", "bird-travel-recommender" in servers)

# Check for similar names
for server in servers:
    if "bird" in server.lower() or "travel" in server.lower():
        print("Found similar server:", server)
