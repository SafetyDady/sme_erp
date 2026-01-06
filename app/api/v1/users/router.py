"""
User & Role Management API
Provides admin functionality for managing users and roles
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.auth.deps import require_admin_and_above, require_super_admin, get_current_user
from app.db.session import get_db
from app.modules.users.models import User, UserRole
from app.modules.users.schemas import UserCreate, UserOut, UserUpdate, RoleChangeRequest, RoleChangeResponse
from app.core.auth.password import get_password_hash

router = APIRouter()

@router.get("/users", response_model=List[UserOut])
def list_users(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    role_filter: Optional[UserRole] = Query(None),
    active_filter: Optional[bool] = Query(None),
    current_user: User = Depends(require_admin_and_above())
):
    """
    List users with optional filtering (ADMIN+ required)
    - Filter by role and/or active status
    - Pagination support
    """
    query = db.query(User)
    
    if role_filter:
        query = query.filter(User.role == role_filter)
    if active_filter is not None:
        query = query.filter(User.is_active == active_filter)
    
    users = query.offset(skip).limit(limit).all()
    return users

@router.get("/users/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_and_above)
):
    """
    Get user by ID (ADMIN+ required)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_and_above())
):
    """
    Create new user (ADMIN+ required)
    - Only SUPER_ADMIN can create ADMIN or SUPER_ADMIN users
    - Email must be unique
    - Auto-activate user
    """
    # Validate email format and check uniqueness
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{user_data.email}' already registered"
        )
    
    # Role creation restrictions - only SUPER_ADMIN can create privileged users
    if user_data.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        if current_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only SUPER_ADMIN can create ADMIN+ users"
            )
    
    # Password strength validation (basic check)
    if len(user_data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    try:
        # Create user with hashed password
        hashed_password = get_password_hash(user_data.password)
        db_user = User(
            email=user_data.email,
            hashed_password=hashed_password,
            role=user_data.role,
            is_active=True
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return db_user
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )

@router.put("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_and_above())
):
    """
    Update user (ADMIN+ required)
    - Only SUPER_ADMIN can modify ADMIN+ users or assign ADMIN+ roles
    - Email uniqueness enforced
    - Prevent privilege escalation
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Permission checks - only SUPER_ADMIN can modify ADMIN+ users
    if user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        if current_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only SUPER_ADMIN can modify ADMIN+ users"
            )
    
    # Email uniqueness check (if email is being updated)
    if user_data.email and user_data.email != user.email:
        existing_user = db.query(User).filter(
            User.email == user_data.email,
            User.id != user_id
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email '{user_data.email}' already in use by another user"
            )
    
    # Role assignment restrictions - prevent privilege escalation
    if user_data.role and user_data.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        if current_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only SUPER_ADMIN can assign ADMIN+ roles"
            )
    
    try:
        # Update only provided fields
        update_data = user_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        db.commit()
        db.refresh(user)
        
        return user
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def disable_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_and_above())
):
    """
    Disable user (soft delete) (ADMIN+ required)
    - Only SUPER_ADMIN can disable ADMIN+ users
    - Cannot disable yourself (safety protection)
    - Soft delete only (is_active = False)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Self-protection: cannot disable your own account
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disable your own account (safety protection)"
        )
    
    # Check if user is already disabled
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already disabled"
        )
    
    # Permission checks - only SUPER_ADMIN can disable ADMIN+ users
    if user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        if current_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only SUPER_ADMIN can disable ADMIN+ users"
            )
    
    try:
        # Soft delete: set is_active to False
        user.is_active = False
        db.commit()
        
        # Return 204 No Content for successful deletion
        return None
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable user"
        )

