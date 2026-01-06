import os
from typing import Optional, List
from dotenv import load_dotenv

# Load environment-specific .env file FIRST
env = os.getenv("ENVIRONMENT", "dev")
env_file = f".env.{env}"
if os.path.exists(env_file):
    load_dotenv(env_file, override=True)
else:
    load_dotenv(override=True)  # Fallback to .env

class Settings:
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "dev")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # JWT Settings
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "14"))
    
    # Database Settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./sme_erp.db")
    
    # Read-Replica Configuration (Phase 9 Task 2)
    READ_REPLICA_ENABLED: bool = os.getenv("READ_REPLICA_ENABLED", "false").lower() == "true"
    READ_REPLICA_DATABASE_URL: Optional[str] = os.getenv("READ_REPLICA_DATABASE_URL", None)
    READ_REPLICA_FALLBACK: bool = os.getenv("READ_REPLICA_FALLBACK", "true").lower() == "true"
    
    # Read-Replica Configuration (Phase 9 Task 2)
    READ_REPLICA_ENABLED: bool = os.getenv("READ_REPLICA_ENABLED", "false").lower() == "true"
    READ_REPLICA_DATABASE_URL: Optional[str] = os.getenv("READ_REPLICA_DATABASE_URL", None)
    READ_REPLICA_FALLBACK: bool = os.getenv("READ_REPLICA_FALLBACK", "true").lower() == "true"
    
    # CORS settings
    BACKEND_CORS_ORIGINS: List[str] = os.getenv("BACKEND_CORS_ORIGINS", '["*"]')
    if isinstance(BACKEND_CORS_ORIGINS, str):
        import json
        try:
            BACKEND_CORS_ORIGINS = json.loads(BACKEND_CORS_ORIGINS)
        except:
            BACKEND_CORS_ORIGINS = ["*"]
    
    # OAuth2
    TOKEN_URL: str = os.getenv("TOKEN_URL", "/api/v1/auth/login")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "detailed")
    
    # Features
    AUDIT_ENABLED: bool = os.getenv("AUDIT_ENABLED", "true").lower() == "true"
    REQUEST_ID_HEADER: str = os.getenv("REQUEST_ID_HEADER", "X-Request-Id")
    
    # Health checks
    HEALTH_CHECK_TIMEOUT: int = int(os.getenv("HEALTH_CHECK_TIMEOUT", "10"))
    READINESS_CHECK_DEPS: List[str] = os.getenv("READINESS_CHECK_DEPS", "database").split(",")
    
    # Performance
    UVICORN_WORKERS: int = int(os.getenv("UVICORN_WORKERS", "1"))
    CONNECTION_POOL_SIZE: int = int(os.getenv("CONNECTION_POOL_SIZE", "10"))
    
    # Development
    AUTO_RELOAD: bool = os.getenv("AUTO_RELOAD", "false").lower() == "true"
    CREATE_TEST_DATA: bool = os.getenv("CREATE_TEST_DATA", "false").lower() == "true"

settings = Settings()

# Validation for production
if settings.ENVIRONMENT == "prod":
    assert settings.JWT_SECRET_KEY != "your_super_secret_jwt_key_change_this_in_production", \
        "JWT_SECRET_KEY must be changed in production"
    assert not settings.DEBUG, "DEBUG must be false in production"
    assert "*" not in settings.BACKEND_CORS_ORIGINS, "CORS must be restrictive in production"