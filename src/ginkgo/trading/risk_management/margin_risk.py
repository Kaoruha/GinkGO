# Upstream: Portfolio (add_risk_manager注册使用)
# Downstream: RiskBase (继承风控基类)
# Role: MarginRisk保证金风控，限制最大杠杆率，支持追保预警和强平信号生成

from typing import List, Dict
from decimal import Decimal
from ginkgo.trading.bases.risk_base import RiskBase as BaseRiskManagement
from ginkgo.entities import Signal
from ginkgo.entities import Order
from ginkgo.entities.mixins import LotAlignableMixin
from ginkgo.enums import DIRECTION_TYPES, EVENT_TYPES
from ginkgo.libs import GLOG


class MarginRisk(LotAlignableMixin, BaseRiskManagement):
    __abstract__ = False

    def __init__(self, name="MarginRisk", max_leverage_ratio=2.0,
                 maintenance_margin_ratio=1.3, margin_call_warning_ratio=1.5,
                 forced_liquidation_ratio=1.2, lot_size: int = 100, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self._max_leverage_ratio = float(max_leverage_ratio)
        self._maintenance_margin_ratio = float(maintenance_margin_ratio)
        self._margin_call_warning_ratio = float(margin_call_warning_ratio)
        self._forced_liquidation_ratio = float(forced_liquidation_ratio)
        self._lot_size = int(lot_size)
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
            scaled = int(order.volume * factor)
            # 最小交易单位 lot_size 对齐(LotAlignableMixin,A 股默认 100 股/手)(#6038)
            # 缩放后不足 1 手拒单(对齐 volatility/concentration/liquidity/max_drawdown 模板,
            # 调用方对 cal() 返回 None 走软拦截 ORDERBLOCKED,零侵入)(#6038)
            aligned = self.align_to_lot(scaled)
            if aligned < self._lot_size:
                GLOG.WARN(f"MarginRisk: Leverage {current_leverage:.2f}x >= forced liquidation "
                         f"{self._forced_liquidation_ratio}x, scaled {order.volume} → {scaled} "
                         f"below 1 lot ({self._lot_size}), blocking order")
                return None
            order.adjust_volume(aligned)
            GLOG.WARN(f"MarginRisk: Leverage {current_leverage:.2f}x >= forced liquidation, "
                     f"reducing order to {order.volume}")
        return order

    def generate_signals(self, portfolio_info: Dict, event) -> List[Signal]:
        signals = []
        margin_info = portfolio_info.get("margin_info", {})
        current_leverage = float(margin_info.get("current_leverage", 1.0))
        if current_leverage >= self._margin_call_warning_ratio:
            signals.append(self.create_signal(
                code="", direction=DIRECTION_TYPES.SHORT,
                reason=f"Margin call warning: leverage {current_leverage:.2f}x",
                strength=0.7))
        return signals
