"""
API 版本控制测试
验证所有API端点都使用了正确的版本前缀和命名规范

Issue: #3532
"""

import pytest


@pytest.mark.integration
class TestAPIVersioning:
    """API版本控制集成测试 - 需要运行中的API服务器"""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        from fastapi.testclient import TestClient
        from main import app
        self.client = TestClient(app)

    def test_health_endpoints_no_version(self):
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "ginkgo-api-server"

        response = self.client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "ginkgo-api-server"

    def test_documentation_endpoints_no_version(self):
        response = self.client.get("/docs")
        assert response.status_code == 200

        response = self.client.get("/redoc")
        assert response.status_code == 200

        response = self.client.get("/openapi.json")
        assert response.status_code == 200

    def test_portfolio_endpoints_use_v1(self):
        response = self.client.get("/api/v1/portfolios")
        assert response.status_code in [200, 401, 403]

        response = self.client.get("/api/v1/portfolios/test-uuid")
        assert response.status_code in [200, 401, 403, 404]

    def test_backtest_endpoints_use_v1(self):
        response = self.client.get("/api/v1/backtests")
        assert response.status_code in [200, 401, 403]

        response = self.client.get("/api/v1/backtests/test-uuid")
        assert response.status_code in [200, 401, 403, 404]

    def test_node_graph_endpoints_use_v1(self):
        response = self.client.get("/api/v1/node-graphs")
        assert response.status_code in [200, 401, 403]

        response = self.client.get("/api/v1/node-graphs/test-uuid")
        assert response.status_code in [200, 401, 403, 404]

    def test_component_endpoints_use_v1(self):
        response = self.client.get("/api/v1/components")
        assert response.status_code in [200, 401, 403]

        response = self.client.get("/api/v1/components/test-uuid")
        assert response.status_code in [200, 401, 403, 404]

    def test_data_endpoints_use_v1(self):
        response = self.client.get("/api/v1/data/stats")
        assert response.status_code in [200, 401, 403]

        response = self.client.get("/api/v1/data/stockinfo")
        assert response.status_code in [200, 401, 403]

    def test_settings_endpoints_use_v1(self):
        response = self.client.get("/api/v1/settings/users")
        assert response.status_code in [200, 401, 403]

    def test_auth_endpoints_use_v1(self):
        response = self.client.post("/api/v1/auth/login", json={
            "username": "test",
            "password": "test"
        })
        assert response.status_code in [200, 401, 422]

    def test_old_paths_not_found(self):
        old_paths = [
            "/portfolio",
            "/backtest",
            "/api/dashboard",
            "/api/portfolio",
            "/api/backtest",
        ]
        for path in old_paths:
            response = self.client.get(path)
            assert response.status_code in [404, 405]

    def test_sse_endpoint_uses_v1(self):
        response = self.client.get("/api/v1/backtests/test-uuid/events")
        assert response.status_code in [404, 401, 403]


class TestAPIVersionConfig:
    """测试版本配置模块 - 纯单元测试，无需服务器"""

    def test_version_constants(self):
        from core.version import API_VERSION, API_PREFIX
        assert API_VERSION == "v1"
        assert API_PREFIX == "/api/v1"

    def test_no_version_endpoints(self):
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
        from core.version import RESOURCE_PLURAL_MAP
        assert RESOURCE_PLURAL_MAP.get("portfolio") == "portfolios"
        assert RESOURCE_PLURAL_MAP.get("backtest") == "backtests"
        assert RESOURCE_PLURAL_MAP.get("node-graph") == "node-graphs"

    def test_get_api_path_function(self):
        from core.version import get_api_path
        assert get_api_path("portfolio", "list") == "/api/v1/portfolios"
        assert get_api_path("backtest", "list") == "/api/v1/backtests"
        assert get_api_path("portfolio", "detail", "123") == "/api/v1/portfolios/123"
        assert get_api_path("backtest", "start", "123") == "/api/v1/backtests/123/start"

    def test_is_versioned_endpoint(self):
        from core.version import is_versioned_endpoint
        assert is_versioned_endpoint("/api/v1/portfolios") is True
        assert is_versioned_endpoint("/api/v1/backtests/123") is True
        assert is_versioned_endpoint("/health") is False
        assert is_versioned_endpoint("/docs") is False
        assert is_versioned_endpoint("/ws/portfolio") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
