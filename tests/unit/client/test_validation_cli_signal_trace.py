"""
validate --show-trace 行情获取链路测试 (#5307)

根因：`_run_signal_tracing` 创建的 SimpleDataFeeder 仅暴露 bars/get_bars，
缺少 feeder 契约要求的 `bar_service` 属性，导致 StrategyDataMixin.get_bars_cached
走 hasattr 守卫失败 → INFO + return [] → 策略 0 信号。

本测试验证 SimpleDataFeeder 遵守 feeder 契约（暴露 bar_service，
.get() 返回 ServiceResult 兼容结构），使追踪环境下 get_bars_cached 能取到行情。
"""
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock

import pytest


def _make_bar(code: str = "000001.SZ", timestamp=None, close: float = 10.0):
    """构造 MBar model mock（对齐 src/ginkgo/data/models/model_bar.py 字段）"""
    bar = MagicMock()
    bar.code = code
    bar.timestamp = timestamp or datetime(2026, 1, 1)
    bar.open = close
    bar.high = close
    bar.low = close
    bar.close = close
    bar.volume = 1000
    return bar


class TestSimpleDataFeederBarServiceContract:
    """SimpleDataFeeder 必须遵守 feeder 契约暴露 bar_service (#5307)"""

    def test_feeder_exposes_bar_service_attribute(self):
        """SimpleDataFeeder 实例应暴露 bar_service 属性（feeder 契约）"""
        from ginkgo.client.validation_cli import SimpleDataFeeder

        feeder = SimpleDataFeeder([_make_bar()])
        assert hasattr(feeder, "bar_service"), "SimpleDataFeeder 缺 bar_service 属性"

    def test_bar_service_get_returns_service_result_with_data(self):
        """bar_service.get(code) 返回 ServiceResult 兼容结构 (success=True, data=[bars])"""
        from ginkgo.client.validation_cli import SimpleDataFeeder

        bars = [
            _make_bar(timestamp=datetime(2026, 1, 1)),
            _make_bar(timestamp=datetime(2026, 1, 2)),
        ]
        feeder = SimpleDataFeeder(bars)
        result = feeder.bar_service.get(code="000001.SZ")

        assert result.success is True
        assert len(result.data) == 2

    def test_bar_service_get_filters_by_date_range(self):
        """bar_service.get 支持 start_date/end_date 过滤（mixin 传 date 对象）"""
        from ginkgo.client.validation_cli import SimpleDataFeeder

        bars = [
            _make_bar(timestamp=datetime(2026, 1, 1)),
            _make_bar(timestamp=datetime(2026, 2, 1)),
            _make_bar(timestamp=datetime(2026, 3, 1)),
        ]
        feeder = SimpleDataFeeder(bars)
        result = feeder.bar_service.get(
            code="000001.SZ",
            start_date=date(2026, 1, 15),
            end_date=date(2026, 2, 15),
        )

        assert result.success is True
        assert len(result.data) == 1

    def test_bar_service_get_unknown_code_returns_empty_success(self):
        """查未加载的 code 返回 success=True 但 data 空（graceful，不崩）"""
        from ginkgo.client.validation_cli import SimpleDataFeeder

        feeder = SimpleDataFeeder([_make_bar(code="000001.SZ")])
        result = feeder.bar_service.get(code="999999.SZ")

        assert result.success is True
        assert result.data == []

    def test_feeder_accepts_time_controller(self):
        """SimpleDataFeeder 可注入 time_controller（追踪按事件时间取数，非 wall clock）"""
        from ginkgo.client.validation_cli import SimpleDataFeeder

        time_controller = MagicMock()
        time_controller.now.return_value = datetime(2026, 1, 5)
        feeder = SimpleDataFeeder([_make_bar()], time_controller=time_controller)

        assert feeder.time_controller is time_controller


class TestGetBarsCachedEndToEnd:
    """端到端：SimpleDataFeeder + StrategyDataMixin → get_bars_cached 取到数据 (#5307)"""

    def test_get_bars_cached_returns_data_via_simple_feeder(self, monkeypatch):
        """修复后 get_bars_cached 不再走 bar_service 缺失的 0 信号分支"""
        from ginkgo.client.validation_cli import SimpleDataFeeder
        from ginkgo.trading.interfaces.mixins import strategy_data_mixin as mixin_mod
        from ginkgo.trading.interfaces.mixins.strategy_data_mixin import StrategyDataMixin

        # 追踪环境：事件时间作为 time_controller，避免 mixin 退回 wall clock 误过滤历史 bar
        event_time = datetime(2026, 1, 10)
        bars = [_make_bar(timestamp=datetime(2026, 1, 1) + timedelta(days=i)) for i in range(10)]
        time_controller = MagicMock()
        time_controller.now.return_value = event_time

        class _TraceStrategy(StrategyDataMixin):
            pass

        strategy = _TraceStrategy()
        strategy.data_feeder = SimpleDataFeeder(bars, time_controller=time_controller)

        # 绕开 model→entity 转换（不在 #5307 修复范围，BarMapper 已被回测/实盘覆盖）
        monkeypatch.setattr(
            mixin_mod.BarMapper, "from_models", staticmethod(lambda models: list(models))
        )

        result = strategy.get_bars_cached("000001.SZ", count=10)
        assert len(result) > 0, "get_bars_cached 在 SimpleDataFeeder 下返回空（#5307 根因未修）"

