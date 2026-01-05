"""
DEVELOPMENT-ONLY MOCK ROUTER
============================

⚠️ WARNING: This router contains SAMPLE/MOCK data and should NEVER be used in production.
This file was moved from app/api/v1/inventory/router.py for security reasons.

For production inventory endpoints, use: app/api/v1/inventory/routes.py

This mock router is kept for:
- Development demonstrations  
- API structure examples
- Testing RBAC enforcement with static data
"""

from fastapi import APIRouter, Depends
from typing import List, Dict, Any
from pydantic import BaseModel
from app.modules.users.models import User
from app.core.auth.deps import (
    get_current_user, 
    require_viewer_and_above,
    require_staff_and_above,
    require_admin_and_above
)

router = APIRouter(prefix="/inventory", tags=["Inventory"])

# Sample inventory data
SAMPLE_ITEMS = [
    {"id": 1, "name": "Laptop", "quantity": 10, "price": 45000, "location_id": 1},
    {"id": 2, "name": "Mouse", "quantity": 25, "price": 350, "location_id": 1},
    {"id": 3, "name": "Keyboard", "quantity": 15, "price": 890, "location_id": 2},
]

SAMPLE_LOCATIONS = [
    {"id": 1, "name": "Warehouse A", "address": "Bangkok"},
    {"id": 2, "name": "Warehouse B", "address": "Chiang Mai"},
]

SAMPLE_STOCK = [
    {"item_id": 1, "location_id": 1, "quantity": 10, "reserved": 2},
    {"item_id": 2, "location_id": 1, "quantity": 25, "reserved": 5},
    {"item_id": 3, "location_id": 2, "quantity": 15, "reserved": 0},
]

# Pydantic models for request/response
class InventoryItem(BaseModel):
    name: str
    quantity: int
    price: float
    location_id: int = 1

class Location(BaseModel):
    name: str
    address: str

class Transaction(BaseModel):
    item_id: int
    quantity: int
    type: str  # "in" or "out"
    notes: str = ""

# VIEWER level endpoints - read only access
@router.get("/items", summary="Get inventory items (VIEWER+)")
async def get_inventory_items(
    current_user: User = Depends(require_viewer_and_above())
):
    """Get all inventory items. Requires VIEWER role or higher."""
    return {
        "message": f"Inventory accessed by {current_user.email} ({current_user.role.value})",
        "items": SAMPLE_ITEMS,
        "user_role": current_user.role.value,
        "permissions": "READ_INVENTORY"
    }

@router.get("/stock", summary="Get stock levels (VIEWER+)")
async def get_stock_levels(
    current_user: User = Depends(require_viewer_and_above())
):
    """Get current stock levels. Requires VIEWER role or higher."""
    return {
        "message": "Stock levels accessed",
        "stock": SAMPLE_STOCK,
        "accessed_by": current_user.email,
        "permissions": "READ_STOCK"
    }

# STAFF level endpoints - can create items and transactions  
@router.post("/items", summary="Create inventory item (STAFF+)")
async def create_inventory_item(
    item: InventoryItem,
    current_user: User = Depends(require_staff_and_above())
):
    """Create new inventory item. Requires STAFF role or higher."""
    return {
        "message": "Item created successfully",
        "item": item.dict(),
        "created_by": current_user.email,
        "permissions": "CREATE_ITEM"
    }

@router.post("/tx", summary="Create inventory transaction (STAFF+)")
async def create_inventory_transaction(
    transaction: Transaction,
    current_user: User = Depends(require_staff_and_above())
):
    """Create inventory transaction (stock in/out). Requires STAFF role or higher."""
    return {
        "message": f"Transaction ({transaction.type}) created successfully",
        "transaction": transaction.dict(),
        "created_by": current_user.email,
        "permissions": "CREATE_TRANSACTION"
    }

# ADMIN level endpoints - advanced management functions
@router.post("/locations", summary="Create warehouse location (ADMIN+)")
async def create_location(
    location: Location,
    current_user: User = Depends(require_admin_and_above())
):
    """Create warehouse location. Requires ADMIN role or higher."""
    return {
        "message": "Location created successfully",
        "location": location.dict(),
        "created_by": current_user.email,
        "permissions": "CREATE_LOCATION"
    }

@router.put("/items/{item_id}", summary="Update inventory item (ADMIN+)")
async def update_inventory_item(
    item_id: int,
    item: InventoryItem,
    current_user: User = Depends(require_admin_and_above())
):
    """Update inventory item. Requires ADMIN role or higher."""
    return {
        "message": f"Item {item_id} updated successfully",
        "item": item.dict(),
        "updated_by": current_user.email,
        "permissions": "UPDATE_ITEM"
    }

@router.delete("/items/{item_id}", summary="Delete inventory item (ADMIN+)")
async def delete_inventory_item(
    item_id: int,
    current_user: User = Depends(require_admin_and_above())
):
    """Delete inventory item. Requires ADMIN role or higher."""
    return {
        "message": f"Item {item_id} deleted successfully",
        "deleted_by": current_user.email,
        "permissions": "DELETE_ITEM"
    }

@router.get("/protected")
async def protected_endpoint(
    current_user: User = Depends(get_current_user)
):
    """A protected endpoint that requires authentication."""
    return {
        "message": "This is a protected endpoint!",
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "role": current_user.role.value
        }
    }