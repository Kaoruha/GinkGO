# Upstream: Portfolio Manager (波动率风控调整仓位)、RiskBase (继承提供风控基础能力)
# Downstream: EventPriceUpdate (监听价格更新事件)、Signal/Order实体(风控信号和订单处理)、DIRECTION_TYPES (方向枚举)、math (数学计算)
# Role: VolatilityRisk波动率风险管理器监控价格波动防止过度波动，提供cal方法和generate_signals方法






"""
波动率风控模块

监控市场波动率，当波动率超过设定阈值时调整仓位大小或暂停交易，
保护投资者免受高波动市场的过度风险。

关键功能：
- 实时波动率计算
- 多周期波动率监控
- 动态仓位调整
- 波动率预警机制
"""

from typing import List, Dict
from decimal import Decimal
from ginkgo.trading.bases.risk_base import RiskBase as BaseRiskManagement
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.entities.order import Order
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES, EVENT_TYPES

import math


class VolatilityRisk(BaseRiskManagement):
    """
    波动率风控模块

    监控市场波动率，当波动率超过设定阈值时
    调整仓位大小或暂停交易。
    """

    __abstract__ = False

    def __init__(
        self,
        name: str = "VolatilityRisk",
        max_volatility: float = 25.0,
        warning_volatility: float = 20.0,
        lookback_period: int = 20,
        volatility_window: int = 10,
        *args,
        **kwargs,
    ):
        """
        Args:
            max_volatility(float): 最大允许波动率，百分比（例如：25.0表示25%）
            warning_volatility(float): 预警波动率阈值，百分比
            lookback_period(int): 历史数据回看期，天数
            volatility_window(int): 波动率计算窗口，天数
        """
        super(VolatilityRisk, self).__init__(name, *args, **kwargs)
        self._max_volatility = float(max_volatility)
        self._warning_volatility = float(warning_volatility)
        self._lookback_period = lookback_period
        self._volatility_window = volatility_window

        # 存储历史价格数据用于波动率计算
        self._price_history = {}  # code: [price_list]
        self._volatility_cache = {}  # code: current_volatility

        self.set_name(f"{name}_max{self._max_volatility}%_warn{self._warning_volatility%}_period{self._lookback_period}")

    @property
    def max_volatility(self) -> float:
        return self._max_volatility

    @property
    def warning_volatility(self) -> float:
        return self._warning_volatility

    @property
    def lookback_period(self) -> int:
        return self._lookback_period

    def cal(self, portfolio_info: Dict, order: Order) -> Order:
        """
        订单风控检查

        当市场波动率过高时，减少订单规模或调整交易策略。

        Args:
            portfolio_info(Dict): 投资组合信息
            order(Order): 待处理的订单

        Returns:
            Order: 处理后的订单
        """
        # 获取订单股票的当前波动率
        current_volatility = self._get_stock_volatility(order.code)

        if current_volatility > self._max_volatility:
            # 波动率过高，大幅减少订单规模
            reduction_factor = (self._max_volatility / current_volatility) ** 2
            original_volume = order.volume
            order.volume = int(order.volume * reduction_factor)

            # 确保最小订单量
            min_volume = max(1, int(original_volume * 0.1))
            order.volume = max(order.volume, min_volume)

            self.log("WARNING", f"VolatilityRisk: High volatility {current_volatility:.1f}% > {self._max_volatility}%, "
                     f"reducing order {original_volume} → {order.volume}")

        elif current_volatility > self._warning_volatility:
            # 波动率预警，适度减少订单规模
            reduction_factor = (self._max_volatility / current_volatility) ** 1.5
            order.volume = int(order.volume * reduction_factor)

            self.log("INFO", f"VolatilityRisk: Warning volatility {current_volatility:.1f}% > {self._warning_volatility}%, "
                     f"adjusting order to {order.volume}")

        return order

    def generate_signals(self, portfolio_info: Dict, event) -> List[Signal]:
        """
        生成波动率风控信号

        当波动率异常时生成相应的风控信号。

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

        # 更新价格历史
        self._update_price_history(event.code, event.close)

        # 计算当前波动率
        current_volatility = self._calculate_volatility(event.code)

        # 检查波动率是否超标
        if current_volatility > self._max_volatility:
            self.log("WARNING", f"VolatilityRisk: EXTREME volatility {current_volatility:.1f}% > {self._max_volatility}% for {event.code}")

            # 生成减仓或暂停交易信号
            signal = Signal(
                portfolio_id=portfolio_info["uuid"],
                engine_id=self.engine_id,
                timestamp=portfolio_info["now"],
                code=event.code,
                direction=DIRECTION_TYPES.SHORT,
                reason=f"EXTREME: Volatility {current_volatility:.1f}% exceeded {self._max_volatility}%",
                source=SOURCE_TYPES.STRATEGY,
            )
            signal.strength = min(0.9, current_volatility / self._max_volatility)  # 波动率越高信号越强
            signals.append(signal)

        elif current_volatility > self._warning_volatility:
            self.log("INFO", f"VolatilityRisk: HIGH volatility {current_volatility:.1f}% > {self._warning_volatility}% for {event.code}")

            # 生成预警信号
            signal = Signal(
                portfolio_id=portfolio_info["uuid"],
                engine_id=self.engine_id,
                timestamp=portfolio_info["now"],
                code=event.code,
                direction=DIRECTION_TYPES.SHORT,
                reason=f"HIGH: Volatility {current_volatility:.1f}% exceeded {self._warning_volatility}%",
                source=SOURCE_TYPES.STRATEGY,
            )
            signal.strength = 0.6  # 中等强度预警信号
            signals.append(signal)

        return signals

    def _update_price_history(self, code: str, price: float) -> None:
        """更新价格历史数据"""
        if code not in self._price_history:
            self._price_history[code] = []

        # 添加新价格
        self._price_history[code].append(price)

        # 保持历史数据在回看期内
        if len(self._price_history[code]) > self._lookback_period:
            self._price_history[code] = self._price_history[code][-self._lookback_period:]

    def _calculate_volatility(self, code: str) -> float:
        """计算指定股票的波动率"""
        if code not in self._price_history or len(self._price_history[code]) < 2:
            return 0.0

        prices = self._price_history[code]

        # 如果历史数据足够，使用滚动窗口计算
        if len(prices) >= self._volatility_window:
            window_prices = prices[-self._volatility_window:]
        else:
            window_prices = prices

        # 计算收益率
        returns = []
        for i in range(1, len(window_prices)):
            if window_prices[i-1] > 0:
                return_rate = (window_prices[i] / window_prices[i-1] - 1) * 100
                returns.append(return_rate)

        if len(returns) < 2:
            return 0.0

        # 计算标准差作为波动率
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        volatility = math.sqrt(variance)

        # 年化波动率（假设日数据）
        annualized_volatility = volatility * math.sqrt(252)

        return float(annualized_volatility)

    def _get_stock_volatility(self, code: str) -> float:
        """获取股票当前波动率"""
        # 先检查缓存
        if code in self._volatility_cache:
            return self._volatility_cache[code]

        # 计算并缓存
        volatility = self._calculate_volatility(code)
        self._volatility_cache[code] = volatility

        return volatility

    def get_portfolio_volatility(self, portfolio_info: Dict) -> float:
        """
        计算投资组合的整体波动率

        Args:
            portfolio_info(Dict): 投资组合信息

        Returns:
            float: 投资组合波动率
        """
        positions = portfolio_info.get("positions", {})
        if not positions:
            return 0.0

        # 计算各股票的波动率和权重
        total_value = sum(pos.market_value for pos in positions.values() if pos and pos.market_value)
        if total_value <= 0:
            return 0.0

        weighted_volatility = 0.0
        for code, position in positions.items():
            if position and position.market_value > 0:
                weight = position.market_value / total_value
                stock_volatility = self._get_stock_volatility(code)
                weighted_volatility += weight * stock_volatility

        return weighted_volatility