from ginkgo.backtest.strategies.base_strategy import StrategyBase


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
        from ginkgo.backtest.signal import Signal
        from ginkgo.libs.ginkgo_logger import GLOG
        from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES

        super(StrategyLossLimit, self).__init__(5, name, *args, **kwargs)
        self._loss_limit = int(loss_limit)
        self.set_name(f"{name}{self.loss_limit}Per")

    @property
    def loss_limit(self) -> int:
        return self._loss_limit

    def cal(self, portfolio, event, *args, **kwargs):
        super(StrategyLossLimit, self).cal(portfolio, event)
        code = event.code
        if code not in portfolio.positions.keys():
            return
        position = portfolio.positions[code]
        cost = position.cost
        price = position.price
        ratio = price / cost
        GLOG.DEBUG(f"Today's price ratio, P/C: {ratio}.")
        GLOG.DEBUG(f"Limit: {1 - self.loss_limit/100}, Price: {price}, Cost: {cost}, Ratio: {ratio}")
        if ratio < 1 - self.loss_limit / 100:
            s = Signal(
                code=code,
                direction=DIRECTION_TYPES.SHORT,
                backtest_id=self.backtest_id,
                # timestamp=self.portfolio.now,
            )
            return s
