"""
统一 API 响应格式

提供标准化的 API 响应模型，确保所有端点返回一致的响应结构。
"""

from typing import Optional, Any, Generic, TypeVar, List
from pydantic import BaseModel, Field

T = TypeVar('T')


class APIResponse(BaseModel, Generic[T]):
    """
    统一 API 响应格式

    标准化所有 API 端点的响应结构，包含成功标志、数据、错误信息和提示消息。

    Attributes:
        success: 请求是否成功
        data: 响应数据（泛型类型）
        error: 错误码/错误信息
        message: 提示信息

    Examples:
        >>> response = APIResponse[str](success=True, data="hello", message="Success")
        >>> response = APIResponse[int](success=False, error="NOT_FOUND", message="Resource not found")
    """
    success: bool = Field(..., description="请求是否成功")
    data: Optional[T] = Field(None, description="响应数据")
    error: Optional[str] = Field(None, description="错误码/错误信息")
    message: Optional[str] = Field(None, description="提示信息")

    class Config:
        """Pydantic 配置"""
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {"id": 1, "name": "Example"},
                "error": None,
                "message": "Operation completed successfully"
            }
        }


class PaginatedData(BaseModel, Generic[T]):
    """
    分页数据容器

    封装分页查询的结果数据。

    Attributes:
        items: 数据项列表
        total: 总记录数
        page: 当前页码
        page_size: 每页大小
        total_pages: 总页数
    """
    items: List[T] = Field(default_factory=list, description="数据项列表")
    total: int = Field(0, description="总记录数")
    page: int = Field(1, description="当前页码", ge=1)
    page_size: int = Field(20, description="每页大小", ge=1, le=100)
    total_pages: int = Field(0, description="总页数", ge=0)

    def __init__(self, **data):
        super().__init__(**data)
        # 自动计算总页数
        if self.page_size > 0:
            self.total_pages = (self.total + self.page_size - 1) // self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """
    分页响应格式

    用于返回分页数据的标准化响应。

    Attributes:
        success: 请求是否成功
        data: 分页数据容器
        message: 提示信息

    Examples:
        >>> response = PaginatedResponse[int](
        ...     success=True,
        ...     data=PaginatedData(items=[1,2,3], total=50, page=1, page_size=10),
        ...     message="Data retrieved successfully"
        ... )
    """
    success: bool = Field(True, description="请求是否成功")
    data: PaginatedData[T] = Field(..., description="分页数据")
    message: Optional[str] = Field(None, description="提示信息")

    class Config:
        """Pydantic 配置"""
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "items": [{"id": 1, "name": "Item 1"}],
                    "total": 100,
                    "page": 1,
                    "page_size": 20,
                    "total_pages": 5
                },
                "message": "Data retrieved successfully"
            }
        }


def success_response(data: Any = None, message: str = None) -> dict:
    """
    创建成功响应的便捷函数

    Args:
        data: 响应数据
        message: 提示信息

    Returns:
        dict: 符合 APIResponse 格式的字典

    Examples:
        >>> return success_response(data={"user": "alice"}, message="User created")
    """
    return {
        "success": True,
        "data": data,
        "error": None,
        "message": message
    }


def error_response(error: str, message: str = None, data: Any = None) -> dict:
    """
    创建错误响应的便捷函数

    Args:
        error: 错误码/错误信息
        message: 提示信息
        data: 响应数据（可选，用于错误时返回部分数据）

    Returns:
        dict: 符合 APIResponse 格式的字典

    Examples:
        >>> return error_response(error="NOT_FOUND", message="Resource not found")
    """
    return {
        "success": False,
        "data": data,
        "error": error,
        "message": message or error
    }


def paginated_response(
    items: List[Any],
    total: int,
    page: int = 1,
    page_size: int = 20,
    message: str = None
) -> dict:
    """
    创建分页响应的便捷函数

    Args:
        items: 数据项列表
        total: 总记录数
        page: 当前页码
        page_size: 每页大小
        message: 提示信息

    Returns:
        dict: 符合 PaginatedResponse 格式的字典

    Examples:
        >>> return paginated_response(
        ...     items=[{"id": 1}, {"id": 2}],
        ...     total=100,
        ...     page=1,
        ...     page_size=20
        ... )
    """
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return {
        "success": True,
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        },
        "message": message
    }
