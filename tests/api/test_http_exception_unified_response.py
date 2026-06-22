"""#5631: HTTPException 必须经 global_error_handler 转统一 {code,data,message,trace_id}。

根因: main.py 只为 Exception/APIError 注册了 global_error_handler，漏 HTTPException，
导致 login/register 等 `raise HTTPException(...)` 走 Starlette 默认 handler 返 {"detail":...}。
"""
import asyncio
import json
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse


class TestGlobalErrorHandlerHttpExceptionFormat:
    """#5631: global_error_handler 对 HTTPException 产出统一格式（钉 handler 逻辑）。"""

    @pytest.mark.unit
    def test_handler_returns_unified_format_for_http_exception(self):
        from middleware.error_handler import global_error_handler

        exc = HTTPException(status_code=401, detail="Invalid username or password")
        resp = asyncio.run(global_error_handler(request=MagicMock(), exc=exc))

        assert isinstance(resp, JSONResponse)
        assert resp.status_code == 401
        body = json.loads(resp.body)
        # 统一格式: code/data/message/trace_id（非 {"detail": ...}）
        assert body["code"] == 401
        assert body["data"] is None
        assert body["message"] == "Invalid username or password"
        assert "trace_id" in body
        assert "detail" not in body, "不应保留 Starlette 默认的 detail 字段"


class TestAppRegistersHttpExceptionHandler:
    """#5631: main.py 必须把 HTTPException 注册到 global_error_handler。

    按文件路径加载真实 api/main.py（绕开根 main.py 遮蔽，见 arch_api_test_root_main_shadow），
    断言 app.exception_handlers[HTTPException] is global_error_handler。
    修复前: HTTPException 未注册 → RED；修复后 → GREEN。
    """

    @pytest.mark.unit
    def test_main_registers_http_exception_to_global_handler(self, api_modules):
        import importlib.util
        from pathlib import Path

        from middleware.error_handler import global_error_handler

        # 用全新 module name 按绝对路径加载 api/main.py，避开 `from main import app` 的根遮蔽
        api_main = Path(__file__).resolve().parents[2] / "api" / "main.py"
        spec = importlib.util.spec_from_file_location("ginkgo_api_main_under_test", str(api_main))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        app = mod.app

        handlers = app.exception_handlers
        assert HTTPException in handlers, \
            "main.py 未把 HTTPException 注册到 global_error_handler（走 Starlette 默认 detail 格式）"
        assert handlers[HTTPException] is global_error_handler, \
            "HTTPException 应路由到 global_error_handler 而非其他 handler"
