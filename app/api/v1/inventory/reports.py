from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_, text
from typing import List, Dict, Any, Optional
from decimal import Decimal
import io
import csv
from datetime import datetime, date, timedelta

from app.db.session import get_db
from app.modules.users.models import User
from app.modules.inventory.models import InventoryItem, Location, StockLedger
from app.modules.inventory.schemas import CurrentStockOut, StockLedgerOut
from app.core.auth.deps import (
    require_viewer_and_above,
    require_admin_and_above
)

router = APIRouter(prefix="/inventory/reports", tags=["Inventory Reports"])

# ============= INVENTORY REPORTS (READ-ONLY) =============

@router.get("/snapshot", response_model=List[CurrentStockOut], summary="Inventory snapshot (VIEWER+)")
async def get_inventory_snapshot(
    location_id: Optional[int] = Query(None, description="Filter by location ID"),
    item_sku: Optional[str] = Query(None, description="Filter by item SKU"),
    item_name: Optional[str] = Query(None, description="Search item name (case-insensitive)"),
    status: Optional[str] = Query(None, description="Filter by item status"),
    min_quantity: Optional[Decimal] = Query(None, description="Minimum stock quantity"),
    max_quantity: Optional[Decimal] = Query(None, description="Maximum stock quantity"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_viewer_and_above())
) -> List[CurrentStockOut]:
    """
    Get current inventory snapshot with filtering and pagination.
    Requires VIEWER role or higher.
    
    This endpoint provides a comprehensive view of current stock levels across all locations.
    """
    
    # Build base query for current stock levels
    base_query = db.query(
        StockLedger.item_id,
        InventoryItem.sku.label('item_sku'),
        InventoryItem.name.label('item_name'),
        InventoryItem.status.label('item_status'),
        InventoryItem.unit.label('item_unit'),
        StockLedger.location_id,
        Location.code.label('location_code'),
        Location.name.label('location_name'),
        func.sum(StockLedger.quantity).label('current_quantity'),
        func.max(StockLedger.transaction_date).label('last_transaction_date'),
        func.count(StockLedger.id).label('transaction_count')
    ).select_from(StockLedger).join(
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
        InventoryItem.status,
        InventoryItem.unit,
        StockLedger.location_id,
        Location.code,
        Location.name
    )
    
    # Apply filters
    if location_id:
        base_query = base_query.filter(StockLedger.location_id == location_id)
    
    if item_sku:
        base_query = base_query.filter(InventoryItem.sku.ilike(f"%{item_sku}%"))
    
    if item_name:
        base_query = base_query.filter(InventoryItem.name.ilike(f"%{item_name}%"))
    
    if status:
        base_query = base_query.filter(InventoryItem.status == status)
    
    # Filter by stock quantities (after aggregation)
    if min_quantity is not None or max_quantity is not None:
        having_conditions = []
        if min_quantity is not None:
            having_conditions.append(func.sum(StockLedger.quantity) >= min_quantity)
        if max_quantity is not None:
            having_conditions.append(func.sum(StockLedger.quantity) <= max_quantity)
        base_query = base_query.having(and_(*having_conditions))
    
    # Apply ordering and pagination
    query = base_query.order_by(
        InventoryItem.sku,
        Location.code
    ).offset(skip).limit(limit)
    
    # Execute query
    results = query.all()
    
    # Transform results
    snapshot = []
    for result in results:
        snapshot_item = CurrentStockOut(
            item_id=result.item_id,
            item_sku=result.item_sku,
            item_name=result.item_name,
            location_id=result.location_id,
            location_code=result.location_code,
            location_name=result.location_name,
            current_quantity=result.current_quantity or Decimal('0'),
            last_transaction_date=result.last_transaction_date
        )
        snapshot.append(snapshot_item)
    
    return snapshot


