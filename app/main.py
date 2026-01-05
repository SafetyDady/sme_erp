from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from app.api.v1.router import api_router as api_v1_router
from app.api.health import router as health_router
from app.db.session import engine
from app.db.base import Base
from app.core.config import settings
from app.core.auth.deps import oauth2_scheme
from app.core.middleware import RequestIdMiddleware
import logging
import time

# Configure logging based on environment
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s' if settings.LOG_FORMAT == 'detailed' 
           else '%(levelname)s:%(name)s:%(message)s'
)

logger = logging.getLogger(__name__)

# Startup time tracking
startup_start = time.time()

logger.info(f"🚀 Starting SME ERP API - Environment: {settings.ENVIRONMENT}")

# Create tables
logger.info("📊 Creating database tables...")
Base.metadata.create_all(bind=engine)
logger.info("✅ Database tables ready")

app = FastAPI(
    title="SME ERP API",
    description="Enterprise Resource Planning for Small and Medium Enterprises",
    version="1.0.0",
    debug=settings.DEBUG
)

# Add Request ID middleware for audit traceability
logger.info("🔍 Setting up request traceability middleware...")
app.add_middleware(RequestIdMiddleware)

# Configure CORS
logger.info(f"🌐 Configuring CORS for environment: {settings.ENVIRONMENT}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include health routes (no prefix for standard health endpoints)
app.include_router(health_router)

# Include API v1 router
app.include_router(api_v1_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "SME ERP API is running", "version": "1.0.0"}

@app.get("/protected-test")
def protected_test(token: str = Depends(oauth2_scheme)):
    """Test endpoint to register OAuth2 scheme with FastAPI."""
    return {"message": "This endpoint helps register OAuth2 security scheme", "token_received": bool(token)}