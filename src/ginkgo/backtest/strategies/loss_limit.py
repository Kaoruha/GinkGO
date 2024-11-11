from decimal import Decimal
from ginkgo.backtest.strategies.base_strategy import StrategyBase
from ginkgo.backtest.signal import Signal
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES


class StrategyLossLimit(StrategyBase):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    # __abstract__ = False

    def __init__(
        self,
        name: str = "LossLimit",
        loss_limit: str = "10",
        *args,
        **kwargs,
    ):

        super(StrategyLossLimit, self).__init__(5, name, *args, **kwargs)
        self._loss_limit = Decimal(loss_limit)
        self.set_name(f"{name}_{self.loss_limit}")

    @property
    def loss_limit(self) -> int:
        return self._loss_limit

    def cal(self, portfolio_info, event, *args, **kwargs):
        super(StrategyLossLimit, self).cal(portfolio_info, event)
        code = event.code
        if code not in portfolio_info["positions"].keys():
            return
        position = portfolio_info["positions"][code]
        cost = position.cost
        price = position.price
        ratio = price / cost
        GLOG.DEBUG(f"Today's price ratio, P/C: {ratio}.")
        GLOG.DEBUG(f"Limit: {1 - self.loss_limit/100}, Price: {price}, Cost: {cost}, Ratio: {ratio}")
        if ratio < 1 - self.loss_limit / 100:
            s = Signal(
                portfolio_id=portfolio_info["uuid"],
                timestamp=portfolio_info["now"],
                code=code,
                direction=DIRECTION_TYPES.SHORT,
                source=SOURCE_TYPES.STRATEGY,
            )
            return s
