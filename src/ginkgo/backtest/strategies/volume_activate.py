from ginkgo.backtest.strategies.base_strategy import StrategyBase
from ginkgo.backtest.signal import Signal
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.backtest.events import EventSignalGeneration
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
import time


class StrategyVolumeActivate(StrategyBase):
    abstract = False

    def __init__(self, spans: int = 20, name: str = "VolumeActivate", *args, **kwargs):
        super(StrategyVolumeActivate, self).__init__(
            spans=spans, name=name, *args, **kwargs
        )
        self._volume_mean = 0
        self._volume_std = 0
        self.win = 0
        self.loss = 0

    def cal(self, bar, *args, **kwargs):
        super(StrategyVolumeActivate, self).cal()
        self.on_price_update(bar)
        code = bar.code
        df = self.raw[code]
        self._volume_mean = df["volume"].mean()
        self._volume_std = df["volume"].std()

        r = bar.volume / self._volume_mean
        if self.raw[code].shape[0] < 2:
            return
        elif r < 0.67 and r > 0.6:
            GLOG.INFO(f"Will Gen Signal about {code}")
            signal = Signal()
            signal.set_source(SOURCE_TYPES.STRATEGY)
            signal.set(
                code,
                DIRECTION_TYPES.LONG,
                self.portfolio.now,
            )
            return signal
