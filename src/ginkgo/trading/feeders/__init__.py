# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: 数据馈送模块导出基类/回测馈送/实盘馈送等数据馈送实现为引擎提供数据输入支持交易系统功能和组件集成提供完整业务支持






from ginkgo.trading.feeders.base_feeder import BaseFeeder
from ginkgo.trading.feeders.backtest_feeder import BacktestFeeder

__all__ = ["BaseFeeder", "BacktestFeeder"]
