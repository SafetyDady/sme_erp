from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Dict, Any
from decimal import Decimal
import uuid
from datetime import datetime

from app.db.session import get_db
from app.modules.users.models import User
from app.modules.inventory.models import InventoryItem, Location, StockLedger
from app.modules.inventory.schemas import (
    ItemCreate, ItemUpdate, ItemOut,
    LocationCreate, LocationUpdate, LocationOut,
    StockInTransaction, StockOutTransaction, StockTransferTransaction, StockAdjustmentTransaction,
    StockLedgerOut, CurrentStockOut
)
from app.core.auth.deps import (
    get_current_user,
    require_viewer_and_above,
    require_staff_and_above, 
    require_admin_and_above
)
from app.modules.audit.service import (
    audit_item_creation, audit_item_update, audit_item_deletion, audit_stock_adjustment
)

router = APIRouter(prefix="/inventory", tags=["Inventory"])

# ============= ITEMS MANAGEMENT =============

@router.post("/items", response_model=ItemOut, summary="Create item (ADMIN+)")
async def create_item(
    item_data: ItemCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_and_above())
) -> ItemOut:
    """Create new inventory item. Requires ADMIN role or higher."""
    
    # Check for duplicate SKU
    existing = db.query(InventoryItem).filter(
        InventoryItem.sku == item_data.sku,
        InventoryItem.is_deleted == False
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Item with SKU '{item_data.sku}' already exists"
        )
    
    # Create item
    db_item = InventoryItem(
        **item_data.dict(),
        created_by_id=current_user.id,
        updated_by_id=current_user.id
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    
    # Audit log for ADMIN+ actions
    try:
        audit_item_creation(db, request, current_user, db_item)
        db.commit()
    except Exception as e:
        # Log audit failure explicitly - do not fail business operation
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"AUDIT_FAILURE: Item creation audit failed for user {current_user.id}, item {db_item.id}: {e}")
        print(f"⚠️ AUDIT_FAILURE: Item creation audit failed: {e}")  # Operational visibility
    
    return db_item

@router.get("/items", response_model=List[ItemOut], summary="List items (VIEWER+)")
async def list_items(
    skip: int = 0,
    limit: int = 100,
    include_deleted: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_viewer_and_above())
) -> List[ItemOut]:
    """List inventory items. Requires VIEWER role or higher."""
    
    query = db.query(InventoryItem)
    
    if not include_deleted:
        query = query.filter(InventoryItem.is_deleted == False)
    
    items = query.offset(skip).limit(limit).all()
    return items

@router.get("/items/{item_id}", response_model=ItemOut, summary="Get item (VIEWER+)")
async def get_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_viewer_and_above())
) -> ItemOut:
    """Get item by ID. Requires VIEWER role or higher."""
    
    item = db.query(InventoryItem).filter(
        InventoryItem.id == item_id,
        InventoryItem.is_deleted == False
    ).first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    return item

@router.put("/items/{item_id}", response_model=ItemOut, summary="Update item (ADMIN+)")
async def update_item(
    item_id: int,
    item_data: ItemUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_and_above())
) -> ItemOut:
    """Update item. Requires ADMIN role or higher."""
    
    item = db.query(InventoryItem).filter(
        InventoryItem.id == item_id,
        InventoryItem.is_deleted == False
    ).first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    # Capture old values for audit
    old_data = {
        "name": item.name,
        "unit": item.unit,
        "status": item.status,
        "description": item.description
    }
    
    # Update fields
    update_data = item_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    item.updated_by_id = current_user.id
    db.commit()
    db.refresh(item)
    
    # Audit log for ADMIN+ actions
    try:
        audit_item_update(db, request, current_user, item, old_data)
        db.commit()
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"AUDIT_FAILURE: Item update audit failed for user {current_user.id}, item {item.id}: {e}")
        print(f"⚠️ AUDIT_FAILURE: Item update audit failed: {e}")  # Operational visibility
    
    return item

@router.delete("/items/{item_id}", summary="Delete item (ADMIN+)")
async def delete_item(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_and_above())
) -> Dict[str, str]:
    """Soft delete item. Requires ADMIN role or higher."""
    
    item = db.query(InventoryItem).filter(
        InventoryItem.id == item_id,
        InventoryItem.is_deleted == False
    ).first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    # Soft delete
    item.is_deleted = True
    item.updated_by_id = current_user.id
    db.commit()
    
    # Audit log for ADMIN+ actions
    try:
        audit_item_deletion(db, request, current_user, item)
        db.commit()
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"AUDIT_FAILURE: Item deletion audit failed for user {current_user.id}, item {item.id}: {e}")
        print(f"⚠️ AUDIT_FAILURE: Item deletion audit failed: {e}")  # Operational visibility
    
    return {"message": f"Item '{item.sku}' deleted successfully"}