@router.get("/movements", response_model=List[StockLedgerOut], summary="Stock movement history (VIEWER+)")
async def get_stock_movements(
    item_id: Optional[int] = Query(None, description="Filter by item ID"),
    location_id: Optional[int] = Query(None, description="Filter by location ID"),
    transaction_type: Optional[str] = Query(None, description="Filter by transaction type"),
    from_date: Optional[date] = Query(None, description="From date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="To date (YYYY-MM-DD)"),
    reference_no: Optional[str] = Query(None, description="Filter by reference number"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_viewer_and_above())
) -> List[StockLedgerOut]:
    """
    Get stock movement history with comprehensive filtering.
    Requires VIEWER role or higher.
    
    Provides detailed audit trail of all inventory movements.
    """
    
    # Build query with joins for readable information
    query = db.query(StockLedger).order_by(desc(StockLedger.transaction_date))
    
    # Apply filters
    if item_id:
        query = query.filter(StockLedger.item_id == item_id)
    
    if location_id:
        query = query.filter(StockLedger.location_id == location_id)
    
    if transaction_type:
        query = query.filter(StockLedger.transaction_type == transaction_type)
    
    if reference_no:
        query = query.filter(StockLedger.reference_no.ilike(f"%{reference_no}%"))
    
    # Date range filtering
    if from_date:
        query = query.filter(StockLedger.transaction_date >= from_date)
    
    if to_date:
        # Include the entire end date
        query = query.filter(StockLedger.transaction_date < (to_date + timedelta(days=1)))
    
    # Apply pagination
    movements = query.offset(skip).limit(limit).all()
    
    return movements


@router.get("/snapshot/csv", summary="Export inventory snapshot to CSV (ADMIN+)")
async def export_inventory_snapshot_csv(
    location_id: Optional[int] = Query(None, description="Filter by location ID"),
    item_sku: Optional[str] = Query(None, description="Filter by item SKU"),
    item_name: Optional[str] = Query(None, description="Search item name"),
    status: Optional[str] = Query(None, description="Filter by item status"),
    min_quantity: Optional[Decimal] = Query(None, description="Minimum stock quantity"),
    max_quantity: Optional[Decimal] = Query(None, description="Maximum stock quantity"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_and_above())
) -> StreamingResponse:
    """
    Export inventory snapshot to CSV format.
    Requires ADMIN role or higher.
    
    WARNING: This endpoint can generate large files. Use filters to limit data size.
    """
    
    # Get snapshot data (no pagination limit for CSV export)
    base_query = db.query(
        InventoryItem.sku,
        InventoryItem.name,
        InventoryItem.status,
        InventoryItem.unit,
        Location.code.label('location_code'),
        Location.name.label('location_name'),
        func.sum(StockLedger.quantity).label('current_quantity'),
        func.max(StockLedger.transaction_date).label('last_transaction_date'),
        func.count(StockLedger.id).label('transaction_count')
    ).select_from(StockLedger).join(
        InventoryItem, StockLedger.item_id == InventoryItem.id
    ).join(
        Location, StockLedger.location_id == Location.id
    ).filter(
        InventoryItem.is_deleted == False,
        Location.is_deleted == False
    ).group_by(
        InventoryItem.sku,
        InventoryItem.name,
        InventoryItem.status,
        InventoryItem.unit,
        Location.code,
        Location.name
    )
    
    # Apply same filters as snapshot endpoint
    if location_id:
        base_query = base_query.filter(StockLedger.location_id == location_id)
    
    if item_sku:
        base_query = base_query.filter(InventoryItem.sku.ilike(f"%{item_sku}%"))
    
    if item_name:
        base_query = base_query.filter(InventoryItem.name.ilike(f"%{item_name}%"))
    
    if status:
        base_query = base_query.filter(InventoryItem.status == status)
    
    if min_quantity is not None or max_quantity is not None:
        having_conditions = []
        if min_quantity is not None:
            having_conditions.append(func.sum(StockLedger.quantity) >= min_quantity)
        if max_quantity is not None:
            having_conditions.append(func.sum(StockLedger.quantity) <= max_quantity)
        base_query = base_query.having(and_(*having_conditions))
    
    # Execute query
    results = base_query.order_by(InventoryItem.sku, Location.code).all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    headers = [
        'Item SKU', 'Item Name', 'Status', 'Unit',
        'Location Code', 'Location Name', 'Current Quantity',
        'Last Transaction Date', 'Total Transactions'
    ]
    writer.writerow(headers)
    
    # Write data rows
    for result in results:
        row = [
            result.sku,
            result.name,
            result.status,
            result.unit,
            result.location_code,
            result.location_name,
            str(result.current_quantity or 0),
            result.last_transaction_date.strftime('%Y-%m-%d %H:%M:%S') if result.last_transaction_date else '',
            result.transaction_count or 0
        ]
        writer.writerow(row)
    
    # Get CSV content
    csv_content = output.getvalue()
    output.close()
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"inventory_snapshot_{timestamp}.csv"
    
    # Create streaming response
    def generate_csv():
        yield csv_content
    
    return StreamingResponse(
        io.BytesIO(csv_content.encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/movements/csv", summary="Export stock movements to CSV (ADMIN+)")
async def export_stock_movements_csv(
    item_id: Optional[int] = Query(None, description="Filter by item ID"),
    location_id: Optional[int] = Query(None, description="Filter by location ID"),
    transaction_type: Optional[str] = Query(None, description="Filter by transaction type"),
    from_date: Optional[date] = Query(None, description="From date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="To date (YYYY-MM-DD)"),
    reference_no: Optional[str] = Query(None, description="Filter by reference number"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_and_above())
) -> StreamingResponse:
    """
    Export stock movement history to CSV format.
    Requires ADMIN role or higher.
    
    WARNING: This endpoint can generate very large files. Use date range filters.
    """
    
    # Build comprehensive query with item and location details
    query = db.query(
        StockLedger.transaction_date,
        StockLedger.transaction_type,
        InventoryItem.sku.label('item_sku'),
        InventoryItem.name.label('item_name'),
        Location.code.label('location_code'),
        Location.name.label('location_name'),
        StockLedger.quantity,
        StockLedger.unit_cost,
        StockLedger.reference_no,
        StockLedger.notes
    ).join(
        InventoryItem, StockLedger.item_id == InventoryItem.id
    ).join(
        Location, StockLedger.location_id == Location.id
    ).order_by(desc(StockLedger.transaction_date))
    
    # Apply filters
    if item_id:
        query = query.filter(StockLedger.item_id == item_id)
    
    if location_id:
        query = query.filter(StockLedger.location_id == location_id)
    
    if transaction_type:
        query = query.filter(StockLedger.transaction_type == transaction_type)
    
    if reference_no:
        query = query.filter(StockLedger.reference_no.ilike(f"%{reference_no}%"))
    
    if from_date:
        query = query.filter(StockLedger.transaction_date >= from_date)
    
    if to_date:
        query = query.filter(StockLedger.transaction_date < (to_date + timedelta(days=1)))
    
    # Execute query (no limit for CSV export, but consider adding safety limits)
    # For production, you might want to add a reasonable limit (e.g., 50000 records)
    results = query.all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    headers = [
        'Transaction Date', 'Type', 'Item SKU', 'Item Name',
        'Location Code', 'Location Name', 'Quantity', 'Unit Cost',
        'Reference No', 'Notes'
    ]
    writer.writerow(headers)
    
    # Write data rows
    for result in results:
        row = [
            result.transaction_date.strftime('%Y-%m-%d %H:%M:%S') if result.transaction_date else '',
            result.transaction_type,
            result.item_sku,
            result.item_name,
            result.location_code,
            result.location_name,
            str(result.quantity),
            str(result.unit_cost) if result.unit_cost else '',
            result.reference_no or '',
            result.notes or ''
        ]
        writer.writerow(row)
    
    # Get CSV content
    csv_content = output.getvalue()
    output.close()
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"stock_movements_{timestamp}.csv"
    
    return StreamingResponse(
        io.BytesIO(csv_content.encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/summary", summary="Inventory summary statistics (VIEWER+)")
async def get_inventory_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_viewer_and_above())
) -> Dict[str, Any]:
    """
    Get high-level inventory summary statistics.
    Requires VIEWER role or higher.
    
    Provides key metrics for dashboard and reporting.
    """
    
    # Total active items
    total_items = db.query(InventoryItem).filter(
        InventoryItem.is_deleted == False,
        InventoryItem.status == 'ACTIVE'
    ).count()
    
    # Total locations
    total_locations = db.query(Location).filter(
        Location.is_deleted == False
    ).count()
    
    # Stock value calculation (if unit_cost is available)
    stock_value_query = db.query(
        func.sum(StockLedger.quantity * StockLedger.unit_cost)
    ).filter(
        StockLedger.unit_cost.isnot(None)
    ).scalar()
    
    # Items with low stock (you may want to make this configurable)
    low_stock_items = db.query(
        func.count().label('count')
    ).select_from(
        db.query(
            StockLedger.item_id,
            func.sum(StockLedger.quantity).label('total_quantity')
        ).group_by(StockLedger.item_id).subquery()
    ).filter(
        text('total_quantity <= 5')  # Configurable threshold
    ).scalar()
    
    # Recent transactions count (last 7 days)
    week_ago = datetime.now() - timedelta(days=7)
    recent_transactions = db.query(StockLedger).filter(
        StockLedger.transaction_date >= week_ago
    ).count()
    
    return {
        "total_items": total_items,
        "total_locations": total_locations,
        "estimated_stock_value": float(stock_value_query) if stock_value_query else 0.0,
        "low_stock_items_count": low_stock_items or 0,
        "recent_transactions_7days": recent_transactions,
        "generated_at": datetime.now().isoformat(),
        "generated_by": current_user.username
    }