from typing import List, Dict
from decimal import Decimal
from ginkgo.trading.bases.risk_base import RiskBase as BaseRiskManagement
from ginkgo.entities import Signal
from ginkgo.entities import Order
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES, EVENT_TYPES
from ginkgo.libs import GLOG


class MarketCapRisk(BaseRiskManagement):
    __abstract__ = False

    def __init__(self, name="MarketCapRisk", large_cap_limit=0.5, mid_cap_limit=0.3,
                 small_cap_limit=0.2, style_drift_threshold=0.15,
                 large_cap_min=20000000000, small_cap_max=5000000000,
                 *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self._large_cap_limit = float(large_cap_limit)
        self._mid_cap_limit = float(mid_cap_limit)
        self._small_cap_limit = float(small_cap_limit)
        self._style_drift_threshold = float(style_drift_threshold)
        self._large_cap_min = large_cap_min
        self._small_cap_max = small_cap_max
        self._cap_classification = {}
        self.set_name(f"{name}_large{self._large_cap_limit}_mid{self._mid_cap_limit}_small{self._small_cap_limit}")

    @property
    def large_cap_limit(self) -> float:
        return self._large_cap_limit

    @property
    def mid_cap_limit(self) -> float:
        return self._mid_cap_limit

    @property
    def small_cap_limit(self) -> float:
        return self._small_cap_limit

    def classify_cap(self, market_cap: float) -> str:
        if market_cap >= self._large_cap_min:
            return "large"
        elif market_cap >= self._small_cap_max:
            return "mid"
        return "small"

    def cal(self, portfolio_info: Dict, order: Order) -> Order:
        if order.direction != DIRECTION_TYPES.LONG:
            return order
        return order

    def generate_signals(self, portfolio_info: Dict, event) -> List[Signal]:
        signals = []
        return signals

    def get_style_exposure(self, portfolio_info: Dict) -> Dict:
        return {"large": 0.0, "mid": 0.0, "small": 0.0}
