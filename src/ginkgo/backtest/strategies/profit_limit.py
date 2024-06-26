from ginkgo.backtest.strategies.base_strategy import StrategyBase
from ginkgo.backtest.signal import Signal
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES


class StrategyProfitLimit(StrategyBase):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(
        self,
        name: str = "ProfitLimit",
        profit_limit: int = 10,
        *args,
        **kwargs,
    ):
        super(StrategyProfitLimit, self).__init__(5, name, *args, **kwargs)
        self._profit_limit = int(profit_limit)
        self.set_name(f"{name}{self.profit_limit}Per")

    @property
    def profit_limit(self) -> int:
        return self._profit_limit

    def cal(self, code: str = "", *args, **kwargs):
        super(StrategyProfitLimit, self).cal()
        if code in self.portfolio.positions.keys():
            position = self.portfolio.positions[code]
            cost = position.cost
            price = position.price
            ratio = price / cost
            GLOG.DEBUG(f"Today's price ratio, P/C: {ratio}.")
            GLOG.DEBUG(
                f"Limit: {1 + self.profit_limit/100}, Price: {price}, Cost: {cost}, Ratio: {ratio}"
            )
            if ratio > (1 + self.profit_limit / 100):
                s = Signal(
                    code=code,
                    direction=DIRECTION_TYPES.SHORT,
                    backtest_id=self.backtest_id,
                    timestamp=self.portfolio.now,
                )
                return s
