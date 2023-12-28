from ginkgo.backtest.strategies.base_strategy import StrategyBase
from ginkgo.backtest.signal import Signal
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES


class StrategyScalping(StrategyBase):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(
        self,
        name: str = "Scalping",
        *args,
        **kwargs,
    ):
        super(StrategyScalping, self).__init__(5, name, *args, **kwargs)
        self.set_name(name)

    def cal(self, bar, *args, **kwargs):
        super(StrategyProfitLimit, self).cal()
        return None
        # code = bar.code
        # if code in self.portfolio.positions.keys():
        #     position = self.portfolio.positions[code]
        #     cost = position.cost
        #     price = position.price
        #     ratio = price / cost
        #     if ratio > (1 + self.profit_limit / 100):
        #         s = Signal(
        #             code=code,
        #             direction=DIRECTION_TYPES.SHORT,
        #             backtest_id=self.backtest_id,
        #             timestamp=self.portfolio.now,
        #         )
        #         return s
