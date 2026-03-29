from typing import List, Dict
from decimal import Decimal
from ginkgo.trading.bases.risk_base import RiskBase as BaseRiskManagement
from ginkgo.entities import Signal
from ginkgo.entities import Order
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES, EVENT_TYPES
from ginkgo.libs import GLOG


class TimeBasedRisk(BaseRiskManagement):
    __abstract__ = False

    def __init__(self, name="TimeBasedRisk", max_holding_days=30,
                 max_intraday_trades=20, max_daily_trades=5,
                 min_holding_period_hours=1, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self._max_holding_days = max_holding_days
        self._max_intraday_trades = max_intraday_trades
        self._max_daily_trades = max_daily_trades
        self._min_holding_period_hours = min_holding_period_hours
        self._trade_count = {}
        self._hold_start = {}
        self.set_name(f"{name}_hold{self._max_holding_days}d_trades{self._max_daily_trades}")

    @property
    def max_holding_days(self) -> int:
        return self._max_holding_days

    @property
    def max_daily_trades(self) -> int:
        return self._max_daily_trades

    def cal(self, portfolio_info: Dict, order: Order) -> Order:
        return order

    def generate_signals(self, portfolio_info: Dict, event) -> List[Signal]:
        return []

    def get_time_report(self, portfolio_info: Dict) -> Dict:
        return {"holding_days": 0, "trade_count": 0}
