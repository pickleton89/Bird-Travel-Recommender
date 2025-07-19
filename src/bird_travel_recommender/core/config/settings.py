"""
Centralized application settings with Pydantic validation.

This module provides a unified configuration system that eliminates scattered
environment variable handling throughout the codebase.
"""

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from pydantic import Field, validator
from typing import Optional, Literal
import os


class Settings(BaseSettings):
    """
    Centralized application settings with validation.
    
    All configuration is managed through environment variables with
    proper validation and type safety.
    """
    
    # API Keys
    ebird_api_key: str = Field(..., env="EBIRD_API_KEY")
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    
    # Application Configuration
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field("INFO", env="LOG_LEVEL")
    environment: Literal["development", "staging", "production"] = Field("development", env="ENVIRONMENT")
    
    # Performance Settings
    max_concurrent_requests: int = Field(10, env="MAX_CONCURRENT_REQUESTS")
    request_timeout: int = Field(30, env="REQUEST_TIMEOUT")
    
    # Cache Configuration
    cache_enabled: bool = Field(True, env="CACHE_ENABLED")
    cache_ttl: int = Field(3600, env="CACHE_TTL")
    
    # eBird API Settings
    ebird_base_url: str = Field("https://api.ebird.org/v2", env="EBIRD_BASE_URL")
    ebird_max_retries: int = Field(3, env="EBIRD_MAX_RETRIES")
    ebird_initial_delay: float = Field(1.0, env="EBIRD_INITIAL_DELAY")
    
    # Development Settings
    debug: bool = Field(False, env="DEBUG")
    testing: bool = Field(False, env="TESTING")
    
    @validator("ebird_api_key")
    def validate_ebird_key(cls, v):
        """Validate eBird API key format."""
        if not v or len(v) < 10:
            raise ValueError("Valid eBird API key required (minimum 10 characters)")
        return v
        
    @validator("openai_api_key")
    def validate_openai_key(cls, v):
        """Validate OpenAI API key format."""
        if not v or not v.startswith("sk-"):
            raise ValueError("Valid OpenAI API key required (must start with 'sk-')")
        return v
        
    @validator("request_timeout")
    def validate_timeout(cls, v):
        """Ensure reasonable timeout values."""
        if v < 1 or v > 300:
            raise ValueError("Request timeout must be between 1 and 300 seconds")
        return v
        
    @validator("max_concurrent_requests")
    def validate_concurrency(cls, v):
        """Ensure reasonable concurrency limits."""
        if v < 1 or v > 100:
            raise ValueError("Max concurrent requests must be between 1 and 100")
        return v
        
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from environment


# Global settings instance
settings = Settings()