#!/usr/bin/env python3
"""
金叉死叉策略回测示例 (Moving Average Crossover Strategy Backtest)

基于Ginkgo框架的事件驱动回测，展示：
1. 金叉死叉策略的使用
2. 移动平均线交叉信号
3. 长时间跨度回测（2020-2023，4年）
4. 完整的事件驱动流程

策略逻辑：
- 金叉（短期MA上穿长期MA）：买入信号
- 死叉（短期MA下穿长期MA）：卖出信号
- 默认参数：MA20（短期）和 MA60（长期）

适用于：策略开发者、量化交易学习、回测验证
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
from ginkgo.trading.strategies.moving_average_crossover import MovingAverageCrossover
from ginkgo.trading.sizers.fixed_sizer import FixedSizer
from ginkgo.trading.selectors.fixed_selector import FixedSelector
from ginkgo.trading.feeders.backtest_feeder import BacktestFeeder
from ginkgo.enums import EVENT_TYPES
from ginkgo.trading.routing.router import Router
from ginkgo.trading.brokers.sim_broker import SimBroker
from ginkgo.enums import ATTITUDE_TYPES
from ginkgo.trading.analysis.analyzers.net_value import NetValue


class MACrossoverBacktest:
    """
    金叉死叉策略回测类
    """

    def __init__(self, initial_cash=1000000, short_period=20, long_period=60):
        self.initial_cash = initial_cash
        self.short_period = short_period
        self.long_period = long_period
        self.engine = None
        self.portfolio = None
        self.strategy = None
        self.feeder = None
        self.router = None
        self.broker = None
        self.net_value_analyzer = None
        self.results = {}
        self.start_date = None
        self.end_date = None

    def setup(self, start_date: datetime.datetime, end_date: datetime.datetime,
              target_stocks=None):
        """设置回测组件和绑定关系"""

        # 保存日期
        self.start_date = start_date
        self.end_date = end_date

        print("🔧 初始化金叉死叉策略回测组件...")

        # 1. 创建时间控制引擎
        self.engine = TimeControlledEventEngine(
            name="MACrossoverBacktest",
            mode=EXECUTION_MODE.BACKTEST,
            logical_time_start=start_date,
            timer_interval=0.01,
        )
        self.engine.set_end_time(end_date)

        # 2. 创建投资组合
        self.portfolio = PortfolioT1Backtest("ma_crossover_portfolio")
        self.portfolio.add_cash(Decimal(str(self.initial_cash)))

        # 3. 创建金叉死叉策略
        self.strategy = MovingAverageCrossover(
            name=f"MA_Crossover_{self.short_period}_{self.long_period}",
            short_period=self.short_period,
            long_period=self.long_period,
            frequency='1d'
        )

        print(f"📊 策略配置:")
        print(f"   - 短期均线: MA{self.short_period}")
        print(f"   - 长期均线: MA{self.long_period}")
        print(f"   - 数据频率: 1d（日线）")

        # 创建选股器和下单器
        sizer = FixedSizer(volume=1000)  # 每次交易1000股

        # 默认股票列表
        if target_stocks is None:
            target_stocks = ["000001.SZ", "000002.SZ"]

        selector = FixedSelector(name="stock_selector", codes=target_stocks)

        # 4. 创建数据源
        self.feeder = BacktestFeeder(name="ma_crossover_feeder")

        # 5. 创建NetValue分析器
        self.net_value_analyzer = NetValue(name="net_value_analyzer")

        # 6. 创建Router/Broker架构
        print("🔗 创建Router/Broker架构...")
        self.broker = SimBroker(
            name="SimBroker",
            attitude=ATTITUDE_TYPES.OPTIMISTIC,
            commission_rate=0.0003,  # 万分之三佣金
            commission_min=5  # 最低5元
        )
        self.router = Router(name="UnifiedRouter", brokers=[self.broker])

        # 7. 按正确顺序绑定组件（自动事件注册）
        print("🔗 绑定组件关系...")
        self.engine.add_portfolio(self.portfolio)
        self.engine.bind_router(self.router)
        self.portfolio.add_strategy(self.strategy)
        self.portfolio.bind_sizer(sizer)
        self.portfolio.bind_selector(selector)
        self.portfolio.add_analyzer(self.net_value_analyzer)
        self.engine.set_data_feeder(self.feeder)

        print(f"✅ 绑定完成: {start_date.date()} ~ {end_date.date()}")
        print(f"💰 初始资金: ¥{self.initial_cash:,}")
        print(f"🎯 目标股票: {selector._interested}")
        print(f"📊 净值分析器已添加")

    def run_backtest(self):
        """运行回测"""
        print("\n🚀 启动金叉死叉策略回测...")

        # 运行前检查
        self.engine.check_components_binding()

        # 启动引擎
        print("⏱️  引擎自动运行中...")
        success = self.engine.start()

        if not success:
            print("❌ 引擎启动失败")
            return

        # 等待回测完成
        print("⏳ 等待回测完成...")

        import time
        start_check = time.time()
        timeout = 600  # 10分钟超时

        while self.engine.is_active and (time.time() - start_check) < timeout:
            time.sleep(0.1)

        if self.engine.is_active:
            print("⚠️ 回测超时，手动停止")
            self.engine.stop()
        else:
            print(f"✅ 回测完成 - 最终时间: {self.engine.now}")

    def generate_report(self):
        """生成回测报告"""
        print("\n" + "=" * 60)
        print("📊 金叉死叉策略回测报告")
        print("=" * 60)

        # 基本统计
        final_value = float(self.portfolio.worth)
        total_return = (final_value - self.initial_cash) / self.initial_cash

        # 交易统计
        order_count = len(self.portfolio.filled_orders) if hasattr(self.portfolio, "filled_orders") else 0
        position_count = len(self.portfolio.positions) if hasattr(self.portfolio, "positions") else 0

        print(f"📅 回测时间: {self.start_date.date()} ~ {self.end_date.date()}")
        print(f"📊 策略参数: MA{self.short_period} / MA{self.long_period}")
        print(f"💰 初始资金: ¥{self.initial_cash:,}")
        print(f"💎 期末价值: ¥{final_value:,.2f}")
        print(f"📈 总收益率: {total_return*100:.2f}%")
        print(f"📦 成交订单数: {order_count}")
        print(f"📊 持仓数量: {position_count}")

        # 显示成交订单详情
        if hasattr(self.portfolio, 'filled_orders') and self.portfolio.filled_orders:
            print(f"\n📋 成交订单明细 (最近10笔):")
            for i, order in enumerate(self.portfolio.filled_orders[-10:]):
                direction_str = "买入" if str(order.direction) == "DIRECTION_TYPES.LONG" else "卖出"
                print(f"  {i+1}. {direction_str} {order.code} "
                      f"{order.transaction_volume}股 @ ¥{order.transaction_price:.2f} "
                      f"@ {order.timestamp}")

        # 显示持仓情况
        if position_count > 0:
            print(f"\n💼 当前持仓:")
            for code, position in self.portfolio.positions.items():
                print(f"  {code}: {position.volume}股, 价值 ¥{float(position.worth):,.2f}")
        else:
            print(f"\n💼 当前持仓: 空仓")

        # 净值分析
        print(f"\n📊 净值分析:")
        if self.net_value_analyzer and hasattr(self.net_value_analyzer, 'current_net_value'):
            current_net_value = self.net_value_analyzer.current_net_value
            print(f"  当前净值: ¥{current_net_value:,.2f}")
            if hasattr(self.net_value_analyzer, '_size') and self.net_value_analyzer._size > 0:
                print(f"  净值记录数: {self.net_value_analyzer._size}")
                if self.net_value_analyzer._size > 1:
                    values = self.net_value_analyzer._values[:self.net_value_analyzer._size]
                    max_net_value = max(values)
                    min_net_value = min(values)
                    max_drawdown = (max_net_value - min_net_value) / max_net_value * 100
                    print(f"  最高净值: ¥{max_net_value:,.2f}")
                    print(f"  最低净值: ¥{min_net_value:,.2f}")
                    print(f"  最大回撤: {max_drawdown:.2f}%")

        # 策略信号统计
        if hasattr(self.strategy, '_ma_states'):
            print(f"\n📈 策略状态:")
            print(f"  跟踪股票数: {len(self.strategy._ma_states)}")

        print("\n" + "=" * 60)
        print("🎉 金叉死叉策略回测完成！")
        print("=" * 60)

        self.results = {
            "initial_cash": self.initial_cash,
            "final_value": final_value,
            "total_return_pct": f"{total_return*100:.2f}%",
            "order_count": order_count,
            "position_count": position_count
        }

        return self.results


def main():
    """主函数"""
    print("🚀 Ginkgo 金叉死叉策略回测示例")
    print("测试时间：2023年1月（1个月快速测试）\n")

    # 开启调试模式
    GCONF.set_debug(True)
    print(f"🔧 调试模式: {GCONF.DEBUGMODE}")

    # 创建回测实例
    # MA10/MA20 更短周期，适合短时间测试
    backtest = MACrossoverBacktest(
        initial_cash=1000000,  # 100万初始资金
        short_period=10,        # MA10 短期均线
        long_period=20          # MA20 长期均线
    )

    # 设置回测时间：2023年1月（1个月，快速测试）
    start_date = datetime.datetime(2023, 1, 1)
    end_date = datetime.datetime(2023, 1, 31)

    # 目标股票（可以修改）
    target_stocks = ["000001.SZ", "000002.SZ"]

    # 设置组件
    backtest.setup(start_date, end_date, target_stocks)

    # 运行回测
    backtest.run_backtest()

    # 生成报告
    results = backtest.generate_report()

    print(f"\n✅ 回测完成！")
    print(f"📈 关键指标: 收益率 {results['total_return_pct']}, 订单数 {results['order_count']}")
    print(f"💡 金叉死叉策略回测完成（如需测试更长时间，修改代码中的日期）")

    return results


if __name__ == "__main__":
    # 运行回测
    results = main()
