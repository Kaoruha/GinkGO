"""
端到端回测测试

验证完整回测流程：
1. 引擎启动和停止
2. 策略信号生成
3. 订单成交和持仓
4. 净值跟踪

运行方式:
    python -m pytest test/e2e/test_backtest_e2e.py -v
"""

import pytest
import sys
from pathlib import Path
import datetime
from decimal import Decimal
import time

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest
from ginkgo.trading.strategies.random_signal_strategy import RandomSignalStrategy
from ginkgo.trading.sizers.fixed_sizer import FixedSizer
from ginkgo.trading.selectors.fixed_selector import FixedSelector
from ginkgo.trading.feeders.backtest_feeder import BacktestFeeder
from ginkgo.trading.gateway.trade_gateway import TradeGateway
from ginkgo.trading.brokers.sim_broker import SimBroker
from ginkgo.enums import EXECUTION_MODE, ATTITUDE_TYPES, DEFAULT_ANALYZER_SET
from ginkgo.libs import GCONF


@pytest.fixture(scope="module")
def setup_debug_mode():
    """设置调试模式"""
    GCONF.set_debug(True)
    yield


class TestBacktestE2E:
    """端到端回测测试"""

    @pytest.fixture(autouse=True)
    def setup(self, setup_debug_mode):
        """每个测试前的设置"""
        self.start_date = datetime.datetime(2023, 12, 1)
        self.end_date = datetime.datetime(2023, 12, 5)
        self.initial_cash = Decimal("100000")

    def create_backtest(self):
        """创建完整回测组件"""
        engine = TimeControlledEventEngine(
            name="E2ETestEngine",
            mode=EXECUTION_MODE.BACKTEST,
            logical_time_start=self.start_date,
            timer_interval=0.001
        )
        engine.set_end_time(self.end_date)

        portfolio = PortfolioT1Backtest(
            name="e2e_portfolio",
            use_default_analyzers=True,
            default_analyzer_set=DEFAULT_ANALYZER_SET.STANDARD
        )
        portfolio.add_cash(self.initial_cash)

        strategy = RandomSignalStrategy(
            buy_probability=0.9,
            sell_probability=0.05,
            max_signals=4
        )
        strategy.set_random_seed(12345)

        sizer = FixedSizer(volume=1000)
        selector = FixedSelector(name="selector", codes=["000001.SZ"])

        broker = SimBroker(name="SimBroker", attitude=ATTITUDE_TYPES.OPTIMISTIC)
        gateway = TradeGateway(name="Gateway", brokers=[broker])

        feeder = BacktestFeeder(name="e2e_feeder")

        engine.add_portfolio(portfolio)
        engine.bind_router(gateway)
        portfolio.add_strategy(strategy)
        portfolio.bind_sizer(sizer)
        portfolio.bind_selector(selector)
        engine.set_data_feeder(feeder)

        return {
            'engine': engine,
            'portfolio': portfolio,
            'strategy': strategy,
            'sizer': sizer,
            'broker': broker,
            'gateway': gateway,
            'feeder': feeder
        }

    def run_backtest(self, components, timeout=60):
        """运行回测直到完成"""
        engine = components['engine']
        success = engine.start()
        if not success:
            return False

        start_time = time.time()
        while engine.is_active and (time.time() - start_time) < timeout:
            time.sleep(0.1)

        return not engine.is_active

    def test_engine_starts_and_stops(self):
        """测试引擎启动和停止"""
        components = self.create_backtest()
        engine = components['engine']

        success = self.run_backtest(components)
        assert success, "Backtest should complete"
        assert not engine.is_active, "Engine should be stopped"

    def test_strategy_generates_signals(self):
        """测试策略生成信号"""
        components = self.create_backtest()
        strategy = components['strategy']

        self.run_backtest(components)
        assert strategy.signal_count > 0, "Strategy should generate signals"

    def test_portfolio_tracks_value(self):
        """测试Portfolio跟踪净值"""
        components = self.create_backtest()
        portfolio = components['portfolio']

        self.run_backtest(components)

        # 净值应该是正数
        assert float(portfolio.worth) > 0, "Worth should be positive"

        # 现金应该非负
        assert float(portfolio.cash) >= 0, "Cash should be non-negative"

        # 冻结资金应该非负
        assert float(portfolio.frozen) >= 0, "Frozen should be non-negative"

    def test_analyzers_record_data(self):
        """测试分析器记录数据"""
        components = self.create_backtest()
        portfolio = components['portfolio']

        self.run_backtest(components)

        # 验证默认分析器存在
        assert 'net_value' in portfolio.analyzers, "net_value analyzer should exist"
        assert 'profit' in portfolio.analyzers, "profit analyzer should exist"

        # 验证分析器有记录
        if hasattr(portfolio.analyzers['net_value'], '_size'):
            assert portfolio.analyzers['net_value']._size > 0, "Net value should have records"

    def test_complete_backtest_workflow(self):
        """测试完整回测工作流 - 核心E2E测试"""
        components = self.create_backtest()
        portfolio = components['portfolio']
        strategy = components['strategy']

        # 1. 运行回测
        success = self.run_backtest(components)
        assert success, "Backtest should complete"

        # 2. 策略生成信号
        assert strategy.signal_count > 0, "Strategy should generate signals"

        # 3. 净值有效
        final_worth = float(portfolio.worth)
        assert final_worth > 0, "Final worth should be positive"

        # 4. 资金一致
        cash = float(portfolio.cash)
        frozen = float(portfolio.frozen)
        position_worth = sum(float(pos.worth) for pos in portfolio.positions.values())
        expected_worth = cash + frozen + position_worth
        assert abs(final_worth - expected_worth) < 1, "Net value should equal cash + frozen + positions"

        # 5. 分析器工作
        if 'net_value' in portfolio.analyzers and hasattr(portfolio.analyzers['net_value'], '_size'):
            assert portfolio.analyzers['net_value']._size > 0, "Analyzer should record data"


class TestBacktestComponents:
    """回测组件测试"""

    def test_portfolio_initialization(self):
        """测试Portfolio初始化"""
        portfolio = PortfolioT1Backtest(name="test_portfolio")
        portfolio.add_cash(Decimal("100000"))

        assert float(portfolio.cash) == 100000
        assert float(portfolio.worth) == 100000
        assert len(portfolio.positions) == 0

    def test_strategy_initialization(self):
        """测试策略初始化"""
        strategy = RandomSignalStrategy(
            buy_probability=0.5,
            sell_probability=0.3,
            max_signals=5
        )
        strategy.set_random_seed(42)

        assert strategy.buy_probability == 0.5
        assert strategy.sell_probability == 0.3

    def test_sizer_initialization(self):
        """测试Sizer初始化"""
        sizer = FixedSizer(volume=500)
        assert sizer.volume == 500

    def test_broker_initialization(self):
        """测试Broker初始化"""
        broker = SimBroker(
            name="TestBroker",
            attitude=ATTITUDE_TYPES.OPTIMISTIC,
            commission_rate=0.0003
        )
        assert broker._attitude == ATTITUDE_TYPES.OPTIMISTIC


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
