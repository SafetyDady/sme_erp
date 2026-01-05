from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr
from app.models.users import UserRole


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None


class LoginRequest(BaseModel):
    username: str  # Can be username or email
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: "UserOut"


class UserOut(BaseModel):
    id: int
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: UserRole = UserRole.VIEWER