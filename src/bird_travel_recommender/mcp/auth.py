#!/usr/bin/env python3
"""
Authentication and Authorization Module for Bird Travel Recommender MCP Server

Provides API key-based authentication and role-based access control to secure MCP
server endpoints. Optional JWT support is available for issuing signed session
tokens.
"""

import os
import json
import time
import hmac
import hashlib
import secrets
import logging
import jwt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, asdict
from functools import wraps
from pathlib import Path

logger = logging.getLogger(__name__)

# Configuration
API_KEY_LENGTH = 32
SESSION_TIMEOUT_MINUTES = 60
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

@dataclass
class UserSession:
    """User session information"""
    user_id: str
    api_key: str
    permissions: List[str]
    created_at: datetime
    last_accessed: datetime
    request_count: int = 0
    failed_attempts: int = 0
    is_locked: bool = False
    lockout_until: Optional[datetime] = None

@dataclass
class APIKey:
    """API key information"""
    key_id: str
    key_hash: str
    user_id: str
    permissions: List[str]
    created_at: datetime
    last_used: Optional[datetime] = None
    is_active: bool = True
    rate_limit: int = 100  # requests per hour
    usage_count: int = 0

class AuthManager:
    """Manages authentication and authorization for MCP server"""
    
    def __init__(self, auth_config_path: Optional[str] = None):
        self.sessions: Dict[str, UserSession] = {}
        self.api_keys: Dict[str, APIKey] = {}
        self.rate_limits: Dict[str, List[float]] = {}  # user_id -> list of request timestamps
        
        # Load configuration
        self.auth_config_path = auth_config_path or self._get_default_config_path()
        self.secret_key = self._get_or_create_secret_key()
        self._load_api_keys()
        
        # Default permissions
        self.default_permissions = [
            "read:species",
            "read:locations",
            "read:observations",
            "use:pipeline",
            "get:advice"
        ]
        
        # Admin permissions (for internal use)
        self.admin_permissions = self.default_permissions + [
            "admin:manage_keys",
            "admin:view_stats",
            "admin:rate_limits"
        ]

    def issue_token(self, session: UserSession, expires_in: int = 3600) -> str:
        """Issue a signed JWT for the given session."""
        payload = {
            "sub": session.user_id,
            "permissions": session.permissions,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(seconds=expires_in),
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")

    def verify_token(self, token: str) -> Optional[dict]:
        """Verify a JWT and return its payload if valid."""
        try:
            return jwt.decode(token, self.secret_key, algorithms=["HS256"])
        except jwt.InvalidTokenError:
            return None
    
    def _get_default_config_path(self) -> str:
        """Get default path for auth configuration"""
        project_root = Path(__file__).parent.parent.parent.parent
        return str(project_root / "config" / "auth_config.json")
    
    def _get_or_create_secret_key(self) -> str:
        """Get or create secret key for signing"""
        secret_file = Path(self.auth_config_path).parent / ".auth_secret"
        
        if secret_file.exists():
            with open(secret_file, 'r') as f:
                return f.read().strip()
        else:
            # Create new secret key
            secret = secrets.token_urlsafe(32)
            with open(secret_file, 'w') as f:
                f.write(secret)
            os.chmod(secret_file, 0o600)  # Secure permissions
            return secret
    
    def _load_api_keys(self) -> None:
        """Load API keys from configuration file"""
        try:
            if os.path.exists(self.auth_config_path):
                with open(self.auth_config_path, 'r') as f:
                    config = json.load(f)
                    
                for key_data in config.get('api_keys', []):
                    api_key = APIKey(
                        key_id=key_data['key_id'],
                        key_hash=key_data['key_hash'],
                        user_id=key_data['user_id'],
                        permissions=key_data['permissions'],
                        created_at=datetime.fromisoformat(key_data['created_at']),
                        last_used=datetime.fromisoformat(key_data['last_used']) if key_data.get('last_used') else None,
                        is_active=key_data.get('is_active', True),
                        rate_limit=key_data.get('rate_limit', 100),
                        usage_count=key_data.get('usage_count', 0)
                    )
                    self.api_keys[key_data['key_id']] = api_key
                    
        except Exception as e:
            logger.warning(f"Failed to load API keys: {e}")
            # Create default development key if none exist
            if not self.api_keys:
                self._create_default_dev_key()
    
    def _create_default_dev_key(self) -> str:
        """Create a default development API key"""
        key_id = "dev_" + secrets.token_urlsafe(8)
        raw_key = secrets.token_urlsafe(API_KEY_LENGTH)
        
        api_key = APIKey(
            key_id=key_id,
            key_hash=self._hash_key(raw_key),
            user_id="developer",
            permissions=self.default_permissions,
            created_at=datetime.now(),
            rate_limit=1000  # Higher limit for development
        )
        
        self.api_keys[key_id] = api_key
        self._save_api_keys()
        
        logger.info(f"Created development API key: {key_id}")
        # Avoid logging the full secret; mask most characters for reference
        masked_key = raw_key[:4] + "***" + raw_key[-4:]
        logger.info(f"Raw key (save this): {masked_key}")
        
        return raw_key
    
    def _save_api_keys(self) -> None:
        """Save API keys to configuration file"""
        try:
            os.makedirs(os.path.dirname(self.auth_config_path), exist_ok=True)
            
            config = {
                'api_keys': []
            }
            
            for api_key in self.api_keys.values():
                config['api_keys'].append({
                    'key_id': api_key.key_id,
                    'key_hash': api_key.key_hash,
                    'user_id': api_key.user_id,
                    'permissions': api_key.permissions,
                    'created_at': api_key.created_at.isoformat(),
                    'last_used': api_key.last_used.isoformat() if api_key.last_used else None,
                    'is_active': api_key.is_active,
                    'rate_limit': api_key.rate_limit,
                    'usage_count': api_key.usage_count
                })
            
            with open(self.auth_config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            os.chmod(self.auth_config_path, 0o600)  # Secure permissions
            
        except Exception as e:
            logger.error(f"Failed to save API keys: {e}")
    
    def _hash_key(self, raw_key: str) -> str:
        """Hash an API key for secure storage"""
        return hashlib.sha256((raw_key + self.secret_key).encode()).hexdigest()
    
    def create_api_key(self, user_id: str, permissions: Optional[List[str]] = None) -> str:
        """Create a new API key for a user"""
        key_id = f"{user_id}_{secrets.token_urlsafe(8)}"
        raw_key = secrets.token_urlsafe(API_KEY_LENGTH)
        
        api_key = APIKey(
            key_id=key_id,
            key_hash=self._hash_key(raw_key),
            user_id=user_id,
            permissions=permissions or self.default_permissions,
            created_at=datetime.now()
        )
        
        self.api_keys[key_id] = api_key
        self._save_api_keys()
        
        logger.info(f"Created API key for user {user_id}: {key_id}")
        return raw_key
    
    def authenticate_request(self, api_key: str) -> Optional[UserSession]:
        """Authenticate a request using API key"""
        if not api_key:
            return None
        
        # Hash the provided key
        key_hash = self._hash_key(api_key)
        
        # Find matching API key
        for stored_key in self.api_keys.values():
            if stored_key.key_hash == key_hash and stored_key.is_active:
                # Update usage statistics
                stored_key.last_used = datetime.now()
                stored_key.usage_count += 1
                
                # Create or update session
                session_id = f"{stored_key.user_id}_{int(time.time())}"
                session = UserSession(
                    user_id=stored_key.user_id,
                    api_key=api_key,
                    permissions=stored_key.permissions,
                    created_at=datetime.now(),
                    last_accessed=datetime.now()
                )
                
                # Check if user is locked out
                if session.is_locked and session.lockout_until and datetime.now() < session.lockout_until:
                    logger.warning(f"User {stored_key.user_id} is locked out until {session.lockout_until}")
                    return None
                
                # Reset lockout if time has passed
                if session.is_locked and session.lockout_until and datetime.now() >= session.lockout_until:
                    session.is_locked = False
                    session.lockout_until = None
                    session.failed_attempts = 0
                
                self.sessions[session_id] = session
                self._save_api_keys()  # Update usage stats
                
                return session
        
        return None
    
    def check_permission(self, session: UserSession, required_permission: str) -> bool:
        """Check if a session has the required permission"""
        if not session:
            return False
        
        # Admin users have all permissions
        if "admin:manage_keys" in session.permissions:
            return True
        
        # Check specific permission
        return required_permission in session.permissions
    
    def check_rate_limit(self, session: UserSession) -> bool:
        """Check if request is within rate limits"""
        if not session:
            return False
        
        now = time.time()
        user_id = session.user_id
        
        # Get rate limit for this user
        api_key = next((k for k in self.api_keys.values() if k.user_id == user_id), None)
        if not api_key:
            return False
        
        rate_limit = api_key.rate_limit
        
        # Initialize rate tracking for user
        if user_id not in self.rate_limits:
            self.rate_limits[user_id] = []
        
        # Remove old requests (older than 1 hour)
        one_hour_ago = now - 3600
        self.rate_limits[user_id] = [ts for ts in self.rate_limits[user_id] if ts > one_hour_ago]
        
        # Check if under limit
        if len(self.rate_limits[user_id]) >= rate_limit:
            return False
        
        # Add current request
        self.rate_limits[user_id].append(now)
        session.request_count += 1
        
        return True
    
    def get_auth_stats(self, session: UserSession) -> Dict[str, Any]:
        """Get authentication statistics (admin only)"""
        if not self.check_permission(session, "admin:view_stats"):
            return {"error": "Insufficient permissions"}
        
        stats = {
            "total_api_keys": len(self.api_keys),
            "active_sessions": len(self.sessions),
            "api_keys": []
        }
        
        for api_key in self.api_keys.values():
            stats["api_keys"].append({
                "key_id": api_key.key_id,
                "user_id": api_key.user_id,
                "permissions": api_key.permissions,
                "created_at": api_key.created_at.isoformat(),
                "last_used": api_key.last_used.isoformat() if api_key.last_used else None,
                "is_active": api_key.is_active,
                "usage_count": api_key.usage_count,
                "rate_limit": api_key.rate_limit
            })
        
        return stats

def require_auth(permissions: List[str] = None):
    """Decorator to require authentication and authorization"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Get auth manager from server instance
            if not hasattr(self, 'auth_manager'):
                logger.error("No auth manager configured")
                return {
                    "success": False,
                    "error": "Authentication not configured",
                    "error_code": "AUTH_NOT_CONFIGURED"
                }
            
            # Extract API key from environment or request context
            api_key = os.getenv('MCP_API_KEY') or kwargs.get('api_key')
            
            if not api_key:
                return {
                    "success": False,
                    "error": "API key required",
                    "error_code": "API_KEY_MISSING"
                }
            
            # Authenticate
            session = self.auth_manager.authenticate_request(api_key)
            if not session:
                return {
                    "success": False,
                    "error": "Invalid API key",
                    "error_code": "INVALID_API_KEY"
                }
            
            # Check rate limits
            if not self.auth_manager.check_rate_limit(session):
                return {
                    "success": False,
                    "error": "Rate limit exceeded",
                    "error_code": "RATE_LIMIT_EXCEEDED"
                }
            
            # Check permissions
            if permissions:
                for required_permission in permissions:
                    if not self.auth_manager.check_permission(session, required_permission):
                        return {
                            "success": False,
                            "error": f"Permission denied: {required_permission}",
                            "error_code": "PERMISSION_DENIED"
                        }
            
            # Add session to kwargs for handler use
            kwargs['session'] = session
            
            return await func(self, *args, **kwargs)
        
        return wrapper
    return decorator