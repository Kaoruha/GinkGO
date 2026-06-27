# Upstream: Portfolio (add_risk_manager注册使用)
# Downstream: RiskBase (继承风控基类)
# Role: TradingTimeRisk交易时段风控，禁止午休和临近收盘时段下单

from typing import List, Dict
from decimal import Decimal
from ginkgo.trading.bases.risk_base import RiskBase as BaseRiskManagement
from ginkgo.entities import Signal
from ginkgo.entities import Order
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES, EVENT_TYPES
from ginkgo.libs import GLOG


class TradingTimeRisk(BaseRiskManagement):
    __abstract__ = False

    def __init__(self, name="TradingTimeRisk",
                 open_minutes_after=5, close_minutes_before=5,
                 lunch_start_hour=11, lunch_start_minute=30,
                 lunch_end_hour=13, lunch_end_minute=0,
                 *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self._open_minutes_after = open_minutes_after
        self._close_minutes_before = close_minutes_before
        self._lunch_start_hour = lunch_start_hour
        self._lunch_start_minute = lunch_start_minute
        self._lunch_end_hour = lunch_end_hour
        self._lunch_end_minute = lunch_end_minute
        self.set_name(f"{name}_open{self._open_minutes_after}m_close{self._close_minutes_before}m")

    @property
    def open_minutes_after(self) -> int:
        return self._open_minutes_after

    @property
    def close_minutes_before(self) -> int:
        return self._close_minutes_before

    def is_trading_allowed(self, current_time: object = None) -> bool:
        if current_time is None:
            return True
        from datetime import time as dt_time
        if hasattr(current_time, "hour"):
            h, m = current_time.hour, current_time.minute
            minutes = h * 60 + m
            # 开盘保护窗口 [9:30, 9:30+open_minutes_after)，0 表示不限制
            if self._open_minutes_after > 0:
                open_start = 9 * 60 + 30
                if open_start <= minutes < open_start + self._open_minutes_after:
                    return False
            # 收盘保护窗口 [15:00-close_minutes_before, 15:00]，0 表示不限制
            if self._close_minutes_before > 0:
                close_end = 15 * 60
                if close_end - self._close_minutes_before <= minutes <= close_end:
                    return False
            if h == self._lunch_start_hour and m >= self._lunch_start_minute:
                return False
            if h == self._lunch_end_hour and m < self._lunch_end_minute:
                return False
        return True

    def cal(self, portfolio_info: Dict, order: Order) -> Order:
        now = portfolio_info.get("now")
        if now and not self.is_trading_allowed(now):
            return None
        return order

    def generate_signals(self, portfolio_info: Dict, event) -> List[Signal]:
        return []
