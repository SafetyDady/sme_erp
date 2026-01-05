from typing import Generic, TypeVar, Any, Optional
from pydantic import BaseModel


T = TypeVar('T')


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class ResponseMeta(BaseModel):
    correlation_id: str
    timestamp: Optional[str] = None


class StandardResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[ErrorDetail] = None
    meta: ResponseMeta


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    meta: ResponseMeta


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
    meta: ResponseMeta