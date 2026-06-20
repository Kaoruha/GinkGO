"""
Tests for POST /api/v1/signals/{signal_id}/report (#6150 回报录入).

#6150 半手动实盘：用户收到信号通知→手动执行→回报实际成交价/量。
端点职责：把回报转发给 signal_tracking_service.set_confirmed（API→Service 单向，
端点零业务逻辑）。set_confirmed 的 actual_* 写入 + 时间偏差计算已在 service 层测试覆盖。
"""
import pytest
from unittest.mock import MagicMock
from types import SimpleNamespace


class TestReportSignalExecution:
    """回报端点：转发用户实际执行结果到 signal_tracking_service。"""

    def test_delegates_to_set_confirmed_with_actual_values(self):
        from api.signals import report_signal_execution, SignalExecutionReport

        mock_service = MagicMock()
        # set_confirmed 返回成功结果（actual_* 已写入由 service 层保证）
        mock_service.set_confirmed.return_value = SimpleNamespace(
            is_success=lambda: True,
            data=SimpleNamespace(signal_id="sig-1"),
        )
        report = SignalExecutionReport(actual_price=10.5, actual_volume=1000)

        report_signal_execution("sig-1", report, service=mock_service)

        mock_service.set_confirmed.assert_called_once_with(
            signal_id="sig-1",
            actual_price=10.5,
            actual_volume=1000,
            execution_timestamp=None,
        )

    def test_not_found_raises_404(self):
        """service 找不到 tracker 时，端点必须返回 404，而非 200 假成功。"""
        from fastapi import HTTPException
        from api.signals import report_signal_execution, SignalExecutionReport

        mock_service = MagicMock()
        mock_service.set_confirmed.return_value = SimpleNamespace(
            is_success=lambda: False,
            error="Signal tracking record not found: sig-x",
        )
        report = SignalExecutionReport(actual_price=10.5, actual_volume=1000)

        with pytest.raises(HTTPException) as exc:
            report_signal_execution("sig-x", report, service=mock_service)
        assert exc.value.status_code == 404


class TestComputeDeviation:
    """#6150 "轻"：偏差 = 预期 − 实际，只算+记录，不回写仓位。

    set_confirmed 已算时间偏差(time_delay_seconds)；这里补价格/数量偏差，
    作为半手动实盘的"对账替代"——用户对照预期手动执行，端点算出差异供排查。
    """

    def test_returns_expected_minus_actual(self):
        from api.signals import _compute_deviation

        tracker = SimpleNamespace(
            expected_price=10.5,
            actual_price=10.3,
            expected_volume=1000,
            actual_volume=980,
        )
        dev = _compute_deviation(tracker)
        assert dev["price_deviation"] == pytest.approx(0.2)
        assert dev["volume_deviation"] == 20

    def test_missing_fields_yield_none(self):
        """预期值缺失时不能崩，返回 None（信号可能未带预期价/量）。"""
        from api.signals import _compute_deviation

        tracker = SimpleNamespace(actual_price=10.3, actual_volume=980)
        dev = _compute_deviation(tracker)
        assert dev["price_deviation"] is None
        assert dev["volume_deviation"] is None
