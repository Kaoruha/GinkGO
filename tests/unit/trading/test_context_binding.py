"""
测试不同的实例化和绑定顺序，确保所有组件都能正确获得上下文
"""

import pytest
from ginkgo.trading.engines import EventEngine
from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest
from ginkgo.trading.strategies import BaseStrategy
from ginkgo.trading.sizers.fixed_sizer import FixedSizer
from ginkgo.trading.selectors.fixed_selector import FixedSelector
from ginkgo.trading.entities.signal import Signal
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from datetime import datetime


class TestStrategy(BaseStrategy):
    def cal(self, portfolio_info, event):
        # 生成测试信号
        signal = Signal(
            portfolio_id=portfolio_info.get("portfolio_id", "test"),
            engine_id=portfolio_info.get("engine_id", "test_engine"),
            run_id=portfolio_info.get("run_id", "test_run"),
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            volume=1000,
            source=SOURCE_TYPES.TEST,
            timestamp=datetime.now()
        )
        return [signal]


class TestContextBinding:
    """测试上下文绑定机制的各种场景"""

    def test_scenario_1_engine_first(self):
        """场景1：先创建引擎，再创建组件，最后绑定"""
        # 1. 先创建引擎
        engine = EventEngine()
        engine.engine_id = "test_engine_1"
        engine._run_id = "test_run_1"

        # 2. 创建组件
        portfolio = PortfolioT1Backtest("test_portfolio_1")
        strategy = TestStrategy("test_strategy_1")
        sizer = FixedSizer("test_sizer_1")
        selector = FixedSelector("test_selector_1", codes='["000001.SZ"]')

        # 3. 绑定关系
        portfolio.add_strategy(strategy)
        portfolio.bind_sizer(sizer)
        portfolio.bind_selector(selector)
        engine.bind_portfolio(portfolio)

        # 4. 验证上下文
        assert portfolio.engine_id == "test_engine_1"
        assert portfolio.run_id == "test_run_1"
        assert strategy.engine_id == "test_engine_1"
        assert strategy.run_id == "test_run_1"
        assert sizer.engine_id == "test_engine_1"
        assert sizer.run_id == "test_run_1"
        assert selector.engine_id == "test_engine_1"
        assert selector.run_id == "test_run_1"

    def test_scenario_2_portfolio_first(self):
        """场景2：先创建portfolio，再创建引擎，最后绑定"""
        # 1. 先创建portfolio和组件
        portfolio = PortfolioT1Backtest("test_portfolio_2")
        strategy = TestStrategy("test_strategy_2")
        sizer = FixedSizer("test_sizer_2")
        selector = FixedSelector("test_selector_2", codes='["000001.SZ"]')

        # 2. 绑定组件到portfolio
        portfolio.add_strategy(strategy)
        portfolio.bind_sizer(sizer)
        portfolio.bind_selector(selector)

        # 3. 创建引擎
        engine = EventEngine()
        engine.engine_id = "test_engine_2"
        engine._run_id = "test_run_2"

        # 4. 绑定引擎到portfolio
        engine.bind_portfolio(portfolio)

        # 5. 验证上下文
        assert portfolio.engine_id == "test_engine_2"
        assert portfolio.run_id == "test_run_2"
        assert strategy.engine_id == "test_engine_2"
        assert strategy.run_id == "test_run_2"
        assert sizer.engine_id == "test_engine_2"
        assert sizer.run_id == "test_run_2"
        assert selector.engine_id == "test_engine_2"
        assert selector.run_id == "test_run_2"

    def test_scenario_3_components_first(self):
        """场景3：先创建所有组件，最后统一绑定"""
        # 1. 创建所有组件
        strategy = TestStrategy("test_strategy_3")
        sizer = FixedSizer("test_sizer_3")
        selector = FixedSelector("test_selector_3", codes='["000001.SZ"]')
        portfolio = PortfolioT1Backtest("test_portfolio_3")
        engine = EventEngine()
        engine.engine_id = "test_engine_3"
        engine._run_id = "test_run_3"

        # 2. 绑定组件到portfolio
        portfolio.add_strategy(strategy)
        portfolio.bind_sizer(sizer)
        portfolio.bind_selector(selector)

        # 3. 绑定引擎
        engine.bind_portfolio(portfolio)

        # 4. 验证上下文
        assert portfolio.engine_id == "test_engine_3"
        assert portfolio.run_id == "test_run_3"
        assert strategy.engine_id == "test_engine_3"
        assert strategy.run_id == "test_run_3"
        assert sizer.engine_id == "test_engine_3"
        assert sizer.run_id == "test_run_3"
        assert selector.engine_id == "test_engine_3"
        assert selector.run_id == "test_run_3"

    def test_scenario_4_late_engine_binding(self):
        """场景4：组件绑定后，引擎最后绑定"""
        # 1. 创建并绑定所有组件（无引擎）
        portfolio = PortfolioT1Backtest("test_portfolio_4")
        strategy = TestStrategy("test_strategy_4")
        sizer = FixedSizer("test_sizer_4")
        selector = FixedSelector("test_selector_4", codes='["000001.SZ"]')

        portfolio.add_strategy(strategy)
        portfolio.bind_sizer(sizer)
        portfolio.bind_selector(selector)

        # 验证绑定前状态（应该为None）
        assert portfolio.engine_id is None
        assert strategy.engine_id is None
        assert sizer.engine_id is None
        assert selector.engine_id is None

        # 2. 最后创建并绑定引擎
        engine = EventEngine()
        engine.engine_id = "test_engine_4"
        engine._run_id = "test_run_4"
        engine.bind_portfolio(portfolio)

        # 3. 验证绑定后状态
        assert portfolio.engine_id == "test_engine_4"
        assert strategy.engine_id == "test_engine_4"
        assert sizer.engine_id == "test_engine_4"
        assert selector.engine_id == "test_engine_4"

    def test_component_context_consistency(self):
        """测试所有组件上下文的一致性"""
        # 创建完整的绑定关系
        engine = EventEngine()
        engine.engine_id = "consistency_test_engine"
        engine._run_id = "consistency_test_run"

        portfolio = PortfolioT1Backtest("consistency_portfolio")
        strategy = TestStrategy("consistency_strategy")
        sizer = FixedSizer("consistency_sizer")
        selector = FixedSelector("consistency_selector", codes='["000001.SZ"]')

        portfolio.add_strategy(strategy)
        portfolio.bind_sizer(sizer)
        portfolio.bind_selector(selector)
        engine.bind_portfolio(portfolio)

        # 验证所有组件的上下文都一致
        expected_engine_id = "consistency_test_engine"
        expected_run_id = "consistency_test_run"

        assert portfolio.engine_id == expected_engine_id
        assert strategy.engine_id == expected_engine_id
        assert sizer.engine_id == expected_engine_id
        assert selector.engine_id == expected_engine_id

        assert portfolio.run_id == expected_run_id
        assert strategy.run_id == expected_run_id
        assert sizer.run_id == expected_run_id
        assert selector.run_id == expected_run_id

    def test_portfolio_id_binding(self):
        """测试portfolio_id绑定"""
        portfolio = PortfolioT1Backtest("test_portfolio_id")
        strategy = TestStrategy("test_strategy_id")
        sizer = FixedSizer("test_sizer_id")
        selector = FixedSelector("test_selector_id", codes='["000001.SZ"]')

        portfolio.add_strategy(strategy)
        portfolio.bind_sizer(sizer)
        portfolio.bind_selector(selector)

        # 验证portfolio_id绑定
        assert strategy.portfolio_id == portfolio.uuid
        assert sizer.portfolio_id == portfolio.uuid
        assert selector.portfolio_id == portfolio.uuid