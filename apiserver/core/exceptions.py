"""
统一异常处理

提供标准化的异常类和错误处理机制，确保所有错误返回一致的响应格式。
"""

from typing import Optional, Any
from fastapi import status


class APIError(Exception):
    """
    自定义 API 错误基类

    所有自定义异常的基类，提供统一的错误处理接口。

    Attributes:
        message: 错误消息
        code: 错误码（字符串标识）
        status_code: HTTP 状态码
        details: 额外的错误详情

    Examples:
        >>> raise APIError("Operation failed", "OPERATION_FAILED", 500)
    """

    def __init__(
        self,
        message: str,
        code: str = "API_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[dict] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict:
        """转换为响应字典"""
        return {
            "success": False,
            "data": None,
            "error": self.code,
            "message": self.message
        }


class NotFoundError(APIError):
    """
    资源未找到错误

    当请求的资源不存在时抛出。

    Args:
        resource: 资源类型名称（如 "Portfolio", "Backtest task"）
        identifier: 资源标识符（可选）

    Examples:
        >>> raise NotFoundError("Portfolio", "abc-123")
        >>> raise NotFoundError("Backtest task")
    """

    def __init__(self, resource: str, identifier: str = ""):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        super().__init__(message, "NOT_FOUND", status.HTTP_404_NOT_FOUND)


class ValidationError(APIError):
    """
    验证错误

    当请求参数验证失败时抛出。

    Args:
        message: 验证失败消息
        field: 失败的字段名（可选）

    Examples:
        >>> raise ValidationError("Invalid date format", "start_date")
        >>> raise ValidationError("Portfolio UUID is required")
    """

    def __init__(self, message: str, field: str = None):
        super().__init__(
            message,
            "VALIDATION_ERROR",
            status.HTTP_400_BAD_REQUEST,
            details={"field": field} if field else {}
        )


class BusinessError(APIError):
    """
    业务逻辑错误

    当业务规则验证失败时抛出。

    Args:
        message: 业务错误消息
        code: 自定义错误码（默认为 "BUSINESS_ERROR"）

    Examples:
        >>> raise BusinessError("Cannot delete running backtest")
        >>> raise BusinessError("Insufficient funds", "INSUFFICIENT_FUNDS")
    """

    def __init__(self, message: str, code: str = "BUSINESS_ERROR"):
        super().__init__(message, code, status.HTTP_400_BAD_REQUEST)


class ConflictError(APIError):
    """
    资源冲突错误

    当操作与现有资源冲突时抛出。

    Args:
        message: 冲突消息
        resource_type: 资源类型（可选）
        resource_id: 资源ID（可选）

    Examples:
        >>> raise ConflictError("Portfolio name already exists", "Portfolio", "MyPortfolio")
    """

    def __init__(self, message: str, resource_type: str = None, resource_id: str = None):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id

        super().__init__(
            message,
            "CONFLICT",
            status.HTTP_409_CONFLICT,
            details=details
        )


class UnauthorizedError(APIError):
    """
    未授权错误

    当用户未认证或认证失败时抛出。

    Args:
        message: 未授权消息

    Examples:
        >>> raise UnauthorizedError("Invalid or missing authentication token")
    """

    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, "UNAUTHORIZED", status.HTTP_401_UNAUTHORIZED)


class ForbiddenError(APIError):
    """
    禁止访问错误

    当用户已认证但无权限执行操作时抛出。

    Args:
        message: 禁止访问消息

    Examples:
        >>> raise ForbiddenError("You don't have permission to delete this portfolio")
    """

    def __init__(self, message: str = "Access forbidden"):
        super().__init__(message, "FORBIDDEN", status.HTTP_403_FORBIDDEN)


class ServiceUnavailableError(APIError):
    """
    服务不可用错误

    当依赖服务不可用时抛出。

    Args:
        message: 不可用消息
        service: 服务名称（可选）

    Examples:
        >>> raise ServiceUnavailableError("Database connection failed", "MySQL")
    """

    def __init__(self, message: str, service: str = None):
        details = {"service": service} if service else {}
        super().__init__(
            message,
            "SERVICE_UNAVAILABLE",
            status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details
        )


class RateLimitError(APIError):
    """
    速率限制错误

    当请求超过速率限制时抛出。

    Args:
        message: 限制消息
        retry_after: 重试等待秒数（可选）

    Examples:
        >>> raise RateLimitError("Too many requests", retry_after=60)
    """

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None):
        details = {"retry_after": retry_after} if retry_after else {}
        super().__init__(
            message,
            "RATE_LIMIT_EXCEEDED",
            status.HTTP_429_TOO_MANY_REQUESTS,
            details=details
        )


# 错误码常量
class ErrorCodes:
    """错误码常量枚举"""
    # 通用错误 (4xx)
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # 业务错误 (4xx)
    BUSINESS_ERROR = "BUSINESS_ERROR"
    INVALID_STATE = "INVALID_STATE"
    OPERATION_FAILED = "OPERATION_FAILED"

    # 服务错误 (5xx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    KAFKA_ERROR = "KAFKA_ERROR"
    REDIS_ERROR = "REDIS_ERROR"
