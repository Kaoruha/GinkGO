# Upstream: api.api.data.sync_data (POST /api/v1/data/sync)
# Downstream: BarService.sync_smart, DataSyncRecordService
# Role: 验证 DataUpdateRequest 单数 code 字段归一化 + 明确错误提示 (#5784)
"""
sync_data 单数 code 字段归一化测试

#5784: 客户端发 {"type":"bars","code":"000001.SZ"}（单数字符串）报
'Codes are required'，因为 DataUpdateRequest 只认复数 codes(list)。
pydantic 默认 ignore extra，单数 code 被静默丢弃 → codes=None。
本测试锁定：单数 code 应归一化为 codes=[code] 并路由成功。
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock

from fastapi import HTTPException


def run_async(coro):
    return asyncio.run(coro)


def make_ok_result():
    """构造一个 is_success 的 ServiceResult 替身"""
    r = MagicMock()
    r.is_success.return_value = True
    r.success = True
    r.message = "ok"
    r.data = None
    r.metadata = {}
    return r


def make_sync_record_mock():
    """构造 DataSyncRecordService + record_start 返回值的替身"""
    svc = MagicMock()
    rec = MagicMock()
    rec.is_success.return_value = True
    rec.data = {"uuid": "rec-uuid-1"}
    svc.record_start.return_value = rec
    return svc


class TestSyncDataCodeField:
    """#5784: 单数 code 字段归一化"""

    @pytest.mark.unit
    def test_singular_code_normalized_to_codes_list(self):
        """单数 code (string) 应被接受并归一化为 codes=[code]，路由到 bars 分支

        RED: 当前 DataUpdateRequest 无 code 字段，pydantic ignore extra →
        codes=None → HTTPException(400, 'Codes are required for bars update')。
        """
        from api.data import sync_data, DataUpdateRequest

        mock_svc = MagicMock()
        mock_svc.sync_smart.return_value = make_ok_result()

        request = DataUpdateRequest(type="bars", code="000001.SZ")

        with patch("api.data.get_bar_service", return_value=mock_svc), \
                patch("api.data.get_sync_record_service", return_value=make_sync_record_mock()):
            try:
                run_async(sync_data(request))
            except HTTPException as e:
                pytest.fail(f"单数 code 应归一化后路由成功，却抛 HTTPException: {e.detail}")

        mock_svc.sync_smart.assert_called_once_with("000001.SZ")

    @pytest.mark.unit
    def test_missing_codes_error_message_names_field_and_format(self):
        """codes 与 code 都缺时，错误提示应明确字段名与格式

        RED: 当前提示 'Codes are required for bars update' 不含格式说明(list)。
        """
        from api.data import sync_data, DataUpdateRequest

        request = DataUpdateRequest(type="bars")  # 既无 code 也无 codes

        with patch("api.data.get_bar_service"), \
                patch("api.data.get_sync_record_service", return_value=make_sync_record_mock()):
            with pytest.raises(HTTPException) as exc:
                run_async(sync_data(request))

        assert exc.value.status_code == 400
        detail = str(exc.value.detail).lower()
        assert "codes" in detail          # 明确字段名
        assert "list" in detail           # 明确格式

    @pytest.mark.unit
    def test_singular_code_works_across_ticks_branch(self):
        """单数 code 归一化在 ticks 分支同样生效（validator 在 model 层，全分支受益）"""
        from api.data import sync_data, DataUpdateRequest

        mock_svc = MagicMock()
        mock_svc.sync_smart.return_value = make_ok_result()

        request = DataUpdateRequest(type="ticks", code="000001.SZ")

        with patch("api.data.get_tick_service", return_value=mock_svc), \
                patch("api.data.get_sync_record_service", return_value=make_sync_record_mock()):
            try:
                run_async(sync_data(request))
            except HTTPException as e:
                pytest.fail(f"ticks 分支单数 code 应路由成功，却抛 HTTPException: {e.detail}")

        mock_svc.sync_smart.assert_called_once_with("000001.SZ", start_date=None, end_date=None)
