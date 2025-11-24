#!/usr/bin/env python3
"""
测试灵活的上下文传播机制

验证无论组件绑定顺序如何，所有组件都能正确获得engine的run_id
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from ginkgo.trading.engines.event_engine import EventEngine
from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest
from ginkgo.trading.time.providers import LogicalTimeProvider
import datetime

# 测试用的简单策略和Sizer（避免跨模块依赖）
from decimal import Decimal
from ginkgo.trading.strategies import BaseStrategy
from ginkgo.trading.bases.sizer_base import SizerBase
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.entities.order import Order
from ginkgo.enums import DIRECTION_TYPES

class TestStrategy(BaseStrategy):
    """测试策略 - 简单突破策略"""
    def __init__(self, threshold=Decimal("10.00")):
        super().__init__()
        self.threshold = threshold
        self.signals_generated = []

    def cal(self, portfolio_info, event, *args, **kwargs):
        if hasattr(event, 'close') and event.close > self.threshold:
            signal = Signal(
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                reason=f"价格{event.close}突破{self.threshold}",
                portfolio_id=portfolio_info.get("portfolio_id", "test"),
                engine_id=portfolio_info.get("engine_id", "test")
            )
            self.signals_generated.append(signal)
            return [signal]
        return []

class TestSizer(SizerBase):
    """测试Sizer"""
    def __init__(self, volume=100):
        super().__init__()
        self.volume = volume
        self.orders_created = []

    def cal(self, portfolio_info, signal):
        order = Order(
            code=signal.code,
            direction=signal.direction,
            volume=self.volume,
            portfolio_id=signal.portfolio_id,
            engine_id=signal.engine_id
        )
        self.orders_created.append(order)
        return order

def test_flexible_context_propagation():
    """测试灵活的上下文传播机制"""
    print("🧪 测试灵活的上下文传播机制")

    # 创建引擎和组件
    engine = EventEngine()
    engine.engine_id = "test_flexible_engine"
    engine.generate_run_id()

    portfolio = PortfolioT1Backtest("test_portfolio")
    strategy = TestStrategy()
    sizer = TestSizer()

    # 设置时间提供者
    time_provider = LogicalTimeProvider(
        initial_time=datetime.datetime(2023, 1, 1, 9, 30, tzinfo=datetime.timezone.utc)
    )
    portfolio.set_time_provider(time_provider)

    print(f"引擎run_id: {engine.run_id}")
    print("=" * 50)

    # 测试方案1：先绑定组件，后绑定引擎（原来的问题场景）
    print("📋 方案1：先绑定组件，后绑定引擎")

    # 步骤1：先绑定组件到portfolio
    portfolio.add_strategy(strategy)
    portfolio.bind_sizer(sizer)

    print(f"绑定portfolio后 - Strategy run_id: {strategy.run_id}")
    print(f"绑定portfolio后 - Sizer run_id: {sizer.run_id}")

    # 步骤2：后绑定引擎到portfolio（应该自动传播到已绑定的组件）
    portfolio.bind_engine(engine)

    print(f"绑定engine后 - Portfolio run_id: {portfolio.run_id}")
    print(f"绑定engine后 - Strategy run_id: {strategy.run_id}")
    print(f"绑定engine后 - Sizer run_id: {sizer.run_id}")

    # 验证所有组件都有相同的run_id
    assert portfolio.run_id == engine.run_id, "Portfolio应该有engine的run_id"
    assert strategy.run_id == engine.run_id, "Strategy应该有engine的run_id"
    assert sizer.run_id == engine.run_id, "Sizer应该有engine的run_id"

    print("✅ 方案1通过：所有组件都正确获得了run_id")
    print("=" * 50)

    # 测试方案2：先绑定引擎，后绑定组件（推荐场景）
    print("📋 方案2：先绑定引擎，后绑定组件")

    # 创建新的组件进行测试
    portfolio2 = PortfolioT1Backtest("test_portfolio2")
    strategy2 = TestStrategy()
    sizer2 = TestSizer()
    portfolio2.set_time_provider(time_provider)

    # 步骤1：先绑定引擎
    portfolio2.bind_engine(engine)

    print(f"绑定engine后 - Portfolio run_id: {portfolio2.run_id}")

    # 步骤2：后绑定组件（应该自动获得engine的run_id）
    portfolio2.add_strategy(strategy2)
    portfolio2.bind_sizer(sizer2)

    print(f"绑定组件后 - Strategy run_id: {strategy2.run_id}")
    print(f"绑定组件后 - Sizer run_id: {sizer2.run_id}")

    # 验证所有组件都有相同的run_id
    assert portfolio2.run_id == engine.run_id, "Portfolio应该有engine的run_id"
    assert strategy2.run_id == engine.run_id, "Strategy应该有engine的run_id"
    assert sizer2.run_id == engine.run_id, "Sizer应该有engine的run_id"

    print("✅ 方案2通过：所有组件都正确获得了run_id")
    print("=" * 50)

    # 测试方案3：混合绑定顺序
    print("📋 方案3：混合绑定顺序")

    # 创建新的组件进行测试
    portfolio3 = PortfolioT1Backtest("test_portfolio3")
    strategy3 = TestStrategy()
    sizer3 = TestSizer()
    portfolio3.set_time_provider(time_provider)

    # 混合顺序：sizer -> engine -> strategy
    portfolio3.bind_sizer(sizer3)
    print(f"绑定sizer后 - Sizer run_id: {sizer3.run_id}")

    portfolio3.bind_engine(engine)
    print(f"绑定engine后 - Portfolio run_id: {portfolio3.run_id}")
    print(f"绑定engine后 - Sizer run_id: {sizer3.run_id}")

    portfolio3.add_strategy(strategy3)
    print(f"绑定strategy后 - Strategy run_id: {strategy3.run_id}")

    # 验证所有组件都有相同的run_id
    assert portfolio3.run_id == engine.run_id, "Portfolio应该有engine的run_id"
    assert strategy3.run_id == engine.run_id, "Strategy应该有engine的run_id"
    assert sizer3.run_id == engine.run_id, "Sizer应该有engine的run_id"

    print("✅ 方案3通过：所有组件都正确获得了run_id")
    print("=" * 50)

    print("🎉 所有测试通过！上下文传播机制工作正常")
    print("💡 现在开发者可以以任意顺序组装组件，无需担心上下文传播问题")

if __name__ == "__main__":
    test_flexible_context_propagation()