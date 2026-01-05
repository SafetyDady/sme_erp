from typing import List, Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.auth.jwt import decode_token, verify_token_type
from app.modules.users.models import User, UserRole
from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=settings.TOKEN_URL)

# Role Permission Constants (SME ERP Standard)
ROLE_VIEWER_AND_ABOVE = [UserRole.VIEWER, UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN]
ROLE_STAFF_AND_ABOVE = [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN]
ROLE_ADMIN_AND_ABOVE = [UserRole.ADMIN, UserRole.SUPER_ADMIN]
ROLE_SUPER_ADMIN_ONLY = [UserRole.SUPER_ADMIN]

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from access token."""
    # Verify it's an access token
    payload = verify_token_type(token, "access")
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user

def require_roles(allowed_roles: List[UserRole]) -> Callable:
    """Dependency factory to require specific roles."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required roles: {[role.value for role in allowed_roles]}"
            )
        return current_user
    return role_checker

# Convenient role dependency functions for common use cases
def require_viewer_and_above():
    """Require VIEWER role or higher (READ access)"""
    return require_roles(ROLE_VIEWER_AND_ABOVE)

def require_staff_and_above():
    """Require STAFF role or higher (WRITE access)"""
    return require_roles(ROLE_STAFF_AND_ABOVE)

def require_admin_and_above():
    """Require ADMIN role or higher (ADMIN access)"""
    return require_roles(ROLE_ADMIN_AND_ABOVE)

def require_super_admin():
    """Require SUPER_ADMIN role (SUPER access)"""
    return require_roles(ROLE_SUPER_ADMIN_ONLY)

# Legacy support
require_staff = require_staff_and_above
require_admin = require_admin_and_above

# Common role dependencies
require_admin = require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN])
require_staff = require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.STAFF])
require_super_admin = require_roles([UserRole.SUPER_ADMIN])