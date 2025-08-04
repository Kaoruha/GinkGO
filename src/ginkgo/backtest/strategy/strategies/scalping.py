from ginkgo.backtest.strategy.strategies.base_strategy import StrategyBase
from ginkgo.backtest.entities.signal import Signal
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
        super(StrategyScalping, self).cal(portfolio_info, event)
        code = event.code
        
        # 策略暂时不实现具体逻辑，直接返回空列表
        return []
