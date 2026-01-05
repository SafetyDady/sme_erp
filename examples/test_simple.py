from fastapi import FastAPI, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="SME ERP API with OAuth2",
    description="Simple test to show Authorize button",
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

# OAuth2 scheme - this will create the Authorize button
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

@app.get("/")
def read_root():
    return {"message": "SME ERP API is running"}

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login endpoint for OAuth2 - this creates the Authorize button."""
    # Simple test - accept admin@sme-erp.com / admin123
    if form_data.username == "admin@sme-erp.com" and form_data.password == "admin123":
        return {
            "access_token": "fake-access-token-for-testing",
            "token_type": "bearer"
        }
    else:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

@app.get("/protected")
async def protected_endpoint(token: str = Depends(oauth2_scheme)):
    """A protected endpoint that requires authentication."""
    return {
        "message": "This is protected!",
        "token": token
    }

@app.get("/inventory/items")
async def get_inventory_items(token: str = Depends(oauth2_scheme)):
    """Protected inventory endpoint."""
    return {
        "message": "Welcome to inventory!",
        "items": [
            {"id": 1, "name": "Laptop", "quantity": 10},
            {"id": 2, "name": "Mouse", "quantity": 25},
        ]
    }
