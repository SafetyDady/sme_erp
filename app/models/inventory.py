import enum
from datetime import datetime
from sqlalchemy import (
    String, Integer, DateTime, Enum, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class ItemType(str, enum.Enum):
    MATERIAL = "MATERIAL"   # วัสดุสิ้นเปลือง/วัตถุดิบ
    TOOL = "TOOL"           # เครื่องมือ/สินทรัพย์

class TxType(str, enum.Enum):
    IN = "IN"               # รับเข้า
    OUT = "OUT"             # เบิก/จ่ายออก
    TRANSFER = "TRANSFER"   # ย้ายที่เก็บ
    ADJUST = "ADJUST"       # ปรับยอด (ต้องมีเหตุผล)
    RETURN = "RETURN"       # คืน

class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    item_type: Mapped[ItemType] = mapped_column(Enum(ItemType), index=True)

    uom: Mapped[str] = mapped_column(String(32), default="EA")  # unit of measure
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    stocks = relationship("StockBalance", back_populates="item", cascade="all, delete-orphan")
    txs = relationship("InventoryTx", back_populates="item", cascade="all, delete-orphan")

class Location(Base):
    __tablename__ = "locations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class StockBalance(Base):
    """
    คงเหลือ ณ ปัจจุบัน (derived state)
    ตัวจริงคือ InventoryTx (ledger)
    """
    __tablename__ = "stock_balances"
    __table_args__ = (
        UniqueConstraint("item_id", "location_id", name="uq_item_location"),
        Index("ix_stock_item_location", "item_id", "location_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"))
    qty_on_hand: Mapped[int] = mapped_column(Integer, default=0)

    item = relationship("Item", back_populates="stocks")
    location = relationship("Location")

class InventoryTx(Base):
    __tablename__ = "inventory_txs"
    __table_args__ = (
        Index("ix_tx_item_date", "item_id", "created_at"),
        Index("ix_tx_location_date", "from_location_id", "to_location_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    tx_type: Mapped[TxType] = mapped_column(Enum(TxType), index=True)

    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    qty: Mapped[int] = mapped_column(Integer)  # integer for MVP (later decimal)

    from_location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"), nullable=True)
    to_location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"), nullable=True)

    reference: Mapped[str | None] = mapped_column(String(128), nullable=True)  # เลขเอกสาร/PR/PO/Job
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    item = relationship("Item", back_populates="txs")
    from_location = relationship("Location", foreign_keys=[from_location_id])
    to_location = relationship("Location", foreign_keys=[to_location_id])