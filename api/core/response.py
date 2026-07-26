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
from typing import Optional, Any, Generic, TypeVar, List, Dict

from pydantic import BaseModel, Field, model_serializer

T = TypeVar('T')


class PaginationMeta(BaseModel):
    """分页元数据"""
    page: int = Field(1, description="当前页码", ge=1)
    page_size: int = Field(20, description="每页大小", ge=1, le=100)
    total: int = Field(0, description="总记录数")
    total_pages: int = Field(0, description="总页数")


# ----------------------------------------------------------------------
# 统一响应信封 (WebResponse 亚型, ADR-025 Step ③ 基座)
# ----------------------------------------------------------------------
# 现状: ok()/paginated()/fail() 返 plain dict → OpenAPI 无响应 schema。
# 本基座补 pydantic 信封泛型, wire 形状与 ok() 逐字段一致 (前端 request.ts/
# types/api.ts 已锁 {code,data,message,meta?,trace_id}), 端点声明
# response_model=APIResponse[...] 即得 OpenAPI schema + 响应校验, wire 不变。
# 后续按域 PR 逐步给端点接 response_model (backtest→portfolio→...); 本 PR 零端点改动。


class APIResponse(BaseModel, Generic[T]):
    """统一响应信封 (HTTP 边界 WebResponse, ADR-025)。

    Wire 形状 (与 ``core.response.ok()`` 逐字段一致)::

        {code, data, message, trace_id} + meta (仅非 None 时出现)

    用法::

        @router.get("/x", response_model=APIResponse[ItemDTO])
        async def get_x(): return ok(data=item_dict)

    ``data: Optional[T]`` 仅在声明 ``response_model=APIResponse[ConcreteDTO]`` 时
    起**类型化**作用 (OpenAPI schema + 响应字段裁剪); ``ok()`` 运行期仍返 dict,
    FastAPI 据响应模型校验/序列化, wire 与既有完全一致。
    """
    code: int = 0
    data: Optional[T] = None
    message: str = "ok"
    trace_id: str = ""
    meta: Optional[Dict[str, Any]] = None

    @model_serializer(mode="wrap")
    def _serialize(self, handler):
        # wire-exact: meta 仅非 None 时出现 (对齐 ok(): meta is None → 省 key)。
        # 其余 code/data/message/trace_id 恒出现 (data 即使 None 亦保留, 同 ok())。
        d = handler(self)
        if d.get("meta") is None:
            d.pop("meta", None)
        return d


class PaginatedResponse(APIResponse):
    """分页响应信封: ``data`` 为 items 列表, ``meta`` 为 PaginationMeta。

    用法::

        @router.get("/x", response_model=PaginatedResponse)
        async def list_x(): return paginated(items=..., total=..., ...)

    若需 item 级强类型, 改声明 ``response_model=APIResponse[List[ItemDTO]]``
    并手填 ``meta`` (PaginatedResponse 本身 data 留 Any, 兼容既有异构列表)。
    """
    data: Optional[List[Any]] = None
    meta: Optional[PaginationMeta] = None


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