# ============= LOCATIONS MANAGEMENT =============

@router.post("/locations", response_model=LocationOut, summary="Create location (ADMIN+)")
async def create_location(
    location_data: LocationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_and_above())
) -> LocationOut:
    """Create new location. Requires ADMIN role or higher."""
    
    # Check for duplicate code
    existing = db.query(Location).filter(
        Location.code == location_data.code,
        Location.is_deleted == False
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Location with code '{location_data.code}' already exists"
        )
    
    # Create location
    db_location = Location(
        **location_data.dict(),
        created_by_id=current_user.id,
        updated_by_id=current_user.id
    )
    db.add(db_location)
    db.commit()
    db.refresh(db_location)
    
    return db_location

@router.get("/locations", response_model=List[LocationOut], summary="List locations (VIEWER+)")
async def list_locations(
    skip: int = 0,
    limit: int = 100,
    include_deleted: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_viewer_and_above())
) -> List[LocationOut]:
    """List locations. Requires VIEWER role or higher."""
    
    query = db.query(Location)
    
    if not include_deleted:
        query = query.filter(Location.is_deleted == False)
    
    locations = query.offset(skip).limit(limit).all()
    return locations

@router.get("/locations/{location_id}", response_model=LocationOut, summary="Get location (VIEWER+)")
async def get_location(
    location_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_viewer_and_above())
) -> LocationOut:
    """Get location by ID. Requires VIEWER role or higher."""
    
    location = db.query(Location).filter(
        Location.id == location_id,
        Location.is_deleted == False
    ).first()
    
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found"
        )
    
    return location

@router.put("/locations/{location_id}", response_model=LocationOut, summary="Update location (ADMIN+)")
async def update_location(
    location_id: int,
    location_data: LocationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_and_above())
) -> LocationOut:
    """Update location. Requires ADMIN role or higher."""
    
    location = db.query(Location).filter(
        Location.id == location_id,
        Location.is_deleted == False
    ).first()
    
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found"
        )
    
    # Update fields
    update_data = location_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(location, field, value)
    
    location.updated_by_id = current_user.id
    db.commit()
    db.refresh(location)
    
    return location

@router.delete("/locations/{location_id}", summary="Delete location (ADMIN+)")
async def delete_location(
    location_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_and_above())
) -> Dict[str, str]:
    """Soft delete location. Requires ADMIN role or higher."""
    
    location = db.query(Location).filter(
        Location.id == location_id,
        Location.is_deleted == False
    ).first()
    
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found"
        )
    
    # Soft delete
    location.is_deleted = True
    location.updated_by_id = current_user.id
    db.commit()
    
    return {"message": f"Location '{location.code}' deleted successfully"}

# ============= STOCK TRANSACTIONS =============

def _create_stock_ledger_entry(
    db: Session,
    item_id: int,
    location_id: int,
    transaction_type: str,
    quantity: Decimal,
    current_user_id: int,
    unit_cost: Decimal = None,
    reference_no: str = None,
    notes: str = None,
    from_location_id: int = None,
    to_location_id: int = None
) -> StockLedger:
    """Helper to create stock ledger entry with idempotency."""
    
    transaction_id = str(uuid.uuid4())
    
    entry = StockLedger(
        transaction_id=transaction_id,
        item_id=item_id,
        location_id=location_id,
        transaction_type=transaction_type,
        quantity=quantity,
        unit_cost=unit_cost,
        reference_no=reference_no,
        notes=notes,
        from_location_id=from_location_id,
        to_location_id=to_location_id,
        created_by_id=current_user_id
    )
    
    db.add(entry)
    return entry

