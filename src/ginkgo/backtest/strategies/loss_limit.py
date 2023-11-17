from ginkgo.backtest.strategies.base_strategy import StrategyBase
from ginkgo.backtest.signal import Signal
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES


class StrategyLossLimit(StrategyBase):
    __abstract__ = False

    def __init__(
        self,
        name: str = "LossLimit",
        loss_limit: int = 10,
        *args,
        **kwargs,
    ):
        super(StrategyLossLimit, self).__init__(name, *args, **kwargs)
        self._loss_limit = loss_limit
        self.set_name(f"{name}{self.loss_limit}Per")

    @property
    def loss_limit(self) -> int:
        return self._loss_limit

    def cal(self, bar, *args, **kwargs):
        super(StrategyLossLimit, self).cal()
        code = bar.code
        if code in self.portfolio.positions.keys():
            position = self.portfolio.positions[code]
            cost = position.cost
            price = position.price
            ratio = price / cost
            if 1 - self.loss_limit / 100:
                s = Signal(
                    code=code,
                    direction=DIRECTION_TYPES.SHORT,
                    backtest_id=self.backtest_id,
                    timestamp=self.portfolio.now,
                )
                return s
