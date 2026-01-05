from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Index
from sqlalchemy.sql import func
from app.db.session import Base

class AuditLog(Base):
    """Append-only audit log for sensitive admin actions"""
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    
    # Request traceability
    request_id = Column(String(50), nullable=False, index=True)
    
    # Who performed the action
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_email = Column(String(255), nullable=False)  # Denormalized for auditability
    user_role = Column(String(50), nullable=False)
    
    # What action was performed
    action_type = Column(String(50), nullable=False)  # CREATE, UPDATE, DELETE, ADJUSTMENT
    http_method = Column(String(10), nullable=False)  # POST, PUT, DELETE
    endpoint = Column(String(255), nullable=False)    # /api/v1/inventory/items
    
    # What entity was affected
    entity_type = Column(String(50), nullable=False)  # item, location, stock_ledger
    entity_id = Column(String(100), nullable=True)    # ID of the affected entity
    entity_identifier = Column(String(255), nullable=True)  # SKU, code, etc for reference
    
    # Change details
    old_values = Column(Text, nullable=True)  # JSON of old values (for UPDATE/DELETE)
    new_values = Column(Text, nullable=True)  # JSON of new values (for CREATE/UPDATE)
    
    # When
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Additional context
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6
    user_agent = Column(String(500), nullable=True)
    notes = Column(String(1000), nullable=True)
    
    __table_args__ = (
        Index("idx_audit_user_action", "user_id", "action_type", "timestamp"),
        Index("idx_audit_entity", "entity_type", "entity_id", "timestamp"),
        Index("idx_audit_request", "request_id", "timestamp"),
        Index("idx_audit_timestamp", "timestamp"),
    )