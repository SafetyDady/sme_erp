import uuid
import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Configure structured logging
logger = logging.getLogger("sme_erp.requests")

class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Enhanced middleware for observability:
    - Adds request_id for audit traceability
    - Structured logging with request details
    - Response time tracking
    """
    
    async def dispatch(self, request: Request, call_next):
        # Generate or extract request ID
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        
        # Store in request state for audit logging
        request.state.request_id = request_id
        
        # Track request timing
        start_time = time.time()
        
        # Log incoming request
        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": str(request.url.path),
                "query_params": str(request.url.query) if request.url.query else None,
                "user_agent": request.headers.get("user-agent"),
                "client_ip": request.client.host if request.client else None,
                "timestamp": time.time()
            }
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            "Request completed", 
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": str(request.url.path),
                "status_code": response.status_code,
                "process_time": round(process_time, 4),
                "timestamp": time.time()
            }
        )
        
        # Add request ID to response headers for client traceability
        response.headers["x-request-id"] = request_id
        
        return response
        
        return response