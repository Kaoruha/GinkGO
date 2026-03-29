from typing import List, Dict
from decimal import Decimal
from ginkgo.trading.bases.risk_base import RiskBase as BaseRiskManagement
from ginkgo.entities import Signal
from ginkgo.entities import Order
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES, EVENT_TYPES
from ginkgo.libs import GLOG


class SuspensionRisk(BaseRiskManagement):
    __abstract__ = False

    def __init__(self, name="SuspensionRisk", max_suspended_ratio=0.1,
                 suspension_warning_days=5, max_suspended_value_ratio=0.05,
                 *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self._max_suspended_ratio = float(max_suspended_ratio)
        self._suspension_warning_days = suspension_warning_days
        self._max_suspended_value_ratio = float(max_suspended_value_ratio)
        self._suspended_stocks = {}
        self.set_name(f"{name}_max{self._max_suspended_ratio}")

    @property
    def max_suspended_ratio(self) -> float:
        return self._max_suspended_ratio

    @property
    def suspension_warning_days(self) -> int:
        return self._suspension_warning_days

    def cal(self, portfolio_info: Dict, order: Order) -> Order:
        return order

    def generate_signals(self, portfolio_info: Dict, event) -> List[Signal]:
        return []

    def get_suspension_report(self, portfolio_info: Dict) -> Dict:
        return {"suspended_count": 0, "suspended_value": 0.0}
