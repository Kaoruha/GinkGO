# Issue: #5654 — GET /api/v1/data/bars 无 order 参数，用户无法控制排序
# Upstream: api.api.data.get_bars
# Downstream: BarService.get(order_by, desc_order)
# Role: 验证 get_bars 暴露 order 参数并正确透传 service.desc_order

"""
data/bars order 参数测试

真实场景：bars endpoint 硬编码 desc_order=True，未暴露 order 参数。
用户传 order=desc 被忽略，无法显式控制 asc/desc。

修复：get_bars 加 order 参数（默认 desc），desc_order=(order == "desc")。
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


def run_async(coro):
    return asyncio.run(coro)


def make_mock_result(data=None, success=True):
    result = MagicMock()
    result.is_success.return_value = success
    result.data = data
    return result


def make_bar(uuid="b1", code="000001.SZ"):
    """模拟真实 MBar（有 uuid/code/timestamp/open 等，无 to_entities）"""
    bar = MagicMock()
    bar.uuid = uuid
    bar.code = code
    bar.timestamp = datetime(2025, 1, 1)
    bar.open = 1.0
    bar.high = 2.0
    bar.low = 0.5
    bar.close = 1.5
    bar.volume = 100.0
    bar.amount = 200.0
    del bar.to_entities
    return bar


class TestGetBarsOrderParam:
    """#5654: get_bars 暴露 order 参数并透传 service.desc_order"""

    def test_order_asc_flips_desc_order_false(self):
        """order=asc → service.get(desc_order=False) 升序"""
        mock_service = MagicMock()
        mock_service.get.return_value = make_mock_result(data=[make_bar()])

        from api.data import get_bars

        with patch("api.data.get_bar_service", return_value=mock_service):
            result = run_async(get_bars(order="asc"))

        assert result.get("code") == 0
        _, kwargs = mock_service.get.call_args
        assert kwargs.get("desc_order") is False

    def test_order_desc_keeps_desc_order_true(self):
        """order=desc → service.get(desc_order=True) 降序（最新在前）"""
        mock_service = MagicMock()
        mock_service.get.return_value = make_mock_result(data=[make_bar()])

        from api.data import get_bars

        with patch("api.data.get_bar_service", return_value=mock_service):
            result = run_async(get_bars(order="desc"))

        assert result.get("code") == 0
        _, kwargs = mock_service.get.call_args
        assert kwargs.get("desc_order") is True

    def test_default_order_is_desc(self):
        """未传 order → 默认 desc（最新在前）"""
        mock_service = MagicMock()
        mock_service.get.return_value = make_mock_result(data=[make_bar()])

        from api.data import get_bars

        with patch("api.data.get_bar_service", return_value=mock_service):
            run_async(get_bars())

        _, kwargs = mock_service.get.call_args
        assert kwargs.get("desc_order") is True

    def test_invalid_order_returns_400(self):
        """order=invalid → 400（清晰错误，不静默）"""
        mock_service = MagicMock()
        mock_service.get.return_value = make_mock_result(data=[make_bar()])

        from api.data import get_bars
        from fastapi import HTTPException

        with patch("api.data.get_bar_service", return_value=mock_service):
            with pytest.raises(HTTPException) as exc_info:
                run_async(get_bars(order="invalid"))

        assert exc_info.value.status_code == 400
