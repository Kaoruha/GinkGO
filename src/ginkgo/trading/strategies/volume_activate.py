# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: Volume Activate策略继承BaseStrategy实现VolumeActivate成交量激活交易逻辑






import time
import datetime
from ginkgo.trading.events import EventSignalGeneration
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.data import get_bars


class StrategyVolumeActivate(BaseStrategy):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, name: str = "VolumeActivate", spans: str = "20", *args, **kwargs):
        super(StrategyVolumeActivate, self).__init__(name, *args, **kwargs)
        self._spans = int(spans)
        self.win = 0
        self.loss = 0

    def cal(self, portfolio_info, event, *args, **kwargs):
        super(StrategyVolumeActivate, self).cal(portfolio_info, event)
        date_start = self.now + datetime.timedelta(days=-self._spans)
        date_end = self.now
        df = get_bars(event.code, date_start, date_end, as_dataframe=True)
        if df.shape[0] == 0:
            return []
        mean = df["volume"].mean()
        std = df["volume"].std()
        r = df["volume"].iloc[-1] / mean
        if r < 0.67 and r > 0.6:
            self.log("INFO", f"Gen Signal about {event.code} from {self.name}")
            s = Signal(
                portfolio_id=portfolio_info["uuid"],
                engine_id=self.engine_id,
                timestamp=portfolio_info["now"],
                code=event.code,
                direction=DIRECTION_TYPES.LONG,
                reason="Volume Activate",
                source=SOURCE_TYPES.STRATEGY,
            )
            return [s]
        
        # 如果没有生成信号，返回空列表
        return []
