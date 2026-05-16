"""
统一 API 响应格式测试

测试新的响应格式和异常处理系统。

Issue: #3532
"""

import pytest
from fastapi import status


class TestResponseModels:
    """测试响应模型"""

    def test_api_response_success(self):
        from core.response import APIResponse
        response = APIResponse[int](
            success=True,
            data=42,
            error=None,
            message="Success"
        )
        assert response.success is True
        assert response.data == 42
        assert response.error is None
        assert response.message == "Success"

    def test_api_response_error(self):
        from core.response import APIResponse
        response = APIResponse[None](
            success=False,
            data=None,
            error="NOT_FOUND",
            message="Resource not found"
        )
        assert response.success is False
        assert response.data is None
        assert response.error == "NOT_FOUND"

    def test_paginated_data(self):
        from core.response import PaginatedData
        data = PaginatedData[int](
            items=[1, 2, 3],
            total=100,
            page=1,
            page_size=10
        )
        assert data.total_pages == 10

    def test_success_response_helper(self):
        from core.response import success_response
        response = success_response(data={"id": 1}, message="Created")
        assert response["success"] is True
        assert response["data"]["id"] == 1
        assert response["message"] == "Created"

    def test_error_response_helper(self):
        from core.response import error_response
        response = error_response(error="VALIDATION_ERROR", message="Invalid input")
        assert response["success"] is False
        assert response["error"] == "VALIDATION_ERROR"

    def test_paginated_response_helper(self):
        from core.response import paginated_response
        response = paginated_response(
            items=[{"id": 1}, {"id": 2}],
            total=50,
            page=1,
            page_size=10
        )
        assert response["success"] is True
        assert response["data"]["total"] == 50
        assert response["data"]["total_pages"] == 5


class TestExceptionClasses:
    """测试异常类"""

    def test_api_error_base(self):
        from core.exceptions import APIError
        error = APIError("Something went wrong", "CUSTOM_ERROR", 500)
        assert error.message == "Something went wrong"
        assert error.code == "CUSTOM_ERROR"
        assert error.status_code == 500

    def test_api_error_to_dict(self):
        from core.exceptions import NotFoundError
        error = NotFoundError("Portfolio", "abc-123")
        response_dict = error.to_dict()
        assert response_dict["success"] is False
        assert response_dict["error"] == "NOT_FOUND"

    def test_not_found_error(self):
        from core.exceptions import NotFoundError
        error = NotFoundError("Portfolio", "abc-123")
        assert "Portfolio not found" in error.message
        assert "abc-123" in error.message
        assert error.status_code == status.HTTP_404_NOT_FOUND

    def test_validation_error(self):
        from core.exceptions import ValidationError
        error = ValidationError("Invalid date format", "start_date")
        assert error.status_code == status.HTTP_400_BAD_REQUEST
        assert error.details["field"] == "start_date"

    def test_business_error(self):
        from core.exceptions import BusinessError
        error = BusinessError("Cannot delete running backtest")
        assert error.code == "BUSINESS_ERROR"
        assert error.status_code == status.HTTP_400_BAD_REQUEST

        error_custom = BusinessError("Insufficient funds", "INSUFFICIENT_FUNDS")
        assert error_custom.code == "INSUFFICIENT_FUNDS"

    def test_conflict_error(self):
        from core.exceptions import ConflictError
        error = ConflictError("Name already exists", "Portfolio", "MyPortfolio")
        assert error.status_code == status.HTTP_409_CONFLICT
        assert error.details["resource_type"] == "Portfolio"
        assert error.details["resource_id"] == "MyPortfolio"

    def test_unauthorized_error(self):
        from core.exceptions import UnauthorizedError
        error = UnauthorizedError("Invalid token")
        assert error.status_code == status.HTTP_401_UNAUTHORIZED

    def test_forbidden_error(self):
        from core.exceptions import ForbiddenError
        error = ForbiddenError("Access denied")
        assert error.status_code == status.HTTP_403_FORBIDDEN

    def test_service_unavailable_error(self):
        from core.exceptions import ServiceUnavailableError
        error = ServiceUnavailableError("Database connection failed", "MySQL")
        assert error.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert error.details["service"] == "MySQL"

    def test_rate_limit_error(self):
        from core.exceptions import RateLimitError
        error = RateLimitError("Too many requests", retry_after=60)
        assert error.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert error.details["retry_after"] == 60


@pytest.mark.integration
class TestHealthEndpoint:
    """集成测试 - 需要运行中的API服务器"""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        from fastapi.testclient import TestClient
        from main import app
        self.client = TestClient(app)

    def test_health_check(self):
        response = self.client.get("/health")
        assert response.status_code == 200
        assert "status" in response.json()


@pytest.mark.integration
class TestBacktestEndpoints:
    """集成测试：回测端点响应格式"""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        from fastapi.testclient import TestClient
        from main import app
        self.client = TestClient(app)

    def test_list_backtests_format(self):
        response = self.client.get("/api/backtest?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "data" in data
        assert "message" in data
        if data["success"] and data["data"]:
            assert "items" in data["data"]
            assert "total" in data["data"]
            assert "page" in data["data"]
            assert "page_size" in data["data"]
            assert "total_pages" in data["data"]

    def test_get_engines_format(self):
        response = self.client.get("/api/backtest/engines")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_get_analyzers_format(self):
        response = self.client.get("/api/backtest/analyzers")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "data" in data
        assert isinstance(data["data"], list)


@pytest.mark.integration
class TestPortfolioEndpoints:
    """集成测试：Portfolio端点响应格式"""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        from fastapi.testclient import TestClient
        from main import app
        self.client = TestClient(app)

    def test_list_portfolios_format(self):
        response = self.client.get("/api/portfolio")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "data" in data
        assert isinstance(data["data"], list)


@pytest.mark.integration
class TestErrorHandling:
    """集成测试：错误处理"""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        from fastapi.testclient import TestClient
        from main import app
        self.client = TestClient(app)

    def test_404_error_format(self):
        response = self.client.get("/api/backtest/non-existent-uuid")
        assert response.status_code == 404
        data = response.json()
        assert "success" in data
        assert data["success"] is False
        assert "error" in data
        assert "message" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
