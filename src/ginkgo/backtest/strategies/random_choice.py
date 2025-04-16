import time
import random
import datetime
from ginkgo.backtest.events import EventSignalGeneration
from ginkgo.backtest.signal import Signal
from ginkgo.backtest.strategies.base_strategy import StrategyBase
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.data import get_bars


class StrategyRandomChoice(StrategyBase):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, name: str = "RandomCHoiceForTest", *args, **kwargs):
        super(StrategyRandomChoice, self).__init__(name, *args, **kwargs)
        self._spans = 10
        self.win = 0
        self.loss = 0

    def cal(self, portfolio_info, event, *args, **kwargs):
        super(StrategyRandomChoice, self).cal(portfolio_info, event)
        date_start = self.now + datetime.timedelta(days=-self._spans)
        date_end = self.now
        df = get_bars(event.code, date_start, date_end, as_dataframe=True)
        mean = df["volume"].mean()
        std = df["volume"].std()
        r = df["volume"].iloc[-1] / mean

        ching = random.randint(0, 100)
        direction = None
        if ching < 40:
            direction = DIRECTION_TYPES.LONG
        elif ching > 70:
            direction = DIRECTION_TYPES.SHORT
        self.log("DEBUG", f"Roll: {ching}, direction: {direction}  {self.now}")

        if direction == None:
            return

        s = Signal(
            portfolio_id=portfolio_info["uuid"],
            engine_id=self.engine_id,
            timestamp=portfolio_info["now"],
            code=event.code,
            direction=direction,
            reason="测试用策略，随机Roll的",
            source=SOURCE_TYPES.STRATEGY,
        )
        return s
