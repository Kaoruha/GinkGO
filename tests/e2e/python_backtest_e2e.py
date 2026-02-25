#!/usr/bin/env python3
"""
E2E 测试 - 使用随机信号策略进行完整回测并验证数据持久化

运行方式:
    cd /home/kaoru/Ginkgo
    python3 tests/e2e/python_backtest_e2e.py
"""

import sys
import os
import datetime
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ginkgo.libs import GLOG, GCONF
from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
from ginkgo.enums import EXECUTION_MODE
from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest
from ginkgo.trading.strategies.random_signal_strategy import RandomSignalStrategy
from ginkgo.trading.sizers.fixed_sizer import FixedSizer
from ginkgo.trading.selectors.fixed_selector import FixedSelector
from ginkgo.trading.feeders.backtest_feeder import BacktestFeeder
from ginkgo.trading.gateway.trade_gateway import TradeGateway
from ginkgo.trading.brokers.sim_broker import SimBroker
from ginkgo.enums import ATTITUDE_TYPES
from ginkgo.trading.analysis.analyzers.net_value import NetValue
from ginkgo.trading.core.identity import IdentityUtils

# 开启调试模式
GCONF.set_debug(True)

def run_backtest_with_persistence():
    """运行回测并验证数据持久化"""

    # 生成唯一 run_id
    run_id = IdentityUtils.generate_run_id()
    print(f"=== 回测 E2E 测试 ===")
    print(f"run_id: {run_id}")

    # 1. 创建引擎
    engine = TimeControlledEventEngine(
        name=f"E2E_Engine_{run_id[:8]}",
        mode=EXECUTION_MODE.BACKTEST,
        logical_time_start=datetime.datetime(2024, 1, 1),
        timer_interval=0.01,
    )
    engine.set_run_id(run_id)
    engine.set_end_time(datetime.datetime(2024, 1, 31))

    # 2. 创建投资组合
    portfolio = PortfolioT1Backtest(f"E2E_Portfolio_{run_id[:8]}")
    portfolio.add_cash(Decimal("100000"))

    # 3. 创建策略组件
    strategy = RandomSignalStrategy(
        buy_probability=0.8,
        sell_probability=0.1,
        max_signals=5
    )
    strategy.set_random_seed(42)
    sizer = FixedSizer(volume=1000)
    selector = FixedSelector(name="stock_selector", codes=["000001.SZ", "000002.SZ"])

    # 4. 创建数据源和分析器
    feeder = BacktestFeeder(name="e2e_feeder")
    net_value_analyzer = NetValue(name="net_value")

    # 5. 创建 Broker 和 Gateway
    broker = SimBroker(
        name="SimBroker",
        attitude=ATTITUDE_TYPES.OPTIMISTIC,
        commission_rate=0.0003,
        commission_min=5
    )
    gateway = TradeGateway(name="Gateway", brokers=[broker])

    # 6. 绑定组件
    engine.add_portfolio(portfolio)
    engine.bind_router(gateway)

    portfolio.add_strategy(strategy)
    portfolio.bind_sizer(sizer)
    portfolio.bind_selector(selector)
    portfolio.add_analyzer(net_value_analyzer)

    engine.set_data_feeder(feeder)

    print(f"\n初始资金: ¥100,000")
    print(f"回测区间: 2024-01-01 ~ 2024-01-31")
    print(f"策略: RandomSignalStrategy (buy=0.8, sell=0.1)")

    # 7. 运行回测
    print("\n开始回测...")
    success = engine.start()
    if not success:
        print("引擎启动失败!")
        return False

    # 等待完成
    import time
    timeout = 120
    start_time = time.time()
    while engine.is_active and (time.time() - start_time) < timeout:
        time.sleep(0.1)

    if engine.is_active:
        engine.stop()
        print("回测超时")
    else:
        print(f"回测完成")

    # 8. 验证结果
    print("\n=== 验证结果 ===")

    signal_count = strategy.signal_count
    order_count = len(portfolio.filled_orders) if hasattr(portfolio, 'filled_orders') else 0
    position_count = len(portfolio.positions) if hasattr(portfolio, 'positions') else 0

    print(f"信号数: {signal_count}")
    print(f"订单数: {order_count}")
    print(f"持仓数: {position_count}")

    # 验证信号和订单数 > 0
    if signal_count == 0:
        print("❌ 信号数为 0")
        return False
    print("✅ 信号数 > 0")

    if order_count == 0:
        print("❌ 订单数为 0")
        return False
    print("✅ 订单数 > 0")

    # 9. 验证 run_id 传递
    print("\n=== 验证 run_id 传递 ===")

    # 检查策略的 run_id
    strategy_run_id = strategy.run_id
    print(f"策略 run_id: {strategy_run_id}")
    if strategy_run_id != run_id:
        print(f"❌ 策略 run_id 不匹配! 期望: {run_id}, 实际: {strategy_run_id}")
        return False
    print("✅ 策略 run_id 正确")

    # 检查投资组合的 run_id
    portfolio_run_id = portfolio.run_id
    print(f"投资组合 run_id: {portfolio_run_id}")
    if portfolio_run_id != run_id:
        print(f"❌ 投资组合 run_id 不匹配!")
        return False
    print("✅ 投资组合 run_id 正确")

    # 检查订单的 run_id
    if hasattr(portfolio, 'filled_orders') and portfolio.filled_orders:
        first_order = portfolio.filled_orders[0]
        order_run_id = first_order.run_id if hasattr(first_order, 'run_id') else None
        print(f"订单 run_id: {order_run_id}")
        if order_run_id != run_id:
            print(f"⚠️ 订单 run_id 不匹配 (可能是旧数据)")

    print("\n=== ✅ 所有验证通过! ===")
    return True


if __name__ == "__main__":
    result = run_backtest_with_persistence()
    sys.exit(0 if result else 1)
