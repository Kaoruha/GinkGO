"""
API 版本控制测试
验证所有API端点都使用了正确的版本前缀和命名规范
"""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestAPIVersioning:
    """API版本控制测试类"""

    def test_health_endpoints_no_version(self):
        """健康检查端点不应该使用版本前缀"""
        # 根健康检查
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "ginkgo-api-server"

        # API路径健康检查
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "ginkgo-api-server"

    def test_documentation_endpoints_no_version(self):
        """文档端点不应该使用版本前缀"""
        # Swagger UI
        response = client.get("/docs")
        assert response.status_code == 200

        # ReDoc
        response = client.get("/redoc")
        assert response.status_code == 200

        # OpenAPI JSON
        response = client.get("/openapi.json")
        assert response.status_code == 200

    def test_portfolio_endpoints_use_v1(self):
        """Portfolio端点应该使用v1版本前缀和复数形式"""
        # 列表端点（需要认证，这里只测试路径存在）
        # GET /api/v1/portfolios
        response = client.get("/api/v1/portfolios")
        # 可能返回401（未认证）或403，但不应返回404
        assert response.status_code in [200, 401, 403]

        # 详情端点
        # GET /api/v1/portfolios/{uuid}
        response = client.get("/api/v1/portfolios/test-uuid")
        assert response.status_code in [200, 401, 403, 404]

    def test_backtest_endpoints_use_v1(self):
        """Backtest端点应该使用v1版本前缀和复数形式"""
        # 列表端点
        response = client.get("/api/v1/backtests")
        assert response.status_code in [200, 401, 403]

        # 详情端点
        response = client.get("/api/v1/backtests/test-uuid")
        assert response.status_code in [200, 401, 403, 404]

    def test_node_graph_endpoints_use_v1(self):
        """NodeGraph端点应该使用v1版本前缀"""
        # 列表端点
        response = client.get("/api/v1/node-graphs")
        assert response.status_code in [200, 401, 403]

        # 详情端点
        response = client.get("/api/v1/node-graphs/test-uuid")
        assert response.status_code in [200, 401, 403, 404]

    def test_component_endpoints_use_v1(self):
        """Component端点应该使用v1版本前缀"""
        # 列表端点
        response = client.get("/api/v1/components")
        assert response.status_code in [200, 401, 403]

        # 详情端点
        response = client.get("/api/v1/components/test-uuid")
        assert response.status_code in [200, 401, 403, 404]

    def test_data_endpoints_use_v1(self):
        """Data端点应该使用v1版本前缀"""
        # 统计端点
        response = client.get("/api/v1/data/stats")
        assert response.status_code in [200, 401, 403]

        # 股票信息端点
        response = client.get("/api/v1/data/stockinfo")
        assert response.status_code in [200, 401, 403]

    def test_settings_endpoints_use_v1(self):
        """Settings端点应该使用v1版本前缀"""
        # 用户列表端点
        response = client.get("/api/v1/settings/users")
        assert response.status_code in [200, 401, 403]

    def test_auth_endpoints_use_v1(self):
        """Auth端点应该使用v1版本前缀"""
        # 登录端点
        response = client.post("/api/v1/auth/login", json={
            "username": "test",
            "password": "test"
        })
        # 可能返回401（认证失败）或422（验证错误），但不应返回404
        assert response.status_code in [200, 401, 422]

    def test_old_paths_not_found(self):
        """旧路径应该返回404"""
        # 测试一些已知的旧路径
        old_paths = [
            "/portfolio",
            "/backtest",
            "/api/dashboard",  # 旧的单数形式
            "/api/portfolio",  # 缺少版本号
            "/api/backtest",   # 缺少版本号
        ]

        for path in old_paths:
            response = client.get(path)
            # 应该返回404或405（方法不允许），而不是200
            assert response.status_code in [404, 405]

    def test_sse_endpoint_uses_v1(self):
        """SSE端点应该使用v1版本前缀"""
        # 这个测试可能会挂起，所以我们只验证路径格式
        # 实际的SSE连接测试应该在集成测试中进行
        response = client.get("/api/v1/backtests/test-uuid/events")
        # 可能返回404（不存在）或其他错误，但不应该是旧路径
        assert response.status_code in [404, 401, 403]


class TestAPIVersionConfig:
    """测试版本配置模块"""

    def test_version_constants(self):
        """测试版本常量定义正确"""
        from core.version import API_VERSION, API_PREFIX

        assert API_VERSION == "v1"
        assert API_PREFIX == "/api/v1"

    def test_no_version_endpoints(self):
        """测试无需版本控制的端点列表"""
        from core.version import NO_VERSION_ENDPOINTS

        expected_no_version = {
            "/health",
            "/api/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/ws",
        }

        assert NO_VERSION_ENDPOINTS == expected_no_version

    def test_resource_plural_map(self):
        """测试资源复数映射"""
        from core.version import RESOURCE_PLURAL_MAP

        assert RESOURCE_PLURAL_MAP.get("portfolio") == "portfolios"
        assert RESOURCE_PLURAL_MAP.get("backtest") == "backtests"
        assert RESOURCE_PLURAL_MAP.get("node-graph") == "node-graphs"

    def test_get_api_path_function(self):
        """测试API路径生成函数"""
        from core.version import get_api_path

        # 列表路径
        assert get_api_path("portfolio", "list") == "/api/v1/portfolios"
        assert get_api_path("backtest", "list") == "/api/v1/backtests"

        # 详情路径
        assert get_api_path("portfolio", "detail", "123") == "/api/v1/portfolios/123"

        # 自定义操作
        assert get_api_path("backtest", "start", "123") == "/api/v1/backtests/123/start"

    def test_is_versioned_endpoint(self):
        """测试端点版本检查函数"""
        from core.version import is_versioned_endpoint

        # 需要版本控制的端点
        assert is_versioned_endpoint("/api/v1/portfolios") == True
        assert is_versioned_endpoint("/api/v1/backtests/123") == True

        # 不需要版本控制的端点
        assert is_versioned_endpoint("/health") == False
        assert is_versioned_endpoint("/docs") == False
        assert is_versioned_endpoint("/ws/portfolio") == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
