# Upstream: Portfolio Manager (添加剥头皮策略)、BaseStrategy (继承提供策略基础能力)
# Downstream: Signal实体(交易信号生成)、DIRECTION_TYPES (方向枚举LONG/SHORT)、SOURCE_TYPES (信号源枚举)
# Role: Scalping剥头皮策略继承BaseStrategy提供短期高频交易策略实现和快速进出场逻辑支持交易系统功能和组件集成提供完整业务支持






from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.trading.entities.signal import Signal
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES


class StrategyScalping(BaseStrategy):
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
