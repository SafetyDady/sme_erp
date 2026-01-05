"""
Rate Limiting Integration for SME ERP
Phase 7 - Operational Excellence

Integration of rate limiting with FastAPI routes and middleware
"""

from fastapi import FastAPI, Request, HTTPException, status, Depends
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.rate_limiting import (
    limiter,
    custom_rate_limit_handler,
    rate_limit_public,
    rate_limit_auth,
    rate_limit_user,
    rate_limit_admin,
    rate_limit_audit,
    rate_limit_monitor
)
from app.core.logging import security_logger


def setup_rate_limiting(app: FastAPI):
    """
    Setup rate limiting for the FastAPI application
    """
    
    # Add rate limiting middleware
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)
    app.add_middleware(SlowAPIMiddleware)
    
    # Add rate limit monitoring endpoint
    @app.get("/internal/rate-limits/stats")
    @rate_limit_admin("10/minute")  # Admin only, 10 requests per minute
    async def get_rate_limit_stats(request: Request):
        """Get rate limiting statistics (admin only)"""
        
        stats = rate_limit_monitor.get_rate_limit_stats()
        health = rate_limit_monitor.check_rate_limit_health()
        
        return {
            "rate_limit_stats": stats,
            "rate_limit_health": health,
            "current_config": {
                "storage_type": "redis" if health["redis_connected"] else "memory",
                "limits_configured": True
            }
        }


# Dependency for user role-aware rate limiting
async def get_user_context(request: Request):
    """
    Extract user context for rate limiting
    This would typically be called after authentication
    """
    # This should be set by your authentication middleware
    user_id = getattr(request.state, 'user_id', None)
    user_role = getattr(request.state, 'user_role', None)
    
    return {
        "user_id": user_id,
        "user_role": user_role
    }


# Custom rate limiting based on user role
def dynamic_rate_limit(base_limit: str = "100/hour"):
    """
    Dynamic rate limiting based on user role
    """
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            user_context = await get_user_context(request)
            
            # Adjust rate limit based on user role
            if user_context["user_role"] == "SUPER_ADMIN":
                # Super admins get higher limits
                adjusted_limit = "500/hour"
            elif user_context["user_role"] == "ADMIN":
                adjusted_limit = "300/hour"
            elif user_context["user_role"] == "STAFF":
                adjusted_limit = "200/hour"
            else:
                # VIEWER or unauthenticated
                adjusted_limit = base_limit
            
            # Apply the rate limit
            @limiter.limit(adjusted_limit)
            async def rate_limited_func(request: Request):
                return await func(request, *args, **kwargs)
            
            return await rate_limited_func(request)
        
        return wrapper
    return decorator


# Rate limit profiles for different endpoint types
ENDPOINT_RATE_LIMITS = {
    # Authentication endpoints
    "auth_login": "5/minute",      # Login attempts
    "auth_register": "3/minute",   # Registration attempts
    "auth_reset": "2/minute",      # Password reset
    
    # Inventory endpoints
    "inventory_read": "500/hour",   # Read operations
    "inventory_write": "50/hour",   # Create/update operations
    "inventory_delete": "10/hour",  # Delete operations
    
    # Admin endpoints
    "admin_audit": "30/hour",       # Audit log access
    "admin_user_mgmt": "20/hour",   # User management
    "admin_config": "10/hour",      # Configuration changes
    
    # Health/monitoring
    "health": "1000/hour",          # Health checks
    "metrics": "100/hour"           # Metrics access
}


def get_endpoint_rate_limit(endpoint_name: str) -> str:
    """Get rate limit for specific endpoint type"""
    return ENDPOINT_RATE_LIMITS.get(endpoint_name, "100/hour")


# Decorators for common endpoint types
def rate_limit_inventory_read(func):
    """Rate limit for inventory read operations"""
    return rate_limit_user(get_endpoint_rate_limit("inventory_read"))(func)

def rate_limit_inventory_write(func):
    """Rate limit for inventory write operations"""
    return rate_limit_user(get_endpoint_rate_limit("inventory_write"))(func)

def rate_limit_inventory_delete(func):
    """Rate limit for inventory delete operations"""
    return rate_limit_admin(get_endpoint_rate_limit("inventory_delete"))(func)

def rate_limit_login(func):
    """Rate limit for login attempts"""
    return rate_limit_auth(get_endpoint_rate_limit("auth_login"))(func)

def rate_limit_user_management(func):
    """Rate limit for user management operations"""
    return rate_limit_admin(get_endpoint_rate_limit("admin_user_mgmt"))(func)


# Rate limiting monitoring and alerts
class RateLimitingAlerter:
    """
    Monitor rate limiting for suspicious activity and send alerts
    """
    
    def __init__(self):
        self.logger = security_logger
    
    def check_for_abuse_patterns(self, client_ip: str, user_id: str = None):
        """
        Check for potential abuse patterns
        """
        # This would typically query rate limiting storage for patterns
        
        # Example patterns to detect:
        # 1. Rapid consecutive rate limit hits
        # 2. Distributed attacks from multiple IPs
        # 3. Account takeover attempts
        
        pass
    
    def send_rate_limit_alert(self, alert_type: str, details: dict):
        """
        Send rate limiting alert to monitoring system
        """
        self.logger.logger.warning(
            f"Rate limiting alert: {alert_type}",
            extra={
                "event_type": "rate_limit_alert",
                "alert_type": alert_type,
                "details": details,
                "severity": "high" if alert_type in ["distributed_attack", "account_takeover"] else "medium"
            }
        )


# Global alerter instance
rate_limit_alerter = RateLimitingAlerter()


# Testing utilities for rate limiting
class RateLimitTester:
    """
    Utilities for testing rate limiting in development/staging
    """
    
    def __init__(self):
        self.logger = security_logger
    
    async def test_rate_limits(self, endpoint: str, expected_limit: int):
        """
        Test that rate limits are working correctly
        """
        # This would make multiple requests to test the rate limit
        pass
    
    def get_current_rate_limit_status(self, identifier: str) -> dict:
        """
        Get current rate limit status for an identifier
        """
        # Query current rate limit counters
        return {
            "identifier": identifier,
            "current_requests": 0,
            "limit": "unknown",
            "reset_time": "unknown"
        }