#!/usr/bin/env python3
"""
Safe MCP Config Merger - Merges MCP server configurations without overwriting existing settings.
Backs up original config and provides preview of changes before applying.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import argparse
import sys


def load_json_file(filepath: Path) -> Dict[str, Any]:
    """Load JSON configuration from file."""
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: {filepath} not found. Creating new config.")
        return {"mcpServers": {}}
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {filepath}: {e}")
        sys.exit(1)


def backup_config(config_path: Path) -> Optional[Path]:
    """Create timestamped backup of existing config."""
    if not config_path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = config_path.parent / "claude_config_backups"
    backup_dir.mkdir(exist_ok=True)

    backup_path = backup_dir / f"claude_desktop_config_{timestamp}.json"
    shutil.copy2(config_path, backup_path)
    print(f"✓ Backed up existing config to: {backup_path}")
    return backup_path


def merge_configs(existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """Merge new MCP servers into existing config, preserving all existing settings."""
    # Deep copy to avoid modifying original
    import copy

    merged = copy.deepcopy(existing)

    # Ensure mcpServers key exists
    if "mcpServers" not in merged:
        merged["mcpServers"] = {}

    # Merge new servers
    if "mcpServers" in new:
        for server_name, server_config in new["mcpServers"].items():
            if server_name in merged["mcpServers"]:
                print(f"⚠️  Warning: '{server_name}' already exists in config")
            else:
                merged["mcpServers"][server_name] = server_config

    return merged


def show_diff(
    existing: Dict[str, Any], merged: Dict[str, Any], new_config: Dict[str, Any]
) -> None:
    """Show what changes will be made."""
    existing_servers = set(existing.get("mcpServers", {}).keys())
    new_config_servers = set(new_config.get("mcpServers", {}).keys())
    merged_servers = set(merged.get("mcpServers", {}).keys())

    # Only show servers that are truly new (not in existing)
    new_servers = new_config_servers - existing_servers
    updated_servers = new_config_servers & existing_servers

    print("\n📋 Config Changes Preview:")
    print("-" * 50)

    # Show existing servers
    if existing_servers:
        print("📦 Existing MCP servers:")
        for server in sorted(existing_servers):
            print(f"   - {server}")

    # Show new servers
    if new_servers:
        print("\n✨ New MCP servers to be added:")
        for server in sorted(new_servers):
            print(f"   - {server}")
            config = new_config["mcpServers"][server]
            print(f"     Command: {config.get('command', 'N/A')}")
            if "cwd" in config:
                print(f"     Working Dir: {config['cwd']}")

    # Show servers that would be updated
    if updated_servers:
        print("\n⚠️  Servers that already exist (will be skipped):")
        for server in sorted(updated_servers):
            print(f"   - {server}")

    if not new_servers and not updated_servers:
        print("\nNo changes to make.")

    print(f"\n📊 Total servers after merge: {len(merged_servers)}")
    print("-" * 50)


def main():
    parser = argparse.ArgumentParser(description="Safely merge MCP configurations")
    parser.add_argument(
        "--source",
        type=str,
        default="scripts/mcp_config_development.json",
        help="Source MCP config file to merge from",
    )
    parser.add_argument(
        "--target",
        type=str,
        default=os.path.expanduser(
            "~/Library/Application Support/Claude/claude_desktop_config.json"
        ),
        help="Target Claude desktop config file",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without applying them"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating backup (not recommended)",
    )
    parser.add_argument(
        "--yes", "-y", action="store_true", help="Skip confirmation prompt"
    )

    args = parser.parse_args()

    # Convert to Path objects
    source_path = Path(args.source)
    target_path = Path(args.target)

    # Ensure source exists
    if not source_path.exists():
        print(f"Error: Source file {source_path} not found")
        sys.exit(1)

    # Load configurations
    print(f"📖 Loading source config from: {source_path}")
    new_config = load_json_file(source_path)

    print(f"📖 Loading target config from: {target_path}")
    existing_config = load_json_file(target_path)

    # Update cwd for bird-travel-recommender to absolute path
    if (
        "mcpServers" in new_config
        and "bird-travel-recommender" in new_config["mcpServers"]
    ):
        if new_config["mcpServers"]["bird-travel-recommender"].get("cwd") == ".":
            new_config["mcpServers"]["bird-travel-recommender"]["cwd"] = str(Path.cwd())

    # Merge configurations
    merged_config = merge_configs(existing_config, new_config)

    # Show preview
    show_diff(existing_config, merged_config, new_config)

    if args.dry_run:
        print("\n🔍 DRY RUN - No changes made")
        return

    # Confirm with user unless --yes flag is used
    if not args.yes:
        response = input("\n🤔 Apply these changes? (yes/no): ").lower().strip()
        if response not in ["yes", "y"]:
            print("❌ Merge cancelled")
            return

    # Backup if requested
    if not args.no_backup and target_path.exists():
        backup_config(target_path)

    # Write merged config
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "w") as f:
        json.dump(merged_config, f, indent=2)

    print(f"\n✅ Successfully merged config to: {target_path}")
    print("🔄 Please restart Claude for changes to take effect")


if __name__ == "__main__":
    main()
