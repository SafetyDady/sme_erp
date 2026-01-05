"""
SME ERP Logging Middleware
Phase 7 - Operational Excellence

Middleware for request/response logging and performance tracking
"""

import time
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import (
    set_request_context, 
    clear_request_context,
    performance_logger,
    security_logger,
    error_logger
)


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for structured logging of all HTTP requests/responses
    """
    
    async def dispatch(self, request: Request, call_next):
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        
        # Set request context for logging correlation
        set_request_context(request_id)
        
        # Add request ID to response headers
        start_time = time.time()
        
        try:
            # Log incoming request
            self.log_request_start(request, request_id)
            
            # Process request
            response = await call_next(request)
            
            # Calculate response time
            process_time = time.time() - start_time
            
            # Add performance headers
            response.headers["X-Request-Id"] = request_id
            response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))
            
            # Log request completion
            self.log_request_complete(request, response, process_time, request_id)
            
            return response
            
        except Exception as e:
            # Calculate error time
            process_time = time.time() - start_time
            
            # Log request error
            self.log_request_error(request, e, process_time, request_id)
            
            # Re-raise the exception
            raise
            
        finally:
            # Clear request context
            clear_request_context()
    
    def log_request_start(self, request: Request, request_id: str):
        """Log incoming request details"""
        
        # Extract client info
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        performance_logger.logger.info(
            "HTTP request started",
            extra={
                "event_type": "http_request_start",
                "request_id": request_id,
                "method": request.method,
                "path": str(request.url.path),
                "query_params": dict(request.query_params),
                "client_ip": client_ip,
                "user_agent": user_agent,
                "content_length": request.headers.get("content-length"),
                "content_type": request.headers.get("content-type")
            }
        )
    
    def log_request_complete(self, request: Request, response: Response, 
                           process_time: float, request_id: str):
        """Log completed request with performance metrics"""
        
        # Extract user ID from response if available
        user_id = getattr(request.state, 'user_id', None)
        
        # Determine if this was a successful request
        is_success = 200 <= response.status_code < 400
        is_client_error = 400 <= response.status_code < 500
        is_server_error = response.status_code >= 500
        
        # Log to appropriate logger based on status
        logger = performance_logger.logger
        level = "info"
        
        if is_server_error:
            logger = error_logger.logger
            level = "error"
        elif is_client_error:
            level = "warning"
        
        getattr(logger, level)(
            "HTTP request completed",
            extra={
                "event_type": "http_request_complete",
                "request_id": request_id,
                "method": request.method,
                "path": str(request.url.path),
                "status_code": response.status_code,
                "response_time_ms": round(process_time * 1000, 2),
                "response_size": response.headers.get("content-length"),
                "user_id": user_id,
                "success": is_success,
                "performance_category": self.categorize_performance(process_time)
            }
        )
        
        # Log slow requests
        if process_time > 1.0:  # Slower than 1 second
            performance_logger.logger.warning(
                "Slow request detected",
                extra={
                    "event_type": "slow_request",
                    "request_id": request_id,
                    "method": request.method,
                    "path": str(request.url.path),
                    "response_time_ms": round(process_time * 1000, 2),
                    "threshold_exceeded": "1000ms"
                }
            )
    
    def log_request_error(self, request: Request, error: Exception, 
                         process_time: float, request_id: str):
        """Log request errors with exception details"""
        
        error_logger.log_application_error(
            error,
            context={
                "event_type": "http_request_error",
                "request_id": request_id,
                "method": request.method,
                "path": str(request.url.path),
                "response_time_ms": round(process_time * 1000, 2),
                "client_ip": request.client.host if request.client else "unknown"
            }
        )
    
    def categorize_performance(self, response_time: float) -> str:
        """Categorize response time performance"""
        if response_time < 0.1:
            return "excellent"
        elif response_time < 0.5:
            return "good"
        elif response_time < 1.0:
            return "acceptable"
        elif response_time < 3.0:
            return "slow"
        else:
            return "very_slow"


class SecurityLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for security event logging
    """
    
    async def dispatch(self, request: Request, call_next):
        
        # Check for suspicious activity
        self.check_suspicious_activity(request)
        
        # Process request
        response = await call_next(request)
        
        # Log authentication/authorization events
        if response.status_code == 401:
            self.log_authentication_failure(request)
        elif response.status_code == 403:
            self.log_authorization_failure(request)
        
        return response
    
    def check_suspicious_activity(self, request: Request):
        """Check for suspicious request patterns"""
        
        # Check for SQL injection patterns
        suspicious_patterns = ["'", "union", "select", "drop", "delete", "insert"]
        query_string = str(request.url.query).lower()
        
        for pattern in suspicious_patterns:
            if pattern in query_string:
                security_logger.logger.warning(
                    "Suspicious activity detected",
                    extra={
                        "event_type": "security_threat",
                        "threat_type": "potential_sql_injection",
                        "pattern": pattern,
                        "query_string": str(request.url.query),
                        "client_ip": request.client.host if request.client else "unknown",
                        "user_agent": request.headers.get("user-agent")
                    }
                )
                break
        
        # Check for unusual user agents
        user_agent = request.headers.get("user-agent", "").lower()
        bot_patterns = ["bot", "crawler", "spider", "scraper"]
        
        if any(pattern in user_agent for pattern in bot_patterns):
            security_logger.logger.info(
                "Bot/crawler detected",
                extra={
                    "event_type": "bot_access",
                    "user_agent": user_agent,
                    "client_ip": request.client.host if request.client else "unknown",
                    "path": str(request.url.path)
                }
            )
    
    def log_authentication_failure(self, request: Request):
        """Log 401 authentication failures"""
        
        security_logger.logger.warning(
            "Authentication failure",
            extra={
                "event_type": "auth_failure",
                "path": str(request.url.path),
                "method": request.method,
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent")
            }
        )
    
    def log_authorization_failure(self, request: Request):
        """Log 403 authorization failures"""
        
        security_logger.logger.warning(
            "Authorization failure", 
            extra={
                "event_type": "authz_failure",
                "path": str(request.url.path),
                "method": request.method,
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent"),
                "user_id": getattr(request.state, 'user_id', None)
            }
        )