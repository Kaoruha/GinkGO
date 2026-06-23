# Issue: #5867 Walk Forward/Sensitivity 端点 404
# Upstream: api.api.validation.walk_forward / sensitivity
# Downstream: ValidationService.walk_forward / sensitivity
# Role: 端点 wiring 契约——参数透传到 service + error 传播为 BusinessError

"""
#5867 端点契约测试

验证 walk-forward / sensitivity 端点：
1. 将 Request 字段正确透传给 ValidationService
2. service 返回 error 时传播为 BusinessError
3. service 返回 success 时包装为 ok(data=...)
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock


def run_async(coro):
    return asyncio.run(coro)


class TestWalkForwardEndpoint:
    """walk-forward 端点契约"""

    def test_success_passes_params_and_returns_data(self):
        from api.validation import walk_forward, WalkForwardRequest
        from ginkgo.data.services.base_service import ServiceResult

        mock_svc = MagicMock()
        mock_svc.walk_forward.return_value = ServiceResult.success(
            data={"n_folds": 3, "folds": [], "avg_train_return": 0.1, "avg_test_return": 0.05, "overfit_score": 0.05}
        )
        req = WalkForwardRequest(task_id="t-1", portfolio_id="p-1", n_folds=3, train_ratio=0.7, window_type="rolling")

        with patch("api.validation.get_validation_service", return_value=mock_svc):
            resp = run_async(walk_forward(req))

        # 参数透传到 service
        kwargs = mock_svc.walk_forward.call_args.kwargs
        assert kwargs["task_id"] == "t-1" and kwargs["portfolio_id"] == "p-1"
        assert kwargs["n_folds"] == 3 and kwargs["train_ratio"] == 0.7
        assert kwargs["window_type"] == "rolling"
        # response 包装
        assert resp["data"]["n_folds"] == 3

    def test_error_propagates_as_business_error(self):
        from api.validation import walk_forward, WalkForwardRequest
        from ginkgo.data.services.base_service import ServiceResult
        from core.exceptions import BusinessError

        mock_svc = MagicMock()
        mock_svc.walk_forward.return_value = ServiceResult.error("数据不足：net_value 记录少于 10 条")
        req = WalkForwardRequest(task_id="t-1", portfolio_id="p-1")

        with patch("api.validation.get_validation_service", return_value=mock_svc):
            with pytest.raises(BusinessError):
                run_async(walk_forward(req))


class TestSensitivityEndpoint:
    """sensitivity 端点契约"""

    def test_success_passes_params_and_returns_data(self):
        from api.validation import sensitivity, SensitivityRequest
        from ginkgo.data.services.base_service import ServiceResult

        mock_svc = MagicMock()
        mock_svc.sensitivity.return_value = ServiceResult.success(
            data={"param_name": "n_segments", "records": [{"param_value": 2}], "sensitivity_score": 0.12}
        )
        req = SensitivityRequest(task_id="t-1", portfolio_id="p-1", param_name="n_segments", param_values=["2", "4", "8"])

        with patch("api.validation.get_validation_service", return_value=mock_svc):
            resp = run_async(sensitivity(req))

        kwargs = mock_svc.sensitivity.call_args.kwargs
        assert kwargs["param_name"] == "n_segments"
        assert kwargs["param_values"] == ["2", "4", "8"]
        assert resp["data"]["sensitivity_score"] == 0.12

    def test_error_propagates_as_business_error(self):
        from api.validation import sensitivity, SensitivityRequest
        from ginkgo.data.services.base_service import ServiceResult
        from core.exceptions import BusinessError

        mock_svc = MagicMock()
        mock_svc.sensitivity.return_value = ServiceResult.error("不支持的 param_name: foo")
        req = SensitivityRequest(task_id="t-1", portfolio_id="p-1", param_values=["2"])

        with patch("api.validation.get_validation_service", return_value=mock_svc):
            with pytest.raises(BusinessError):
                run_async(sensitivity(req))
