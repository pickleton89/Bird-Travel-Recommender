#!/usr/bin/env python3
"""
MCP Server Deployment and Configuration Manager

This script provides utilities for deploying and managing the Bird Travel Recommender
MCP server in different environments (development, production, local).
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv


class MCPDeploymentManager:
    """Manages MCP server deployment configurations and setup"""
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.config_dir = self.project_root / "scripts"
        
        # Load environment variables
        env_path = self.project_root / ".env"
        if env_path.exists():
            load_dotenv(env_path)
        
    def get_config_path(self, environment: str) -> Path:
        """Get the configuration file path for the specified environment"""
        config_files = {
            "development": "mcp_config_development.json",
            "production": "mcp_config_production.json",
            "local": "mcp_config.json"
        }
        
        config_file = config_files.get(environment, "mcp_config.json")
        return self.config_dir / config_file
    
    def load_config(self, environment: str) -> Dict[str, Any]:
        """Load MCP server configuration for the specified environment"""
        config_path = self.get_config_path(environment)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def update_config_path(self, environment: str, new_path: Optional[str] = None) -> None:
        """Update the cwd path in the configuration file"""
        config_path = self.get_config_path(environment)
        config = self.load_config(environment)
        
        # Update the cwd path - use relative path by default
        target_path = new_path or "."
        
        for server_name, server_config in config["mcpServers"].items():
            server_config["cwd"] = target_path
        
        # Write updated configuration
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"Updated {environment} configuration with path: {target_path}")
    
    def validate_environment(self) -> Dict[str, bool]:
        """Validate the deployment environment"""
        checks = {}
        
        # Check if API keys are set
        checks["openai_api_key"] = bool(os.getenv("OPENAI_API_KEY"))
        checks["ebird_api_key"] = bool(os.getenv("EBIRD_API_KEY"))
        
        # Check if required files exist
        required_files = ["mcp_server.py", "pyproject.toml", ".env"]
        for file_name in required_files:
            checks[f"file_{file_name}"] = (self.project_root / file_name).exists()
        
        # Check if uv is installed
        try:
            result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
            checks["uv_installed"] = result.returncode == 0
        except FileNotFoundError:
            checks["uv_installed"] = False
        
        # Check if dependencies are installed
        try:
            result = subprocess.run(["uv", "sync", "--check"], 
                                  cwd=self.project_root, capture_output=True, text=True)
            checks["dependencies_synced"] = result.returncode == 0
        except (FileNotFoundError, subprocess.CalledProcessError):
            checks["dependencies_synced"] = False
        
        return checks
    
    def setup_environment(self, environment: str) -> None:
        """Set up the environment for MCP server deployment"""
        print(f"Setting up {environment} environment...")
        
        # Validate environment
        checks = self.validate_environment()
        failed_checks = [k for k, v in checks.items() if not v]
        
        if failed_checks:
            print("❌ Environment validation failed:")
            for check in failed_checks:
                print(f"  - {check}")
            
            # Attempt to fix some issues
            if not checks["dependencies_synced"]:
                print("Attempting to sync dependencies...")
                try:
                    subprocess.run(["uv", "sync"], cwd=self.project_root, check=True)
                    print("✅ Dependencies synced successfully")
                except subprocess.CalledProcessError as e:
                    print(f"❌ Failed to sync dependencies: {e}")
                    return
        else:
            print("✅ Environment validation passed")
        
        # Update configuration paths
        self.update_config_path(environment)
        
        # Create environment-specific settings
        self._create_environment_settings(environment)
        
        print(f"✅ {environment.capitalize()} environment setup complete")
    
    def _create_environment_settings(self, environment: str) -> None:
        """Create environment-specific settings file"""
        settings = {
            "environment": environment,
            "log_level": "DEBUG" if environment == "development" else "INFO",
            "cache_enabled": environment != "development",
            "debug_mode": environment == "development",
            "max_concurrent_requests": 5 if environment == "development" else 10
        }
        
        settings_path = self.project_root / f".env.{environment}"
        
        with open(settings_path, 'w') as f:
            f.write(f"# {environment.upper()} ENVIRONMENT SETTINGS\\n")
            for key, value in settings.items():
                f.write(f"BIRD_TRAVEL_{key.upper()}={value}\\n")
        
        print(f"Created environment settings: {settings_path}")
    
    def test_mcp_server(self, environment: str) -> bool:
        """Test the MCP server in the specified environment"""
        print(f"Testing MCP server in {environment} environment...")
        
        try:
            # Try to run the server with a quick test
            cmd = ["uv", "run", "python", "-c", 
                   "import mcp_server; print('MCP server import successful')"]
            
            result = subprocess.run(cmd, cwd=self.project_root, 
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✅ MCP server test passed")
                return True
            else:
                print(f"❌ MCP server test failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ MCP server test timed out")
            return False
        except Exception as e:
            print(f"❌ MCP server test error: {e}")
            return False
    
    def deploy(self, environment: str, test: bool = True) -> None:
        """Deploy the MCP server for the specified environment"""
        print(f"🚀 Deploying Bird Travel Recommender MCP Server ({environment})...")
        
        # Setup environment
        self.setup_environment(environment)
        
        # Test if requested
        if test:
            if not self.test_mcp_server(environment):
                print("❌ Deployment aborted due to test failure")
                return
        
        # Display deployment information
        config = self.load_config(environment)
        server_info = list(config["mcpServers"].items())[0]
        server_name, server_config = server_info
        
        print("\\n📋 Deployment Summary:")
        print(f"  Environment: {environment}")
        print(f"  Server Name: {server_name}")
        print(f"  Working Directory: {server_config['cwd']}")
        print(f"  Command: {server_config['command']} {' '.join(server_config['args'])}")
        print(f"  Configuration File: {self.get_config_path(environment)}")
        
        print("\\n✅ MCP server deployment complete!")
        print("\\n📖 Next Steps:")
        print("1. Copy the configuration to your Claude CLI config:")
        print(f"   cp {self.get_config_path(environment)} ~/.claude/mcp_servers.json")
        print("2. Restart Claude CLI to load the new server")
        print(f"3. Test the server with: claude chat --server {server_name}")


def main():
    """Main CLI interface for MCP deployment"""
    parser = argparse.ArgumentParser(
        description="Bird Travel Recommender MCP Server Deployment Manager"
    )
    
    parser.add_argument(
        "environment", 
        choices=["development", "production", "local"],
        help="Deployment environment"
    )
    
    parser.add_argument(
        "--project-root",
        type=Path,
        help="Project root directory (default: current directory)"
    )
    
    parser.add_argument(
        "--no-test",
        action="store_true",
        help="Skip testing during deployment"
    )
    
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate environment, don't deploy"
    )
    
    parser.add_argument(
        "--update-path",
        type=str,
        help="Update configuration path to specified directory"
    )
    
    args = parser.parse_args()
    
    # Create deployment manager
    manager = MCPDeploymentManager(args.project_root)
    
    try:
        if args.validate_only:
            checks = manager.validate_environment()
            print("Environment Validation Results:")
            for check, passed in checks.items():
                status = "✅" if passed else "❌"
                print(f"  {status} {check}")
            
            failed_count = sum(1 for passed in checks.values() if not passed)
            if failed_count == 0:
                print("\\n✅ All validation checks passed!")
                sys.exit(0)
            else:
                print(f"\\n❌ {failed_count} validation check(s) failed")
                sys.exit(1)
        
        elif args.update_path:
            manager.update_config_path(args.environment, args.update_path)
        
        else:
            manager.deploy(args.environment, test=not args.no_test)
    
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()