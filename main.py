#!/usr/bin/env python3
"""
Bird Travel Recommender - Entry Point

Simple entry point script that delegates to the main package.
For development convenience - allows running 'python main.py' from root.
"""

import sys
from pathlib import Path

# Add src to Python path for development
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from bird_travel_recommender.main import main

if __name__ == "__main__":
    main()