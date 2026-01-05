import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class RequestIdMiddleware(BaseHTTPMiddleware):
    """Minimal middleware to add request_id for audit traceability"""
    
    async def dispatch(self, request: Request, call_next):
        # Generate or extract request ID
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        
        # Store in request state for audit logging
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add request ID to response headers for client traceability
        response.headers["x-request-id"] = request_id
        
        return response