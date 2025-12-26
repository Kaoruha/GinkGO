import time
import random
import datetime
from ginkgo.trading.events import EventSignalGeneration
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES


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
        # super(StrategyRandomChoice, self).cal(portfolio_info, event)

        # 使用print强制输出调用信息
        print(f"DEBUG: StrategyRandomChoice.cal() called - event code: {getattr(event, 'code', 'unknown')}")

        ching = random.randint(0, 100)
        direction = None
        if ching < 40:
            direction = DIRECTION_TYPES.LONG
        elif ching > 70:
            direction = DIRECTION_TYPES.SHORT

        print(f"DEBUG: Roll: {ching}, direction: {direction} at {portfolio_info.get('now', 'unknown')}")

        # 🔑 关键修复：使用 is None 并且在direction为None时直接返回
        if direction is None:
            print(f"DEBUG: No signal generated (neutral range: 40-70)")
            return []

        s = Signal(
            portfolio_id=portfolio_info.get("uuid", "unknown"),
            engine_id=getattr(self, 'engine_id', 'unknown'),
            timestamp=portfolio_info.get("now", datetime.datetime.now()),
            code=getattr(event, 'code', 'unknown'),
            direction=direction,
            reason=f"测试用策略，随机Roll的 {ching}",
            source=SOURCE_TYPES.STRATEGY,
        )
        return [s]
