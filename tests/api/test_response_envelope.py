# Issue: ADR-025 第③步 (HTTP ResponseMapper 基座)
# Upstream: api/core/response.py (APIResponse / PaginatedResponse 泛型)
# Downstream: pytest, fastapi, pydantic
# Role: 验证统一响应信封泛型 wire 逐字段一致 + response_model 生成 OpenAPI schema

"""ADR-025 第③步 HTTP ResponseMapper 基座 — 统一响应信封泛型测试。

基座 PR 仅补 pydantic 信封泛型 (APIResponse[T]/PaginatedResponse), 零端点改动。
本测试证明三件事 (后续按域 PR 给端点接 response_model 的契约前提):

- wire-exact: APIResponse/PaginatedResponse 序列化形状与 ok()/paginated()/fail()
  逐字段一致 (meta 仅非 None 时出现, data 即使 None 亦保留)。
- 泛型参数化: APIResponse[DTO] 对 data 强类型 (非法类型 ValidationError)。
- response_model 契约: 端点声明 response_model=APIResponse[DTO] 即得
  OpenAPI schema + 响应字段裁剪 (mini FastAPI app 证)。
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError


class _Item(BaseModel):
    """测试用业务 DTO (证泛型参数化)。"""

    id: int
    name: str


class TestAPIResponseWireExact:
    """APIResponse 序列化形状须与 ok()/fail() 逐字段一致。"""

    def test_ok_shape_omits_meta_when_none(self, api_modules):
        from core.response import ok, APIResponse

        raw = ok(data={"id": 1})
        resp = APIResponse.model_validate(raw)
        d = resp.model_dump()
        # wire-exact: code/data/message/trace_id 恒在; meta None 时省 key (对齐 ok())
        assert set(d.keys()) == {"code", "data", "message", "trace_id"}
        assert d["code"] == 0
        assert d["data"] == {"id": 1}
        assert d["message"] == "ok"
        assert d["trace_id"]  # 非空

    def test_ok_shape_keeps_meta_when_present(self, api_modules):
        from core.response import ok, pagination_meta, APIResponse

        raw = ok(data=[1, 2], meta=pagination_meta(1, 50, 10))
        resp = APIResponse.model_validate(raw)
        d = resp.model_dump()
        assert "meta" in d
        assert d["meta"]["total"] == 50
        assert d["meta"]["total_pages"] == 5

    def test_fail_shape_propagates_error_code(self, api_modules):
        from core.response import fail, APIResponse

        raw = fail(404, "Portfolio not found")
        resp = APIResponse.model_validate(raw)
        d = resp.model_dump()
        assert d["code"] == 404
        assert d["message"] == "Portfolio not found"
        assert d["data"] is None
        assert "meta" not in d  # fail() 不带 meta


class TestPaginatedResponse:
    """PaginatedResponse 验证 paginated() 形状, meta 为 PaginationMeta。"""

    def test_paginated_shape_carries_pagination_meta(self, api_modules):
        from core.response import paginated, PaginatedResponse

        raw = paginated(items=[{"id": 1}], total=50, page=1, page_size=10)
        resp = PaginatedResponse.model_validate(raw)
        d = resp.model_dump()
        assert d["code"] == 0
        assert d["meta"]["total_pages"] == 5
        assert d["meta"]["page"] == 1
        assert d["data"] == [{"id": 1}]

    def test_paginated_meta_validates_constraints(self, api_modules):
        # PaginationMeta: page>=1, page_size 1..100 — 非法值须 ValidationError 响亮报错
        from core.response import PaginatedResponse

        raw = {
            "code": 0,
            "data": [],
            "message": "ok",
            "trace_id": "t",
            "meta": {"page": 0, "page_size": 10, "total": 0, "total_pages": 0},
        }
        with pytest.raises(ValidationError):
            PaginatedResponse.model_validate(raw)


class TestGenericParameterization:
    """APIResponse[T] 对 data 强类型 (运行期校验非法类型)。"""

    def test_typed_data_coerced_to_dto(self, api_modules):
        from core.response import APIResponse

        raw = {"code": 0, "data": {"id": 1, "name": "x"}, "message": "ok", "trace_id": "t"}
        resp = APIResponse[_Item].model_validate(raw)
        assert isinstance(resp.data, _Item)
        assert resp.data.id == 1

    def test_typed_data_rejects_wrong_shape(self, api_modules):
        from core.response import APIResponse

        raw = {"code": 0, "data": {"id": "not-an-int"}, "message": "ok", "trace_id": "t"}
        with pytest.raises(ValidationError):
            APIResponse[_Item].model_validate(raw)


class TestFastAPIResponseModel:
    """端点声明 response_model=APIResponse[T] → OpenAPI schema + 响应校验/裁剪。"""

    def test_openapi_schema_generated_and_wire_exact(self, api_modules):
        from core.response import APIResponse, ok

        app = FastAPI()

        @app.get("/item", response_model=APIResponse[_Item])
        async def get_item():
            return ok(data={"id": 1, "name": "x"})

        client = TestClient(app)
        # response_model 已注册 OpenAPI schema (200 响应有定义)
        schema = app.openapi()
        assert "200" in schema["paths"]["/item"]["get"]["responses"]
        # 实际响应 wire-exact: 无 meta key
        body = client.get("/item").json()
        assert set(body.keys()) == {"code", "data", "message", "trace_id"}
        assert body["data"] == {"id": 1, "name": "x"}

    def test_response_model_strips_unknown_fields(self, api_modules):
        from core.response import APIResponse, ok

        app = FastAPI()

        @app.get("/item", response_model=APIResponse[_Item])
        async def get_item():
            # handler 返回多带 extra; response_model=_Item 须裁剪只留 schema 内字段
            return ok(data={"id": 1, "name": "x", "extra": "should-be-stripped"})

        client = TestClient(app)
        body = client.get("/item").json()
        assert "extra" not in body["data"]
        assert body["data"] == {"id": 1, "name": "x"}
