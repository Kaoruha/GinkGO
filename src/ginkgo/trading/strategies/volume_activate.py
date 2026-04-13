# Upstream: PortfolioBase, ComponentFactoryService
# Downstream: BaseStrategy, IDataFeeder, Signal, EventSignalGeneration, DIRECTION_TYPES
# Role: 成交量激活策略 — 通过 data_feeder 获取历史成交量检测均值偏离






import time
import datetime
from ginkgo.trading.events import EventSignalGeneration
from ginkgo.trading.strategies.strategy_base import BaseStrategy
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.libs import GLOG


class StrategyVolumeActivate(BaseStrategy):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, name: str = "VolumeActivate", spans: str = "20", *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self._spans = int(spans)
        self.win = 0
        self.loss = 0

    def cal(self, portfolio_info, event, *args, **kwargs):
        super().cal(portfolio_info, event)
        date_start = self.business_timestamp + datetime.timedelta(days=-self._spans)
        date_end = self.business_timestamp
        df = self.data_feeder.get_historical_data(
            symbols=[event.code], start_time=date_start,
            end_time=date_end, data_type="bar"
        )
        if df is None or df.empty:
            return []
        mean = df["volume"].mean()
        std = df["volume"].std()
        r = df["volume"].iloc[-1] / mean
        if r < 0.67 and r > 0.6:
            GLOG.INFO(f"Gen Signal about {event.code} from {self.name}")
            s = self.create_signal(
                code=event.code,
                direction=DIRECTION_TYPES.LONG,
                reason="Volume Activate",
                business_timestamp=portfolio_info.get("now"),
            )
            return [s]

        # 如果没有生成信号，返回空列表
        return []
