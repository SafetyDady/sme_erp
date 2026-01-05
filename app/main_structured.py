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
from app.core.logging import setup_structured_logging, get_logger
from app.core.logging_middleware import StructuredLoggingMiddleware, SecurityLoggingMiddleware
import logging
import time

# Configure structured logging based on environment
setup_structured_logging(
    log_level=settings.LOG_LEVEL,
    log_format="json" if settings.ENVIRONMENT == "production" else "text"
)

logger = get_logger("main")

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

# Add logging and traceability middleware
logger.info("🔍 Setting up logging and traceability middleware...")
app.add_middleware(StructuredLoggingMiddleware)
app.add_middleware(SecurityLoggingMiddleware)
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

# Log startup completion
startup_end = time.time()
logger.info(f"✅ Application startup completed in {startup_end - startup_start:.3f}s")
logger.info("🎯 SME ERP API ready for requests")