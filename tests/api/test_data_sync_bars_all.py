# Upstream: api.api.data.sync_data (POST /api/v1/data/sync)
# Downstream: StockinfoService.list_all_codes, BarService.sync_smart, DataSyncRecordService
# Role: 验证 bars sync codes=['all'] 展开为 stockinfo 全表批量同步 (#5866 AC1)
"""
sync_data bars codes=['all'] 展开测试

#5866: bars sync 端点只接受显式 codes 数组，缺一键同步全表机制。
用户须逐只 POST {"type":"bars","codes":["000002.SZ"]}，50 只股票 62% 无数据。
本测试锁定：codes=["all"] 展开为 stockinfo 全表 code，逐个 sync_smart。
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock

from fastapi import HTTPException


def run_async(coro):
    return asyncio.run(coro)


def make_ok_result():
    r = MagicMock()
    r.is_success.return_value = True
    r.success = True
    r.message = "ok"
    r.data = None
    r.metadata = {}
    return r


def make_sync_record_mock():
    svc = MagicMock()
    rec = MagicMock()
    rec.is_success.return_value = True
    rec.data = {"uuid": "rec-uuid-1"}
    svc.record_start.return_value = rec
    return svc


def make_codes_result(codes):
    """构造 list_all_codes 的 ServiceResult 替身"""
    r = MagicMock()
    r.is_success.return_value = True
    r.success = True
    r.data = codes
    return r


class TestSyncBarsCodesAll:
    """#5866 AC1: bars sync codes=['all'] 展开为 stockinfo 全表"""

    @pytest.mark.unit
    def test_codes_all_expands_to_all_stockinfo_codes(self):
        """codes=['all'] 展开为 stockinfo 全表，对每个 code 调一次 sync_smart

        RED: 当前 codes=['all'] 当字面 'all' 传 sync_smart('all')，
        不会展开为 stockinfo 全表 code 列表。
        """
        from api.data import sync_data, DataUpdateRequest

        mock_bar_svc = MagicMock()
        mock_bar_svc.sync_smart.return_value = make_ok_result()

        mock_stockinfo_svc = MagicMock()
        mock_stockinfo_svc.list_all_codes.return_value = make_codes_result(
            ["000001.SZ", "000002.SZ", "000026.SZ"]
        )

        request = DataUpdateRequest(type="bars", codes=["all"])

        with patch("api.data.get_bar_service", return_value=mock_bar_svc), \
                patch("api.data.get_stockinfo_service", return_value=mock_stockinfo_svc), \
                patch("api.data.get_sync_record_service", return_value=make_sync_record_mock()):
            try:
                run_async(sync_data(request))
            except HTTPException as e:
                pytest.fail(f"codes=['all'] 应展开并路由成功，却抛 HTTPException: {e.detail}")

        assert mock_bar_svc.sync_smart.call_count == 3
        called_codes = [call.args[0] for call in mock_bar_svc.sync_smart.call_args_list]
        assert called_codes == ["000001.SZ", "000002.SZ", "000026.SZ"]

    @pytest.mark.unit
    def test_codes_all_empty_stockinfo_raises_helpful_error(self):
        """codes=['all'] 但 stockinfo 表空时报 400，提示先 sync stockinfo"""
        from api.data import sync_data, DataUpdateRequest

        mock_stockinfo_svc = MagicMock()
        mock_stockinfo_svc.list_all_codes.return_value = make_codes_result([])

        request = DataUpdateRequest(type="bars", codes=["all"])

        with patch("api.data.get_bar_service"), \
                patch("api.data.get_stockinfo_service", return_value=mock_stockinfo_svc), \
                patch("api.data.get_sync_record_service", return_value=make_sync_record_mock()):
            with pytest.raises(HTTPException) as exc:
                run_async(sync_data(request))

        assert exc.value.status_code == 400
        assert "stockinfo" in str(exc.value.detail).lower()
