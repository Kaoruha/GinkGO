"""
Portfolio信号延迟执行机制测试

测试Portfolio基于当前信息决策、下一时间点执行的延迟执行机制。
这不是T+1交易规则，而是决策与执行的时间分离机制。
"""

import pytest
import datetime
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.events.signal_generation import EventSignalGeneration
from ginkgo.trading.entities.bar import Bar
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.trading.bases.sizer_base import SizerBase as BaseSizer
from ginkgo.trading.bases.risk_base import RiskBase as BaseRiskManagement
from ginkgo.enums import SOURCE_TYPES, DIRECTION_TYPES, RECORDSTAGE_TYPES


class TestStrategy(BaseStrategy):
    """测试策略 - 基于价格信息生成信号"""

    def __init__(self):
        super().__init__()
        self.decision_made = False
        self.decision_timestamp = None
        self.decision_price = None

    def cal(self, portfolio_info, event, *args, **kwargs):
        """基于当前价格信息做出决策"""
        if isinstance(event, EventPriceUpdate) and event.code == "000001.SZ":
            # 记录决策时刻的信息
            self.decision_made = True
            self.decision_timestamp = event.business_timestamp
            self.decision_price = event.close

            # 基于当前信息生成信号
            if event.close > Decimal("10.00"):
                return [Signal(
                    code="000001.SZ",
                    direction=DIRECTION_TYPES.LONG,
                    reason=f"价格{event.close}超过10.00",
                    timestamp=event.business_timestamp
                )]
        return []


class TestSizer(BaseSizer):
    """测试Sizer - 固定订单大小"""

    def cal(self, portfolio_info, signal):
        if signal and signal.direction == DIRECTION_TYPES.LONG:
            return Mock(
                code=signal.code,
                direction=signal.direction,
                volume=100,
                limit_price=Decimal("10.50"),
                reason=signal.reason,
                uuid=f"order_{signal.code}"
            )
        return None


@pytest.mark.integration
class TestInformationDecisionSeparation:
    """测试信息决策分离机制"""

    def setup_method(self):
        """测试前设置"""
        self.portfolio = PortfolioT1Backtest()
        self.strategy = TestStrategy()
        self.sizer = TestSizer()

        self.portfolio.add_strategy(self.strategy)
        self.portfolio.set_sizer(self.sizer)
        self.portfolio.engine_id = "test_engine"

    def test_decision_based_on_current_info(self):
        """测试基于当前时间点信息做出决策"""
        # 创建当前时间点的价格事件
        current_time = datetime.datetime(2023, 1, 1, 9, 30)
        bar = Bar(
            code="000001.SZ",
            timestamp=current_time,
            close=Decimal("10.50")  # 价格超过10.00
        )

        price_event = EventPriceUpdate(
            price_info=bar,
            source=SOURCE_TYPES.BACKTESTFEEDER,
            timestamp=current_time
        )

        # Portfolio处理价格事件（决策阶段）
        with patch.object(self.portfolio, 'put') as mock_put:
            self.portfolio.on_price_received(price_event)

        # 验证策略基于当前信息做出决策
        assert self.strategy.decision_made, "策略应该基于当前信息做出决策"
        assert self.strategy.decision_timestamp == current_time, "决策时间戳应该是当前时间"
        assert self.strategy.decision_price == Decimal("10.50"), "决策价格应该是当前价格"

    def test_decision_saved_for_next_timepoint(self):
        """测试决策保存用于下一时间点执行"""
        current_time = datetime.datetime(2023, 1, 1, 9, 30)
        bar = Bar(code="000001.SZ", timestamp=current_time, close=Decimal("10.50"))
        price_event = EventPriceUpdate(price_info=bar, timestamp=current_time)

        # 处理价格事件（决策保存阶段）
        with patch.object(self.portfolio, 'put') as mock_put:
            self.portfolio.on_price_received(price_event)

        # 验证决策被保存（信号在portfolio中累积）
        signals_in_portfolio = self.portfolio.signals
        assert len(signals_in_portfolio) > 0, "决策信号应该被保存到portfolio"

        # 验证保存的信号包含决策信息
        saved_signal = signals_in_portfolio[0]
        assert saved_signal.code == "000001.SZ", "保存的信号代码正确"
        assert saved_signal.reason and "10.50" in saved_signal.reason, "保存的信号包含决策价格信息"


