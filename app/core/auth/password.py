from passlib.context import CryptContext

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a plain password."""
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(password, hashed)

def get_password_hash(password: str) -> str:
    """Alias for hash_password for compatibility."""
    return hash_password(password)