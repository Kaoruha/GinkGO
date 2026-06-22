"""#5450: _record_sync_result API 层透传测试。

service 层 (PR #6270) 对"已是最新"返回 `ServiceResult.success(message=...,
data=DataSyncResult(metadata reason=already_up_to_date))`。API 层 `_record_sync_result`
须读 `dsr.metadata.reason` 并透传 `result.message`，否则 sync_history 记
`status=partial/proc=0` 无说明 —— 验收标准 2（端到端 status message explains why
0 records）未满足。

按 [[arch_api_test_import_collapse]]：conftest `api_modules` 是 autouse session
fixture，collection 阶段 sys.path 未注入，须函数体内 `import api.data`。
"""
from types import SimpleNamespace
from unittest.mock import MagicMock


def _make_dsr(
    records_processed=0,
    records_added=0,
    records_updated=0,
    records_failed=0,
    records_skipped=0,
    metadata=None,
    sync_strategy="smart",
):
    """构造 DataSyncResult 替身（只覆盖 _record_sync_result 读取的属性）"""
    return SimpleNamespace(
        records_processed=records_processed,
        records_added=records_added,
        records_updated=records_updated,
        records_failed=records_failed,
        records_skipped=records_skipped,
        is_successful=lambda: True,
        metadata=metadata if metadata is not None else {},
        sync_strategy=sync_strategy,
    )


def test_record_sync_result_already_up_to_date_status_success_with_message(api_modules):
    """#5450: '已是最新'结果 → status=success（非 partial）+ 说明透传 error_message"""
    import api.data as data_mod
    from ginkgo.data.services.base_service import ServiceResult

    dsr = _make_dsr(metadata={"reason": "already_up_to_date"})
    result = ServiceResult.success(data=dsr, message="000001.SZ 数据已是最新，无需同步")

    sync_svc = MagicMock()
    data_mod._record_sync_result(sync_svc, "rec-uuid", result, started_at=0.0)

    sync_svc.record_complete.assert_called_once()
    kwargs = sync_svc.record_complete.call_args.kwargs
    assert kwargs["status"] == "success", (
        f"已是最新应为 success 非 partial，实际 {kwargs['status']}"
    )
    assert kwargs["error_message"] == "000001.SZ 数据已是最新，无需同步", "说明须透传到 error_message"
    assert kwargs["records_processed"] == 0


def test_record_sync_result_normal_success_no_message_pollution(api_modules):
    """#5450 回归：正常成功 (records_processed>0, 无 reason) → error_message 不被污染"""
    import api.data as data_mod
    from ginkgo.data.services.base_service import ServiceResult

    dsr = _make_dsr(records_processed=5, records_added=5, metadata={})
    result = ServiceResult.success(data=dsr, message="ok")

    sync_svc = MagicMock()
    data_mod._record_sync_result(sync_svc, "rec-uuid", result, started_at=0.0)

    kwargs = sync_svc.record_complete.call_args.kwargs
    assert kwargs["status"] == "success"
    assert not kwargs.get("error_message"), (
        f"正常成功不应写 error_message，实际 {kwargs.get('error_message')}"
    )