@router.post("/users/{user_id}/reset-password", response_model=dict)
def reset_user_password(
    user_id: int,
    new_password: str = Query(..., min_length=8, max_length=128),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """
    Reset user password (SUPER_ADMIN only)
    - Security-sensitive operation requires highest privileges
    - Password strength validation
    - Cannot reset your own password via this endpoint
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Security check: cannot reset own password via admin endpoint
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reset your own password via admin endpoint. Use profile settings."
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reset password for disabled user"
        )
    
    # Password strength validation
    if len(new_password.strip()) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    try:
        # Hash and update password
        user.hashed_password = get_password_hash(new_password)
        db.commit()
        
        return {
            "message": f"Password reset successfully for user '{user.email}'",
            "user_id": user.id
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )

@router.get("/roles", response_model=List[dict])
def list_roles(
    current_user: User = Depends(require_admin_and_above)
):
    """
    List available roles with descriptions (ADMIN+ required)
    """
    return [
        {
            "role": UserRole.VIEWER,
            "description": "Read-only access to inventory data",
            "permissions": ["inventory:read"]
        },
        {
            "role": UserRole.STAFF,
            "description": "Inventory management and updates",
            "permissions": ["inventory:read", "inventory:write"]
        },
        {
            "role": UserRole.ADMIN,
            "description": "Full inventory control and user management",
            "permissions": ["inventory:*", "users:read", "users:write"]
        },
        {
            "role": UserRole.SUPER_ADMIN,
            "description": "System administration and security",
            "permissions": ["*"]
        }
    ]

@router.get("/current-user", response_model=UserOut)
def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user information
    """
    return current_user

@router.post("/users/{user_id}/roles", response_model=RoleChangeResponse)
def assign_user_role(
    user_id: int,
    role_change: RoleChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_and_above)
):
    """
    Assign/change user role (ADMIN+ required)
    - ADMIN can only change VIEWER ↔ STAFF  
    - SUPER_ADMIN can change any role
    - Cannot change own role (safety protection)
    - Audit logged with before/after values
    """
    from datetime import datetime
    import uuid
    
    # Find target user
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Self-protection: cannot change own role
    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role (safety protection)"
        )
    
    # Check if user is active
    if not target_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change role of disabled user"
        )
    
    # Store old role for audit
    old_role = target_user.role
    new_role = role_change.new_role
    
    # No-op check
    if old_role == new_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User already has role '{new_role.value}'"
        )
    
    # RBAC validation based on current user's role
    if current_user.role == UserRole.ADMIN:
        # ADMIN can only change between VIEWER and STAFF
        allowed_roles = [UserRole.VIEWER, UserRole.STAFF]
        
        if new_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ADMIN can only assign VIEWER or STAFF roles"
            )
        
        # ADMIN cannot modify ADMIN+ users
        if old_role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ADMIN cannot modify ADMIN+ users"
            )
            
    elif current_user.role == UserRole.SUPER_ADMIN:
        # SUPER_ADMIN can change any role
        pass
    else:
        # This shouldn't happen due to require_admin_and_above, but safety check
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for role assignment"
        )
    
    try:
        # Generate audit ID for traceability
        audit_id = str(uuid.uuid4())[:8]
        timestamp = datetime.utcnow()
        
        # Update role
        target_user.role = new_role
        db.commit()
        db.refresh(target_user)
        
        # Create audit log entry (simple in-memory for this demo)
        # In production, this would go to audit_logs table
        audit_entry = {
            "audit_id": audit_id,
            "timestamp": timestamp.isoformat(),
            "action": "role_change",
            "changed_by": current_user.email,
            "target_user_id": target_user.id,
            "target_user_email": target_user.email,
            "old_role": old_role.value,
            "new_role": new_role.value,
            "reason": role_change.reason
        }
        
        # Log to application logs for audit trail
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"ROLE_CHANGE: {audit_entry}")
        
        return RoleChangeResponse(
            user_id=target_user.id,
            email=target_user.email,
            old_role=old_role,
            new_role=new_role,
            changed_by=current_user.email,
            timestamp=timestamp,
            audit_id=audit_id,
            message=f"Role changed from {old_role.value} to {new_role.value}"
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change user role"
        )