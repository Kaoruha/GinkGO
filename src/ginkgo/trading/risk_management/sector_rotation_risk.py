from typing import List, Dict
from decimal import Decimal
from ginkgo.trading.bases.risk_base import RiskBase as BaseRiskManagement
from ginkgo.entities import Signal
from ginkgo.entities import Order
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES, EVENT_TYPES
from ginkgo.libs import GLOG


class SectorRotationRisk(BaseRiskManagement):
    __abstract__ = False

    def __init__(self, name="SectorRotationRisk", max_sector_exposure=0.4,
                 sector_warning_threshold=0.3, rotation_detection_days=20,
                 *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self._max_sector_exposure = float(max_sector_exposure)
        self._sector_warning_threshold = float(sector_warning_threshold)
        self._rotation_detection_days = rotation_detection_days
        self._sector_performance = {}
        self.set_name(f"{name}_max{self._max_sector_exposure}_warn{self._sector_warning_threshold}")

    @property
    def max_sector_exposure(self) -> float:
        return self._max_sector_exposure

    @property
    def sector_warning_threshold(self) -> float:
        return self._sector_warning_threshold

    def cal(self, portfolio_info: Dict, order: Order) -> Order:
        return order

    def generate_signals(self, portfolio_info: Dict, event) -> List[Signal]:
        return []

    def get_sector_report(self, portfolio_info: Dict) -> Dict:
        return {"sector_count": 0, "max_exposure": 0.0}
