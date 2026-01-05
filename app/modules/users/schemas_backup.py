from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.modules.users.models import UserRole

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: Optional[UserRole] = UserRole.VIEWER

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str    refresh_token: str

class RoleChangeRequest(BaseModel):
    """Request model for role assignment/change"""
    new_role: UserRole
    reason: Optional[str] = "Role change requested by admin"

class RoleChangeResponse(BaseModel):
    """Response model for role assignment/change"""
    user_id: int
    email: str
    old_role: UserRole
    new_role: UserRole
    changed_by: str
    timestamp: datetime
    audit_id: Optional[str] = None
    message: str
