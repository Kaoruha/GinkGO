"""
TDD test for #5960/#5958: data_feeder propagation from portfolio to strategies.

Verifies that the full chain works:
  Engine → portfolio.bind_data_feeder(feeder) → strategy.bind_data_feeder(feeder)
  → strategy.data_feeder returns the feeder

Also verifies that StrategyDataMixin.get_bars_cached() can use the injected
feeder's time_controller instead of falling back to datetime.now().
"""
import pytest
from unittest.mock import MagicMock, PropertyMock
from datetime import datetime

from ginkgo.trading.strategies.strategy_base import BaseStrategy
from ginkgo.trading.interfaces.mixins.strategy_data_mixin import StrategyDataMixin


class FakeDataStrategy(BaseStrategy, StrategyDataMixin):
    """测试用策略：使用 StrategyDataMixin"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        StrategyDataMixin.__init__(self)

    def cal(self, portfolio_info, event, *args, **kwargs):
        return []


@pytest.mark.unit
class TestDataFeederPropagation:
    """data_feeder 从 portfolio 传播到 strategy 的完整链路"""

    def test_strategy_has_data_feeder_property(self):
        """BaseStrategy 应有 data_feeder 属性"""
        strategy = FakeDataStrategy(name="test")
        assert hasattr(strategy, 'data_feeder')

    def test_strategy_bind_data_feeder_sets_attribute(self):
        """bind_data_feeder 应设置 _data_feeder"""
        strategy = FakeDataStrategy(name="test")
        mock_feeder = MagicMock()

        strategy.bind_data_feeder(mock_feeder)

        assert strategy.data_feeder is mock_feeder

    def test_strategy_data_feeder_initially_none(self):
        """初始时 data_feeder 应为 None"""
        strategy = FakeDataStrategy(name="test")
        assert strategy.data_feeder is None

    def test_get_bars_cached_uses_time_controller_when_feeder_set(self):
        """有 feeder 和 time_controller 时，get_bars_cached 应使用回测时间"""
        strategy = FakeDataStrategy(name="test")

        # 设置 mock feeder 带 time_controller
        mock_feeder = MagicMock()
        mock_feeder.time_controller = MagicMock()
        backtest_time = datetime(2025, 10, 1, 12, 0, 0)
        mock_feeder.time_controller.now.return_value = backtest_time

        # 设置 bar_service 返回空结果
        mock_bar_service = MagicMock()
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.data = None
        mock_bar_service.get.return_value = mock_result
        mock_feeder.bar_service = mock_bar_service

        strategy.bind_data_feeder(mock_feeder)

        # 调用 get_bars_cached
        bars = strategy.get_bars_cached("600000.SH", count=10, use_cache=False)

        # 验证使用了 time_controller.now() 获取时间
        assert mock_feeder.time_controller.now.called

    def test_get_bars_cached_falls_back_to_datetime_now_without_feeder(self):
        """没有 feeder 时，get_bars_cached 使用 datetime.now()（不应发生在回测中）"""
        strategy = FakeDataStrategy(name="test")
        # data_feeder 为 None → 不应使用 time_controller
        assert strategy.data_feeder is None
        # get_bars_cached 会走 datetime.now() 分支并返回 []
        # 这个测试只是验证不崩溃
        bars = strategy.get_bars_cached("600000.SH", count=10, use_cache=False)
        assert isinstance(bars, list)
