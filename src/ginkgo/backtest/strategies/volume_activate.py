import time
import datetime
from ginkgo.backtest.events import EventSignalGeneration
from ginkgo.backtest.signal import Signal
from ginkgo.backtest.strategies.base_strategy import StrategyBase
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES


class StrategyVolumeActivate(StrategyBase):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, name: str = "VolumeActivate", spans: int = 20, *args, **kwargs):
        super(StrategyVolumeActivate, self).__init__(spans=spans, name=name, *args, **kwargs)
        self._volume_mean = 0
        self._volume_std = 0
        self.win = 0
        self.loss = 0

    def cal(self, portfolio, event, *args, **kwargs):
        super(StrategyVolumeActivate, self).cal(portfolio, event)
        return
        # df = GDATA.get_daybar_df(
        #     code, self.now - datetime.timedelta(days=self.attention_spans), self.now
        # )

        # if df.shape[0] == 0:
        #     return
        # self._volume_mean = df["volume"].mean()
        # self._volume_std = df["volume"].std()

        # r = df["volume"].iloc[-1] / self._volume_mean
        # if r < 0.67 and r > 0.6:
        #     GLOG.INFO(f"Will Gen Signal about {code}")
        #     signal = Signal()
        #     signal.set_source(SOURCE_TYPES.STRATEGY)
        #     signal.set(
        #         code,
        #         DIRECTION_TYPES.LONG,
        #         self.portfolio.now,
        #         self.backtest_id,
        #     )
        #     return signal
