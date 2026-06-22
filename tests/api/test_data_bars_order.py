# #5652 — data/bars order 参数被忽略
"""
验证 GET /api/v1/data/bars?order=asc|desc 映射到 bar_service.get(desc_order)。

端点原签名 (api/api/data.py get_bars) 无 order/sort 参数，
FastAPI 静默丢弃未知 query 参数 → ?order=desc 无效，用户无法控制排序方向。
"""
import pytest
from unittest.mock import MagicMock, patch


def _mock_empty_result():
    """构造 is_success=False 的 mock result，让端点走空结果早退，
    只为捕获 service.get 的调用参数（desc_order）。"""
    mock_result = MagicMock()
    mock_result.is_success.return_value = False
    mock_result.data = None
    return mock_result


class TestGetBarsOrderParam:
    """get_bars 应把 order 参数映射到 service.get(desc_order=...)"""

    @pytest.mark.asyncio
    @patch("api.data.get_bar_service")
    async def test_order_asc_maps_to_desc_order_false(self, mock_get_svc):
        """order=asc → service.get(desc_order=False)（升序）"""
        from api.data import get_bars

        mock_svc = MagicMock()
        mock_svc.get.return_value = _mock_empty_result()
        mock_get_svc.return_value = mock_svc

        await get_bars(code="000001.SZ", order="asc")

        _, kwargs = mock_svc.get.call_args
        assert kwargs.get("desc_order") is False, "order=asc 应映射为 desc_order=False"

    @pytest.mark.asyncio
    @patch("api.data.get_bar_service")
    async def test_order_desc_maps_to_desc_order_true(self, mock_get_svc):
        """order=desc → service.get(desc_order=True)（降序，最新在前）"""
        from api.data import get_bars

        mock_svc = MagicMock()
        mock_svc.get.return_value = _mock_empty_result()
        mock_get_svc.return_value = mock_svc

        await get_bars(code="000001.SZ", order="desc")

        _, kwargs = mock_svc.get.call_args
        assert kwargs.get("desc_order") is True, "order=desc 应映射为 desc_order=True"

    @pytest.mark.asyncio
    @patch("api.data.get_bar_service")
    async def test_no_order_defaults_to_desc(self, mock_get_svc):
        """不传 order → 默认降序（最新在前），符合 #5652 验收点2"""
        from api.data import get_bars

        mock_svc = MagicMock()
        mock_svc.get.return_value = _mock_empty_result()
        mock_get_svc.return_value = mock_svc

        await get_bars(code="000001.SZ")

        _, kwargs = mock_svc.get.call_args
        assert kwargs.get("desc_order") is True, "默认应降序（desc_order=True）"
