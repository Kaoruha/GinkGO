# Upstream: Portfolio (add_risk_manager注册使用)
# Downstream: RiskBase (继承风控基类)
# Role: CapitalRisk资金风控，限制总资金使用率和单笔交易占比，超阈值生成平仓信号

from typing import List, Dict
from decimal import Decimal
from ginkgo.trading.bases.risk_base import RiskBase as BaseRiskManagement
from ginkgo.entities import Signal
from ginkgo.entities import Order
from ginkgo.enums import DIRECTION_TYPES, EVENT_TYPES
from ginkgo.libs import GLOG


class CapitalRisk(BaseRiskManagement):
    __abstract__ = False

    def __init__(self, name="CapitalRisk", max_capital_usage_ratio=0.9,
                 single_trade_max_ratio=0.1, cash_reserve_ratio=0.1,
                 *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self._max_capital_usage_ratio = float(max_capital_usage_ratio)
        self._single_trade_max_ratio = float(single_trade_max_ratio)
        self._cash_reserve_ratio = float(cash_reserve_ratio)
        self.set_name(f"{name}_usage{self._max_capital_usage_ratio}_single{self._single_trade_max_ratio}")

    @property
    def max_capital_usage_ratio(self) -> float:
        return self._max_capital_usage_ratio

    @property
    def single_trade_max_ratio(self) -> float:
        return self._single_trade_max_ratio

    def cal(self, portfolio_info: Dict, order: Order) -> Order:
        if order.direction != DIRECTION_TYPES.LONG:
            return order
        capital_info = portfolio_info.get("capital_info", {})
        used_ratio = float(capital_info.get("used_ratio", 0.0))
        if used_ratio + self._single_trade_max_ratio > self._max_capital_usage_ratio:
            return None
        return order

    def generate_signals(self, portfolio_info: Dict, event) -> List[Signal]:
        signals = []
        capital_info = portfolio_info.get("capital_info", {})
        used_ratio = float(capital_info.get("used_ratio", 0.0))
        if used_ratio > self._max_capital_usage_ratio * 0.9:
            signals.append(self.create_signal(
                code="CAPITAL_WARNING", direction=DIRECTION_TYPES.SHORT,
                reason=f"Capital usage warning: {used_ratio:.1%}",
                strength=0.7))
        return signals
