"""
SME ERP Structured Logging System
Phase 7 - Operational Excellence

Features:
- JSON structured logs for production
- Correlation with request IDs
- Error tracking and metrics
- Performance monitoring
- Security event logging
"""

import json
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime
import traceback
from contextvars import ContextVar
from fastapi import Request
import uuid

# Context variables for request tracking
request_id_context: ContextVar[str] = ContextVar('request_id', default='')
user_id_context: ContextVar[str] = ContextVar('user_id', default='')

class StructuredLogFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        
        # Base log structure
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add request context if available
        request_id = request_id_context.get('')
        if request_id:
            log_entry["request_id"] = request_id
        
        user_id = user_id_context.get('')
        if user_id:
            log_entry["user_id"] = user_id
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields from record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'exc_info', 
                          'exc_text', 'stack_info']:
                extra_fields[key] = value
        
        if extra_fields:
            log_entry["extra"] = extra_fields
        
        return json.dumps(log_entry)


class PerformanceLogger:
    """
    Logger for performance metrics and monitoring
    """
    
    def __init__(self):
        self.logger = logging.getLogger("sme_erp.performance")
    
    def log_request_metrics(self, request: Request, response_time: float, 
                          status_code: int, user_id: Optional[str] = None):
        """Log HTTP request performance metrics"""
        
        self.logger.info(
            "HTTP request processed",
            extra={
                "event_type": "http_request",
                "method": request.method,
                "path": str(request.url.path),
                "query_params": dict(request.query_params),
                "status_code": status_code,
                "response_time_ms": round(response_time * 1000, 2),
                "user_agent": request.headers.get("user-agent"),
                "client_ip": request.client.host if request.client else None,
                "user_id": user_id
            }
        )
    
    def log_database_query(self, query_type: str, table: str, 
                          duration: float, record_count: int = None):
        """Log database query performance"""
        
        self.logger.info(
            f"Database {query_type} executed",
            extra={
                "event_type": "database_query",
                "query_type": query_type,
                "table": table,
                "duration_ms": round(duration * 1000, 2),
                "record_count": record_count
            }
        )


class SecurityLogger:
    """
    Logger for security events and audit trails
    """
    
    def __init__(self):
        self.logger = logging.getLogger("sme_erp.security")
    
    def log_authentication_attempt(self, email: str, success: bool, 
                                 ip_address: str, user_agent: str):
        """Log authentication attempts"""
        
        self.logger.info(
            "Authentication attempt",
            extra={
                "event_type": "authentication",
                "email": email,
                "success": success,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "severity": "info" if success else "warning"
            }
        )
    
    def log_authorization_failure(self, user_id: str, action: str, 
                                resource: str, required_role: str):
        """Log authorization failures"""
        
        self.logger.warning(
            "Authorization denied",
            extra={
                "event_type": "authorization_failure",
                "user_id": user_id,
                "action": action,
                "resource": resource,
                "required_role": required_role,
                "severity": "warning"
            }
        )
    
    def log_admin_action(self, admin_id: str, action: str, 
                        target_resource: str, changes: Dict[str, Any] = None):
        """Log administrative actions"""
        
        self.logger.info(
            "Administrative action performed",
            extra={
                "event_type": "admin_action",
                "admin_id": admin_id,
                "action": action,
                "target_resource": target_resource,
                "changes": changes,
                "severity": "info"
            }
        )


class ErrorLogger:
    """
    Logger for application errors and exceptions
    """
    
    def __init__(self):
        self.logger = logging.getLogger("sme_erp.errors")
    
    def log_application_error(self, error: Exception, context: Dict[str, Any] = None):
        """Log application errors with context"""
        
        self.logger.error(
            f"Application error: {str(error)}",
            exc_info=True,
            extra={
                "event_type": "application_error",
                "error_type": type(error).__name__,
                "context": context or {},
                "severity": "error"
            }
        )
    
    def log_database_error(self, error: Exception, operation: str):
        """Log database-related errors"""
        
        self.logger.error(
            f"Database error during {operation}",
            exc_info=True,
            extra={
                "event_type": "database_error",
                "operation": operation,
                "error_type": type(error).__name__,
                "severity": "error"
            }
        )


class BusinessLogger:
    """
    Logger for business events and operations
    """
    
    def __init__(self):
        self.logger = logging.getLogger("sme_erp.business")
    
    def log_inventory_transaction(self, user_id: str, transaction_type: str,
                                item_id: int, quantity: float, location: str):
        """Log inventory transactions"""
        
        self.logger.info(
            f"Inventory {transaction_type}",
            extra={
                "event_type": "inventory_transaction",
                "user_id": user_id,
                "transaction_type": transaction_type,
                "item_id": item_id,
                "quantity": quantity,
                "location": location,
                "business_impact": True
            }
        )
    
    def log_user_management(self, admin_id: str, action: str, 
                          target_user_id: str, role_change: Dict = None):
        """Log user management actions"""
        
        self.logger.info(
            f"User management: {action}",
            extra={
                "event_type": "user_management",
                "admin_id": admin_id,
                "action": action,
                "target_user_id": target_user_id,
                "role_change": role_change,
                "business_impact": True
            }
        )


def setup_structured_logging(log_level: str = "INFO", log_format: str = "json"):
    """
    Configure structured logging for the application
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type ("json" for structured, "text" for human-readable)
    """
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    logger.handlers = []
    
    # Create console handler
    console_handler = logging.StreamHandler()
    
    if log_format.lower() == "json":
        # Use structured JSON formatter
        formatter = StructuredLogFormatter()
    else:
        # Use standard text formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Configure specific loggers
    loggers_config = {
        "sme_erp.performance": logging.INFO,
        "sme_erp.security": logging.INFO,
        "sme_erp.errors": logging.ERROR,
        "sme_erp.business": logging.INFO,
        "uvicorn": logging.INFO,
        "fastapi": logging.INFO,
        "sqlalchemy.engine": logging.WARNING  # Reduce SQL query noise
    }
    
    for logger_name, level in loggers_config.items():
        logging.getLogger(logger_name).setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance"""
    return logging.getLogger(f"sme_erp.{name}")


# Global logger instances for easy access
performance_logger = PerformanceLogger()
security_logger = SecurityLogger()
error_logger = ErrorLogger()
business_logger = BusinessLogger()


# Context managers for request tracking
def set_request_context(request_id: str, user_id: str = ''):
    """Set request context for logging correlation"""
    request_id_context.set(request_id)
    if user_id:
        user_id_context.set(user_id)


def clear_request_context():
    """Clear request context"""
    request_id_context.set('')
    user_id_context.set('')


# Performance tracking decorator
def track_performance(operation_name: str):
    """Decorator to track operation performance"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                performance_logger.logger.info(
                    f"Operation {operation_name} completed",
                    extra={
                        "event_type": "operation_performance",
                        "operation": operation_name,
                        "duration_ms": round(duration * 1000, 2),
                        "success": True
                    }
                )
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                
                performance_logger.logger.error(
                    f"Operation {operation_name} failed",
                    extra={
                        "event_type": "operation_performance",
                        "operation": operation_name,
                        "duration_ms": round(duration * 1000, 2),
                        "success": False,
                        "error": str(e)
                    }
                )
                raise
        return wrapper
    return decorator