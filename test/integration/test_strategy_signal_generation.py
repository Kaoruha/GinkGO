"""
策略信号生成测试

测试从价格事件到策略信号的完整转换过程，验证策略计算和信号生成的正确性。
"""

import pytest
import datetime
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.entities.bar import Bar
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.trading.bases.sizer_base import SizerBase as BaseSizer
from ginkgo.enums import SOURCE_TYPES, DIRECTION_TYPES


class PriceBreakthroughStrategy(BaseStrategy):
    """价格突破策略 - 简单测试策略"""

    def __init__(self, threshold=Decimal("10.00")):
        super().__init__()
        self.threshold = threshold
        self.cal_called = False
        self.last_portfolio_info = None
        self.last_event = None

    def cal(self, portfolio_info, event, *args, **kwargs):
        """基于价格突破生成信号"""
        self.cal_called = True
        self.last_portfolio_info = portfolio_info
        self.last_event = event

        if isinstance(event, EventPriceUpdate) and event.code == "000001.SZ":
            if event.close > self.threshold:
                return [Signal(
                    code="000001.SZ",
                    direction=DIRECTION_TYPES.LONG,
                    reason=f"价格{event.close}突破{self.threshold}",
                    timestamp=event.business_timestamp
                )]
            elif event.close < self.threshold - Decimal("1.00"):
                return [Signal(
                    code="000001.SZ",
                    direction=DIRECTION_TYPES.SHORT,
                    reason=f"价格{event.close}跌破{self.threshold - Decimal('1.00')}",
                    timestamp=event.business_timestamp
                )]
        return []


class TechnicalIndicatorStrategy(BaseStrategy):
    """技术指标策略 - 测试多策略场景"""

    def __init__(self, ma_period=5):
        super().__init__()
        self.ma_period = ma_period
        self.price_history = []
        self.cal_called = False

    def cal(self, portfolio_info, event, *args, **kwargs):
        """基于移动平均线生成信号"""
        self.cal_called = True

        if isinstance(event, EventPriceUpdate) and event.code == "000001.SZ":
            self.price_history.append(event.close)

            if len(self.price_history) >= self.ma_period:
                # 计算简单移动平均
                recent_prices = self.price_history[-self.ma_period:]
                ma = sum(recent_prices) / len(recent_prices)

                if event.close > ma:
                    return [Signal(
                        code="000001.SZ",
                        direction=DIRECTION_TYPES.LONG,
                        reason=f"价格{event.close}高于均线{ma:.2f}",
                        timestamp=event.business_timestamp
                    )]
        return []


class ErrorStrategy(BaseStrategy):
    """异常测试策略"""

    def __init__(self, should_error=False, return_none=False):
        super().__init__()
        self.should_error = should_error
        self.return_none = return_none
        self.cal_called = False

    def cal(self, portfolio_info, event, *args, **kwargs):
        """测试异常情况"""
        self.cal_called = True

        if self.should_error:
            raise ValueError("策略计算异常")

        if self.return_none:
            return None

        return []  # 空信号列表


@pytest.mark.integration
class TestPriceEventTrigger:
    """测试价格事件触发机制"""

    def setup_method(self):
        """测试前设置"""
        self.portfolio = PortfolioT1Backtest()
        self.strategy = PriceBreakthroughStrategy()
        self.sizer = Mock()

        self.portfolio.add_strategy(self.strategy)
        self.portfolio.set_sizer(self.sizer)
        self.portfolio.engine_id = "test_engine"

    def test_price_update_triggers_strategy_calculation(self):
        """测试价格更新触发策略计算"""
        # 创建价格事件
        bar = Bar(
            code="000001.SZ",
            timestamp=datetime.datetime(2023, 1, 1, 9, 30),
            close=Decimal("10.50")
        )
        price_event = EventPriceUpdate(
            price_info=bar,
            source=SOURCE_TYPES.BACKTESTFEEDER
        )

        # Portfolio处理价格事件
        self.portfolio.on_price_received(price_event)

        # 验证策略被调用
        assert self.strategy.cal_called, "价格事件应该触发策略计算"

    def test_strategy_receives_correct_parameters(self):
        """测试策略接收正确的参数"""
        bar = Bar(
            code="000001.SZ",
            timestamp=datetime.datetime(2023, 1, 1, 9, 30),
            close=Decimal("10.50"),
            volume=1000000
        )
        price_event = EventPriceUpdate(price_info=bar)

        # Portfolio处理价格事件
        self.portfolio.on_price_received(price_event)

        # 验证策略接收的参数
        assert self.strategy.last_event == price_event, "策略应该接收到正确的事件"
        assert self.strategy.last_portfolio_info is not None, "策略应该接收到portfolio_info"

        # 验证portfolio_info包含基本信息
        portfolio_info = self.strategy.last_portfolio_info
        assert isinstance(portfolio_info, dict), "portfolio_info应该是字典类型"


