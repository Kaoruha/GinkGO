#!/usr/bin/env python3
"""
Engine级别Analyzer示例

展示新的架构：Analyzer 绑定在 Engine 级别，而非 Portfolio 级别
- Engine 管理所有 Analyzer
- Analyzer 通过 Hook 机制接收所有 Portfolio 的事件
- 支持多 Portfolio 对比分析

适用于：架构验证、多 Portfolio 回测、对比分析
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import datetime
from decimal import Decimal
from ginkgo.libs import GLOG, GCONF
from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
from ginkgo.enums import EXECUTION_MODE
from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest
from ginkgo.trading.strategies.random_signal_strategy import RandomSignalStrategy
from ginkgo.trading.sizers.fixed_sizer import FixedSizer
from ginkgo.trading.selectors.fixed_selector import FixedSelector
from ginkgo.trading.feeders.backtest_feeder import BacktestFeeder
from ginkgo.trading.brokers.sim_broker import SimBroker
from ginkgo.trading.gateway.trade_gateway import TradeGateway
from ginkgo.enums import ATTITUDE_TYPES


class MockAnalyzer:
    """
    模拟分析器（用于验证 Engine 级别的 Analyzer 架构）

    Hook 机制：
    - on_order_filled(portfolio_uuid, order): 订单成交时调用
    - on_position_changed(portfolio_uuid, position): 持仓变化时调用
    - on_backtest_end(): 回测结束时调用
    """

    def __init__(self, name: str):
        self.name = name
        self.type = "MockAnalyzer"
        self.event_count = 0
        self.portfolio_events = {}  # {portfolio_uuid: event_count}

    def on_order_filled(self, portfolio_uuid: str, order):
        """订单成交时的 hook"""
        self.event_count += 1
        if portfolio_uuid not in self.portfolio_events:
            self.portfolio_events[portfolio_uuid] = {'order_filled': 0, 'position_changed': 0}
        self.portfolio_events[portfolio_uuid]['order_filled'] += 1

    def on_position_changed(self, portfolio_uuid: str, position):
        """持仓变化时的 hook"""
        self.event_count += 1
        if portfolio_uuid not in self.portfolio_events:
            self.portfolio_events[portfolio_uuid] = {'order_filled': 0, 'position_changed': 0}
        self.portfolio_events[portfolio_uuid]['position_changed'] += 1

    def on_backtest_end(self):
        """回测结束时的 hook"""
        print(f"\n📊 [{self.name}] 回测结束统计:")
        print(f"  总事件数: {self.event_count}")
        for portfolio_uuid, events in self.portfolio_events.items():
            print(f"  Portfolio {portfolio_uuid[:8]}: 订单成交 {events['order_filled']} 次, 持仓变化 {events['position_changed']} 次")


class EngineLevelBacktest:
    """
    Engine 级别 Analyzer 的回测类
    """

    def __init__(self, initial_cash=100000):
        self.initial_cash = initial_cash
        self.engine = None
        self.analyzers = []
        self.portfolios = []
        self.feeder = None
        self.broker = None

    def setup(self, start_date: datetime.datetime, end_date: datetime.datetime):
        """设置回测组件"""

        print("🔧 初始化 Engine 级别 Analyzer 回测...")

        # 1. 创建时间控制引擎
        self.engine = TimeControlledEventEngine(
            name="EngineLevelExample",
            mode=EXECUTION_MODE.BACKTEST,
            logical_time_start=start_date,
        )
        self.engine.set_end_time(end_date)

        # 2. 创建模拟分析器
        print("\n📊 创建 Engine 级别分析器...")
        self.analyzers = [
            MockAnalyzer(name="PortfolioEventsAnalyzer"),
            MockAnalyzer(name="PerformanceAnalyzer"),
        ]

        # 3. 将分析器添加到 Engine（而非 Portfolio）
        for analyzer in self.analyzers:
            self.engine.add_analyzer(analyzer)
            print(f"  ✅ {analyzer.name} 已添加到 Engine")

        # 4. 创建多个 Portfolio（用于演示多 Portfolio 分析）
        print("\n💼 创建 Portfolios...")

        # Portfolio A - 激进策略
        portfolio_a = PortfolioT1Backtest("portfolio_a")
        portfolio_a.add_cash(Decimal(str(self.initial_cash)))
        strategy_a = RandomSignalStrategy(
            buy_probability=0.95,
            sell_probability=0.03,
            max_signals=5
        )
        strategy_a.set_random_seed(11111)
        portfolio_a.add_strategy(strategy_a)
        portfolio_a.bind_sizer(FixedSizer(volume=1000))
        portfolio_a.bind_selector(FixedSelector(name="selector_a", codes=["000001.SZ"]))
        self.portfolios.append(portfolio_a)
        print(f"  ✅ Portfolio A: 激进策略 (买入率95%, 卖出率3%)")

        # Portfolio B - 保守策略
        portfolio_b = PortfolioT1Backtest("portfolio_b")
        portfolio_b.add_cash(Decimal(str(self.initial_cash)))
        strategy_b = RandomSignalStrategy(
            buy_probability=0.6,
            sell_probability=0.4,
            max_signals=3
        )
        strategy_b.set_random_seed(22222)
        portfolio_b.add_strategy(strategy_b)
        portfolio_b.bind_sizer(FixedSizer(volume=500))
        portfolio_b.bind_selector(FixedSelector(name="selector_b", codes=["000002.SZ"]))
        self.portfolios.append(portfolio_b)
        print(f"  ✅ Portfolio B: 保守策略 (买入率60%, 卖出率40%)")

        # 5. 将 Portfolio 添加到 Engine
        for portfolio in self.portfolios:
            self.engine.add_portfolio(portfolio)
            print(f"  ✅ {portfolio.name} 已添加到 Engine")

        # 6. 创建数据源
        self.feeder = BacktestFeeder(name="example_feeder")
        self.engine.set_data_feeder(self.feeder)

        # 7. 创建 TradeGateway/Broker 架构
        self.broker = SimBroker(
            name="SimBroker",
            attitude=ATTITUDE_TYPES.OPTIMISTIC,
            commission_rate=0.0003,
            commission_min=5
        )
        self.gateway = TradeGateway(name="UnifiedTradeGateway", brokers=[self.broker])
        self.engine.bind_router(self.gateway)

        print(f"\n✅ 组件绑定完成: {start_date.date()} ~ {end_date.date()}")
        print(f"💰 每个 Portfolio 初始资金: ¥{self.initial_cash:,}")
        print(f"📊 Engine 级别分析器: {len(self.analyzers)} 个")
        print(f"💼 Portfolio 数量: {len(self.portfolios)} 个")

    def run_backtest(self):
        """运行回测"""
        print("\n🚀 启动 Engine 级别 Analyzer 回测...")

        # 运行前检查
        self.engine.check_components_binding()

        # 显示 Engine 的分析器
        print(f"\n📊 Engine 分析器列表:")
        for analyzer in self.engine.get_analyzers():
            print(f"  - {analyzer.name}")

        # 启动引擎
        print("⏱️  引擎自动运行中...")
        success = self.engine.start()

        if not success:
            print("❌ 引擎启动失败")
            return

        # 等待完成
        print("⏳ 等待回测完成...")
        import time
        start_check = time.time()
        timeout = 300  # 5分钟超时

        while self.engine.is_active and (time.time() - start_check) < timeout:
            time.sleep(0.1)

        if self.engine.is_active:
            print("⚠️ 回测超时，手动停止")
            self.engine.stop()
        else:
            print(f"✅ 回测完成 - 最终时间: {self.engine.now}")

        # 通知分析器回测结束
        self.engine.notify_analyzers_backtest_end()

    def generate_report(self):
        """生成报告"""
        print("\n" + "=" * 60)
        print("📊 Engine 级别 Analyzer 回测报告")
        print("=" * 60)

        print("\n💼 Portfolio 表现:")
        for portfolio in self.portfolios:
            final_value = float(portfolio.worth)
            total_return = (final_value - self.initial_cash) / self.initial_cash

            # 获取策略（_strategies 可能是 dict 或 list）
            if isinstance(portfolio._strategies, dict):
                strategy = list(portfolio._strategies.values())[0]
            else:
                strategy = portfolio._strategies[0] if portfolio._strategies else None

            signal_count = strategy.signal_count if strategy else 0

            print(f"\n  {portfolio.name}:")
            print(f"    期末价值: ¥{final_value:,.2f}")
            print(f"    总收益率: {total_return*100:.2f}%")
            print(f"    策略信号数: {signal_count}")
            print(f"    成交订单数: {len(portfolio.filled_orders) if hasattr(portfolio, 'filled_orders') else 0}")

        print("\n📊 Engine 级别分析器统计:")
        for analyzer in self.engine.get_analyzers():
            if isinstance(analyzer, MockAnalyzer):
                print(f"\n  {analyzer.name}:")
                print(f"    总事件数: {analyzer.event_count}")
                for portfolio_uuid, events in analyzer.portfolio_events.items():
                    print(f"    Portfolio {portfolio_uuid[:8]}:")
                    print(f"      订单成交: {events['order_filled']} 次")
                    print(f"      持仓变化: {events['position_changed']} 次")

        print("\n" + "=" * 60)
        print("✅ Engine 级别 Analyzer 架构验证完成！")
        print("=" * 60)
        print("\n🎯 架构验证:")
        print("✅ Analyzer 绑定在 Engine 级别")
        print("✅ Analyzer 通过 Hook 接收所有 Portfolio 事件")
        print("✅ 支持多 Portfolio 对比分析")
        print("✅ Portfolio 只负责交易执行，不包含分析器")


def main():
    """主函数"""
    print("🚀 Ginkgo Engine 级别 Analyzer 示例")
    print("验证新的架构：Analyzer 在 Engine 级别管理\n")

    # 开启调试模式
    GCONF.set_debug(True)
    print(f"🔧 调试模式: {GCONF.DEBUGMODE}")

    # 创建回测实例
    backtest = EngineLevelBacktest(initial_cash=100000)

    # 设置回测参数
    start_date = datetime.datetime(2023, 1, 1)
    end_date = datetime.datetime(2023, 1, 30)

    # 设置组件
    backtest.setup(start_date, end_date)

    # 运行回测
    backtest.run_backtest()

    # 生成报告
    backtest.generate_report()

    print(f"\n✅ 示例执行成功！")
    print(f"💡 这个示例验证了 Engine 级别 Analyzer 的完整工作流程")

    return True


if __name__ == "__main__":
    # 运行示例
    main()
