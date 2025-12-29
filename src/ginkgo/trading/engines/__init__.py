# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: 引擎模块导出引擎基类/事件引擎/时间控制引擎等核心引擎组件支持交易系统功能和组件集成提供完整业务支持






from ginkgo.trading.engines.base_engine import BaseEngine
from ginkgo.trading.engines.event_engine import EventEngine
from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
from ginkgo.enums import EXECUTION_MODE

# Backward compatibility alias
BacktestEngine = TimeControlledEventEngine
