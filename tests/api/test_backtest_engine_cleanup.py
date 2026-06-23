"""
#5779: DELETE /engines/stale 僵尸引擎清理端点测试。

直调端点函数（避开 app 启动 / root main.py 遮蔽），
patch get_engine_service 注入 mock。
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock

from ginkgo.data.services.base_service import ServiceResult
from core.exceptions import BusinessError


class TestCleanupStaleEnginesEndpoint:
    """DELETE /engines/stale 端点契约。"""

    def test_dry_run_returns_count_and_wires_is_live(self):
        """dry_run=True 透传 service，is_live=False 映射 0（回测）。"""
        from api.backtest import cleanup_stale_engines

        mock_service = MagicMock()
        mock_service.cleanup_stale_engines.return_value = ServiceResult.success(
            data={"stale_count": 5, "stale_uuids": ["z1", "z2"], "dry_run": True},
            message="DRY RUN: 5",
        )
        with patch("api.backtest.get_engine_service", return_value=mock_service):
            result = asyncio.run(cleanup_stale_engines(is_live=False, dry_run=True))

        mock_service.cleanup_stale_engines.assert_called_once_with(is_live=0, dry_run=True)
        assert result["code"] == 0
        assert result["data"]["stale_count"] == 5
        assert result["data"]["dry_run"] is True

    def test_service_error_raises_business_error(self):
        """service 返回 error 时端点抛 BusinessError（不静默吞）。"""
        from api.backtest import cleanup_stale_engines

        mock_service = MagicMock()
        mock_service.cleanup_stale_engines.return_value = ServiceResult.error("DB down")
        with patch("api.backtest.get_engine_service", return_value=mock_service):
            with pytest.raises(BusinessError):
                asyncio.run(cleanup_stale_engines(is_live=False, dry_run=False))
