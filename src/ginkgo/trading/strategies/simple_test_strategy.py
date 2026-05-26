# 简化测试策略 - 每次都产生买入信号

import datetime
from ginkgo.entities import Signal
from ginkgo.trading.strategies.strategy_base import BaseStrategy
from ginkgo.enums import DIRECTION_TYPES
from ginkgo.libs import GLOG


class SimpleTestStrategy(BaseStrategy):
    """
    简化测试策略 - 验证信号链路
    每次调用都产生买入信号（只要没有持仓）
    """

    __abstract__ = False

    def __init__(self, name: str = "SimpleTest", *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        GLOG.INFO(f"[SimpleTest] Strategy initialized")

    def cal(self, portfolio_info, event, *args, **kwargs):
        super().cal(portfolio_info, event)

        has_position = event.code in portfolio_info.get("positions", {})

        if not has_position:
            GLOG.INFO(f"[SimpleTest] Generating BUY signal for {event.code}")
            return self.create_signal(
                code=event.code,
                direction=DIRECTION_TYPES.LONG,
                reason="SimpleTest signal",
                timestamp=portfolio_info.get("now"),
            )

        return []