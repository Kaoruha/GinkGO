from typing import List, Dict
from decimal import Decimal
from ginkgo.trading.bases.risk_base import RiskBase as BaseRiskManagement
from ginkgo.entities import Signal
from ginkgo.entities import Order
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES, EVENT_TYPES
from ginkgo.libs import GLOG


class MarginRisk(BaseRiskManagement):
    __abstract__ = False

    def __init__(self, name="MarginRisk", max_leverage_ratio=2.0,
                 maintenance_margin_ratio=1.3, margin_call_warning_ratio=1.5,
                 forced_liquidation_ratio=1.2, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self._max_leverage_ratio = float(max_leverage_ratio)
        self._maintenance_margin_ratio = float(maintenance_margin_ratio)
        self._margin_call_warning_ratio = float(margin_call_warning_ratio)
        self._forced_liquidation_ratio = float(forced_liquidation_ratio)
        self.set_name(f"{name}_lev{self._max_leverage_ratio}x_mm{self._maintenance_margin_ratio}")

    @property
    def max_leverage_ratio(self) -> float:
        return self._max_leverage_ratio

    @property
    def maintenance_margin_ratio(self) -> float:
        return self._maintenance_margin_ratio

    @property
    def margin_call_warning_ratio(self) -> float:
        return self._margin_call_warning_ratio

    @property
    def forced_liquidation_ratio(self) -> float:
        return self._forced_liquidation_ratio

    def cal(self, portfolio_info: Dict, order: Order) -> Order:
        if order.direction != DIRECTION_TYPES.LONG:
            return order
        margin_info = portfolio_info.get("margin_info", {})
        current_leverage = float(margin_info.get("current_leverage", 1.0))
        if current_leverage >= self._max_leverage_ratio:
            return None
        if current_leverage >= self._forced_liquidation_ratio:
            factor = max(0.1, (self._max_leverage_ratio - current_leverage) /
                        (self._max_leverage_ratio - self._forced_liquidation_ratio))
            order.volume = int(order.volume * factor)
        return order

    def generate_signals(self, portfolio_info: Dict, event) -> List[Signal]:
        signals = []
        margin_info = portfolio_info.get("margin_info", {})
        current_leverage = float(margin_info.get("current_leverage", 1.0))
        if current_leverage >= self._margin_call_warning_ratio:
            signals.append(Signal(
                portfolio_id=portfolio_info.get("uuid", ""),
                engine_id=self.engine_id, run_id="", timestamp=portfolio_info.get("now"),
                code="", direction=DIRECTION_TYPES.SHORT,
                reason=f"Margin call warning: leverage {current_leverage:.2f}x",
                source=SOURCE_TYPES.STRATEGY))
            signals[-1].strength = 0.7
        return signals
