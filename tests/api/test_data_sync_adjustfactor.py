# Upstream: api.api.data.sync_data (POST /api/v1/data/sync)
# Downstream: AdjustfactorService.sync_batch, DataSyncRecordService
# Role: 验证 sync_data 的 type 分发接受 adjustfactor/adjustfactors 双别名 (#5868)
"""
sync_data type 别名测试

#5868: GET /api/v1/data/adjustfactors 用复数，但 POST /sync 的 type 分发只认
单数 adjustfactor → 客户端传 adjustfactors 报 "Unsupported data type"。
本测试锁定 type 别名路由：单数/复数都应进入 adjustfactor 分支并调用 sync_batch。
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


class TestSyncDataAdjustfactorAlias:
    """#5868: type 单复数别名路由"""

    @pytest.mark.unit
    def test_plural_type_routes_to_adjustfactor_branch(self):
        """type='adjustfactors' (复数) 应路由到 adjustfactor 分支并调 sync_batch

        RED 状态：旧代码只匹配单数 'adjustfactor'，复数落到 else →
        HTTPException(400, 'Unsupported data type: adjustfactors')。
        """
        from api.data import sync_data, DataUpdateRequest

        mock_svc = MagicMock()
        mock_svc.sync_batch.return_value = make_ok_result()

        request = DataUpdateRequest(type="adjustfactors", codes=["000001.SZ"])

        with patch("api.data.get_adjustfactor_service", return_value=mock_svc), \
                patch("api.data.get_sync_record_service", return_value=make_sync_record_mock()):
            try:
                run_async(sync_data(request))
            except HTTPException as e:
                pytest.fail(
                    f"type='adjustfactors' 应回 adjustfactor 分支，却抛 HTTPException: {e.detail}"
                )

        mock_svc.sync_batch.assert_called_once_with(["000001.SZ"])

    @pytest.mark.unit
    def test_singular_type_still_routes(self):
        """type='adjustfactor' (单数) 回归保护：仍应调 sync_batch"""
        from api.data import sync_data, DataUpdateRequest

        mock_svc = MagicMock()
        mock_svc.sync_batch.return_value = make_ok_result()

        request = DataUpdateRequest(type="adjustfactor", codes=["000001.SZ"])

        with patch("api.data.get_adjustfactor_service", return_value=mock_svc), \
                patch("api.data.get_sync_record_service", return_value=make_sync_record_mock()):
            run_async(sync_data(request))

        mock_svc.sync_batch.assert_called_once_with(["000001.SZ"])

    @pytest.mark.unit
    def test_sync_success_chains_calculate_per_code(self):
        """收敛：API sync 成功后应衔接 calculate（与 task_timer/worker 主力路径对齐）

        sync 只落原始 adjustfactor，fore/back 占位 1.0，需 calculate 推导覆盖。
        当前 handler 仅 sync_batch 不调 calculate → 本测试红。
        """
        from api.data import sync_data, DataUpdateRequest

        mock_svc = MagicMock()
        mock_svc.sync_batch.return_value = make_ok_result()
        mock_svc.calculate.return_value = make_ok_result()

        request = DataUpdateRequest(type="adjustfactor", codes=["000001.SZ", "000002.SZ"])

        with patch("api.data.get_adjustfactor_service", return_value=mock_svc), \
                patch("api.data.get_sync_record_service", return_value=make_sync_record_mock()):
            run_async(sync_data(request))

        mock_svc.sync_batch.assert_called_once_with(["000001.SZ", "000002.SZ"])
        # sync 成功后，每个 code 都应衔接 calculate 推导 fore/back
        assert mock_svc.calculate.call_count == 2
        called_codes = {call.args[0] for call in mock_svc.calculate.call_args_list}
        assert called_codes == {"000001.SZ", "000002.SZ"}
