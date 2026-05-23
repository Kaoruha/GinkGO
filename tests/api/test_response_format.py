# Issue: #3850
# Upstream: api.core.response, api.core.exceptions
# Downstream: pytest
# Role: 统一 API 响应格式与异常处理测试

"""
统一 API 响应格式测试

按实际 response.py (ok/fail/paginated) 和 exceptions.py 接口编写。
"""

import pytest
from fastapi import status


class TestResponseHelpers:
    """测试 response.py 辅助函数"""

    def test_ok_basic(self):
        from core.response import ok

        result = ok(data={"id": 1}, message="Success")
        assert result["code"] == 0
        assert result["data"]["id"] == 1
        assert result["message"] == "Success"
        assert "trace_id" in result

    def test_ok_default_message(self):
        from core.response import ok

        result = ok(data=42)
        assert result["message"] == "ok"

    def test_ok_with_meta(self):
        from core.response import ok

        meta = {"page": 1, "total": 100}
        result = ok(data=[1, 2], meta=meta)
        assert result["meta"]["page"] == 1
        assert result["meta"]["total"] == 100

    def test_ok_no_data(self):
        from core.response import ok

        result = ok()
        assert result["data"] is None
        assert result["code"] == 0

    def test_fail_basic(self):
        from core.response import fail

        result = fail(404, "Not found")
        assert result["code"] == 404
        assert result["message"] == "Not found"
        assert result["data"] is None
        assert "trace_id" in result

    def test_fail_default_message(self):
        from core.response import fail

        result = fail(500)
        assert result["message"] == "error"

    def test_paginated_response(self):
        from core.response import paginated

        items = [{"id": 1}, {"id": 2}]
        result = paginated(items=items, total=50, page=1, page_size=10)
        assert result["code"] == 0
        assert len(result["data"]) == 2
        assert result["meta"]["total"] == 50
        assert result["meta"]["total_pages"] == 5
        assert result["meta"]["page"] == 1

    def test_paginated_last_page(self):
        from core.response import paginated

        result = paginated(items=[], total=50, page=5, page_size=10)
        assert result["meta"]["total_pages"] == 5

    def test_pagination_meta(self):
        from core.response import pagination_meta

        meta = pagination_meta(page=1, total=25, page_size=10)
        assert meta["total_pages"] == 3

    def test_pagination_meta_zero_total(self):
        from core.response import pagination_meta

        meta = pagination_meta(page=1, total=0, page_size=10)
        assert meta["total_pages"] == 0

    def test_trace_id_passthrough(self):
        from core.response import ok, fail

        r1 = ok(data=1, trace_id="custom-trace")
        assert r1["trace_id"] == "custom-trace"

        r2 = fail(400, trace_id="custom-trace-2")
        assert r2["trace_id"] == "custom-trace-2"


class TestExceptionClasses:
    """测试 exceptions.py 异常类"""

    def test_api_error_base(self):
        from core.exceptions import APIError

        error = APIError("Something went wrong", code=500)
        assert error.message == "Something went wrong"
        assert error.code == 500
        assert error.status_code == 500

    def test_api_error_to_dict(self):
        from core.exceptions import APIError

        error = APIError("fail", code=500)
        d = error.to_dict()
        assert d["code"] == 500
        assert d["data"] is None
        assert d["message"] == "fail"
        assert "trace_id" in d

    def test_not_found_error(self):
        from core.exceptions import NotFoundError

        error = NotFoundError("Portfolio", "abc-123")
        assert "Portfolio not found" in error.message
        assert "abc-123" in error.message
        assert error.status_code == status.HTTP_404_NOT_FOUND
        assert error.code == 404

    def test_not_found_no_identifier(self):
        from core.exceptions import NotFoundError

        error = NotFoundError("Portfolio")
        assert error.message == "Portfolio not found"

    def test_validation_error(self):
        from core.exceptions import ValidationError

        error = ValidationError("Invalid date format", field="start_date")
        assert error.status_code == status.HTTP_400_BAD_REQUEST
        assert error.code == 400
        assert error.details["field"] == "start_date"

    def test_validation_error_no_field(self):
        from core.exceptions import ValidationError

        error = ValidationError("Bad input")
        assert error.details == {}

    def test_business_error(self):
        from core.exceptions import BusinessError

        error = BusinessError("Cannot delete running backtest")
        assert error.code == 400
        assert error.status_code == status.HTTP_400_BAD_REQUEST

    def test_business_error_custom_code(self):
        from core.exceptions import BusinessError

        error = BusinessError("Insufficient funds", code=402)
        assert error.code == 402

    def test_conflict_error(self):
        from core.exceptions import ConflictError

        error = ConflictError("Name already exists", resource_type="Portfolio", resource_id="MyPortfolio")
        assert error.status_code == status.HTTP_409_CONFLICT
        assert error.details["resource_type"] == "Portfolio"
        assert error.details["resource_id"] == "MyPortfolio"

    def test_unauthorized_error(self):
        from core.exceptions import UnauthorizedError

        error = UnauthorizedError("Invalid token")
        assert error.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthorized_error_default_message(self):
        from core.exceptions import UnauthorizedError

        error = UnauthorizedError()
        assert "Authentication required" in error.message

    def test_forbidden_error(self):
        from core.exceptions import ForbiddenError

        error = ForbiddenError("Access denied")
        assert error.status_code == status.HTTP_403_FORBIDDEN

    def test_forbidden_error_default_message(self):
        from core.exceptions import ForbiddenError

        error = ForbiddenError()
        assert "Access forbidden" in error.message

    def test_service_unavailable_error(self):
        from core.exceptions import ServiceUnavailableError

        error = ServiceUnavailableError("Database connection failed", service="MySQL")
        assert error.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert error.details["service"] == "MySQL"

    def test_rate_limit_error(self):
        from core.exceptions import RateLimitError

        error = RateLimitError("Too many requests", retry_after=60)
        assert error.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert error.details["retry_after"] == 60

    def test_rate_limit_error_defaults(self):
        from core.exceptions import RateLimitError

        error = RateLimitError()
        assert error.code == 429
        assert error.details == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
