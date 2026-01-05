from datetime import datetime
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.shared.schemas import SuccessResponse, ResponseMeta

router = APIRouter(tags=["health"])


@router.get("/health")
def health(request: Request):
    """Simple health check - backward compatible"""
    return {"status": "ok"}


@router.get("/health/detailed", response_model=SuccessResponse[dict])
def detailed_health(request: Request, db: Session = Depends(get_db)):
    """Detailed health check with standard response format"""
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    
    # Test database connectivity
    try:
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    health_data = {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": db_status,
            "api": "healthy"
        }
    }
    
    return SuccessResponse(
        data=health_data,
        meta=ResponseMeta(
            correlation_id=correlation_id,
            timestamp=datetime.utcnow().isoformat()
        )
    )