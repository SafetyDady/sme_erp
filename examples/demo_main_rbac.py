from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Dict, Any
import enum

# FastAPI app configuration
app = FastAPI(
    title="SME ERP API with RBAC",
    description="Enterprise Resource Planning with Role-Based Access Control",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# User roles
class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin" 
    STAFF = "staff"
    VIEWER = "viewer"

# Mock users database with different roles
MOCK_USERS = {
    "admin@sme-erp.com": {
        "id": 1,
        "email": "admin@sme-erp.com", 
        "password": "admin123",
        "role": UserRole.SUPER_ADMIN,
        "is_active": True
    },
    "staff@sme-erp.com": {
        "id": 2,
        "email": "staff@sme-erp.com",
        "password": "staff123", 
        "role": UserRole.STAFF,
        "is_active": True
    },
    "viewer@sme-erp.com": {
        "id": 3,
        "email": "viewer@sme-erp.com",
        "password": "viewer123",
        "role": UserRole.VIEWER, 
        "is_active": True
    }
}

# Pydantic schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class User(BaseModel):
    id: int
    email: str
    role: UserRole
    is_active: bool

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

# Role permission constants
ROLE_VIEWER_AND_ABOVE = [UserRole.VIEWER, UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN]
ROLE_STAFF_AND_ABOVE = [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN]
ROLE_ADMIN_AND_ABOVE = [UserRole.ADMIN, UserRole.SUPER_ADMIN]

# Auth functions
def authenticate_user(username: str, password: str):
    user_data = MOCK_USERS.get(username)
    if not user_data or user_data["password"] != password:
        return None
    return user_data

def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get current user from token"""
    # In real app, decode JWT token
    # For demo, extract user from token
    if "admin" in token:
        return MOCK_USERS["admin@sme-erp.com"]
    elif "staff" in token:
        return MOCK_USERS["staff@sme-erp.com"] 
    elif "viewer" in token:
        return MOCK_USERS["viewer@sme-erp.com"]
    else:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_roles(allowed_roles):
    def role_checker(current_user: Dict = Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {[role.value for role in allowed_roles]}"
            )
        return current_user
    return role_checker

# Sample data
SAMPLE_ITEMS = [
    {"id": 1, "name": "Laptop", "quantity": 10, "price": 45000, "location_id": 1},
    {"id": 2, "name": "Mouse", "quantity": 25, "price": 350, "location_id": 1}, 
    {"id": 3, "name": "Keyboard", "quantity": 15, "price": 890, "location_id": 2},
]

SAMPLE_STOCK = [
    {"item_id": 1, "location_id": 1, "quantity": 10, "reserved": 2},
    {"item_id": 2, "location_id": 1, "quantity": 25, "reserved": 5},
    {"item_id": 3, "location_id": 2, "quantity": 15, "reserved": 0},
]

# Auth endpoints
@app.get("/")
def read_root():
    return {"message": "SME ERP API with RBAC is running", "version": "1.0.0"}

@app.post("/api/v1/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login and get access token. OAuth2 compatible for Swagger with RBAC."""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create token with role info
    token_suffix = user["role"].value.replace("_", "")
    return {
        "access_token": f"mock-jwt-token-{token_suffix}-{user['id']}",
        "refresh_token": f"mock-refresh-token-{token_suffix}-{user['id']}", 
        "token_type": "bearer"
    }

@app.get("/api/v1/auth/me")
async def get_current_user_profile(current_user: Dict = Depends(get_current_user)):
    """Get current user profile."""
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "role": current_user["role"].value,
        "is_active": current_user["is_active"]
    }

# Inventory endpoints with RBAC

# VIEWER level endpoints (read-only)
@app.get("/api/v1/inventory/items")
async def get_inventory_items(
    current_user: Dict = Depends(require_roles(ROLE_VIEWER_AND_ABOVE))
):
    """Get all inventory items. Requires VIEWER role or higher."""
    return {
        "message": f"Inventory accessed by {current_user['email']} ({current_user['role'].value})",
        "items": SAMPLE_ITEMS,
        "user_role": current_user["role"].value,
        "permissions": "READ_INVENTORY"
    }

@app.get("/api/v1/inventory/stock") 
async def get_stock_levels(
    current_user: Dict = Depends(require_roles(ROLE_VIEWER_AND_ABOVE))
):
    """Get current stock levels. Requires VIEWER role or higher."""
    return {
        "message": "Stock levels accessed",
        "stock": SAMPLE_STOCK,
        "accessed_by": current_user["email"],
        "permissions": "READ_STOCK"
    }

# STAFF level endpoints (can create items and transactions)
@app.post("/api/v1/inventory/items")
async def create_inventory_item(
    item: InventoryItem,
    current_user: Dict = Depends(require_roles(ROLE_STAFF_AND_ABOVE))
):
    """Create new inventory item. Requires STAFF role or higher."""
    return {
        "message": "Item created successfully",
        "item": item.dict(),
        "created_by": current_user["email"],
        "permissions": "CREATE_ITEM"
    }

@app.post("/api/v1/inventory/tx")
async def create_inventory_transaction(
    transaction: Transaction,
    current_user: Dict = Depends(require_roles(ROLE_STAFF_AND_ABOVE))
):
    """Create inventory transaction (stock in/out). Requires STAFF role or higher."""
    return {
        "message": f"Transaction ({transaction.type}) created successfully",
        "transaction": transaction.dict(),
        "created_by": current_user["email"],
        "permissions": "CREATE_TRANSACTION"
    }

# ADMIN level endpoints (advanced management)
@app.post("/api/v1/inventory/locations")
async def create_location(
    location: Location,
    current_user: Dict = Depends(require_roles(ROLE_ADMIN_AND_ABOVE))
):
    """Create warehouse location. Requires ADMIN role or higher."""
    return {
        "message": "Location created successfully", 
        "location": location.dict(),
        "created_by": current_user["email"],
        "permissions": "CREATE_LOCATION"
    }

@app.put("/api/v1/inventory/items/{item_id}")
async def update_inventory_item(
    item_id: int,
    item: InventoryItem, 
    current_user: Dict = Depends(require_roles(ROLE_ADMIN_AND_ABOVE))
):
    """Update inventory item. Requires ADMIN role or higher."""
    return {
        "message": f"Item {item_id} updated successfully",
        "item": item.dict(),
        "updated_by": current_user["email"],
        "permissions": "UPDATE_ITEM"
    }

@app.delete("/api/v1/inventory/items/{item_id}")
async def delete_inventory_item(
    item_id: int,
    current_user: Dict = Depends(require_roles(ROLE_ADMIN_AND_ABOVE))
):
    """Delete inventory item. Requires ADMIN role or higher."""
    return {
        "message": f"Item {item_id} deleted successfully",
        "deleted_by": current_user["email"],
        "permissions": "DELETE_ITEM"
    }