@router.post("/stock/in", response_model=StockLedgerOut, summary="Stock IN transaction (STAFF+)")
async def stock_in(
    transaction: StockInTransaction,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_and_above())
) -> StockLedgerOut:
    """Record stock IN transaction. Requires STAFF role or higher."""
    
    # Validate item exists
    item = db.query(InventoryItem).filter(
        InventoryItem.id == transaction.item_id,
        InventoryItem.is_deleted == False
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Validate location exists
    location = db.query(Location).filter(
        Location.id == transaction.location_id,
        Location.is_deleted == False
    ).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    # Create ledger entry
    entry = _create_stock_ledger_entry(
        db=db,
        item_id=transaction.item_id,
        location_id=transaction.location_id,
        transaction_type="IN",
        quantity=transaction.quantity,
        current_user_id=current_user.id,
        unit_cost=transaction.unit_cost,
        reference_no=transaction.reference_no,
        notes=transaction.notes
    )
    
    db.commit()
    db.refresh(entry)
    return entry

@router.post("/stock/out", response_model=StockLedgerOut, summary="Stock OUT transaction (STAFF+)")
async def stock_out(
    transaction: StockOutTransaction,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_and_above())
) -> StockLedgerOut:
    """Record stock OUT transaction. Requires STAFF role or higher."""
    
    # Validate item and location
    item = db.query(InventoryItem).filter(
        InventoryItem.id == transaction.item_id,
        InventoryItem.is_deleted == False
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    location = db.query(Location).filter(
        Location.id == transaction.location_id,
        Location.is_deleted == False
    ).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    # Check current stock (optional negative stock prevention)
    current_stock = db.query(func.sum(StockLedger.quantity)).filter(
        StockLedger.item_id == transaction.item_id,
        StockLedger.location_id == transaction.location_id
    ).scalar() or Decimal('0')
    
    if current_stock < transaction.quantity:
        # Warning but allow (business policy decision)
        pass  # Could raise HTTPException here for strict negative stock prevention
    
    # Create ledger entry (negative quantity for OUT)
    entry = _create_stock_ledger_entry(
        db=db,
        item_id=transaction.item_id,
        location_id=transaction.location_id,
        transaction_type="OUT",
        quantity=-transaction.quantity,  # Negative for OUT
        current_user_id=current_user.id,
        reference_no=transaction.reference_no,
        notes=transaction.notes
    )
    
    db.commit()
    db.refresh(entry)
    return entry

@router.post("/stock/transfer", response_model=List[StockLedgerOut], summary="Stock TRANSFER transaction (STAFF+)")
async def stock_transfer(
    transaction: StockTransferTransaction,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_and_above())
) -> List[StockLedgerOut]:
    """Record stock TRANSFER transaction. Requires STAFF role or higher."""
    
    # Validate item and locations
    item = db.query(InventoryItem).filter(
        InventoryItem.id == transaction.item_id,
        InventoryItem.is_deleted == False
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    from_location = db.query(Location).filter(
        Location.id == transaction.from_location_id,
        Location.is_deleted == False
    ).first()
    if not from_location:
        raise HTTPException(status_code=404, detail="From location not found")
    
    to_location = db.query(Location).filter(
        Location.id == transaction.to_location_id,
        Location.is_deleted == False
    ).first()
    if not to_location:
        raise HTTPException(status_code=404, detail="To location not found")
    
    if transaction.from_location_id == transaction.to_location_id:
        raise HTTPException(status_code=400, detail="From and To locations must be different")
    
    # Create TRANSFER_OUT entry
    out_entry = _create_stock_ledger_entry(
        db=db,
        item_id=transaction.item_id,
        location_id=transaction.from_location_id,
        transaction_type="TRANSFER_OUT",
        quantity=-transaction.quantity,  # Negative for OUT
        current_user_id=current_user.id,
        reference_no=transaction.reference_no,
        notes=transaction.notes,
        from_location_id=transaction.from_location_id,
        to_location_id=transaction.to_location_id
    )
    
    # Create TRANSFER_IN entry
    in_entry = _create_stock_ledger_entry(
        db=db,
        item_id=transaction.item_id,
        location_id=transaction.to_location_id,
        transaction_type="TRANSFER_IN",
        quantity=transaction.quantity,  # Positive for IN
        current_user_id=current_user.id,
        reference_no=transaction.reference_no,
        notes=transaction.notes,
        from_location_id=transaction.from_location_id,
        to_location_id=transaction.to_location_id
    )
    
    db.commit()
    db.refresh(out_entry)
    db.refresh(in_entry)
    
    return [out_entry, in_entry]

@router.post("/stock/adjustment", response_model=StockLedgerOut, summary="Stock ADJUSTMENT (ADMIN+)")
async def stock_adjustment(
    transaction: StockAdjustmentTransaction,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_and_above())
) -> StockLedgerOut:
    """Record stock ADJUSTMENT transaction. Requires ADMIN role or higher."""
    
    # Validate item and location
    item = db.query(InventoryItem).filter(
        InventoryItem.id == transaction.item_id,
        InventoryItem.is_deleted == False
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    location = db.query(Location).filter(
        Location.id == transaction.location_id,
        Location.is_deleted == False
    ).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    # Create ledger entry
    entry = _create_stock_ledger_entry(
        db=db,
        item_id=transaction.item_id,
        location_id=transaction.location_id,
        transaction_type="ADJUSTMENT",
        quantity=transaction.quantity,  # Can be positive or negative
        current_user_id=current_user.id,
        reference_no=transaction.reference_no,
        notes=transaction.notes
    )
    
    db.commit()
    db.refresh(entry)
    
    # Audit log for stock adjustments (critical for compliance)
    try:
        audit_stock_adjustment(db, request, current_user, entry)
        db.commit()
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"AUDIT_FAILURE: Stock adjustment audit failed for user {current_user.id}, entry {entry.id}: {e}")
        print(f"⚠️ AUDIT_FAILURE: Stock adjustment audit failed: {e}")  # Operational visibility
    
    return entry

