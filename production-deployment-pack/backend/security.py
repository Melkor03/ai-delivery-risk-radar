"""
Risk Radar Security Module
- API Token Encryption (AES-256)
- Rate Limiting
- Input Validation
- Security Headers
"""

import os
import time
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import wraps
import logging

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64

logger = logging.getLogger(__name__)


# ============================================
# ENCRYPTION - AES-256 for API Tokens
# ============================================

class TokenEncryption:
    """
    Encrypts sensitive data like API tokens using Fernet (AES-256-CBC).
    
    Usage:
        encryptor = TokenEncryption()
        encrypted = encryptor.encrypt("my-api-token")
        decrypted = encryptor.decrypt(encrypted)
    """
    
    def __init__(self, key: Optional[str] = None):
        """
        Initialize with encryption key from environment or parameter.
        
        Args:
            key: Base64-encoded 32-byte key. If not provided, reads from ENCRYPTION_KEY env var.
        """
        self.key = key or os.environ.get('ENCRYPTION_KEY')
        
        if not self.key:
            logger.warning("No ENCRYPTION_KEY set! Generating temporary key (NOT FOR PRODUCTION)")
            self.key = Fernet.generate_key().decode()
        
        # Ensure key is proper Fernet format
        try:
            self.fernet = Fernet(self.key.encode() if isinstance(self.key, str) else self.key)
        except Exception:
            # Derive a proper key from the provided string
            self.fernet = Fernet(self._derive_key(self.key))
    
    def _derive_key(self, password: str) -> bytes:
        """Derive a valid Fernet key from any string password."""
        salt = b'risk_radar_salt_v1'  # Fixed salt - in production, store per-user salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string and return base64-encoded ciphertext.
        
        Args:
            plaintext: The string to encrypt
            
        Returns:
            Base64-encoded encrypted string
        """
        if not plaintext:
            return ""
        
        try:
            encrypted = self.fernet.encrypt(plaintext.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError("Failed to encrypt data")
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a base64-encoded ciphertext.
        
        Args:
            ciphertext: The encrypted string
            
        Returns:
            Decrypted plaintext string
        """
        if not ciphertext:
            return ""
        
        try:
            decrypted = self.fernet.decrypt(ciphertext.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Failed to decrypt data - invalid key or corrupted data")
    
    @staticmethod
    def generate_key() -> str:
        """Generate a new encryption key suitable for ENCRYPTION_KEY env var."""
        return Fernet.generate_key().decode()


# ============================================
# RATE LIMITING - In-Memory & Redis Support
# ============================================

class RateLimiter:
    """
    Rate limiter with in-memory storage (for single instance)
    or Redis backend (for distributed deployments).
    
    Usage:
        limiter = RateLimiter(requests_per_minute=60)
        
        if limiter.is_allowed("user_123"):
            # Process request
        else:
            # Return 429 Too Many Requests
    """
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        redis_client = None
    ):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Max requests per minute per key
            requests_per_hour: Max requests per hour per key
            redis_client: Optional Redis client for distributed limiting
        """
        self.rpm = requests_per_minute
        self.rph = requests_per_hour
        self.redis = redis_client
        
        # In-memory storage: {key: [(timestamp, count), ...]}
        self._memory_store: Dict[str, list] = {}
    
    def is_allowed(self, key: str) -> bool:
        """
        Check if request is allowed for the given key.
        
        Args:
            key: Unique identifier (user_id, IP address, API key)
            
        Returns:
            True if request is allowed, False if rate limited
        """
        if self.redis:
            return self._check_redis(key)
        return self._check_memory(key)
    
    def _check_memory(self, key: str) -> bool:
        """Check rate limit using in-memory storage."""
        now = time.time()
        minute_ago = now - 60
        hour_ago = now - 3600
        
        # Initialize or get existing requests
        if key not in self._memory_store:
            self._memory_store[key] = []
        
        requests = self._memory_store[key]
        
        # Clean old entries
        requests = [ts for ts in requests if ts > hour_ago]
        self._memory_store[key] = requests
        
        # Count requests in windows
        requests_last_minute = sum(1 for ts in requests if ts > minute_ago)
        requests_last_hour = len(requests)
        
        # Check limits
        if requests_last_minute >= self.rpm:
            logger.warning(f"Rate limit exceeded (minute) for key: {key[:20]}...")
            return False
        
        if requests_last_hour >= self.rph:
            logger.warning(f"Rate limit exceeded (hour) for key: {key[:20]}...")
            return False
        
        # Record this request
        requests.append(now)
        return True
    
    def _check_redis(self, key: str) -> bool:
        """Check rate limit using Redis (sliding window)."""
        try:
            now = time.time()
            minute_key = f"ratelimit:minute:{key}"
            hour_key = f"ratelimit:hour:{key}"
            
            pipe = self.redis.pipeline()
            
            # Minute window
            pipe.zremrangebyscore(minute_key, 0, now - 60)
            pipe.zcard(minute_key)
            pipe.zadd(minute_key, {str(now): now})
            pipe.expire(minute_key, 60)
            
            # Hour window
            pipe.zremrangebyscore(hour_key, 0, now - 3600)
            pipe.zcard(hour_key)
            pipe.zadd(hour_key, {str(now): now})
            pipe.expire(hour_key, 3600)
            
            results = pipe.execute()
            
            minute_count = results[1]
            hour_count = results[5]
            
            if minute_count >= self.rpm or hour_count >= self.rph:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Redis rate limit error: {e}")
            # Fail open - allow request if Redis is down
            return True
    
    def get_remaining(self, key: str) -> Dict[str, int]:
        """Get remaining requests for a key."""
        now = time.time()
        
        if key not in self._memory_store:
            return {"minute": self.rpm, "hour": self.rph}
        
        requests = self._memory_store[key]
        minute_count = sum(1 for ts in requests if ts > now - 60)
        hour_count = sum(1 for ts in requests if ts > now - 3600)
        
        return {
            "minute": max(0, self.rpm - minute_count),
            "hour": max(0, self.rph - hour_count)
        }


# ============================================
# FASTAPI MIDDLEWARE & DEPENDENCIES
# ============================================

# Global instances
_token_encryptor: Optional[TokenEncryption] = None
_rate_limiter: Optional[RateLimiter] = None


def get_encryptor() -> TokenEncryption:
    """Get or create token encryptor singleton."""
    global _token_encryptor
    if _token_encryptor is None:
        _token_encryptor = TokenEncryption()
    return _token_encryptor


def get_rate_limiter() -> RateLimiter:
    """Get or create rate limiter singleton."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(
            requests_per_minute=int(os.environ.get('RATE_LIMIT_RPM', 60)),
            requests_per_hour=int(os.environ.get('RATE_LIMIT_RPH', 1000))
        )
    return _rate_limiter


