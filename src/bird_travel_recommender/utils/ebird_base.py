"""
Base eBird API client with core infrastructure and HTTP handling.

This module provides the foundational components for the eBird API client,
including error handling, session management, and the core request mechanism.
"""

import os
import time
import requests
from requests.exceptions import Timeout, ConnectionError
from typing import Dict, Any, Optional, Union, List
from dotenv import load_dotenv
import logging
from ..constants import HTTP_TIMEOUT_DEFAULT

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


class EBirdAPIError(Exception):
    """Custom exception for eBird API errors."""

    pass


class EBirdBaseClient:
    """
    Base eBird API client with core infrastructure.

    Provides the foundational HTTP handling, authentication, and error management
    that all specialized eBird API modules inherit from.

    Features:
    - Centralized make_request() method for all HTTP interactions
    - Consistent error handling with formatted messages
    - Rate limiting with exponential backoff
    - Connection reuse for multiple sequential requests
    - Session management with proper cleanup
    """

    BASE_URL = "https://api.ebird.org/v2"
    MAX_RETRIES = 3
    INITIAL_DELAY = 1.0  # seconds

    def __init__(self):
        """Initialize the eBird API client with authentication and session setup."""
        self.api_key = os.getenv("EBIRD_API_KEY")
        if not self.api_key:
            raise ValueError(
                "EBIRD_API_KEY not found in environment variables. "
                "Please get your key from https://ebird.org/api/keygen and add it to your .env file."
            )

        # Create session for connection reuse
        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-eBirdApiToken": self.api_key,
                "User-Agent": "Bird-Travel-Recommender/1.0",
            }
        )

    def make_request(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Union[List[Dict], Dict, str]:
        """
        Centralized request handler for all eBird API interactions.

        This method handles all HTTP communication with the eBird API, including
        authentication, error handling, rate limiting, and retries with exponential backoff.

        Args:
            endpoint: API endpoint path (e.g., "/data/obs/US-MA/recent")
            params: Query parameters dictionary

        Returns:
            API response data (parsed JSON)

        Raises:
            EBirdAPIError: For API errors with descriptive messages
        """
        url = f"{self.BASE_URL}{endpoint}"
        delay = self.INITIAL_DELAY

        for attempt in range(self.MAX_RETRIES):
            try:
                logger.debug(
                    f"Making eBird API request: {endpoint} (attempt {attempt + 1})"
                )
                response = self.session.get(
                    url, params=params, timeout=HTTP_TIMEOUT_DEFAULT
                )

                # Handle different HTTP status codes
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 400:
                    raise EBirdAPIError(
                        f"Bad request: Invalid parameters for {endpoint}"
                    )
                elif response.status_code == 404:
                    raise EBirdAPIError(
                        f"Not found: Invalid region or species code for {endpoint}"
                    )
                elif response.status_code == 429:
                    # Rate limit exceeded - exponential backoff
                    if attempt < self.MAX_RETRIES - 1:
                        logger.warning(
                            f"Rate limit exceeded, waiting {delay}s before retry"
                        )
                        time.sleep(delay)
                        delay *= 2  # Exponential backoff
                        continue
                    else:
                        raise EBirdAPIError(
                            "Rate limit exceeded - please try again later"
                        )
                elif response.status_code >= 500:
                    # Server error - retry with backoff
                    if attempt < self.MAX_RETRIES - 1:
                        logger.warning(
                            f"Server error {response.status_code}, retrying in {delay}s"
                        )
                        time.sleep(delay)
                        delay *= 2
                        continue
                    else:
                        raise EBirdAPIError(
                            f"Server error: eBird API returned {response.status_code}"
                        )
                else:
                    raise EBirdAPIError(f"Unexpected response: {response.status_code}")

            except Timeout:
                if attempt < self.MAX_RETRIES - 1:
                    logger.warning(f"Request timeout, retrying in {delay}s")
                    time.sleep(delay)
                    delay *= 2
                    continue
                else:
                    raise EBirdAPIError("Request timeout - eBird API is not responding")

            except ConnectionError:
                if attempt < self.MAX_RETRIES - 1:
                    logger.warning(f"Connection error, retrying in {delay}s")
                    time.sleep(delay)
                    delay *= 2
                    continue
                else:
                    raise EBirdAPIError("Connection error - unable to reach eBird API")

        raise EBirdAPIError("Maximum retries exceeded")

    def close(self):
        """Close the HTTP session and clean up resources."""
        if hasattr(self, "session"):
            self.session.close()
            logger.debug("eBird API session closed")