@pytest.mark.integration
class TestStrategyCalculation:
    """测试策略计算逻辑"""

    def setup_method(self):
        """测试前设置"""
        self.portfolio = PortfolioT1Backtest()
        self.strategy = PriceBreakthroughStrategy(threshold=Decimal("10.00"))
        self.sizer = Mock()

        self.portfolio.add_strategy(self.strategy)
        self.portfolio.set_sizer(self.sizer)
        self.portfolio.engine_id = "test_engine"

    def test_strategy_cal_method_invocation(self):
        """测试strategy.cal方法调用"""
        # 测试突破阈值
        bar_above = Bar(
            code="000001.SZ",
            timestamp=datetime.datetime(2023, 1, 1, 9, 30),
            close=Decimal("10.50")  # 高于阈值
        )
        price_event = EventPriceUpdate(price_info=bar_above)

        with patch.object(self.portfolio, 'put') as mock_put:
            self.portfolio.on_price_received(price_event)

        # 验证策略被调用
        assert self.strategy.cal_called, "strategy.cal方法应该被调用"

    def test_signal_generation_logic(self):
        """测试信号生成逻辑"""
        # 测试突破信号生成
        bar_above = Bar(code="000001.SZ", close=Decimal("10.50"))
        price_event = EventPriceUpdate(price_info=bar_above)

        with patch.object(self.portfolio, 'put') as mock_put:
            self.portfolio.on_price_received(price_event)

        # 验证信号被生成
        assert mock_put.called, "应该生成信号事件"

        # 检查生成的信号
        call_args = mock_put.call_args
        if call_args:
            signal_event = call_args[0][0]
            assert signal_event.code == "000001.SZ", "信号代码应该正确"
            assert signal_event.direction == DIRECTION_TYPES.LONG, "信号方向应该为买入"
            assert "突破" in signal_event.value.reason, "信号原因应该包含突破信息"

        # 测试跌破信号生成
        bar_below = Bar(code="000001.SZ", close=Decimal("8.50"))
        price_event_below = EventPriceUpdate(price_info=bar_below)

        with patch.object(self.portfolio, 'put') as mock_put:
            self.portfolio.on_price_received(price_event_below)

        # 验证卖出信号
        if mock_put.called:
            call_args = mock_put.call_args
            signal_event = call_args[0][0]
            assert signal_event.direction == DIRECTION_TYPES.SHORT, "应该生成卖出信号"


@pytest.mark.integration
class TestMultipleStrategies:
    """测试多策略并发执行"""

    def setup_method(self):
        """测试前设置"""
        self.portfolio = PortfolioT1Backtest()
        self.strategy1 = PriceBreakthroughStrategy(threshold=Decimal("10.00"))
        self.strategy2 = TechnicalIndicatorStrategy(ma_period=3)
        self.sizer = Mock()

        self.portfolio.add_strategy(self.strategy1)
        self.portfolio.add_strategy(self.strategy2)
        self.portfolio.set_sizer(self.sizer)
        self.portfolio.engine_id = "test_engine"

    def test_multiple_strategies_concurrent_execution(self):
        """测试多策略并发执行"""
        bar = Bar(
            code="000001.SZ",
            timestamp=datetime.datetime(2023, 1, 1, 9, 30),
            close=Decimal("10.50")
        )
        price_event = EventPriceUpdate(price_info=bar)

        # Portfolio处理价格事件
        self.portfolio.on_price_received(price_event)

        # 验证所有策略都被调用
        assert self.strategy1.cal_called, "策略1应该被调用"
        assert self.strategy2.cal_called, "策略2应该被调用"

    def test_signal_combination(self):
        """测试多策略信号组合"""
        # 提供多个价格点让技术指标策略计算均线
        prices = [Decimal("9.50"), Decimal("9.80"), Decimal("10.20")]

        for i, price in enumerate(prices):
            bar = Bar(
                code="000001.SZ",
                timestamp=datetime.datetime(2023, 1, 1, 9, 30) + datetime.timedelta(minutes=i),
                close=price
            )
            price_event = EventPriceUpdate(price_info=bar)

            with patch.object(self.portfolio, 'put') as mock_put:
                self.portfolio.on_price_received(price_event)

                # 最后一个价格点应该同时触发两个策略
                if i == len(prices) - 1:
                    # 两个策略都应该生成信号
                    assert mock_put.call_count >= 2, "两个策略都应该生成信号"


@pytest.mark.integration
class TestStrategyErrorHandling:
    """测试策略异常处理"""

    def setup_method(self):
        """测试前设置"""
        self.portfolio = PortfolioT1Backtest()
        self.sizer = Mock()
        self.portfolio.set_sizer(self.sizer)
        self.portfolio.engine_id = "test_engine"

    def test_strategy_exception_handling(self):
        """测试策略异常处理"""
        # 创建会抛异常的策略
        error_strategy = ErrorStrategy(should_error=True)
        self.portfolio.add_strategy(error_strategy)

        bar = Bar(code="000001.SZ", close=Decimal("10.50"))
        price_event = EventPriceUpdate(price_info=bar)

        # 即使策略抛异常，Portfolio应该继续工作
        with patch.object(self.portfolio, 'put') as mock_put:
            # 不应该抛出异常
            self.portfolio.on_price_received(price_event)

        # 验证策略被调用了
        assert error_strategy.cal_called, "异常策略应该被调用"

    def test_empty_signal_handling(self):
        """测试空信号处理"""
        # 创建返回空信号列表的策略
        empty_strategy = ErrorStrategy(return_none=True)
        self.portfolio.add_strategy(empty_strategy)

        bar = Bar(code="000001.SZ", close=Decimal("10.50"))
        price_event = EventPriceUpdate(price_info=bar)

        with patch.object(self.portfolio, 'put') as mock_put:
            self.portfolio.on_price_received(price_event)

        # 验证空信号被正确处理
        # 即使策略返回None或空列表，也不应该出错
        assert empty_strategy.cal_called, "空信号策略应该被调用"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])