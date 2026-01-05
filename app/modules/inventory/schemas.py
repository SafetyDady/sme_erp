from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum

# Enums
class ItemStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DISCONTINUED = "DISCONTINUED"

class LocationType(str, Enum):
    WAREHOUSE = "WAREHOUSE"
    BIN = "BIN"
    ZONE = "ZONE"

class TransactionType(str, Enum):
    IN = "IN"
    OUT = "OUT"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    ADJUSTMENT = "ADJUSTMENT"

# Item schemas
class ItemBase(BaseModel):
    sku: str = Field(..., max_length=50, description="Stock Keeping Unit")
    name: str = Field(..., max_length=255, description="Item name")
    unit: str = Field(default="PCS", max_length=20, description="Unit of measure")
    status: ItemStatus = Field(default=ItemStatus.ACTIVE, description="Item status")
    description: Optional[str] = Field(None, max_length=500)

class ItemCreate(ItemBase):
    pass

class ItemUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    unit: Optional[str] = Field(None, max_length=20)
    status: Optional[ItemStatus] = None
    description: Optional[str] = Field(None, max_length=500)

class ItemOut(ItemBase):
    id: int
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    created_by_id: int
    updated_by_id: int

    model_config = ConfigDict(
from_attributes=True)

# Location schemas
class LocationBase(BaseModel):
    code: str = Field(..., max_length=30, description="Location code")
    name: str = Field(..., max_length=255, description="Location name")
    location_type: LocationType = Field(default=LocationType.WAREHOUSE)
    address: Optional[str] = Field(None, max_length=500)
    parent_id: Optional[int] = None

class LocationCreate(LocationBase):
    pass

class LocationUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    location_type: Optional[LocationType] = None
    address: Optional[str] = Field(None, max_length=500)
    parent_id: Optional[int] = None

class LocationOut(LocationBase):
    id: int
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    created_by_id: int
    updated_by_id: int

    model_config = ConfigDict(
from_attributes=True)

# Stock Transaction schemas
class StockTransactionBase(BaseModel):
    item_id: int
    location_id: int
    transaction_type: TransactionType
    quantity: Decimal = Field(..., description="Transaction quantity")
    unit_cost: Optional[Decimal] = Field(None)
    reference_no: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=500)

class StockInTransaction(BaseModel):
    """Stock IN transaction"""
    item_id: int
    location_id: int
    quantity: Decimal = Field(..., gt=0)
    unit_cost: Optional[Decimal] = Field(None)
    reference_no: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=500)

class StockOutTransaction(BaseModel):
    """Stock OUT transaction"""
    item_id: int
    location_id: int
    quantity: Decimal = Field(..., gt=0)
    reference_no: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=500)

class StockTransferTransaction(BaseModel):
    """Stock TRANSFER transaction"""
    item_id: int
    from_location_id: int
    to_location_id: int
    quantity: Decimal = Field(..., gt=0)
    reference_no: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=500)

class StockAdjustmentTransaction(BaseModel):
    """Stock ADJUSTMENT transaction"""
    item_id: int
    location_id: int
    quantity: Decimal = Field(..., description="Adjustment quantity (can be negative)")
    reference_no: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=500)

class StockLedgerOut(BaseModel):
    id: int
    transaction_id: str
    item_id: int
    location_id: int
    transaction_type: TransactionType
    quantity: Decimal
    unit_cost: Optional[Decimal]
    reference_no: Optional[str]
    from_location_id: Optional[int]
    to_location_id: Optional[int]
    notes: Optional[str]
    transaction_date: datetime
    created_by_id: int
    created_at: datetime

    model_config = ConfigDict(
from_attributes=True)

class CurrentStockOut(BaseModel):
    """Current stock summary by item and location"""
    item_id: int
    item_sku: str
    item_name: str
    location_id: int
    location_code: str
    location_name: str
    current_quantity: Decimal
    last_transaction_date: Optional[datetime]

    model_config = ConfigDict(
from_attributes=True)