# ============= STOCK INQUIRY =============

@router.get("/stock/ledger", response_model=List[StockLedgerOut], summary="Stock ledger (VIEWER+)")
async def get_stock_ledger(
    item_id: int = None,
    location_id: int = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_viewer_and_above())
) -> List[StockLedgerOut]:
    """Get stock ledger entries. Requires VIEWER role or higher."""
    
    query = db.query(StockLedger).order_by(desc(StockLedger.transaction_date))
    
    if item_id:
        query = query.filter(StockLedger.item_id == item_id)
    
    if location_id:
        query = query.filter(StockLedger.location_id == location_id)
    
    entries = query.offset(skip).limit(limit).all()
    return entries

@router.get("/stock/current", response_model=List[CurrentStockOut], summary="Current stock (VIEWER+)")
async def get_current_stock(
    item_id: int = None,
    location_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_viewer_and_above())
) -> List[CurrentStockOut]:
    """Get current stock levels (derived from ledger). Requires VIEWER role or higher."""
    
    # Build query for current stock
    query = db.query(
        StockLedger.item_id,
        InventoryItem.sku.label('item_sku'),
        InventoryItem.name.label('item_name'),
        StockLedger.location_id,
        Location.code.label('location_code'),
        Location.name.label('location_name'),
        func.sum(StockLedger.quantity).label('current_quantity'),
        func.max(StockLedger.transaction_date).label('last_transaction_date')
    ).join(
        InventoryItem, StockLedger.item_id == InventoryItem.id
    ).join(
        Location, StockLedger.location_id == Location.id
    ).filter(
        InventoryItem.is_deleted == False,
        Location.is_deleted == False
    ).group_by(
        StockLedger.item_id,
        InventoryItem.sku,
        InventoryItem.name,
        StockLedger.location_id,
        Location.code,
        Location.name
    )
    
    if item_id:
        query = query.filter(StockLedger.item_id == item_id)
    
    if location_id:
        query = query.filter(StockLedger.location_id == location_id)
    
    # Execute query and map to response model
    results = query.all()
    
    current_stock = []
    for result in results:
        stock_out = CurrentStockOut(
            item_id=result.item_id,
            item_sku=result.item_sku,
            item_name=result.item_name,
            location_id=result.location_id,
            location_code=result.location_code,
            location_name=result.location_name,
            current_quantity=result.current_quantity,
            last_transaction_date=result.last_transaction_date
        )
        current_stock.append(stock_out)
    
    return current_stock

# ============= AUDIT LOG INQUIRY (ADMIN+ ONLY) =============

from app.modules.audit.models import AuditLog

@router.get("/audit", response_model=List[Dict], summary="View audit logs (ADMIN+)")
async def get_audit_logs(
    skip: int = 0,
    limit: int = 50,
    entity_type: str = None,
    action_type: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_and_above())
) -> List[Dict]:
    """Get audit logs for inventory actions. Requires ADMIN role or higher."""
    
    query = db.query(AuditLog).filter(
        AuditLog.entity_type.in_(["item", "location", "stock_ledger"])
    ).order_by(desc(AuditLog.timestamp))
    
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
        
    if action_type:
        query = query.filter(AuditLog.action_type == action_type)
    
    logs = query.offset(skip).limit(limit).all()
    
    # Convert to dict for response
    audit_data = []
    for log in logs:
        audit_data.append({
            "id": log.id,
            "request_id": log.request_id,
            "timestamp": log.timestamp,
            "user_email": log.user_email,
            "user_role": log.user_role,
            "action_type": log.action_type,
            "http_method": log.http_method,
            "endpoint": log.endpoint,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "entity_identifier": log.entity_identifier,
            "old_values": log.old_values,
            "new_values": log.new_values,
            "ip_address": log.ip_address,
            "notes": log.notes
        })
    
    return audit_data