# Upstream: CLI命令, API接口, core.containers
# Downstream: engines.base_engine, engines.event_engine, engines.time_controlled_engine, enums.EXECUTION_MODE
# Role: 引擎模块包入口，导出BaseEngine基类、EventEngine事件引擎、TimeControlledEventEngine时间控制引擎及兼容别名






from ginkgo.trading.engines.base_engine import BaseEngine
from ginkgo.trading.engines.event_engine import EventEngine
from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
from ginkgo.enums import EXECUTION_MODE

# Backward compatibility alias
BacktestEngine = TimeControlledEventEngine

