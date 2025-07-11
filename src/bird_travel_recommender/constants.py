"""
Constants for the Bird Travel Recommender application.

This module contains all magic numbers and configuration constants used throughout
the application, centralized for easy maintenance and modification.
"""

# =============================================================================
# API Configuration Constants
# =============================================================================

# eBird API Limits and Defaults
EBIRD_MAX_RESULTS_DEFAULT = 100
EBIRD_MAX_RESULTS_LIMIT = 10000
EBIRD_DAYS_BACK_DEFAULT = 30
EBIRD_DAYS_BACK_MAX = 30
EBIRD_RADIUS_KM_DEFAULT = 25
EBIRD_RADIUS_KM_MAX = 50

# Request timeouts (seconds)
HTTP_TIMEOUT_DEFAULT = 30
HTTP_TIMEOUT_LONG = 60

# =============================================================================
# Geographic and Distance Constants
# =============================================================================

# Distance calculations
CLUSTER_RADIUS_KM_DEFAULT = 15.0
MAX_DAILY_DISTANCE_KM_DEFAULT = 200
SEARCH_RADIUS_KM_DEFAULT = 25

# Coordinate validation
LATITUDE_MIN = -90.0
LATITUDE_MAX = 90.0
LONGITUDE_MIN = -180.0
LONGITUDE_MAX = 180.0

# =============================================================================
# Pipeline Processing Constants
# =============================================================================

# Concurrency limits
MAX_WORKERS_DEFAULT = 5
MAX_WORKERS_HIGH = 10

# Batch processing
BATCH_SIZE_DEFAULT = 100
BATCH_SIZE_LARGE = 500

# Location and route optimization
MAX_LOCATIONS_FOR_OPTIMIZATION = 12
MAX_LOCATIONS_PER_DAY = 8
MIN_LOCATION_SCORE = 0.3

# =============================================================================
# Time and Date Constants
# =============================================================================

# Travel planning
MAX_DAYS_DEFAULT = 3
MAX_DAYS_EXTENDED = 14

# Seasonal patterns (months)
PEAK_BIRDING_MONTHS = [4, 5, 9, 10]  # April, May, September, October
BREEDING_SEASON_MONTHS = [4, 5, 6, 7, 8]  # April through August

# =============================================================================
# LLM and NLP Constants
# =============================================================================

# Retry configuration
MAX_RETRIES_DEFAULT = 3
MAX_RETRIES_HIGH = 5

# Token limits
MAX_TOKEN_LIMIT = 4000
PROMPT_TOKEN_BUFFER = 500

# =============================================================================
# Data Processing Constants
# =============================================================================

# Statistics and scoring
MIN_CONFIDENCE_SCORE = 0.5
HIGH_CONFIDENCE_SCORE = 0.8

# Data validation
MIN_OBSERVATIONS_THRESHOLD = 5
MIN_HOTSPOTS_THRESHOLD = 3

# =============================================================================
# Route Optimization Constants
# =============================================================================

# Driving speed assumptions (km/h)
AVERAGE_DRIVING_SPEED = 60.0
CITY_DRIVING_SPEED = 40.0
HIGHWAY_DRIVING_SPEED = 80.0

# Route planning
MAX_ROUTE_SEGMENTS = 20
MIN_STOP_DURATION_HOURS = 1.0
MAX_STOP_DURATION_HOURS = 4.0

# =============================================================================
# File and Resource Constants
# =============================================================================

# File size limits (bytes)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_LOG_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Cache settings
CACHE_TTL_SECONDS = 3600  # 1 hour
CACHE_MAX_ENTRIES = 1000

# =============================================================================
# Placeholder Data Constants
# =============================================================================

# Default values for missing data
DEFAULT_ELEVATION_M = 250
DEFAULT_SPECIES_COUNT = 0
DEFAULT_OBSERVATION_COUNT = 0

# Simulation ranges for demo data
SIMULATED_SPECIES_MIN = 50
SIMULATED_SPECIES_MAX = 500
SIMULATED_CHECKLISTS_MIN = 20
SIMULATED_CHECKLISTS_MAX = 200
