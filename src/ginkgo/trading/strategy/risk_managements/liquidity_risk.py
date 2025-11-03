"""
流动性风控模块

监控投资组合的流动性风险，包括个股流动性、市场流动性、交易量等指标，
防止因流动性不足导致的交易困难和价格冲击。

关键功能：
- 实时流动性监控
- 价格冲击计算
- 交易量限制
- 流动性预警机制
"""

from typing import List, Dict, Optional
from decimal import Decimal
from ginkgo.trading.strategy.risk_managements.base_risk import BaseRiskManagement
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.entities.order import Order
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES, EVENT_TYPES


class LiquidityRisk(BaseRiskManagement):
    """
    流动性风控模块

    监控投资组合的流动性风险，
    当流动性不足时调整交易策略或限制交易。
    """

    __abstract__ = False

    def __init__(
        self,
        name: str = "LiquidityRisk",
        min_avg_volume_ratio: float = 0.1,
        warning_avg_volume_ratio: float = 0.2,
        max_price_impact: float = 5.0,
        warning_price_impact: float = 3.0,
        min_turnover_ratio: float = 1000000,  # 最小日成交额
        warning_turnover_ratio: float = 5000000,
        liquidity_lookback_days: int = 20,
        *args,
        **kwargs,
    ):
        """
        Args:
            min_avg_volume_ratio(float): 最小平均成交量比例（订单量/平均成交量）
            warning_avg_volume_ratio(float): 预警平均成交量比例
            max_price_impact(float): 最大价格冲击影响，百分比
            warning_price_impact(float): 预警价格冲击影响，百分比
            min_turnover_ratio(float): 最小日成交额阈值
            warning_turnover_ratio(float): 预警日成交额阈值
            liquidity_lookback_days(int): 流动性数据回看天数
        """
        super(LiquidityRisk, self).__init__(name, *args, **kwargs)
        self._min_avg_volume_ratio = float(min_avg_volume_ratio)
        self._warning_avg_volume_ratio = float(warning_avg_volume_ratio)
        self._max_price_impact = float(max_price_impact)
        self._warning_price_impact = float(warning_price_impact)
        self._min_turnover_ratio = float(min_turnover_ratio)
        self._warning_turnover_ratio = float(warning_turnover_ratio)
        self._liquidity_lookback_days = liquidity_lookback_days

        # 存储历史流动性数据
        self._volume_history = {}  # code: [volume_list]
        self._turnover_history = {}  # code: [turnover_list]
        self._price_history = {}    # code: [price_list]

        self.set_name(f"{name}_volume{self._min_avg_volume_ratio}%_impact{self._max_price_impact}%_turnover{self._min_turnover_ratio}")

    @property
    def min_avg_volume_ratio(self) -> float:
        return self._min_avg_volume_ratio

    @property
    def warning_avg_volume_ratio(self) -> float:
        return self._warning_avg_volume_ratio

    @property
    def max_price_impact(self) -> float:
        return self._max_price_impact

    def cal(self, portfolio_info: Dict, order: Order) -> Order:
        """
        订单风控检查

        当流动性不足时，调整订单规模或拒绝交易。

        Args:
            portfolio_info(Dict): 投资组合信息
            order(Order): 待处理的订单

        Returns:
            Order: 处理后的订单，可能为None
        """
        liquidity_metrics = self._calculate_liquidity_metrics(order.code)

        # 检查平均成交量比例
        avg_volume_ratio = self._calculate_order_volume_ratio(order, liquidity_metrics)

        if avg_volume_ratio > self._warning_avg_volume_ratio:
            if avg_volume_ratio > self._min_avg_volume_ratio:
                # 流动性严重不足，大幅减少订单
                reduction_factor = self._min_avg_volume_ratio / avg_volume_ratio
                original_volume = order.volume
                order.volume = int(order.volume * reduction_factor)

                min_volume = max(1, int(original_volume * 0.1))
                order.volume = max(order.volume, min_volume)

                self.log("WARNING", f"LiquidityRisk: Low liquidity for {order.code}, volume ratio {avg_volume_ratio:.3f} > {self._min_avg_volume_ratio}, "
                         f"reducing order {original_volume} → {order.volume}")
            else:
                # 流动性预警，适度减少订单
                reduction_factor = 0.8  # 预警时减少20%
                order.volume = int(order.volume * reduction_factor)

                self.log("INFO", f"LiquidityRisk: Liquidity warning for {order.code}, volume ratio {avg_volume_ratio:.3f} > {self._warning_avg_volume_ratio}, "
                         f"adjusting order to {order.volume}")

        # 检查价格冲击影响
        price_impact = self._calculate_price_impact(order, liquidity_metrics)
        if price_impact > self._max_price_impact:
            # 价格冲击过大，拒绝订单
            self.log("CRITICAL", f"LiquidityRisk: High price impact {price_impact:.2f}% > {self._max_price_impact}% for {order.code}, rejecting order")
            return None
        elif price_impact > self._warning_price_impact:
            # 价格冲击预警，减少订单
            reduction_factor = self._warning_price_impact / price_impact
            order.volume = int(order.volume * reduction_factor)

            self.log("WARNING", f"LiquidityRisk: Price impact warning {price_impact:.2f}% > {self._warning_price_impact}% for {order.code}, "
                     f"adjusting order to {order.volume}")

        # 检查日成交额
        avg_turnover = liquidity_metrics.get('avg_turnover', 0)
        if avg_turnover < self._min_turnover_ratio:
            # 成交额过低，限制交易
            reduction_factor = avg_turnover / self._min_turnover_ratio
            order.volume = int(order.volume * max(reduction_factor, 0.1))

            self.log("WARNING", f"LiquidityRisk: Low turnover {avg_turnover:,.0f} < {self._min_turnover_ratio:,.0f} for {order.code}, "
                     f"reducing order to {order.volume}")

        return order

    def generate_signals(self, portfolio_info: Dict, event) -> List[Signal]:
        """
        生成流动性风控信号

        当流动性异常时生成相应的风控信号。

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

        # 更新历史数据
        self._update_liquidity_history(event)

        # 计算流动性指标
        liquidity_metrics = self._calculate_liquidity_metrics(event.code)

        # 检查严重流动性不足
        if liquidity_metrics.get('avg_turnover', 0) < self._min_turnover_ratio:
            self.log("CRITICAL", f"LiquidityRisk: CRITICAL low liquidity for {event.code}, turnover {liquidity_metrics.get('avg_turnover', 0):,.0f}")

            # 生成减仓信号
            signal = Signal(
                portfolio_id=portfolio_info["uuid"],
                engine_id=self.engine_id,
                timestamp=portfolio_info["now"],
                code=event.code,
                direction=DIRECTION_TYPES.SHORT,
                reason=f"CRITICAL: Liquidity too low, turnover {liquidity_metrics.get('avg_turnover', 0):,.0f} < {self._min_turnover_ratio:,.0f}",
                source=SOURCE_TYPES.STRATEGY,
            )
            signal.strength = 0.9  # 高强度信号
            signals.append(signal)

        # 检查价格冲击风险
        current_position = portfolio_info.get("positions", {}).get(event.code)
        if current_position and current_position.volume > 0:
            # 模拟平仓的价格冲击
            sell_order = Order()
            sell_order.code = event.code
            sell_order.volume = current_position.volume
            sell_order.direction = DIRECTION_TYPES.SHORT
            sell_order.limit_price = event.close

            price_impact = self._calculate_price_impact(sell_order, liquidity_metrics)
            if price_impact > self._warning_price_impact:
                signal = Signal(
                    portfolio_id=portfolio_info["uuid"],
                    engine_id=self.engine_id,
                    timestamp=portfolio_info["now"],
                    code=event.code,
                    direction=DIRECTION_TYPES.SHORT,
                    reason=f"WARNING: High exit price impact {price_impact:.2f}% > {self._warning_price_impact}%",
                    source=SOURCE_TYPES.STRATEGY,
                )
                signal.strength = 0.6  # 中等强度信号
                signals.append(signal)

        return signals

    def _update_liquidity_history(self, event) -> None:
        """更新流动性历史数据"""
        code = event.code

        # 初始化历史数据
        if code not in self._volume_history:
            self._volume_history[code] = []
        if code not in self._turnover_history:
            self._turnover_history[code] = []
        if code not in self._price_history:
            self._price_history[code] = []

        # 添加新数据（这里需要从实际数据源获取）
        # 简化处理：使用价格变动估算成交量
        # 实际实现中应该从数据源获取真实的成交量和成交额
        volume = getattr(event, 'volume', 1000000)  # 默认值
        turnover = getattr(event, 'turnover', event.close * volume)  # 估算成交额

        self._volume_history[code].append(volume)
        self._turnover_history[code].append(turnover)
        self._price_history[code].append(event.close)

        # 保持历史数据在回看期内
        if len(self._volume_history[code]) > self._liquidity_lookback_days:
            self._volume_history[code] = self._volume_history[code][-self._liquidity_lookback_days:]
        if len(self._turnover_history[code]) > self._liquidity_lookback_days:
            self._turnover_history[code] = self._turnover_history[code][-self._liquidity_lookback_days:]
        if len(self._price_history[code]) > self._liquidity_lookback_days:
            self._price_history[code] = self._price_history[code][-self._liquidity_lookback_days:]

    def _calculate_liquidity_metrics(self, code: str) -> Dict:
        """计算流动性指标"""
        if code not in self._volume_history or len(self._volume_history[code]) == 0:
            return {
                'avg_volume': 0,
                'avg_turnover': 0,
                'volatility': 0,
                'price_stability': 1.0
            }

        volumes = self._volume_history[code]
        turnovers = self._turnover_history[code]
        prices = self._price_history[code]

        # 计算平均成交量和成交额
        avg_volume = sum(volumes) / len(volumes)
        avg_turnover = sum(turnovers) / len(turnovers)

        # 计算价格波动率
        volatility = 0.0
        if len(prices) >= 2:
            returns = []
            for i in range(1, len(prices)):
                if prices[i-1] > 0:
                    return_rate = (prices[i] / prices[i-1] - 1) * 100
                    returns.append(return_rate)

            if len(returns) >= 2:
                mean_return = sum(returns) / len(returns)
                variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
                volatility = variance ** 0.5

        # 价格稳定性（波动率越小越稳定）
        price_stability = max(0.1, 1.0 / (1.0 + volatility))

        return {
            'avg_volume': avg_volume,
            'avg_turnover': avg_turnover,
            'volatility': volatility,
            'price_stability': price_stability
        }

    def _calculate_order_volume_ratio(self, order: Order, liquidity_metrics: Dict) -> float:
        """计算订单量占平均成交量的比例"""
        avg_volume = liquidity_metrics.get('avg_volume', 0)
        if avg_volume <= 0:
            return 999.0  # 表示流动性极差

        # 估算订单成交金额
        order_value = order.volume * (order.limit_price or 100)  # 默认价格100
        avg_daily_value = liquidity_metrics.get('avg_turnover', avg_volume * 100)

        if avg_daily_value <= 0:
            return 999.0

        return order_value / avg_daily_value

    def _calculate_price_impact(self, order: Order, liquidity_metrics: Dict) -> float:
        """计算价格冲击影响"""
        # 简化的价格冲击模型
        # 实际模型需要考虑订单簿深度、市场微观结构等因素

        order_value = order.volume * (order.limit_price or 100)
        avg_turnover = liquidity_metrics.get('avg_turnover', 0)
        price_stability = liquidity_metrics.get('price_stability', 1.0)

        if avg_turnover <= 0:
            return 999.0  # 流动性极差

        # 基础价格冲击 = 订单金额 / 平均日成交额 * 稳定性因子
        base_impact = (order_value / avg_turnover) * 100

        # 根据流动性调整
        liquidity_adjustment = 1.0 / price_stability

        # 根据订单方向调整（卖出通常冲击更大）
        direction_adjustment = 1.2 if order.direction == DIRECTION_TYPES.SHORT else 1.0

        price_impact = base_impact * liquidity_adjustment * direction_adjustment

        return float(price_impact)

    def get_liquidity_score(self, code: str) -> float:
        """
        计算流动性评分（0-100）

        Args:
            code: 股票代码

        Returns:
            float: 流动性评分
        """
        metrics = self._calculate_liquidity_metrics(code)

        avg_turnover = metrics.get('avg_turnover', 0)
        volume_score = min(50, (avg_turnover / self._warning_turnover_ratio) * 50)

        volatility = metrics.get('volatility', 100)
        stability_score = max(0, 50 - volatility)

        price_stability = metrics.get('price_stability', 0)
        stability_bonus = price_stability * 10

        total_score = volume_score + stability_score + stability_bonus
        return min(100.0, max(0.0, total_score))

    def get_liquidity_report(self, portfolio_info: Dict) -> Dict:
        """
        生成流动性风险报告

        Args:
            portfolio_info: 投资组合信息

        Returns:
            Dict: 流动性分析报告
        """
        positions = portfolio_info.get("positions", {})
        portfolio_liquidity_score = 0.0
        total_value = 0.0
        low_liquidity_positions = []

        for code, position in positions.items():
            if position and position.market_value > 0:
                liquidity_score = self.get_liquidity_score(code)
                position_weight = position.market_value
                total_value += position_weight

                # 计算加权流动性评分
                portfolio_liquidity_score += liquidity_score * position_weight

                # 识别低流动性持仓
                if liquidity_score < 30:
                    low_liquidity_positions.append({
                        'code': code,
                        'liquidity_score': liquidity_score,
                        'market_value': position.market_value,
                        'weight': position_weight
                    })

        if total_value > 0:
            portfolio_liquidity_score /= total_value

        return {
            'portfolio_liquidity_score': portfolio_liquidity_score,
            'liquidity_level': 'excellent' if portfolio_liquidity_score >= 80
                           else 'good' if portfolio_liquidity_score >= 60
                           else 'fair' if portfolio_liquidity_score >= 40
                           else 'poor' if portfolio_liquidity_score >= 20
                           else 'critical',
            'low_liquidity_positions': low_liquidity_positions,
            'low_liquidity_ratio': len(low_liquidity_positions) / len(positions) if positions else 0,
            'total_positions': len(positions)
        }