import time
import random
import datetime
from ginkgo.trading.events import EventSignalGeneration
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.data import get_bars


class StrategyRandomChoice(BaseStrategy):
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

        ching = random.randint(0, 100)
        direction = None
        if ching < 40:
            direction = DIRECTION_TYPES.LONG
        elif ching > 70:
            direction = DIRECTION_TYPES.SHORT

        self.log("DEBUG", f"Roll: {ching}, direction: {direction} at {self.now}")

        # 🔑 关键修复：使用 is None 并且在direction为None时直接返回
        if direction is None:
            self.log("DEBUG", f"No signal generated (neutral range: 40-70)")
            return []

        s = Signal(
            portfolio_id=portfolio_info["uuid"],
            engine_id=self.engine_id,
            timestamp=portfolio_info["now"],
            code=event.code,
            direction=direction,
            reason=f"测试用策略，随机Roll的 {ching}",
            source=SOURCE_TYPES.STRATEGY,
        )
        return [s]
