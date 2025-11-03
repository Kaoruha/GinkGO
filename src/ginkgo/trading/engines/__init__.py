from ginkgo.trading.engines.base_engine import BaseEngine
from ginkgo.trading.engines.event_engine import EventEngine
from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
from ginkgo.enums import EXECUTION_MODE

# Backward compatibility alias
BacktestEngine = TimeControlledEventEngine
