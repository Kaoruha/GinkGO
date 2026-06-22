"""
#4607: 提取 PortfolioBase._propagate_context(component) 助手方法。

背景：add_strategy / bind_selector / bind_sizer 各自重复同一套 4 步上下文传播：
  bind_portfolio → bind_engine → set_time_provider → bind_data_feeder
bind_engine 循环又对已注册组件重复 bind_portfolio + bind_engine 两步。
提取助手方法消除重复，使"新增一个 bind 步骤"只需改一处。
"""
from unittest.mock import MagicMock, patch

import pytest

from ginkgo.trading.bases.portfolio_base import PortfolioBase
from ginkgo.trading.portfolios import PortfolioT1Backtest
from ginkgo.trading.selectors import FixedSelector
from ginkgo.trading.sizers import FixedSizer
from ginkgo.trading.strategies.strategy_base import BaseStrategy


@pytest.fixture
def portfolio():
    return PortfolioT1Backtest()


class TestPropagateContextDelegation:
    """add_*/bind_* 必须委托给 _propagate_context（契约守护 #4607 重构不被回退）。"""

    def test_add_strategy_delegates(self, portfolio):
        s = BaseStrategy()
        with patch.object(portfolio, "_propagate_context") as spy:
            portfolio.add_strategy(s)
        spy.assert_called_once_with(s)

    def test_bind_selector_delegates(self, portfolio):
        sel = FixedSelector()
        with patch.object(portfolio, "_propagate_context") as spy:
            portfolio.bind_selector(sel)
        spy.assert_called_once_with(sel)

    def test_bind_sizer_delegates(self, portfolio):
        sizer = FixedSizer()
        with patch.object(portfolio, "_propagate_context") as spy:
            portfolio.bind_sizer(sizer)
        spy.assert_called_once_with(sizer)


class TestPropagateContext:
    """_propagate_context 把 portfolio 当前上下文同步给单个组件。"""

    def test_binds_all_four_contexts_when_populated(self, portfolio):
        engine, tp, feeder = MagicMock(), MagicMock(), MagicMock()
        portfolio._bound_engine = engine
        portfolio._time_provider = tp
        portfolio._data_feeder = feeder

        component = MagicMock()
        portfolio._propagate_context(component)

        component.bind_portfolio.assert_called_once_with(portfolio)
        component.bind_engine.assert_called_once_with(engine)
        component.set_time_provider.assert_called_once_with(tp)
        component.bind_data_feeder.assert_called_once_with(feeder)

    def test_skips_none_optional_contexts(self, portfolio):
        # engine/time_provider/data_feeder 均未设置（默认 None）
        component = MagicMock()
        portfolio._propagate_context(component)

        # portfolio 自身总是传播（非可选）
        component.bind_portfolio.assert_called_once_with(portfolio)
        # 可选上下文为 None 时不传播
        component.bind_engine.assert_not_called()
        component.set_time_provider.assert_not_called()
        component.bind_data_feeder.assert_not_called()
