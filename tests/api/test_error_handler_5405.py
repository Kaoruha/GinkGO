# Issue: #5405
# Upstream: api.main, api.middleware.error_handler
# Downstream: pytest
# Role: 全局错误处理器注册测试——raise HTTPException 必须返标准格式含 trace_id

"""
全局错误处理器注册测试 (#5405)。

#5405 根因：api/main.py 只注册了 Exception / APIError 的异常处理器，
未注册 fastapi.HTTPException。FastAPI/Starlette 异常查找走 MRO 精确匹配，
fastapi.HTTPException（子类）会先匹配自身，找不到才回溯父类
starlette.exceptions.HTTPException——而后者有 Starlette 内置默认处理器
返回 {"detail": ...} 无 trace_id，于是子类异常被「截胡」。
导致 api/api/settings.py 等处 raise HTTPException 的端点失败时
返回 {detail} 而非标准 {code,data,message,trace_id} 格式。

修复：main.py 显式注册 fastapi.HTTPException → global_error_handler，
激活 error_handler.py 既有 HTTPException 分支（死代码→活代码）。
"""

import pytest


class TestGlobalErrorHandlerRegistration:
    """#5405: main.py 必须注册 fastapi.HTTPException → global_error_handler。"""

    def test_http_exception_registered_to_global_handler(self, api_modules):
        """app 必须显式注册 fastapi.HTTPException 异常处理器。

        不能依赖 Exception 基类回溯——Starlette 对 fastapi.HTTPException
        有内置默认处理器（返 {detail}），会先于 Exception 基类 handler 命中。
        """
        import sys
        from pathlib import Path

        # 仓库根 main.py 遮蔽 api/main.py（见 #5766）。api_modules fixture 已把
        # api/ 插入 sys.path，但 tests/conftest.py 的后续 autouse fixture 会把
        # tests/fixtures 等路径重新插到 [0]，叠加 cwd('') 使根 main.py 优先。
        # 这里把 api/ 提回 [0] 并清 main 缓存，确保解析到 api/main.py。
        api_dir = str(Path(__file__).resolve().parent.parent.parent / "api")
        if sys.path[0] != api_dir:
            sys.path.insert(0, api_dir)
        sys.modules.pop("main", None)
        import main
        from fastapi import HTTPException
        from middleware.error_handler import global_error_handler

        handlers = main.app.exception_handlers
        assert HTTPException in handlers, (
            "fastapi.HTTPException 未注册到 app.exception_handlers，"
            "raise HTTPException 会走 Starlette 内置处理器返 {detail} 无 trace_id (#5405)"
        )
        # 注册的必须是 global_error_handler（激活 error_handler.py:27-37 既有死代码分支）
        assert handlers[HTTPException] is global_error_handler


class TestGlobalErrorHandlerBehavior:
    """回归守护：global_error_handler 对 HTTPException 必须返标准格式含 trace_id。

    契约测试只验「注册存在」，本测试验「注册的 handler 行为正确」——防止
    未来有人重构 handler 丢掉 trace_id 或 message 字段，而注册契约仍绿。
    """

    def test_handler_returns_trace_id_for_http_exception(self):
        """global_error_handler 处理 HTTPException 返 {code,data,message,trace_id}。"""
        import asyncio
        import json

        from fastapi import HTTPException
        from middleware.error_handler import global_error_handler

        class _FakeUrl:
            path = "/api/v1/test-5405"

        class _FakeRequest:
            url = _FakeUrl()

        exc = HTTPException(status_code=404, detail="Not found")
        resp = asyncio.run(global_error_handler(_FakeRequest(), exc))

        body = json.loads(resp.body)
        assert resp.status_code == 404
        assert body["code"] == 404
        assert body["message"] == "Not found"
        assert body["data"] is None
        assert "trace_id" in body
        assert body["trace_id"]  # 非空


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
