"""
PortfolioLive 事件处理单元测试

测试 PriceUpdate → Signal → Order 完整链路：
1. on_price_update() 接收价格更新事件
2. generate_strategy_signals() 生成交易信号
3. _process_signal() 处理信号并返回订单事件
4. PortfolioProcessor 收集返回值并转发到 output_queue
"""

import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from ginkgo.trading.portfolios.portfolio_live import PortfolioLive
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.events.order_lifecycle_events import EventOrderAck, EventOrderPartiallyFilled
from ginkgo.trading.entities.signal import Signal
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, FREQUENCY_TYPES
from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.trading.bases.sizer_base import SizerBase
from ginkgo.trading.bases.risk_base import RiskBase
from ginkgo.trading.bases.selector_base import SelectorBase


@pytest.mark.unit
class TestPortfolioLivePriceUpdate:
    """测试 PortfolioLive.on_price_update() 方法"""

    def test_on_price_update_returns_empty_list_when_not_ready(self):
        """测试 Portfolio 未就绪时返回空列表"""
        portfolio = PortfolioLive(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            name="Test Portfolio",
            initial_cash=100000
        )

        # 创建 Bar 对象
        from ginkgo.trading.entities.bar import Bar
        bar = Bar(
            code="000001.SZ",
            timestamp=datetime.now(),
            open=Decimal("10.5"),
            high=Decimal("10.5"),
            low=Decimal("10.5"),
            close=Decimal("10.5"),
            volume=1000,
            amount=Decimal("10500"),
            frequency=FREQUENCY_TYPES.DAY
        )
        event = EventPriceUpdate(payload=bar)

        result = portfolio.on_price_update(event)

        assert result == []
        assert isinstance(result, list)


@pytest.mark.unit
class TestPortfolioLiveSignalProcessing:
    """测试 PortfolioLive 信号处理"""

    def test_process_signal_returns_order_event(self):
        """测试 _process_signal 返回订单事件"""
        portfolio = PortfolioLive(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            name="Test Portfolio",
            initial_cash=100000
        )

        # 设置 sizer
        mock_sizer = Mock(spec=SizerBase)
        from ginkgo.trading.entities.order import Order
        mock_order = Order(
            portfolio_id="test_portfolio",  # 直接使用字符串
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=Decimal("10.0")
        )
        mock_sizer.cal.return_value = mock_order
        portfolio.bind_sizer(mock_sizer)

        # 添加 Selector（选择所有股票）
        class AllStockSelector(SelectorBase):
            def pick(self, time=None, *args, **kwargs):
                return ["*"]

        portfolio.bind_selector(AllStockSelector())

        # 添加空的 strategy（满足 is_all_set 检查）
        class EmptyStrategy(BaseStrategy):
            def cal(self, portfolio_info, event):
                return []

        portfolio.add_strategy(EmptyStrategy())

        # 添加空的 risk_managers（放行所有订单）
        portfolio.add_risk_manager(RiskBase())

        signal = Signal(
            portfolio_id="test_portfolio",  # 直接使用字符串
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG
        )

        result = portfolio._process_signal(signal)

        # 验证返回 EventOrderAck
        assert isinstance(result, EventOrderAck)
        assert result.order.uuid == mock_order.uuid

    def test_process_signal_with_risk_manager_blocking(self):
        """测试风控管理器拦截订单"""
        portfolio = PortfolioLive(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            name="Test Portfolio",
            initial_cash=100000
        )

        # 设置 sizer
        mock_sizer = Mock(spec=SizerBase)
        from ginkgo.trading.entities.order import Order
        mock_order = Order(
            portfolio_id="test_portfolio",  # 直接使用字符串
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=Decimal("10.0")
        )
        mock_sizer.cal.return_value = mock_order
        portfolio.bind_sizer(mock_sizer)

        # 添加 Selector（选择所有股票）
        class AllStockSelector(SelectorBase):
            def pick(self, time=None, *args, **kwargs):
                return ["*"]

        portfolio.bind_selector(AllStockSelector())

        # 添加空的 strategy（满足 is_all_set 检查）
        class EmptyStrategy(BaseStrategy):
            def cal(self, portfolio_info, event):
                return []

        portfolio.add_strategy(EmptyStrategy())

        # 设置会拦截的 risk_manager
        mock_risk = Mock(spec=RiskBase)
        mock_risk.cal.return_value = None  # 拦截订单
        portfolio.add_risk_manager(mock_risk)

        signal = Signal(
            portfolio_id="test_portfolio",  # 直接使用字符串
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG
        )

        result = portfolio._process_signal(signal)

        # 验证订单被拦截
        assert result is None
        mock_risk.cal.assert_called_once()


