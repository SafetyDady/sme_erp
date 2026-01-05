"""
SME ERP Rate Limiting System
Phase 7 - Operational Excellence

Features:
- IP-based rate limiting for public endpoints
- User-based rate limiting for authenticated endpoints  
- Stricter limits for admin endpoints
- Redis-backed storage (with in-memory fallback)
- Customizable limits per endpoint type
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from app.core.logging import security_logger, get_logger
import redis
from typing import Optional, Callable
import os

# Rate limiting configuration
RATE_LIMITS = {
    # Public endpoints (no authentication required)
    "public": {
        "default": "100/hour",  # 100 requests per hour per IP
        "auth": "10/minute",    # Login attempts
        "health": "500/hour"    # Health checks
    },
    
    # Authenticated endpoints
    "authenticated": {
        "default": "1000/hour",  # 1000 requests per hour per user
        "read": "500/hour",      # Read operations
        "write": "100/hour"      # Write operations
    },
    
    # Admin endpoints (higher privilege, stricter limits)
    "admin": {
        "default": "200/hour",   # 200 admin requests per hour
        "audit": "50/hour",      # Audit log access
        "user_mgmt": "20/hour"   # User management
    }
}

# Logger for rate limiting
rate_limit_logger = get_logger("ratelimit")

def get_user_id(request: Request) -> str:
    """
    Extract user ID from request for user-based rate limiting
    Falls back to IP address for anonymous users
    """
    # Try to get user ID from request state (set by auth middleware)
    user_id = getattr(request.state, 'user_id', None)
    
    if user_id:
        return f"user:{user_id}"
    else:
        # Fall back to IP-based limiting
        return f"ip:{get_remote_address(request)}"


def get_admin_user_id(request: Request) -> str:
    """
    Extract admin user ID with role validation
    """
    user_id = getattr(request.state, 'user_id', None)
    user_role = getattr(request.state, 'user_role', None)
    
    if not user_id:
        return f"ip:{get_remote_address(request)}"
    
    # Only count as admin if user has admin role
    if user_role in ['ADMIN', 'SUPER_ADMIN']:
        return f"admin:{user_id}"
    else:
        # Non-admin users get standard limits
        return f"user:{user_id}"


def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom rate limit exceeded handler with structured logging
    """
    
    # Extract client info
    client_ip = get_remote_address(request)
    user_id = getattr(request.state, 'user_id', None)
    user_agent = request.headers.get("user-agent", "unknown")
    
    # Log rate limit violation
    security_logger.logger.warning(
        "Rate limit exceeded",
        extra={
            "event_type": "rate_limit_exceeded",
            "client_ip": client_ip,
            "user_id": user_id,
            "path": str(request.url.path),
            "method": request.method,
            "user_agent": user_agent,
            "limit": str(exc.detail),
            "security_impact": "medium"
        }
    )
    
    # Return structured error response
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please try again later.",
            "detail": f"Rate limit: {exc.detail}",
            "retry_after": getattr(exc, 'retry_after', 60)
        },
        headers={
            "Retry-After": str(getattr(exc, 'retry_after', 60)),
            "X-RateLimit-Limit": str(exc.detail)
        }
    )


# Configure Redis connection for rate limiting storage
def get_redis_client() -> Optional[redis.Redis]:
    """
    Get Redis client for rate limit storage
    Falls back to in-memory if Redis not available
    """
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/1")
    
    try:
        client = redis.from_url(redis_url, decode_responses=True)
        # Test connection
        client.ping()
        rate_limit_logger.info("Connected to Redis for rate limiting")
        return client
    except Exception as e:
        rate_limit_logger.warning(f"Redis unavailable, using in-memory rate limiting: {e}")
        return None


# Initialize rate limiter
redis_client = get_redis_client()

if redis_client:
    # Use Redis for distributed rate limiting
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri="redis://localhost:6379/1",
        default_limits=[RATE_LIMITS["public"]["default"]]
    )
else:
    # Use in-memory rate limiting (not suitable for production clusters)
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[RATE_LIMITS["public"]["default"]]
    )


