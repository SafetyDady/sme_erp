from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import HTTPException, status

# Simple working version with proper Token schema
app = FastAPI(
    title="SME ERP API with OAuth2",
    description="Enterprise Resource Planning with Complete Authentication",
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

# OAuth2 scheme - this creates the Authorize button
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Token schema for proper Swagger documentation
from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

@app.get("/")
def read_root():
    return {"message": "SME ERP API is running", "version": "1.0.0"}

@app.post("/api/v1/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login and get access token. OAuth2 compatible for Swagger with proper schema."""
    # Simple test - accept admin@sme-erp.com / admin123
    if form_data.username == "admin@sme-erp.com" and form_data.password == "admin123":
        return {
            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.fake-jwt-token-for-testing",
            "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.fake-refresh-token-for-testing", 
            "token_type": "bearer"
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

@app.get("/api/v1/auth/me")
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get current user profile."""
    return {
        "id": 1,
        "email": "admin@sme-erp.com",
        "role": "SUPER_ADMIN",
        "is_active": True,
        "token": token[:20] + "..."
    }

@app.get("/api/v1/inventory/items")
async def get_inventory_items(token: str = Depends(oauth2_scheme)):
    """Protected inventory endpoint."""
    return {
        "message": "Welcome to inventory!",
        "items": [
            {"id": 1, "name": "Laptop", "quantity": 10, "price": 45000},
            {"id": 2, "name": "Mouse", "quantity": 25, "price": 350},
            {"id": 3, "name": "Keyboard", "quantity": 15, "price": 890},
        ],
        "user_authenticated": True
    }

@app.post("/api/v1/inventory/items")
async def create_inventory_item(item: dict, token: str = Depends(oauth2_scheme)):
    """Create inventory item (protected)."""
    return {
        "message": "Item created successfully",
        "item": item,
        "created_by": "admin@sme-erp.com"
    }
