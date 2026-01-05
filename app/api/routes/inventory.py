from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.db import get_db
from app.models.inventory import Item, Location, StockBalance, InventoryTx, TxType
from app.schemas.inventory import (
    ItemCreate, ItemOut,
    LocationCreate, LocationOut,
    TxCreate, TxOut, StockOut
)

router = APIRouter(prefix="/inventory", tags=["inventory"])

@router.post("/items", response_model=ItemOut)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)):
    exists = db.scalar(select(Item).where(Item.code == payload.code))
    if exists:
        raise HTTPException(status_code=409, detail="Item code already exists")

    item = Item(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@router.get("/items", response_model=list[ItemOut])
def list_items(db: Session = Depends(get_db)):
    return list(db.scalars(select(Item).order_by(Item.id)).all())

@router.post("/locations", response_model=LocationOut)
def create_location(payload: LocationCreate, db: Session = Depends(get_db)):
    exists = db.scalar(select(Location).where(Location.code == payload.code))
    if exists:
        raise HTTPException(status_code=409, detail="Location code already exists")

    loc = Location(**payload.model_dump())
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc

@router.get("/locations", response_model=list[LocationOut])
def list_locations(db: Session = Depends(get_db)):
    return list(db.scalars(select(Location).order_by(Location.id)).all())

def _get_item_by_code(db: Session, code: str) -> Item:
    item = db.scalar(select(Item).where(Item.code == code))
    if not item:
        raise HTTPException(status_code=404, detail=f"Item not found: {code}")
    return item

def _get_loc_by_code(db: Session, code: str) -> Location:
    loc = db.scalar(select(Location).where(Location.code == code))
    if not loc:
        raise HTTPException(status_code=404, detail=f"Location not found: {code}")
    return loc

def _get_or_create_balance(db: Session, item_id: int, location_id: int) -> StockBalance:
    bal = db.scalar(select(StockBalance).where(
        StockBalance.item_id == item_id,
        StockBalance.location_id == location_id
    ))
    if bal:
        return bal
    bal = StockBalance(item_id=item_id, location_id=location_id, qty_on_hand=0)
    db.add(bal)
    db.flush()  # ให้ได้ id
    return bal

@router.post("/tx", response_model=TxOut)
def create_tx(payload: TxCreate, db: Session = Depends(get_db)):
    item = _get_item_by_code(db, payload.item_code)

    from_loc = _get_loc_by_code(db, payload.from_location_code) if payload.from_location_code else None
    to_loc = _get_loc_by_code(db, payload.to_location_code) if payload.to_location_code else None

    # Validate ตามประเภท
    if payload.tx_type == TxType.IN and not to_loc:
        raise HTTPException(400, "IN requires to_location_code")
    if payload.tx_type == TxType.OUT and not from_loc:
        raise HTTPException(400, "OUT requires from_location_code")
    if payload.tx_type == TxType.TRANSFER and (not from_loc or not to_loc):
        raise HTTPException(400, "TRANSFER requires both from_location_code and to_location_code")

    # Check stock ก่อน OUT/TRANSFER
    if payload.tx_type in (TxType.OUT, TxType.TRANSFER):
        bal_from = _get_or_create_balance(db, item.id, from_loc.id)
        if bal_from.qty_on_hand < payload.qty:
            raise HTTPException(409, f"Insufficient stock at {from_loc.code}: {bal_from.qty_on_hand}")

    tx = InventoryTx(
        tx_type=payload.tx_type,
        item_id=item.id,
        qty=payload.qty,
        from_location_id=from_loc.id if from_loc else None,
        to_location_id=to_loc.id if to_loc else None,
        reference=payload.reference,
        note=payload.note,
    )
    db.add(tx)

    # Apply to balances
    if payload.tx_type == TxType.IN:
        bal_to = _get_or_create_balance(db, item.id, to_loc.id)
        bal_to.qty_on_hand += payload.qty

    elif payload.tx_type == TxType.OUT:
        bal_from = _get_or_create_balance(db, item.id, from_loc.id)
        bal_from.qty_on_hand -= payload.qty

    elif payload.tx_type == TxType.TRANSFER:
        bal_from = _get_or_create_balance(db, item.id, from_loc.id)
        bal_to = _get_or_create_balance(db, item.id, to_loc.id)
        bal_from.qty_on_hand -= payload.qty
        bal_to.qty_on_hand += payload.qty

    else:
        # ADJUST/RETURN จะเพิ่มกติกาในรอบถัดไป (ตอนนี้ให้ผ่านเฉย ๆ หรือจะบังคับทีหลังก็ได้)
        pass

    db.commit()
    db.refresh(tx)
    return tx

@router.get("/stock", response_model=list[StockOut])
def list_stock(db: Session = Depends(get_db)):
    rows = db.execute(
        select(StockBalance, Item, Location)
        .join(Item, StockBalance.item_id == Item.id)
        .join(Location, StockBalance.location_id == Location.id)
        .order_by(Item.code, Location.code)
    ).all()

    out: list[StockOut] = []
    for bal, item, loc in rows:
        out.append(StockOut(item_code=item.code, location_code=loc.code, qty_on_hand=bal.qty_on_hand))
    return out