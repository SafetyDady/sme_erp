import enum
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"  # Full system access
    ADMIN = "ADMIN"              # Administrative access  
    STAFF = "STAFF"              # Standard user access
    VIEWER = "VIEWER"            # Read-only access


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.VIEWER, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)