# Rate limiting decorators for different endpoint types

def rate_limit_public(limit: str = None):
    """Rate limit for public endpoints (IP-based)"""
    actual_limit = limit or RATE_LIMITS["public"]["default"]
    return limiter.limit(actual_limit, key_func=get_remote_address)


def rate_limit_auth(limit: str = None):
    """Rate limit for authentication endpoints"""
    actual_limit = limit or RATE_LIMITS["public"]["auth"]
    return limiter.limit(actual_limit, key_func=get_remote_address)


def rate_limit_user(limit: str = None):
    """Rate limit for authenticated user endpoints"""
    actual_limit = limit or RATE_LIMITS["authenticated"]["default"]
    return limiter.limit(actual_limit, key_func=get_user_id)


def rate_limit_admin(limit: str = None):
    """Rate limit for admin endpoints"""
    actual_limit = limit or RATE_LIMITS["admin"]["default"]
    return limiter.limit(actual_limit, key_func=get_admin_user_id)


def rate_limit_audit(limit: str = None):
    """Strict rate limit for audit log access"""
    actual_limit = limit or RATE_LIMITS["admin"]["audit"]
    return limiter.limit(actual_limit, key_func=get_admin_user_id)


# Rate limit monitoring functions

class RateLimitMonitor:
    """Monitor and report rate limiting statistics"""
    
    def __init__(self):
        self.logger = get_logger("ratelimit.monitor")
    
    def get_rate_limit_stats(self, time_window: str = "1hour") -> dict:
        """
        Get rate limiting statistics for monitoring
        """
        try:
            if redis_client:
                # Get stats from Redis (implementation depends on storage format)
                stats = {
                    "storage_type": "redis",
                    "time_window": time_window,
                    "total_requests": 0,  # Would need to implement Redis-based counting
                    "rate_limited_requests": 0,
                    "top_limited_ips": [],
                    "top_limited_users": []
                }
            else:
                # In-memory stats (limited)
                stats = {
                    "storage_type": "memory",
                    "time_window": time_window,
                    "note": "In-memory storage provides limited statistics"
                }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get rate limit stats: {e}")
            return {"error": "Failed to retrieve statistics"}
    
    def check_rate_limit_health(self) -> dict:
        """
        Check rate limiting system health
        """
        health = {
            "storage_available": False,
            "storage_type": "none",
            "redis_connected": False,
            "active_limits": len(RATE_LIMITS)
        }
        
        try:
            if redis_client:
                redis_client.ping()
                health["redis_connected"] = True
                health["storage_type"] = "redis"
                health["storage_available"] = True
            else:
                health["storage_type"] = "memory"
                health["storage_available"] = True
                
        except Exception as e:
            self.logger.error(f"Rate limit storage health check failed: {e}")
        
        return health


# Global monitor instance
rate_limit_monitor = RateLimitMonitor()


# Utility functions for endpoint protection

def protect_endpoint(endpoint_type: str = "public", custom_limit: str = None):
    """
    Decorator factory for easy endpoint protection
    
    Args:
        endpoint_type: Type of endpoint (public, authenticated, admin)
        custom_limit: Custom rate limit override
    """
    
    if endpoint_type == "admin":
        return rate_limit_admin(custom_limit)
    elif endpoint_type == "authenticated":
        return rate_limit_user(custom_limit)
    elif endpoint_type == "auth":
        return rate_limit_auth(custom_limit)
    else:
        return rate_limit_public(custom_limit)


# Rate limit bypass for monitoring/health endpoints
def rate_limit_bypass(request: Request) -> str:
    """
    Bypass rate limiting for health/monitoring endpoints
    """
    # Health endpoints get more generous limits
    if request.url.path.startswith("/health/"):
        return f"health:{get_remote_address(request)}"
    
    return get_remote_address(request)


# Configure health endpoint rate limiting
rate_limit_health = limiter.limit(
    RATE_LIMITS["public"]["health"], 
    key_func=rate_limit_bypass
)