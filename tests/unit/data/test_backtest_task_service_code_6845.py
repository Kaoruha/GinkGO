"""#6845: BacktestTaskService.update_status 返回 code（方案B 契约级区分）。

让 progress_tracker._write_status_to_db 能据 code 区分：
- NOT_FOUND：task 未预建，预期容许（progress_tracker 转为 success 容错，body: 算预期容许）
- UPDATE_FAILED：真实 DB 故障（progress_tracker 传播 error，可见不撒谎）
- INVALID_STATUS：参数非法

向后兼容：调用方不读 code，新增字段不影响既有调用。
"""
from unittest.mock import MagicMock

import pytest

from ginkgo.data.services.backtest_task_service import BacktestTaskService


def _mk_svc(crud_mock) -> BacktestTaskService:
    """跳过 __init__ 的容器装配，仅注入 _crud_repo（update_status 唯一依赖）。"""
    svc = BacktestTaskService.__new__(BacktestTaskService)
    svc._crud_repo = crud_mock
    return svc


@pytest.mark.tdd
class TestUpdateStatusReturnsCode_6845:
    def test_not_found_returns_code(self):
        """task 不存在 → code=NOT_FOUND（供 progress_tracker 容错判定）。"""
        crud = MagicMock()
        crud.get_by_uuid.return_value = None
        crud.get_by_task_id.return_value = None
        svc = _mk_svc(crud)
        result = svc.update_status("nonexistent-uuid", "completed")
        assert not result.is_success()
        assert result.code == "NOT_FOUND", f"应返 NOT_FOUND，实际 {result.code!r}"

    def test_db_failure_returns_code(self):
        """DB 异常 → code=UPDATE_FAILED（供 progress_tracker 传播 error 判定）。"""
        crud = MagicMock()
        crud.get_by_uuid.side_effect = Exception("OperationalError: connection lost")
        svc = _mk_svc(crud)
        result = svc.update_status("some-uuid", "completed")
        assert not result.is_success()
        assert result.code == "UPDATE_FAILED", f"应返 UPDATE_FAILED，实际 {result.code!r}"

    def test_invalid_status_returns_code(self):
        """非法 status → code=INVALID_STATUS。"""
        svc = _mk_svc(MagicMock())
        result = svc.update_status("some-uuid", "bogus-status")
        assert not result.is_success()
        assert result.code == "INVALID_STATUS", f"应返 INVALID_STATUS，实际 {result.code!r}"
