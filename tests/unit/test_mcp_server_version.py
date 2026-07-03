"""MCP Server 版本一致性测试。

验收（issue #4969）：MCP Server /health 与 / 返回的 version 必须与
`ginkgo version`（即 config.package.VERSION）一致，不能再硬编码字面量。

通过公共 ASGI 接口（Starlette TestClient）验证，不耦合 handler 内部实现。

注意：测试文件平铺在 tests/unit/ 下而非 tests/unit/mcp_server/，避免测试包名
遮蔽仓库根的真 `mcp_server` 包（sys.path 上 tests/unit/ 在前会先命中测试包）。
"""
import os
import sys

import pytest

# mcp_server 是仓库根目录下的顶层包（不在 src/ginkgo 下），需把 repo root 加入 sys.path
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


@pytest.fixture
def http_app():
    """构建 MCP HTTP ASGI app（sse 模式，无需 API Key/DB）。"""
    from mcp_server.server import GinkgoMCPServer
    import asyncio
    server = GinkgoMCPServer(transport="sse")
    return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
        server._build_http_app()
    )


def _get_version_truth():
    from ginkgo.config.package import VERSION
    return VERSION


class TestMCPServerVersionConsistency:
    """MCP Server 暴露的版本必须与 CLI 同源（config.package.VERSION）。"""

    def test_health_endpoint_returns_canonical_version(self, http_app):
        from starlette.testclient import TestClient
        expected = _get_version_truth()
        with TestClient(http_app) as client:
            resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert "version" in body, f"/health 缺 version 字段: {body}"
        assert body["version"] == expected, (
            f"/health version={body['version']!r} 与 ginkgo version={expected!r} 不一致"
        )

    def test_root_endpoint_returns_canonical_version(self, http_app):
        from starlette.testclient import TestClient
        expected = _get_version_truth()
        with TestClient(http_app) as client:
            resp = client.get("/")
        assert resp.status_code == 200
        body = resp.json()
        assert "version" in body, f"/ 缺 version 字段: {body}"
        assert body["version"] == expected, (
            f"/ version={body['version']!r} 与 ginkgo version={expected!r} 不一致"
        )
