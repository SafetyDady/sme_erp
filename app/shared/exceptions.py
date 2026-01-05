from typing import Any, Optional


class SMEERPException(Exception):
    """Base exception for SME ERP application"""
    def __init__(
        self, 
        message: str, 
        code: str = "INTERNAL_ERROR", 
        details: Optional[Any] = None,
        status_code: int = 500
    ):
        self.message = message
        self.code = code
        self.details = details
        self.status_code = status_code
        super().__init__(message)


class ValidationError(SMEERPException):
    """Data validation error"""
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message, "VALIDATION_ERROR", details, 400)


class NotFoundError(SMEERPException):
    """Resource not found error"""
    def __init__(self, resource: str, identifier: str):
        message = f"{resource} not found: {identifier}"
        super().__init__(message, "NOT_FOUND", {"resource": resource, "id": identifier}, 404)


class ConflictError(SMEERPException):
    """Resource conflict error"""
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message, "CONFLICT", details, 409)


class DatabaseError(SMEERPException):
    """Database operation error"""
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message, "DATABASE_ERROR", details, 500)