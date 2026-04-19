"""
统一异常处理

所有 APIError 子类在 to_dict() 中使用新的响应格式:
{
    "code": <错误码>,
    "data": null,
    "message": "...",
    "trace_id": "..."
}
"""

import uuid
from typing import Optional

from fastapi import status


class APIError(Exception):
    """API 错误基类"""

    def __init__(
        self,
        message: str,
        code: int = 500,
        status_code: int = None,
        details: Optional[dict] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code or code
        self.details = details or {}
        self.trace_id = uuid.uuid4().hex[:16]
        super().__init__(message)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "data": None,
            "message": self.message,
            "trace_id": self.trace_id,
        }


class NotFoundError(APIError):
    def __init__(self, resource: str, identifier: str = ""):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        super().__init__(message, code=404, status_code=status.HTTP_404_NOT_FOUND)


class ValidationError(APIError):
    def __init__(self, message: str, field: str = None):
        super().__init__(
            message, code=400, status_code=status.HTTP_400_BAD_REQUEST,
            details={"field": field} if field else {},
        )


class BusinessError(APIError):
    def __init__(self, message: str, code: int = 400):
        super().__init__(message, code=code, status_code=code)


class ConflictError(APIError):
    def __init__(self, message: str, resource_type: str = None, resource_id: str = None):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        super().__init__(message, code=409, status_code=status.HTTP_409_CONFLICT, details=details)


class UnauthorizedError(APIError):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, code=401, status_code=status.HTTP_401_UNAUTHORIZED)


class ForbiddenError(APIError):
    def __init__(self, message: str = "Access forbidden"):
        super().__init__(message, code=403, status_code=status.HTTP_403_FORBIDDEN)


class ServiceUnavailableError(APIError):
    def __init__(self, message: str, service: str = None):
        details = {"service": service} if service else {}
        super().__init__(message, code=503, status_code=status.HTTP_503_SERVICE_UNAVAILABLE, details=details)


class RateLimitError(APIError):
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None):
        details = {"retry_after": retry_after} if retry_after else {}
        super().__init__(message, code=429, status_code=status.HTTP_429_TOO_MANY_REQUESTS, details=details)