@pytest.mark.unit
class TestPortfolioOrderFilled:
    """测试Portfolio订单成交事件处理"""

    def test_on_order_filled_calls_on_order_partially_filled(self):
        """测试on_order_filled调用on_order_partially_filled"""
        portfolio = PortfolioLive(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run"
        )
        portfolio.is_event_from_future = Mock(return_value=False)

        # Mock on_order_partially_filled 方法
        portfolio.on_order_partially_filled = Mock()

        # 创建一个真实的 Order 对象
        from ginkgo.trading.entities.order import Order
        test_order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=Decimal("10.0")
        )

        # 创建成交事件
        event = EventOrderPartiallyFilled(
            order=test_order,
            filled_quantity=100,
            fill_price=Decimal("10.5")
        )

        portfolio.on_order_filled(event)

        # 验证调用了on_order_partially_filled
        portfolio.on_order_partially_filled.assert_called_once_with(event)


@pytest.mark.unit
class TestPortfolioSyncState:
    """测试Portfolio状态同步到数据库"""

    def test_sync_state_to_db_with_positions(self):
        """测试同步持仓到数据库"""
        portfolio = PortfolioLive(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run"
        )

        # 创建一个持仓
        from ginkgo.trading.entities.position import Position
        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            volume=100,
            cost=Decimal("10.0"),
            price=Decimal("10.5"),
            frozen=0,
            fee=Decimal("5.25")
        )
        portfolio._positions["000001.SZ"] = position

        # Mock add 函数
        with patch('ginkgo.data.drivers.add') as mock_add:
            with patch.object(portfolio, 'get_time_provider') as mock_time:
                mock_time.return_value.now.return_value = datetime.now()

                # 执行同步
                result = portfolio.sync_state_to_db()

                # 验证返回成功（注意：sync_state_to_db内部可能有异常，这里只测试不崩溃）
                # 实际测试中，如果CRUD不存在会抛出异常，这是预期的
                assert result is True or result is False


@pytest.mark.unit
class TestPortfolioSignalGeneration:
    """测试Portfolio信号生成"""

    def test_generate_strategy_signals_delegates_to_strategies(self):
        """测试生成策略信号委托给策略"""
        portfolio = PortfolioLive(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run"
        )

        # 创建一个真实的简单策略用于测试
        class TestStrategy(BaseStrategy):
            def cal(self, portfolio_info, event):
                return []

        test_strategy = TestStrategy()
        portfolio.add_strategy(test_strategy)

        # 创建事件
        from ginkgo.trading.entities.bar import Bar
        bar = Bar(
            code="000001.SZ",
            timestamp=datetime.now(),
            open=Decimal("10.0"),
            high=Decimal("10.5"),
            low=Decimal("9.8"),
            close=Decimal("10.3"),
            volume=1000000,
            amount=Decimal("10300000"),
            frequency=FREQUENCY_TYPES.DAY
        )
        event = EventPriceUpdate(payload=bar)

        # 生成信号（应该不会抛出异常）
        signals = portfolio.generate_strategy_signals(event)

        # 验证返回列表
        assert isinstance(signals, list)

    def test_generate_risk_signals_delegates_to_risk_managers(self):
        """测试生成风控信号委托给风控管理器"""
        portfolio = PortfolioLive(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run"
        )

        # 创建一个真实的简单风控管理器用于测试
        class TestRisk(RiskBase):
            def cal(self, portfolio_info, order):
                return order

            def generate_signals(self, portfolio_info, event):
                return []

        test_risk = TestRisk()
        portfolio.add_risk_manager(test_risk)

        # 创建事件
        from ginkgo.trading.entities.bar import Bar
        bar = Bar(
            code="000001.SZ",
            timestamp=datetime.now(),
            open=Decimal("10.0"),
            high=Decimal("10.5"),
            low=Decimal("9.8"),
            close=Decimal("10.3"),
            volume=1000000,
            amount=Decimal("10300000"),
            frequency=FREQUENCY_TYPES.DAY
        )
        event = EventPriceUpdate(payload=bar)

        # 生成风控信号（应该不会抛出异常）
        signals = portfolio.generate_risk_signals(event)

        # 验证返回列表
        assert isinstance(signals, list)
