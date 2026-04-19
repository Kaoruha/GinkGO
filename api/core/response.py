"""
统一 API 响应格式

所有接口统一返回:
{
    "code": 0,          // 0=成功, 非零=错误码
    "data": <业务数据>,  // 成功时为实际数据
    "message": "ok",    // 描述信息
    "meta": {...},       // 分页元数据(仅分页接口)
    "trace_id": "..."   // 请求追踪ID
}
"""

import uuid
from typing import Optional, Any, Generic, TypeVar, List

from pydantic import BaseModel, Field

T = TypeVar('T')


class PaginationMeta(BaseModel):
    """分页元数据"""
    page: int = Field(1, description="当前页码", ge=1)
    page_size: int = Field(20, description="每页大小", ge=1, le=100)
    total: int = Field(0, description="总记录数")
    total_pages: int = Field(0, description="总页数")


def _new_trace_id() -> str:
    return uuid.uuid4().hex[:16]


def ok(data: Any = None, message: str = "ok", meta: dict = None, trace_id: str = None) -> dict:
    """
    成功响应

    Examples:
        return ok(data={"id": 1})
        return ok(data=items, meta=pagination_meta(page=1, total=100, page_size=20))
    """
    result = {
        "code": 0,
        "data": data,
        "message": message,
        "trace_id": trace_id or _new_trace_id(),
    }
    if meta is not None:
        result["meta"] = meta
    return result


def fail(code: int, message: str = None, data: Any = None, trace_id: str = None) -> dict:
    """
    错误响应

    Examples:
        return fail(404, "Portfolio not found")
        return fail(400, "Invalid parameter")
    """
    return {
        "code": code,
        "data": data,
        "message": message or "error",
        "trace_id": trace_id or _new_trace_id(),
    }


def pagination_meta(page: int, total: int, page_size: int) -> dict:
    """生成分页元数据"""
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }


def paginated(items: list, total: int, page: int = 1, page_size: int = 20,
              message: str = "ok", trace_id: str = None) -> dict:
    """
    分页成功响应

    Examples:
        return paginated(items=[...], total=100, page=1, page_size=20)
    """
    return ok(
        data=items,
        message=message,
        meta=pagination_meta(page, total, page_size),
        trace_id=trace_id,
    )