def encrypt_api_token(token: str) -> str:
    """Convenience function to encrypt an API token."""
    return get_encryptor().encrypt(token)


def decrypt_api_token(encrypted_token: str) -> str:
    """Convenience function to decrypt an API token."""
    return get_encryptor().decrypt(encrypted_token)


# ============================================
# FASTAPI INTEGRATION
# ============================================

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.
    
    Usage in server.py:
        from security import RateLimitMiddleware
        app.add_middleware(RateLimitMiddleware)
    """
    
    # Endpoints with stricter limits
    STRICT_ENDPOINTS = {
        "/api/auth/login": 5,      # 5 per minute
        "/api/auth/register": 3,   # 3 per minute
        "/api/auth/reset-password": 3,
    }
    
    # Endpoints exempt from rate limiting
    EXEMPT_ENDPOINTS = {
        "/api/health",
        "/health",
        "/docs",
        "/openapi.json",
    }
    
    async def dispatch(self, request: Request, call_next):
        # Skip exempt endpoints
        path = request.url.path
        if path in self.EXEMPT_ENDPOINTS:
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_id(request)
        limiter = get_rate_limiter()
        
        # Check strict endpoints
        if path in self.STRICT_ENDPOINTS:
            strict_limiter = RateLimiter(
                requests_per_minute=self.STRICT_ENDPOINTS[path],
                requests_per_hour=self.STRICT_ENDPOINTS[path] * 20
            )
            if not strict_limiter.is_allowed(f"{client_id}:{path}"):
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Too many requests. Please try again later."},
                    headers={"Retry-After": "60"}
                )
        
        # Check general rate limit
        if not limiter.is_allowed(client_id):
            remaining = limiter.get_remaining(client_id)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded",
                    "remaining": remaining
                },
                headers={"Retry-After": "60"}
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        remaining = limiter.get_remaining(client_id)
        response.headers["X-RateLimit-Limit-Minute"] = str(limiter.rpm)
        response.headers["X-RateLimit-Remaining-Minute"] = str(remaining["minute"])
        response.headers["X-RateLimit-Limit-Hour"] = str(limiter.rph)
        response.headers["X-RateLimit-Remaining-Hour"] = str(remaining["hour"])
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier from request."""
        # Prefer authenticated user ID
        if hasattr(request.state, 'user') and request.state.user:
            return f"user:{request.state.user.get('id', 'unknown')}"
        
        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        
        return f"ip:{request.client.host if request.client else 'unknown'}"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.
    
    Usage:
        app.add_middleware(SecurityHeadersMiddleware)
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # HSTS (only in production with HTTPS)
        if os.environ.get('ENVIRONMENT') == 'production':
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


