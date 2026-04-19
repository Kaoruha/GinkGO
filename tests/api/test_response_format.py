"""
统一 API 响应格式测试

测试新的响应格式和异常处理系统。
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from main import app
from core.response import APIResponse, PaginatedResponse, success_response, error_response, paginated_response
from core.exceptions import (
    APIError,
    NotFoundError,
    ValidationError,
    BusinessError,
    ConflictError,
    UnauthorizedError,
    ForbiddenError,
    ServiceUnavailableError,
    RateLimitError
)


client = TestClient(app)


class TestResponseModels:
    """测试响应模型"""

    def test_api_response_success(self):
        """测试成功响应"""
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
        """测试错误响应"""
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
        """测试分页数据"""
        from core.response import PaginatedData

        data = PaginatedData[int](
            items=[1, 2, 3],
            total=100,
            page=1,
            page_size=10
        )
        assert data.total_pages == 10  # 自动计算总页数

    def test_success_response_helper(self):
        """测试成功响应辅助函数"""
        response = success_response(data={"id": 1}, message="Created")
        assert response["success"] is True
        assert response["data"]["id"] == 1
        assert response["message"] == "Created"

    def test_error_response_helper(self):
        """测试错误响应辅助函数"""
        response = error_response(error="VALIDATION_ERROR", message="Invalid input")
        assert response["success"] is False
        assert response["error"] == "VALIDATION_ERROR"

    def test_paginated_response_helper(self):
        """测试分页响应辅助函数"""
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
        """测试基础 APIError"""
        error = APIError("Something went wrong", "CUSTOM_ERROR", 500)
        assert error.message == "Something went wrong"
        assert error.code == "CUSTOM_ERROR"
        assert error.status_code == 500

    def test_api_error_to_dict(self):
        """测试 APIError 转换为字典"""
        error = NotFoundError("Portfolio", "abc-123")
        response_dict = error.to_dict()
        assert response_dict["success"] is False
        assert response_dict["error"] == "NOT_FOUND"

    def test_not_found_error(self):
        """测试 NotFoundError"""
        error = NotFoundError("Portfolio", "abc-123")
        assert "Portfolio not found" in error.message
        assert "abc-123" in error.message
        assert error.status_code == status.HTTP_404_NOT_FOUND

    def test_validation_error(self):
        """测试 ValidationError"""
        error = ValidationError("Invalid date format", "start_date")
        assert error.status_code == status.HTTP_400_BAD_REQUEST
        assert error.details["field"] == "start_date"

    def test_business_error(self):
        """测试 BusinessError"""
        error = BusinessError("Cannot delete running backtest")
        assert error.code == "BUSINESS_ERROR"
        assert error.status_code == status.HTTP_400_BAD_REQUEST

        error_custom = BusinessError("Insufficient funds", "INSUFFICIENT_FUNDS")
        assert error_custom.code == "INSUFFICIENT_FUNDS"

    def test_conflict_error(self):
        """测试 ConflictError"""
        error = ConflictError("Name already exists", "Portfolio", "MyPortfolio")
        assert error.status_code == status.HTTP_409_CONFLICT
        assert error.details["resource_type"] == "Portfolio"
        assert error.details["resource_id"] == "MyPortfolio"

    def test_unauthorized_error(self):
        """测试 UnauthorizedError"""
        error = UnauthorizedError("Invalid token")
        assert error.status_code == status.HTTP_401_UNAUTHORIZED

    def test_forbidden_error(self):
        """测试 ForbiddenError"""
        error = ForbiddenError("Access denied")
        assert error.status_code == status.HTTP_403_FORBIDDEN

    def test_service_unavailable_error(self):
        """测试 ServiceUnavailableError"""
        error = ServiceUnavailableError("Database connection failed", "MySQL")
        assert error.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert error.details["service"] == "MySQL"

    def test_rate_limit_error(self):
        """测试 RateLimitError"""
        error = RateLimitError("Too many requests", retry_after=60)
        assert error.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert error.details["retry_after"] == 60


class TestHealthEndpoint:
    """测试健康检查端点（验证响应格式）"""

    def test_health_check(self):
        """测试健康检查端点"""
        response = client.get("/health")
        assert response.status_code == 200
        # 健康检查端点可能返回旧格式，这是可以接受的
        assert "status" in response.json()


@pytest.mark.integration
class TestBacktestEndpoints:
    """集成测试：回测端点响应格式"""

    def test_list_backtests_format(self):
        """测试回测列表响应格式"""
        response = client.get("/api/backtest?page=1&page_size=10")
        assert response.status_code == 200

        data = response.json()
        # 验证新响应格式
        assert "success" in data
        assert "data" in data
        assert "message" in data

        if data["success"] and data["data"]:
            # 验证分页结构
            assert "items" in data["data"]
            assert "total" in data["data"]
            assert "page" in data["data"]
            assert "page_size" in data["data"]
            assert "total_pages" in data["data"]

    def test_get_engines_format(self):
        """测试引擎列表响应格式"""
        response = client.get("/api/backtest/engines")
        assert response.status_code == 200

        data = response.json()
        # 验证新响应格式
        assert "success" in data
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_get_analyzers_format(self):
        """测试分析器列表响应格式"""
        response = client.get("/api/backtest/analyzers")
        assert response.status_code == 200

        data = response.json()
        # 验证新响应格式
        assert "success" in data
        assert "data" in data
        assert isinstance(data["data"], list)


@pytest.mark.integration
class TestPortfolioEndpoints:
    """集成测试：Portfolio端点响应格式"""

    def test_list_portfolios_format(self):
        """测试Portfolio列表响应格式"""
        response = client.get("/api/portfolio")
        assert response.status_code == 200

        data = response.json()
        # 验证新响应格式
        assert "success" in data
        assert "data" in data
        assert isinstance(data["data"], list)


class TestErrorHandling:
    """测试错误处理"""

    def test_404_error_format(self):
        """测试404错误响应格式"""
        # 使用不存在的UUID
        response = client.get("/api/backtest/non-existent-uuid")
        assert response.status_code == 404

        data = response.json()
        # 验证新错误格式
        assert "success" in data
        assert data["success"] is False
        assert "error" in data
        assert "message" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