@pytest.mark.integration
class TestDelayedExecutionMechanism:
    """测试延迟执行机制"""

    def setup_method(self):
        """测试前设置"""
        self.portfolio = PortfolioT1Backtest()
        self.strategy = TestStrategy()
        self.sizer = TestSizer()

        self.portfolio.add_strategy(self.strategy)
        self.portfolio.set_sizer(self.sizer)
        self.portfolio.engine_id = "test_engine"

        # 预先保存一个决策信号
        current_time = datetime.datetime(2023, 1, 1, 9, 30)
        bar = Bar(code="000001.SZ", timestamp=current_time, close=Decimal("10.50"))
        price_event = EventPriceUpdate(price_info=bar, timestamp=current_time)

        with patch.object(self.portfolio, 'put'):
            self.portfolio.on_price_received(price_event)

    def test_execution_at_next_timepoint(self):
        """测试在下一时间点执行决策"""
        next_time = datetime.datetime(2023, 1, 1, 10, 30)  # 下一个时间点

        # 记录执行前的信号数量
        signals_before = len(self.portfolio.signals)

        # 模拟时间推进触发执行
        with patch.object(self.portfolio, 'put') as mock_put:
            self.portfolio.advance_time(next_time)

        # 验证决策在下一时间点被执行
        assert mock_put.called, "应该执行决策推送"

        # 验证推送的是EventSignalGeneration
        call_args_list = mock_put.call_args_list
        signal_events = [call[0][0] for call in call_args_list
                        if isinstance(call[0][0], EventSignalGeneration)]
        assert len(signal_events) > 0, "应该推送EventSignalGeneration事件"

    def test_signals_cleared_after_execution(self):
        """测试执行后信号清空"""
        next_time = datetime.datetime(2023, 1, 1, 10, 30)

        # 验证执行前有保存的信号
        assert len(self.portfolio.signals) > 0, "执行前应该有保存的信号"

        # 执行时间推进
        with patch.object(self.portfolio, 'put'):
            self.portfolio.advance_time(next_time)

        # 验证执行后信号被清空
        assert len(self.portfolio.signals) == 0, "执行后信号列表应该被清空"


@pytest.mark.integration
class TestTimeAdvanceTrigger:
    """测试时间推进触发机制"""

    def setup_method(self):
        """测试前设置"""
        self.portfolio = PortfolioT1Backtest()
        self.strategy = TestStrategy()
        self.sizer = TestSizer()

        self.portfolio.add_strategy(self.strategy)
        self.portfolio.set_sizer(self.sizer)
        self.portfolio.engine_id = "test_engine"

    def test_advance_time_triggers_execution(self):
        """测试时间推进触发执行"""
        # 第一步：在当前时间点做出决策
        current_time = datetime.datetime(2023, 1, 1, 9, 30)
        bar = Bar(code="000001.SZ", timestamp=current_time, close=Decimal("10.50"))
        price_event = EventPriceUpdate(price_info=bar, timestamp=current_time)

        with patch.object(self.portfolio, 'put'):
            self.portfolio.on_price_received(price_event)

        # 验证决策已保存但未执行
        assert len(self.portfolio.signals) > 0, "决策应该已保存"

        # 第二步：时间推进触发执行
        next_time = datetime.datetime(2023, 1, 1, 10, 30)
        with patch.object(self.portfolio, 'put') as mock_put:
            self.portfolio.advance_time(next_time)

        # 验证时间推进触发了执行
        assert mock_put.call_count > 0, "时间推进应该触发执行"

    def test_multiple_advance_time_cycles(self):
        """测试多个时间推进周期"""
        times = [
            datetime.datetime(2023, 1, 1, 9, 30),
            datetime.datetime(2023, 1, 1, 10, 30),
            datetime.datetime(2023, 1, 1, 11, 30)
        ]

        execution_counts = []

        for i, time_point in enumerate(times):
            # 在每个时间点做出决策
            bar = Bar(
                code="000001.SZ",
                timestamp=time_point,
                close=Decimal(f"{10.00 + i * 0.10}")
            )
            price_event = EventPriceUpdate(price_info=bar, timestamp=time_point)

            with patch.object(self.portfolio, 'put') as mock_put:
                self.portfolio.on_price_received(price_event)

                # 推进到下一个时间点（除了最后一个）
                if i < len(times) - 1:
                    next_time = times[i + 1]
                    self.portfolio.advance_time(next_time)
                    execution_counts.append(mock_put.call_count)

        # 验证每个周期都有执行动作
        assert len(execution_counts) == 2, "应该有2个执行周期"
        assert all(count > 0 for count in execution_counts), "每个周期都应该有执行"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])