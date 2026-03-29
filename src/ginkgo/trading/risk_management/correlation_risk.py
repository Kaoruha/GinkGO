from typing import List, Dict
from decimal import Decimal
from ginkgo.trading.bases.risk_base import RiskBase as BaseRiskManagement
from ginkgo.entities import Signal
from ginkgo.entities import Order
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES, EVENT_TYPES
from ginkgo.libs import GLOG


class CorrelationRisk(BaseRiskManagement):
    __abstract__ = False

    def __init__(self, name="CorrelationRisk", max_correlation=0.7,
                 warning_correlation=0.5, min_diversification_score=0.6,
                 *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self._max_correlation = float(max_correlation)
        self._warning_correlation = float(warning_correlation)
        self._min_diversification_score = float(min_diversification_score)
        self._correlation_matrix = {}
        self.set_name(f"{name}_max{self._max_correlation}_warn{self._warning_correlation}")

    @property
    def max_correlation(self) -> float:
        return self._max_correlation

    @property
    def warning_correlation(self) -> float:
        return self._warning_correlation

    def cal(self, portfolio_info: Dict, order: Order) -> Order:
        return order

    def generate_signals(self, portfolio_info: Dict, event) -> List[Signal]:
        return []

    def get_correlation_report(self, portfolio_info: Dict) -> Dict:
        return {"avg_correlation": 0.0}
