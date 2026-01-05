import uuid
import json
from typing import Any, Dict, Optional
from fastapi import Request
from sqlalchemy.orm import Session
from app.modules.audit.models import AuditLog
from app.modules.users.models import User

class AuditLogger:
    """Minimal audit logging utility for compliance"""
    
    @staticmethod
    def log_admin_action(
        db: Session,
        request: Request,
        user: User,
        action_type: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        entity_identifier: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None
    ) -> AuditLog:
        """
        Log sensitive admin actions for compliance.
        Only logs ADMIN/SUPER_ADMIN actions as per Phase 5 requirements.
        """
        
        # Only log ADMIN and SUPER_ADMIN actions
        if user.role.value not in ["admin", "super_admin"]:
            return None
        
        # Generate or extract request ID for traceability
        request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
        
        # Extract client info
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")
        
        # Create audit entry
        audit_entry = AuditLog(
            request_id=request_id,
            user_id=user.id,
            user_email=user.email,
            user_role=user.role.value,
            action_type=action_type,
            http_method=request.method,
            endpoint=str(request.url.path),
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            entity_identifier=entity_identifier,
            old_values=json.dumps(old_values) if old_values else None,
            new_values=json.dumps(new_values) if new_values else None,
            ip_address=client_ip,
            user_agent=user_agent[:500] if user_agent else None,  # Truncate user agent
            notes=notes
        )
        
        db.add(audit_entry)
        return audit_entry

# Decorator for automatic audit logging
def audit_admin_action(
    action_type: str,
    entity_type: str,
    get_entity_id: callable = None,
    get_entity_identifier: callable = None,
    get_old_values: callable = None,
    get_new_values: callable = None
):
    """
    Decorator to automatically audit ADMIN/SUPER_ADMIN actions.
    
    Usage:
    @audit_admin_action("CREATE", "item", lambda result: result.id, lambda result: result.sku)
    def create_item_endpoint(...):
        pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Execute the original function
            result = func(*args, **kwargs)
            
            # Extract request, db, and user from function kwargs/args
            request = None
            db = None
            user = None
            
            for arg in args + tuple(kwargs.values()):
                if hasattr(arg, 'method') and hasattr(arg, 'url'):  # FastAPI Request
                    request = arg
                elif hasattr(arg, 'query'):  # SQLAlchemy Session
                    db = arg
                elif hasattr(arg, 'email') and hasattr(arg, 'role'):  # User
                    user = arg
            
            # Only proceed if we have all required components and user is ADMIN+
            if request and db and user and user.role.value in ["admin", "super_admin"]:
                try:
                    entity_id = get_entity_id(result) if get_entity_id else None
                    entity_identifier = get_entity_identifier(result) if get_entity_identifier else None
                    old_values = get_old_values(result) if get_old_values else None
                    new_values = get_new_values(result) if get_new_values else None
                    
                    AuditLogger.log_admin_action(
                        db=db,
                        request=request,
                        user=user,
                        action_type=action_type,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        entity_identifier=entity_identifier,
                        old_values=old_values,
                        new_values=new_values
                    )
                    db.commit()  # Commit audit log
                except Exception as e:
                    # Log audit failure but don't break the main operation
                    print(f"Audit logging failed: {e}")
            
            return result
        return wrapper
    return decorator

# Manual audit logging functions for specific use cases
def audit_item_creation(db: Session, request: Request, user: User, item):
    """Audit item creation"""
    return AuditLogger.log_admin_action(
        db=db,
        request=request,
        user=user,
        action_type="CREATE",
        entity_type="item",
        entity_id=str(item.id),
        entity_identifier=item.sku,
        new_values={
            "sku": item.sku,
            "name": item.name,
            "unit": item.unit,
            "status": item.status
        }
    )

def audit_item_update(db: Session, request: Request, user: User, item, old_data: Dict):
    """Audit item update"""
    return AuditLogger.log_admin_action(
        db=db,
        request=request,
        user=user,
        action_type="UPDATE",
        entity_type="item",
        entity_id=str(item.id),
        entity_identifier=item.sku,
        old_values=old_data,
        new_values={
            "sku": item.sku,
            "name": item.name,
            "unit": item.unit,
            "status": item.status
        }
    )

def audit_item_deletion(db: Session, request: Request, user: User, item):
    """Audit item deletion (soft delete)"""
    return AuditLogger.log_admin_action(
        db=db,
        request=request,
        user=user,
        action_type="DELETE",
        entity_type="item",
        entity_id=str(item.id),
        entity_identifier=item.sku,
        old_values={
            "sku": item.sku,
            "name": item.name,
            "is_deleted": False
        },
        new_values={
            "is_deleted": True
        }
    )

def audit_stock_adjustment(db: Session, request: Request, user: User, ledger_entry):
    """Audit stock adjustment"""
    return AuditLogger.log_admin_action(
        db=db,
        request=request,
        user=user,
        action_type="ADJUSTMENT",
        entity_type="stock_ledger",
        entity_id=str(ledger_entry.id),
        entity_identifier=ledger_entry.transaction_id,
        new_values={
            "item_id": ledger_entry.item_id,
            "location_id": ledger_entry.location_id,
            "quantity": str(ledger_entry.quantity),
            "transaction_type": ledger_entry.transaction_type,
            "reference_no": ledger_entry.reference_no
        },
        notes=f"Stock adjustment by {user.role.value}"
    )

# Global audit service instance
# audit_service = AuditLogger()  # Fixed C02: Use existing class
