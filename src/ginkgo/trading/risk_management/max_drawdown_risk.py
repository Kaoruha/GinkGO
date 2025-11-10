"""
最大回撤风控模块

监控投资组合的最大回撤，当回撤超过设定阈值时强制减仓或停止交易，
保护投资者资金免受深度损失。

关键功能：
- 实时回撤监控
- 动态回撤计算
- 分级风控策略
- 自动减仓机制
"""

from typing import List, Dict
from decimal import Decimal
from ginkgo.trading.bases.risk_base import RiskBase as BaseRiskManagement
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.entities.order import Order
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES, EVENT_TYPES


class MaxDrawdownRisk(BaseRiskManagement):
    """
    最大回撤风控模块

    监控投资组合的最大回撤，当回撤超过设定阈值时
    主动生成减仓信号或停止交易信号。
    """

    __abstract__ = False

    def __init__(
        self,
        name: str = "MaxDrawdownRisk",
        max_drawdown: float = 15.0,
        warning_drawdown: float = 10.0,
        critical_drawdown: float = 20.0,
        *args,
        **kwargs,
    ):
        """
        Args:
            max_drawdown(float): 最大允许回撤，百分比（例如：15.0表示15%）
            warning_drawdown(float): 预警回撤阈值，百分比
            critical_drawdown(float): 严重回撤阈值，百分比
        """
        super(MaxDrawdownRisk, self).__init__(name, *args, **kwargs)
        self._max_drawdown = float(max_drawdown)
        self._warning_drawdown = float(warning_drawdown)
        self._critical_drawdown = float(critical_drawdown)

        # 记录历史最高点
        self._peak_values = {}  # code: peak_value
        self._portfolio_peak = Decimal('0')

        self.set_name(f"{name}_max{self._max_drawdown}%_warn{self._warning_drawdown}%_critical{self._critical_drawdown}%")

    @property
    def max_drawdown(self) -> float:
        return self._max_drawdown

    @property
    def warning_drawdown(self) -> float:
        return self._warning_drawdown

    @property
    def critical_drawdown(self) -> float:
        return self._critical_drawdown

    def cal(self, portfolio_info: Dict, order: Order) -> Order:
        """
        订单风控检查

        当回撤超过阈值时，限制新开仓或减少订单规模。

        Args:
            portfolio_info(Dict): 投资组合信息
            order(Order): 待处理的订单

        Returns:
            Order: 处理后的订单，如果回撤严重可能返回None
        """
        current_drawdown = self._calculate_portfolio_drawdown(portfolio_info)

        # 买入订单限制
        if order.direction == DIRECTION_TYPES.LONG:
            if current_drawdown > self._critical_drawdown:
                # 严重回撤，停止新开仓
                self.log("CRITICAL", f"MaxDrawdownRisk: Critical drawdown {current_drawdown:.1f}% > {self._critical_drawdown}%, stopping new positions")
                return None
            elif current_drawdown > self._max_drawdown:
                # 超过最大回撤，减少开仓规模
                reduction_factor = (self._critical_drawdown - current_drawdown) / (self._critical_drawdown - self._max_drawdown)
                order.volume = int(order.volume * max(reduction_factor, 0.1))
                self.log("WARNING", f"MaxDrawdownRisk: Reducing position size due to drawdown {current_drawdown:.1f}%")

        # 卖出订单允许通过（减仓）
        return order

    def generate_signals(self, portfolio_info: Dict, event) -> List[Signal]:
        """
        生成回撤风控信号

        当回撤超过不同阈值时生成相应的风控信号。

        Args:
            portfolio_info(Dict): 投资组合信息
            event: 事件对象

        Returns:
            List[Signal]: 风控信号列表
        """
        signals = []

        # 只处理价格更新事件
        if not isinstance(event, EventPriceUpdate) and event.event_type != EVENT_TYPES.PRICEUPDATE:
            return signals

        self._update_peak_values(portfolio_info)
        current_drawdown = self._calculate_portfolio_drawdown(portfolio_info)

        # 严重回撤 - 强制减仓
        if current_drawdown > self._critical_drawdown:
            self.log("CRITICAL", f"MaxDrawdownRisk: CRITICAL drawdown {current_drawdown:.1f}% > {self._critical_drawdown}%")

            # 为所有持仓生成减仓信号
            for code in portfolio_info.get("positions", {}):
                if portfolio_info["positions"][code] and portfolio_info["positions"][code].volume > 0:
                    signal = Signal(
                        portfolio_id=portfolio_info["uuid"],
                        engine_id=self.engine_id,
                        timestamp=portfolio_info["now"],
                        code=code,
                        direction=DIRECTION_TYPES.SHORT,
                        reason=f"CRITICAL: Max drawdown {current_drawdown:.1f}% exceeded {self._critical_drawdown}%",
                        source=SOURCE_TYPES.STRATEGY,
                    )
                    signal.strength = 0.95  # 高强度信号
                    signals.append(signal)

        # 超过最大回撤 - 警告减仓
        elif current_drawdown > self._max_drawdown:
            self.log("WARNING", f"MaxDrawdownRisk: WARNING drawdown {current_drawdown:.1f}% > {self._max_drawdown}%")

            # 选择亏损最大的股票减仓
            worst_position = self._find_worst_performing_position(portfolio_info)
            if worst_position:
                signal = Signal(
                    portfolio_id=portfolio_info["uuid"],
                    engine_id=self.engine_id,
                    timestamp=portfolio_info["now"],
                    code=worst_position,
                    direction=DIRECTION_TYPES.SHORT,
                    reason=f"WARNING: Max drawdown {current_drawdown:.1f}% exceeded {self._max_drawdown}%",
                    source=SOURCE_TYPES.STRATEGY,
                )
                signal.strength = 0.7  # 中等强度信号
                signals.append(signal)

        # 预警回撤 - 记录警告
        elif current_drawdown > self._warning_drawdown:
            self.log("INFO", f"MaxDrawdownRisk: WARNING level drawdown {current_drawdown:.1f}% > {self._warning_drawdown}%")

        return signals

    def _update_peak_values(self, portfolio_info: Dict) -> None:
        """更新历史最高值"""
        current_value = Decimal(str(portfolio_info.get("worth", 0)))

        # 更新组合最高值
        if current_value > self._portfolio_peak:
            self._portfolio_peak = current_value

        # 更新各股票最高值
        positions = portfolio_info.get("positions", {})
        for code, position in positions.items():
            if position and position.volume > 0:
                position_value = Decimal(str(position.market_value))
                if code not in self._peak_values or position_value > self._peak_values[code]:
                    self._peak_values[code] = position_value

    def _calculate_portfolio_drawdown(self, portfolio_info: Dict) -> float:
        """计算投资组合当前回撤"""
        current_value = Decimal(str(portfolio_info.get("worth", 0)))
        if self._portfolio_peak <= 0 or current_value <= 0:
            return 0.0

        drawdown = (1 - current_value / self._portfolio_peak) * 100
        return float(drawdown)

    def _find_worst_performing_position(self, portfolio_info: Dict) -> str:
        """找到表现最差的持仓股票"""
        worst_code = None
        worst_ratio = 0.0

        positions = portfolio_info.get("positions", {})
        for code, position in positions.items():
            if position and position.volume > 0:
                peak_value = self._peak_values.get(code, Decimal('0'))
                current_value = Decimal(str(position.market_value))

                if peak_value > 0 and current_value > 0:
                    drawdown = (1 - current_value / peak_value) * 100
                    if drawdown > worst_ratio:
                        worst_ratio = drawdown
                        worst_code = code

        return worst_code