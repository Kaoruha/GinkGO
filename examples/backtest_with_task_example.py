#!/usr/bin/env python3
"""
带BacktestTask的回测示例

演示完整的回测流程，包括：
1. 创建BacktestTask记录
2. 运行事件驱动回测
3. 更新任务状态和结果
4. 保存AnalyzerRecord记录

适用于：验证BacktestTask和AnalyzerRecord数据生成
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
from ginkgo.trading.gateway.trade_gateway import TradeGateway
from ginkgo.trading.brokers.sim_broker import SimBroker
from ginkgo.enums import ATTITUDE_TYPES
from ginkgo.trading.analysis.analyzers.net_value import NetValue
from ginkgo import service_hub


class BacktestWithTaskExample:
    """
    带BacktestTask创建的回测示例
    """

    def __init__(self, initial_cash=100000):
        self.initial_cash = initial_cash
        self.engine = None
        self.portfolio = None
        self.strategy = None
        self.feeder = None
        self.gateway = None
        self.broker = None
        self.net_value_analyzer = None
        self.task_service = None
        self.run_id = None
        self.start_date = None
        self.end_date = None

    def setup(self, start_date: datetime.datetime, end_date: datetime.datetime):
        """设置回测组件"""
        # 保存时间范围
        self.start_date = start_date
        self.end_date = end_date
        """设置回测组件"""

        print("🔧 初始化回测组件...")

        # 1. 创建时间控制引擎
        self.engine = TimeControlledEventEngine(
            name="BacktestWithTaskExample",
            mode=EXECUTION_MODE.BACKTEST,
            logical_time_start=start_date,
            timer_interval=0.01,
        )
        self.engine.set_end_time(end_date)

        # 2. 创建投资组合
        self.portfolio = PortfolioT1Backtest("example_portfolio")
        self.portfolio.add_cash(Decimal(str(self.initial_cash)))

        # 3. 创建策略组件
        self.strategy = RandomSignalStrategy(buy_probability=0.9, sell_probability=0.05, max_signals=4)
        self.strategy.set_random_seed(12345)
        sizer = FixedSizer(volume=1000)
        selector = FixedSelector(name="stock_selector", codes=["000001.SZ", "000002.SZ"])

        # 4. 创建数据源
        self.feeder = BacktestFeeder(name="example_feeder")

        # 5. 创建NetValue分析器
        self.net_value_analyzer = NetValue(name="net_value_analyzer")

        # 6. 创建TradeGateway/Broker架构
        self.broker = SimBroker(
            name="SimBroker", attitude=ATTITUDE_TYPES.OPTIMISTIC, commission_rate=0.0003, commission_min=5
        )
        self.gateway = TradeGateway(name="UnifiedTradeGateway", brokers=[self.broker])

        # 7. 绑定组件关系
        print("🔗 绑定组件关系...")
        self.engine.add_portfolio(self.portfolio)
        self.engine.bind_router(self.gateway)
        self.portfolio.add_strategy(self.strategy)
        self.portfolio.bind_sizer(sizer)
        self.portfolio.bind_selector(selector)
        self.portfolio.add_analyzer(self.net_value_analyzer)
        self.engine.set_data_feeder(self.feeder)

        # 8. 生成run_id（在启动前设置，引擎会保留）
        import uuid
        self.run_id = uuid.uuid4().hex
        self.engine.set_run_id(self.run_id)
        print(f"📋 Run ID已设置: {self.run_id}")

        # 9. 获取服务
        self.task_service = service_hub.data.backtest_task_service()

        print(f"✅ 设置完成: {start_date.date()} ~ {end_date.date()}")

    def create_backtest_task(self) -> bool:
        """创建BacktestTask记录"""
        print("\n📝 创建BacktestTask记录...")

        try:
            # 使用已设置的run_id
            print(f"📋 使用Run ID: {self.run_id}")

            # 使用保存的时间范围
            start_time_dt = self.start_date
            end_time_dt = self.end_date

            # 创建任务
            result = self.task_service.create(
                run_id=self.run_id,  # 使用run_id而不是task_id
                name=f"Example_Task_{self.run_id[:8]}",
                engine_id=self.engine.engine_id,
                portfolio_id=self.portfolio.portfolio_id,
                backtest_start_date=start_time_dt,
                backtest_end_date=end_time_dt,
                config_snapshot={
                    "engine_name": self.engine.name,
                    "start_time": str(start_time_dt),
                    "end_time": str(end_time_dt),
                    "initial_cash": float(self.initial_cash),
                }
            )

            if result.is_success():
                print(f"✅ BacktestTask创建成功: {self.run_id}")
                return True
            else:
                print(f"❌ BacktestTask创建失败: {result.error}")
                return False

        except Exception as e:
            print(f"❌ 创建BacktestTask时出错: {e}")
            return False

    def run_backtest(self):
        """运行回测"""
        print("\n🚀 启动回测...")

        # 运行前检查
        self.engine.check_components_binding()

        # 启动引擎（会保留已设置的run_id）
        print("⏱️  引擎运行中...")
        success = self.engine.start()

        if not success:
            print("❌ 引擎启动失败")
            self._update_task_status("failed", error_message="引擎启动失败")
            return

        # 验证run_id未改变
        if self.engine.run_id != self.run_id:
            print(f"⚠️ 警告: run_id已改变! 预期:{self.run_id}, 实际:{self.engine.run_id}")
            self.run_id = self.engine.run_id

        # 等待完成
        print("⏳ 等待回测完成...")
        import time
        start_check = time.time()
        timeout = 300

        while self.engine.is_active and (time.time() - start_check) < timeout:
            time.sleep(0.1)

        if self.engine.is_active:
            print("⚠️ 回测超时")
            self.engine.stop()
            self._update_task_status("failed", error_message="回测超时")
        else:
            print(f"✅ 回测完成 - 最终时间: {self.engine.now}")

    def _update_task_status(self, status: str, error_message: str = None):
        """更新任务状态"""
        if not self.task_service or not self.run_id:
            return

        try:
            # 获取回测结果
            final_value = float(self.portfolio.worth)
            total_pnl = final_value - self.initial_cash

            # 更新任务
            self.task_service.update(
                uuid=self.run_id,
                status=status,
                end_time=datetime.datetime.now(),
                final_portfolio_value=str(final_value),
                total_pnl=str(total_pnl),
                error_message=error_message or "",
            )
            print(f"📊 任务状态已更新: {status}")
        except Exception as e:
            print(f"⚠️ 更新任务状态失败: {e}")

    def verify_results(self):
        """验证数据生成情况"""
        print("\n" + "=" * 60)
        print("📊 数据验证")
        print("=" * 60)

        # 1. 验证BacktestTask
        print("\n📝 BacktestTask验证:")
        task_result = self.task_service.get(run_id=self.run_id)
        if task_result.is_success() and task_result.data:
            task = task_result.data[0]
            print(f"  ✅ 找到BacktestTask:")
            print(f"     uuid: {task.uuid}")
            print(f"     name: {task.name}")
            print(f"     status: {task.status}")
            print(f"     final_portfolio_value: {task.final_portfolio_value}")
            print(f"     total_pnl: {task.total_pnl}")
        else:
            print(f"  ❌ 未找到BacktestTask")

        # 2. 验证AnalyzerRecord
        print("\n📊 AnalyzerRecord验证:")
        analyzer_record_crud = service_hub.data.cruds.analyzer_record()
        records = analyzer_record_crud.get_by_run_id(run_id=self.run_id, page_size=100)
        print(f"  ✅ 找到 {len(records)} 条AnalyzerRecord")

        if records:
            print(f"     分析器名称: {records[0].name}")
            print(f"     时间范围: {records[-1].timestamp} ~ {records[0].timestamp}")
            print(f"     最新净值: {records[0].value}")

        print("\n" + "=" * 60)
        print("🎉 验证完成！")
        print("=" * 60)


def main():
    """主函数"""
    print("🚀 带BacktestTask的回测示例")
    print("演示完整的数据生成流程\n")

    # 开启调试模式
    GCONF.set_debug(True)
    print(f"🔧 调试模式: {GCONF.DEBUGMODE}")

    # 创建回测实例
    backtest = BacktestWithTaskExample(initial_cash=100000)

    # 设置回测参数
    start_date = datetime.datetime(2023, 1, 1)
    end_date = datetime.datetime(2023, 1, 15)

    # 设置组件
    backtest.setup(start_date, end_date)

    # 创建BacktestTask
    if not backtest.create_backtest_task():
        print("❌ 无法创建BacktestTask，终止回测")
        return

    # 运行回测
    backtest.run_backtest()

    # 更新任务状态为完成
    backtest._update_task_status("completed")

    # 生成报告
    print("\n📈 回测结果:")
    print(f"  初始资金: ¥{backtest.initial_cash:,}")
    print(f"  期末价值: ¥{float(backtest.portfolio.worth):,.2f}")
    print(f"  总盈亏: ¥{float(backtest.portfolio.worth) - backtest.initial_cash:,.2f}")
    print(f"  策略信号数: {backtest.strategy.signal_count}")

    # 验证数据
    backtest.verify_results()

    return backtest.run_id


if __name__ == "__main__":
    run_id = main()
    print(f"\n✅ 回测完成！Run ID: {run_id}")
