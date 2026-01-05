from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import select, or_

from app.core.db import get_db
from app.core.auth.password import verify_password
from app.core.auth.jwt import create_access_token
from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import LoginResponse, UserOut
from app.shared.schemas import SuccessResponse, ResponseMeta
from app.models.users import User

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=SuccessResponse[LoginResponse])
async def login(
    request: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login with username/email and password"""
    
    # Find user by username or email
    user = db.scalar(
        select(User).where(
            or_(
                User.username == request.username,
                User.email == request.username
            )
        )
    )
    
    # Verify user and password
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    # Create response
    login_response = LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserOut.model_validate(user)
    )
    
    return SuccessResponse(
        data=login_response,
        meta=ResponseMeta(
            correlation_id=getattr(request, "correlation_id", "login"),
            timestamp=datetime.utcnow().isoformat()
        )
    )


@router.get("/me", response_model=SuccessResponse[UserOut])
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user profile"""
    
    return SuccessResponse(
        data=UserOut.model_validate(current_user),
        meta=ResponseMeta(
            correlation_id=getattr(current_user, "correlation_id", "me"),
            timestamp=datetime.utcnow().isoformat()
        )
    )