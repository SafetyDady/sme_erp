from datetime import datetime
from pydantic import BaseModel, Field
from app.models.inventory import ItemType, TxType

class ItemCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    item_type: ItemType
    uom: str = Field(default="EA", max_length=32)

class ItemOut(BaseModel):
    id: int
    code: str
    name: str
    item_type: ItemType
    uom: str
    created_at: datetime
    class Config:
        from_attributes = True

class LocationCreate(BaseModel):
    code: str
    name: str

class LocationOut(BaseModel):
    id: int
    code: str
    name: str
    class Config:
        from_attributes = True

class TxCreate(BaseModel):
    tx_type: TxType
    item_code: str
    qty: int = Field(gt=0)

    from_location_code: str | None = None
    to_location_code: str | None = None

    reference: str | None = None
    note: str | None = None

class TxOut(BaseModel):
    id: int
    tx_type: TxType
    qty: int
    reference: str | None
    note: str | None
    created_at: datetime
    class Config:
        from_attributes = True

class StockOut(BaseModel):
    item_code: str
    location_code: str
    qty_on_hand: int