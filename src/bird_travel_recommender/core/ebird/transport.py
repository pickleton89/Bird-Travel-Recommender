"""
Transport layer implementations for eBird API clients.

This module provides both sync and async transport implementations
that share the same interface, eliminating code duplication.
"""

import asyncio
from typing import Dict, Any
import httpx
import aiohttp
from ..config.settings import settings
from ..config.logging import get_logger
from ..exceptions import (
    EBirdAPIError,
    EBirdAuthenticationError,
    EBirdRateLimitError,
    EBirdTimeoutError,
    EBirdServerError,
)
from .protocols import EBirdTransportProtocol


class HttpxTransport:
    """
    Synchronous transport using httpx.
    
    Provides sync HTTP transport with automatic error handling
    and retry logic.
    """
    
    def __init__(self, api_key: str, base_url: str = None):
        self.api_key = api_key
        self.base_url = base_url or settings.ebird_base_url
        self.logger = get_logger(__name__)
        
        self.client = httpx.Client(
            headers={"X-eBirdApiToken": api_key},
            timeout=settings.request_timeout
        )
        
    async def request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make synchronous request (wrapped for async compatibility).
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            JSON response data
            
        Raises:
            EBirdAPIError: For various API errors
        """
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(settings.ebird_max_retries):
            try:
                self.logger.debug(f"Making request to {url} with params {params}")
                
                response = self.client.get(url, params=params)
                
                # Handle different status codes
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    raise EBirdAuthenticationError(
                        "Invalid eBird API key",
                        status_code=response.status_code,
                        endpoint=endpoint
                    )
                elif response.status_code == 429:
                    raise EBirdRateLimitError(
                        "Rate limit exceeded",
                        status_code=response.status_code,
                        endpoint=endpoint
                    )
                elif 500 <= response.status_code < 600:
                    raise EBirdServerError(
                        f"Server error: {response.status_code}",
                        status_code=response.status_code,
                        endpoint=endpoint
                    )
                else:
                    raise EBirdAPIError(
                        f"API error: {response.status_code} - {response.text}",
                        status_code=response.status_code,
                        endpoint=endpoint
                    )
                    
            except httpx.TimeoutException:
                if attempt == settings.ebird_max_retries - 1:
                    raise EBirdTimeoutError(
                        f"Request timeout after {settings.request_timeout}s",
                        endpoint=endpoint
                    )
                    
                # Wait before retry
                await asyncio.sleep(settings.ebird_initial_delay * (2 ** attempt))
                
            except httpx.ConnectError as e:
                if attempt == settings.ebird_max_retries - 1:
                    raise EBirdAPIError(
                        f"Connection error: {str(e)}",
                        endpoint=endpoint
                    )
                    
                # Wait before retry
                await asyncio.sleep(settings.ebird_initial_delay * (2 ** attempt))
                
        # Should not reach here
        raise EBirdAPIError("Max retries exceeded", endpoint=endpoint)
        
    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()


class AiohttpTransport:
    """
    Asynchronous transport using aiohttp.
    
    Provides async HTTP transport with automatic error handling
    and retry logic.
    """
    
    def __init__(self, api_key: str, base_url: str = None):
        self.api_key = api_key
        self.base_url = base_url or settings.ebird_base_url
        self.logger = get_logger(__name__)
        self.session = None
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Lazy session creation."""
        if self.session is None:
            headers = {"X-eBirdApiToken": self.api_key}
            timeout = aiohttp.ClientTimeout(total=settings.request_timeout)
            self.session = aiohttp.ClientSession(
                headers=headers, 
                timeout=timeout
            )
        return self.session
        
    async def request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make asynchronous request.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            JSON response data
            
        Raises:
            EBirdAPIError: For various API errors
        """
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(settings.ebird_max_retries):
            try:
                self.logger.debug(f"Making async request to {url} with params {params}")
                
                async with session.get(url, params=params) as response:
                    
                    # Handle different status codes
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 401:
                        raise EBirdAuthenticationError(
                            "Invalid eBird API key",
                            status_code=response.status,
                            endpoint=endpoint
                        )
                    elif response.status == 429:
                        raise EBirdRateLimitError(
                            "Rate limit exceeded",
                            status_code=response.status,
                            endpoint=endpoint
                        )
                    elif 500 <= response.status < 600:
                        raise EBirdServerError(
                            f"Server error: {response.status}",
                            status_code=response.status,
                            endpoint=endpoint
                        )
                    else:
                        text = await response.text()
                        raise EBirdAPIError(
                            f"API error: {response.status} - {text}",
                            status_code=response.status,
                            endpoint=endpoint
                        )
                        
            except aiohttp.ServerTimeoutError:
                if attempt == settings.ebird_max_retries - 1:
                    raise EBirdTimeoutError(
                        f"Request timeout after {settings.request_timeout}s",
                        endpoint=endpoint
                    )
                    
                # Wait before retry
                await asyncio.sleep(settings.ebird_initial_delay * (2 ** attempt))
                
            except aiohttp.ClientConnectorError as e:
                if attempt == settings.ebird_max_retries - 1:
                    raise EBirdAPIError(
                        f"Connection error: {str(e)}",
                        endpoint=endpoint
                    )
                    
                # Wait before retry
                await asyncio.sleep(settings.ebird_initial_delay * (2 ** attempt))
                
        # Should not reach here
        raise EBirdAPIError("Max retries exceeded", endpoint=endpoint)
        
    def close(self) -> None:
        """Close the aiohttp session."""
        if self.session:
            asyncio.create_task(self.session.close())