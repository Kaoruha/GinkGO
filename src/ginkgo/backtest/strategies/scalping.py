from ginkgo.backtest.strategies.base_strategy import StrategyBase
from ginkgo.backtest.signal import Signal
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

    def cal(self, portfolio_info, event, *args, **kwargs):
        import pdb

        pdb.set_trace()
        super(StrategyProfitLimit, self).cal(portfolio_info, event)
        code = bar.code
        if code in portfolio.positions.keys():
            position = portfolio.positions[code]
            cost = position.cost
            price = position.price
            ratio = price / cost
            if ratio > (1 + self.profit_limit / 100):
                s = Signal(
                    portfolio_id=portfolio_info["uuid"],
                    engine_id=self.engine_id,
                    timestamp=portfolio_info["now"],
                    code=code,
                    direction=DIRECTION_TYPES.SHORT,
                    reason="Scalping",
                    source=SOURCE_TYPES.STRATEGY,
                )
                return s
