# Upstream: api.api.data._record_sync_result (POST /api/v1/data/sync 的状态记录)
# Downstream: DataSyncRecordService.record_complete / record_fail
# Role: 验证同步状态决策——0 条处理（可疑空）应报 partial 而非 success (#5893)
"""
sync 状态决策测试

#5893: _record_sync_result 把"无法判断"和"0 条处理"都当 success。
DataSyncResult.is_successful() 只判 has_errors 不看 records_processed=0，
导致源无数据的同步被误报成功。本测试锁定状态决策语义：

  processed>0 无错误        -> success（真实成功）
  processed=0 & skipped>0   -> success（幂等：数据已存在被跳过）
  processed=0 & skipped=0   -> partial（可疑空：源无数据）
  records_failed>0 / errors -> partial（有失败）
"""
import time
import pytest
from unittest.mock import MagicMock


def make_dsr(processed=0, added=0, updated=0, skipped=0, failed=0, errors=None):
    """构造真实 DataSyncResult（验证 is_successful 真实语义，非 mock）"""
    from ginkgo.libs.data.results.data_sync_result import DataSyncResult
    return DataSyncResult(
        entity_type="bars",
        entity_identifier="000001.SZ",
        sync_range=(None, None),
        records_processed=processed,
        records_added=added,
        records_updated=updated,
        records_skipped=skipped,
        records_failed=failed,
        sync_duration=0.1,
        is_idempotent=True,
        sync_strategy="incremental",
        errors=errors or [],
    )


class TestRecordSyncResultStatus:
    """#5893: sync 状态决策——区分真实成功 / 幂等 / 可疑空 / 失败"""

    @pytest.mark.unit
    def test_zero_processed_zero_skipped_reports_partial(self):
        """0 条处理且无幂等跳过 -> partial（可疑空，非 success）

        RED：当前 L534 用 dsr.is_successful()，0 条无错误 -> True -> success。
        修复后应区分 skipped：processed=0 & skipped=0 -> partial。
        """
        from api.data import _record_sync_result
        from ginkgo.data.services.base_service import ServiceResult

        svc = MagicMock()
        result = ServiceResult.success(data=make_dsr(processed=0, skipped=0))

        _record_sync_result(svc, "uuid-1", result, time.time())

        svc.record_complete.assert_called_once()
        assert svc.record_complete.call_args.kwargs["status"] == "partial", (
            "0 条处理且无幂等跳过应报 partial，而非 success"
        )

    @pytest.mark.unit
    def test_processed_records_reports_success(self):
        """回归：有处理记录且无错误 -> success（真实成功）"""
        from api.data import _record_sync_result
        from ginkgo.data.services.base_service import ServiceResult

        svc = MagicMock()
        result = ServiceResult.success(data=make_dsr(processed=10, added=10))

        _record_sync_result(svc, "uuid-2", result, time.time())

        svc.record_complete.assert_called_once()
        assert svc.record_complete.call_args.kwargs["status"] == "success"

    @pytest.mark.unit
    def test_zero_processed_with_skipped_reports_success(self):
        """幂等正常：0 条处理但有跳过（数据已存在）-> success"""
        from api.data import _record_sync_result
        from ginkgo.data.services.base_service import ServiceResult

        svc = MagicMock()
        result = ServiceResult.success(data=make_dsr(processed=0, skipped=5))

        _record_sync_result(svc, "uuid-3", result, time.time())

        svc.record_complete.assert_called_once()
        assert svc.record_complete.call_args.kwargs["status"] == "success"

    @pytest.mark.unit
    def test_records_failed_reports_partial(self):
        """有失败记录 -> partial"""
        from api.data import _record_sync_result
        from ginkgo.data.services.base_service import ServiceResult

        svc = MagicMock()
        result = ServiceResult.success(data=make_dsr(processed=10, failed=3))

        _record_sync_result(svc, "uuid-4", result, time.time())

        svc.record_complete.assert_called_once()
        assert svc.record_complete.call_args.kwargs["status"] == "partial"

    @pytest.mark.unit
    def test_none_result_records_fail(self):
        """回归：result None -> record_fail（保护现有行为）"""
        from api.data import _record_sync_result

        svc = MagicMock()
        _record_sync_result(svc, "uuid-5", None, time.time())

        svc.record_fail.assert_called_once()
        svc.record_complete.assert_not_called()

    @pytest.mark.unit
    def test_result_data_without_stats_reports_partial(self):
        """result.data 无 records_processed 统计 -> partial（非 success）

        RED：当前 L546 fallback 无条件 status="success"。返回成功但无标准
        DataSyncResult 统计时，无法判断产出，应报 partial。
        """
        from api.data import _record_sync_result
        from ginkgo.data.services.base_service import ServiceResult

        svc = MagicMock()
        # data 为不透明对象，无 records_processed 属性 -> 走 L546 fallback
        result = ServiceResult.success(data="opaque-payload-without-stats")

        _record_sync_result(svc, "uuid-6", result, time.time())

        svc.record_complete.assert_called_once()
        assert svc.record_complete.call_args.kwargs["status"] == "partial", (
            "无统计信息时无法判断产出，应报 partial 而非乐观 success"
        )

    @pytest.mark.unit
    def test_result_without_is_success_reports_partial(self):
        """result 无 is_success 方法 -> partial（回归保护 L550）

        返回值不规范（非 ServiceResult，无成败判断接口）时，无法判断成败，
        应报 partial 而非乐观 success。
        """
        from api.data import _record_sync_result

        svc = MagicMock()
        result = {"raw": "not-a-service-result"}  # 无 is_success 方法

        _record_sync_result(svc, "uuid-7", result, time.time())

        svc.record_complete.assert_called_once()
        assert svc.record_complete.call_args.kwargs["status"] == "partial"
