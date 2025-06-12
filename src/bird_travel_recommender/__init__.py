"""
Bird Travel Recommender - A PocketFlow-based birding travel planning system.

This package provides intelligent birding trip recommendations using eBird data
and LLM-powered itinerary generation.
"""

__version__ = "0.1.0"
__author__ = "Bird Travel Recommender Team"

from .flow import run_birding_pipeline, create_birding_flow
from .main import main

__all__ = ["run_birding_pipeline", "create_birding_flow", "main"]