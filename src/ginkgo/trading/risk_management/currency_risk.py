from typing import List, Dict
from decimal import Decimal
from ginkgo.trading.bases.risk_base import RiskBase as BaseRiskManagement
from ginkgo.entities import Signal
from ginkgo.entities import Order
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES, EVENT_TYPES
from ginkgo.libs import GLOG


class CurrencyRisk(BaseRiskManagement):
    __abstract__ = False

    def __init__(self, name="CurrencyRisk", single_currency_exposure_limit=0.2,
                 total_currency_exposure_limit=0.5, volatility_warning_threshold=0.05,
                 hedge_ratio_target=0.8, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self._single_currency_exposure_limit = float(single_currency_exposure_limit)
        self._total_currency_exposure_limit = float(total_currency_exposure_limit)
        self._volatility_warning_threshold = float(volatility_warning_threshold)
        self._hedge_ratio_target = float(hedge_ratio_target)
        self.set_name(f"{name}_exp{self._single_currency_exposure_limit}_total{self._total_currency_exposure_limit}")

    @property
    def single_currency_exposure_limit(self) -> float:
        return self._single_currency_exposure_limit

    @property
    def total_currency_exposure_limit(self) -> float:
        return self._total_currency_exposure_limit

    @property
    def volatility_warning_threshold(self) -> float:
        return self._volatility_warning_threshold

    def cal(self, portfolio_info: Dict, order: Order) -> Order:
        return order

    def generate_signals(self, portfolio_info: Dict, event) -> List[Signal]:
        return []

    def get_exposure_report(self, portfolio_info: Dict) -> Dict:
        return {"total_exposure": 0.0}
