#!/usr/bin/env python3
"""
默认分析器回测验证脚本

运行方式:
    cd /home/kaoru/Ginkgo
    python scripts/test_default_analyzer_backtest.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import datetime
from decimal import Decimal
import time

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


def main():
    print("=" * 60)
    print("🚀 默认分析器回测验证")
    print("=" * 60)

    # 开启调试模式
    GCONF.set_debug(True)

    # 数据库中000001.SZ的日期范围是 2023-12-01 ~ 2023-12-05
    start_date = datetime.datetime(2023, 12, 1)
    end_date = datetime.datetime(2023, 12, 5)

    print(f"\n📅 回测日期: {start_date.date()} ~ {end_date.date()}")

    # 1. 创建引擎
    print("\n1️⃣ 创建引擎...")
    engine = TimeControlledEventEngine(
        name="DefaultAnalyzerTest",
        mode=EXECUTION_MODE.BACKTEST,
        logical_time_start=start_date,
        timer_interval=0.001
    )
    engine.set_end_time(end_date)

    # 2. 创建Portfolio - 使用默认分析器
    print("\n2️⃣ 创建Portfolio（默认STANDARD分析器）...")
    portfolio = PortfolioT1Backtest(
        name="test_portfolio",
        use_default_analyzers=True,
        default_analyzer_set=DEFAULT_ANALYZER_SET.STANDARD
    )
    portfolio.add_cash(Decimal("1000000"))

    print(f"   ✅ 默认分析器: {list(portfolio.analyzers.keys())}")

    # 3. 创建策略组件
    print("\n3️⃣ 创建策略组件...")
    strategy = RandomSignalStrategy(
        buy_probability=0.9,
        sell_probability=0.05,
        max_signals=5
    )
    strategy.set_random_seed(42)

    sizer = FixedSizer(volume=1000)
    selector = FixedSelector(name="selector", codes=["000001.SZ"])

    # 4. 创建Broker
    print("\n4️⃣ 创建Broker...")
    broker = SimBroker(name="SimBroker", attitude=ATTITUDE_TYPES.OPTIMISTIC)
    gateway = TradeGateway(name="Gateway", brokers=[broker])

    # 5. 创建DataFeeder
    feeder = BacktestFeeder(name="test_feeder")

    # 6. 绑定组件
    print("\n5️⃣ 绑定组件...")
    engine.add_portfolio(portfolio)
    engine.bind_router(gateway)
    portfolio.add_strategy(strategy)
    portfolio.bind_sizer(sizer)
    portfolio.bind_selector(selector)
    engine.set_data_feeder(feeder)
    print("   ✅ 绑定完成")

    # 7. 运行回测
    print("\n6️⃣ 运行回测...")
    success = engine.start()
    if not success:
        print("   ❌ 引擎启动失败")
        return

    start_time = time.time()
    timeout = 60
    while engine.is_active and (time.time() - start_time) < timeout:
        time.sleep(0.1)

    print("   ✅ 回测完成")

    # 8. 输出结果
    print("\n" + "=" * 60)
    print("📊 回测结果")
    print("=" * 60)

    print(f"\n✅ 默认分析器状态:")
    for name, analyzer in portfolio.analyzers.items():
        if hasattr(analyzer, '_size'):
            print(f"   {name}: {analyzer._size}条记录")

    print(f"\n✅ 策略: {strategy.signal_count}个信号")

    print(f"\n✅ Portfolio:")
    print(f"   初始资金: ¥1,000,000.00")
    print(f"   期末现金: ¥{float(portfolio.cash):,.2f}")
    print(f"   期末冻结: ¥{float(portfolio.frozen):,.2f}")
    print(f"   期末净值: ¥{float(portfolio.worth):,.2f}")
    print(f"   持仓数量: {len(portfolio.positions)}")

    if 'net_value' in portfolio.analyzers:
        nv = portfolio.analyzers['net_value']
        if hasattr(nv, '_size') and nv._size > 0:
            values = nv._values[:nv._size]
            print(f"\n📈 净值曲线:")
            print(f"   起始: ¥{values[0]:,.2f}")
            print(f"   期末: ¥{values[-1]:,.2f}")

    print("\n" + "=" * 60)
    print("🎉 验证完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