# ============================================
# INPUT VALIDATION & SANITIZATION
# ============================================

import re
import html


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitize user input to prevent XSS and injection attacks.
    
    Args:
        text: User input string
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not text:
        return ""
    
    # Truncate
    text = text[:max_length]
    
    # HTML escape
    text = html.escape(text)
    
    # Remove potentially dangerous patterns
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    text = re.sub(r'data:', '', text, flags=re.IGNORECASE)
    text = re.sub(r'vbscript:', '', text, flags=re.IGNORECASE)
    
    return text.strip()


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_project_name(name: str) -> bool:
    """Validate project name (alphanumeric, spaces, hyphens, underscores)."""
    if not name or len(name) > 100:
        return False
    pattern = r'^[a-zA-Z0-9\s\-_]+$'
    return bool(re.match(pattern, name))


# ============================================
# SECURE PASSWORD UTILITIES
# ============================================

def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)


def hash_password_for_comparison(password: str, salt: str) -> str:
    """
    Hash password for secure comparison (use bcrypt for storage).
    This is for additional verification layers, not primary storage.
    """
    return hashlib.pbkdf2_hmac(
        'sha256',
        password.encode(),
        salt.encode(),
        100000
    ).hex()


# ============================================
# AUDIT LOGGING
# ============================================

class AuditLogger:
    """
    Security audit logger for tracking sensitive operations.
    
    Usage:
        audit = AuditLogger()
        audit.log("login_success", user_id="123", ip="192.168.1.1")
    """
    
    def __init__(self, logger_name: str = "security.audit"):
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)
    
    def log(self, event: str, **kwargs):
        """Log a security event."""
        timestamp = datetime.utcnow().isoformat()
        message = {
            "timestamp": timestamp,
            "event": event,
            **kwargs
        }
        self.logger.info(f"AUDIT: {message}")
    
    def login_attempt(self, email: str, success: bool, ip: str):
        """Log login attempt."""
        self.log(
            "login_attempt",
            email=email[:3] + "***",  # Partially mask email
            success=success,
            ip=ip
        )
    
    def api_token_access(self, user_id: str, action: str, integration: str):
        """Log API token access."""
        self.log(
            "api_token_access",
            user_id=user_id,
            action=action,
            integration=integration
        )
    
    def data_export(self, user_id: str, data_type: str, record_count: int):
        """Log data export."""
        self.log(
            "data_export",
            user_id=user_id,
            data_type=data_type,
            record_count=record_count
        )


# Export all public APIs
__all__ = [
    'TokenEncryption',
    'RateLimiter',
    'RateLimitMiddleware',
    'SecurityHeadersMiddleware',
    'AuditLogger',
    'get_encryptor',
    'get_rate_limiter',
    'encrypt_api_token',
    'decrypt_api_token',
    'sanitize_input',
    'validate_email',
    'validate_project_name',
    'generate_secure_token',
]
