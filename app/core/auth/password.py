from passlib.context import CryptContext
from app.core.config import settings
import hashlib

# Password hashing configuration - ไม่ใช้ bcrypt เนื่องจาก version compatibility issue  
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a plain password."""
    if settings.ENVIRONMENT == "staging":
        # Simple hash for staging
        return hashlib.sha256(password.encode()).hexdigest()
    else:
        # Use passlib for production (safer fallback)
        return pwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    """Verify a plain password against a hashed password."""
    if settings.ENVIRONMENT == "staging":
        # Simple verification for staging
        simple_hash = hashlib.sha256(password.encode()).hexdigest()
        return simple_hash == hashed
    else:
        # Use passlib for production (safer fallback)
        return pwd_context.verify(password, hashed)

def get_password_hash(password: str) -> str:
    """Alias for hash_password for compatibility."""
    return hash_password(password)