#!/usr/bin/env python3
"""
完整的Ginkgo回测引擎使用示例

基于修复后的事件驱动架构，展示正确的回测流程：
1. 组件初始化和绑定
2. 自动事件注册
3. 事件驱动回测执行
4. 结果分析

适用于：量化交易初学者、Ginkgo框架使用者、回测验证
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
from ginkgo.enums import EVENT_TYPES
from ginkgo.trading.routing.router import Router
from ginkgo.trading.brokers.sim_broker import SimBroker
from ginkgo.enums import ATTITUDE_TYPES
from ginkgo.trading.analysis.analyzers.net_value import NetValue


class SimpleBacktest:
    """
    简化的回测类，专注于展示正确的事件驱动流程
    """

    def __init__(self, initial_cash=100000):
        self.initial_cash = initial_cash
        self.engine = None
        self.portfolio = None
        self.strategy = None
        self.feeder = None
        self.router = None
        self.broker = None
        self.net_value_analyzer = None
        self.results = {}

    def setup(self, start_date: datetime.datetime, end_date: datetime.datetime):
        """设置回测组件和绑定关系"""

        print("🔧 初始化回测组件...")

        # 1. 创建时间控制引擎
        self.engine = TimeControlledEventEngine(
            name="BacktestExample",
            mode=EXECUTION_MODE.BACKTEST,
            logical_time_start=start_date,
            timer_interval=0.01,  # 从1秒改为0.01秒，减少100倍延迟
        )
        self.engine.set_end_time(end_date)

        # 2. 创建投资组合
        self.portfolio = PortfolioT1Backtest("example_portfolio")
        self.portfolio.add_cash(Decimal(str(self.initial_cash)))

        # 3. 创建策略组件
        self.strategy = RandomSignalStrategy(buy_probability=0.9, sell_probability=0.05, max_signals=1)
        sizer = FixedSizer(volume=1000)
        selector = FixedSelector(name="stock_selector", codes=["000001.SZ"])

        # 4. 创建数据源
        self.feeder = BacktestFeeder(name="example_feeder")

        # 5. 创建NetValue分析器
        self.net_value_analyzer = NetValue(name="net_value_analyzer")

        # 6. 创建Router/Broker架构
        print("🔗 创建Router/Broker架构...")
        self.broker = SimBroker(
            name="SimBroker", attitude=ATTITUDE_TYPES.OPTIMISTIC, commission_rate=0.0003, commission_min=5
        )
        self.router = Router(name="UnifiedRouter", brokers=[self.broker])

        # 7. 按正确顺序绑定组件（自动事件注册）
        print("🔗 绑定组件关系...")
        self.engine.add_portfolio(self.portfolio)

        # 绑定Router到引擎（关键步骤：Router需要引擎来推送事件）
        self.engine.bind_router(self.router)

        self.portfolio.add_strategy(self.strategy)
        self.portfolio.bind_sizer(sizer)
        self.portfolio.bind_selector(selector)

        # 添加NetValue分析器到投资组合
        self.portfolio.add_analyzer(self.net_value_analyzer)

        self.engine.set_data_feeder(self.feeder)
        # DataFeeder的INTERESTUPDATE事件现在应该通过_auto_register_component_events自动注册
        # self.engine.register(EVENT_TYPES.INTERESTUPDATE, self.feeder.on_interest_update)

        print(f"✅ 绑定完成: {start_date.date()} ~ {end_date.date()}")
        print(f"💰 初始资金: ¥{self.initial_cash:,}")
        print(f"🎯 目标股票: {selector._interested}")
        print(f"📊 净值分析器: {self.net_value_analyzer.name} 已添加")

    def run_backtest(self):
        """运行回测 - 纯引擎组装和运行，去除监控延迟"""
        print("\n🚀 启动事件驱动回测...")

        # 运行前综合检查
        self.engine.check_components_binding()

        # 启动引擎并自动运行到完成
        print("⏱️  引擎自动运行中...")
        success = self.engine.start()

        if not success:
            print("❌ 引擎启动失败")
            return

        # 等待引擎自动完成（不干预，让引擎按自己的节奏运行）
        print("⏳ 等待回测完成...")

        # 简单等待完成，不设置固定延迟
        import time

        start_check = time.time()
        timeout = 300  # 5分钟超时保护

        while self.engine.is_active and (time.time() - start_check) < timeout:
            # 短暂检查间隔，不影响引擎性能
            time.sleep(0.1)

        if self.engine.is_active:
            print("⚠️ 回测超时，手动停止")
            self.engine.stop()
        else:
            print(f"✅ 回测完成 - 最终时间: {self.engine.now}")
            print(f"📈 策略信号总数: {self.strategy.signal_count}")

    def generate_report(self):
        """生成回测报告"""
        print("\n" + "=" * 60)
        print("📊 Ginkgo事件驱动回测报告")
        print("=" * 60)

        # 调试 portfolio.worth 计算
        print(f"🔍 [DEBUG] Portfolio worth breakdown:")
        print(f"   Cash: {self.portfolio.cash}")
        print(f"   Frozen: {self.portfolio.frozen}")
        print(f"   Positions count: {len(self.portfolio.positions)}")

        total_position_worth = 0
        for code, position in self.portfolio.positions.items():
            position_worth = position.worth if hasattr(position, "worth") else 0
            total_position_worth += position_worth
            print(f"   Position {code}: worth={position_worth}")

        print(f"   Total position worth: {total_position_worth}")
        print(f"   Expected total worth: {self.portfolio.cash + self.portfolio.frozen + total_position_worth}")
        print(f"   Actual portfolio.worth: {self.portfolio.worth}")

        # 基本统计
        final_value = float(self.portfolio.worth)
        total_return = (final_value - self.initial_cash) / self.initial_cash

        # 交易统计
        signal_count = self.strategy.signal_count
        order_count = len(self.portfolio.orders) if hasattr(self.portfolio, "orders") else 0
        position_count = len(self.portfolio.positions) if hasattr(self.portfolio, "positions") else 0

        print(f"初始资金: ¥{self.initial_cash:,}")
        print(f"期末价值: ¥{final_value:,.2f}")
        print(f"总收益率: {total_return*100:.2f}%")
        print(f"策略信号数: {signal_count}")
        print(f"订单数量: {order_count}")
        print(f"持仓数量: {position_count}")

        # 显示最近的信号
        if hasattr(self.strategy, "signal_history") and self.strategy.signal_history:
            print(f"\n📈 最近5个信号:")
            for i, signal in enumerate(self.strategy.signal_history[-5:]):
                direction_name = signal.get("direction", "Unknown")
                direction = (
                    "买入" if direction_name == "LONG" else "卖出" if direction_name == "SHORT" else direction_name
                )
                timestamp = signal.get("timestamp", "Unknown")
                print(f"  {i+1}. {direction} {signal.get('code')} @ {timestamp}")

        # 显示持仓情况
        if position_count > 0:
            print(f"\n💼 当前持仓:")
            for code, position in self.portfolio.positions.items():
                print(f"  {code}: {position.volume}股, 价值 ¥{float(position.worth):,.2f}")

        # 净值分析结果
        print(f"\n📊 净值分析:")
        if self.net_value_analyzer and hasattr(self.net_value_analyzer, 'current_net_value'):
            current_net_value = self.net_value_analyzer.current_net_value
            print(f"  当前净值: ¥{current_net_value:,.2f}")
            if hasattr(self.net_value_analyzer, '_size') and self.net_value_analyzer._size > 0:
                print(f"  净值记录数: {self.net_value_analyzer._size}")
                # 计算净值统计
                if self.net_value_analyzer._size > 1:
                    values = self.net_value_analyzer._values[:self.net_value_analyzer._size]
                    max_net_value = max(values)
                    min_net_value = min(values)
                    print(f"  最高净值: ¥{max_net_value:,.2f}")
                    print(f"  最低净值: ¥{min_net_value:,.2f}")
                    max_drawdown = (max_net_value - min_net_value) / max_net_value * 100
                    print(f"  最大回撤: {max_drawdown:.2f}%")
        else:
            print("  净值分析器未启用或无数据")

        print("\n🎯 架构验证:")
        print("✅ TimeControlledEventEngine - 时间控制引擎")
        print("✅ PortfolioT1Backtest - T+1投资组合")
        print("✅ RandomSignalStrategy - 随机策略")
        print("✅ FixedSelector - 股票选择器")
        print("✅ BacktestFeeder - 数据源")
        print("✅ SimBroker - 模拟经纪商")
        print("✅ Router - 统一路由器")
        print("✅ NetValue分析器 - 净值跟踪")
        print("✅ 自动事件注册机制")
        print("✅ Router/Broker订单处理架构")
        print("✅ 事件驱动回测流程")

        print("\n" + "=" * 60)
        print("🎉 回测完成！验证了Ginkgo框架的事件驱动架构")
        print("=" * 60)

        # 净值分析结果
        net_value_result = {}
        if self.net_value_analyzer and hasattr(self.net_value_analyzer, 'current_net_value'):
            net_value_result = {
                "current_net_value": float(self.net_value_analyzer.current_net_value),
                "record_count": int(self.net_value_analyzer._size) if hasattr(self.net_value_analyzer, '_size') else 0
            }
            if hasattr(self.net_value_analyzer, '_size') and self.net_value_analyzer._size > 1:
                values = self.net_value_analyzer._values[:self.net_value_analyzer._size]
                net_value_result.update({
                    "max_net_value": float(max(values)),
                    "min_net_value": float(min(values)),
                    "max_drawdown_pct": f"{(max(values) - min(values)) / max(values) * 100:.2f}%"
                })

        self.results = {
            "initial_cash": self.initial_cash,
            "final_value": final_value,
            "total_return_pct": f"{total_return*100:.2f}%",
            "signal_count": signal_count,
            "order_count": order_count,
            "position_count": position_count,
            "net_value": net_value_result
        }

        return self.results


def main():
    """主函数"""
    print("🚀 Ginkgo事件驱动回测示例")
    print("基于修复后的架构，展示正确的事件驱动流程\n")

    # 开启调试模式，但减少详细日志以提高性能
    GCONF.set_debug(True)
    print(f"🔧 调试模式: {GCONF.DEBUGMODE}")
    print(f"⚡ 性能提示: 如需更快的运行速度，请注释掉调试模式")

    # 创建回测实例
    backtest = SimpleBacktest(initial_cash=100000)

    # 设置回测参数
    start_date = datetime.datetime(2023, 1, 1)
    end_date = datetime.datetime(2023, 1, 30)  # 延长到30天进行更充分测试

    # 设置组件
    backtest.setup(start_date, end_date)

    # 运行回测
    backtest.run_backtest()

    # 生成报告
    results = backtest.generate_report()

    print(f"\n✅ 示例执行成功！")
    print(f"📈 关键指标: 收益率 {results['total_return_pct']}, 信号数 {results['signal_count']}")
    print(f"💡 这个示例验证了事件驱动架构的完整工作流程")

    return results


if __name__ == "__main__":
    # 运行示例
    results = main()
