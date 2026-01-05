from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Index, CheckConstraint, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base
from decimal import Decimal as PyDecimal

class InventoryItem(Base):
    """Master data for inventory items (SKUs)"""
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    unit = Column(String(20), nullable=False, default="PCS")  # PCS, KG, M, etc.
    status = Column(String(20), nullable=False, default="ACTIVE")  # ACTIVE, INACTIVE, DISCONTINUED
    description = Column(String(500))
    
    # Soft delete
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    stock_ledger_entries = relationship("StockLedger", back_populates="item")

    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE', 'DISCONTINUED')", name="check_item_status"),
        Index("idx_item_sku_active", "sku", "is_deleted"),
        Index("idx_item_status_active", "status", "is_deleted"),
    )

class Location(Base):
    """Warehouse locations and bins"""
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(30), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    location_type = Column(String(20), nullable=False, default="WAREHOUSE")  # WAREHOUSE, BIN, ZONE
    address = Column(String(500))
    parent_id = Column(Integer, ForeignKey("locations.id"), nullable=True)  # For hierarchical locations
    
    # Soft delete
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    children = relationship("Location", back_populates="parent", remote_side=[parent_id])
    parent = relationship("Location", back_populates="children", remote_side=[id])
    stock_ledger_entries = relationship("StockLedger", back_populates="location", foreign_keys="StockLedger.location_id")

    __table_args__ = (
        CheckConstraint("location_type IN ('WAREHOUSE', 'BIN', 'ZONE')", name="check_location_type"),
        Index("idx_location_code_active", "code", "is_deleted"),
        Index("idx_location_type_active", "location_type", "is_deleted"),
    )

class StockLedger(Base):
    """Immutable stock transaction ledger"""
    __tablename__ = "stock_ledger"

    id = Column(Integer, primary_key=True, index=True)
    
    # Transaction identification (for idempotency)
    transaction_id = Column(String(50), unique=True, nullable=False, index=True)
    reference_no = Column(String(100), nullable=True)  # External reference (PO, SO, etc.)
    
    # What/Where/When
    item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    transaction_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Transaction details
    transaction_type = Column(String(20), nullable=False)  # IN, OUT, TRANSFER_IN, TRANSFER_OUT, ADJUSTMENT
    quantity = Column(Numeric(15, 3), nullable=False)  # Can be negative for OUT transactions
    unit_cost = Column(Numeric(15, 2), nullable=True)  # For cost tracking
    
    # Transfer details (for TRANSFER_IN/TRANSFER_OUT)
    from_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    to_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    
    # Business context
    notes = Column(String(500))
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    item = relationship("InventoryItem", back_populates="stock_ledger_entries")
    location = relationship("Location", back_populates="stock_ledger_entries", foreign_keys=[location_id])
    from_location = relationship("Location", foreign_keys=[from_location_id])
    to_location = relationship("Location", foreign_keys=[to_location_id])

    __table_args__ = (
        CheckConstraint("transaction_type IN ('IN', 'OUT', 'TRANSFER_IN', 'TRANSFER_OUT', 'ADJUSTMENT')", 
                       name="check_transaction_type"),
        CheckConstraint("quantity != 0", name="check_nonzero_quantity"),
        CheckConstraint(
            "(transaction_type IN ('TRANSFER_IN', 'TRANSFER_OUT') AND from_location_id IS NOT NULL AND to_location_id IS NOT NULL) OR "
            "(transaction_type IN ('IN', 'OUT', 'ADJUSTMENT') AND from_location_id IS NULL AND to_location_id IS NULL)", 
            name="check_transfer_locations"
        ),
        Index("idx_stock_item_location_date", "item_id", "location_id", "transaction_date"),
        Index("idx_stock_transaction_type", "transaction_type", "transaction_date"),
        Index("idx_stock_reference", "reference_no", "transaction_date"),
    )