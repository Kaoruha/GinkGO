"""
集中度风控模块

监控投资组合的集中度风险，包括单一股票、行业、概念等维度的集中度，
防止投资过于集中在少数标的，分散投资风险。

关键功能：
- 多维度集中度监控
- 动态集中度限制
- 分级预警机制
- 自动分散化建议
"""

from typing import List, Dict, Optional
from decimal import Decimal
from ginkgo.trading.strategy.risk_managements.base_risk import BaseRiskManagement
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.entities.order import Order
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES, EVENT_TYPES


class ConcentrationRisk(BaseRiskManagement):
    """
    集中度风控模块

    监控投资组合在不同维度的集中度风险，
    当集中度超过阈值时生成风控信号或调整订单。
    """

    __abstract__ = False

    def __init__(
        self,
        name: str = "ConcentrationRisk",
        max_single_position_ratio: float = 10.0,
        warning_single_position_ratio: float = 8.0,
        max_industry_ratio: float = 30.0,
        warning_industry_ratio: float = 25.0,
        max_concept_ratio: float = 40.0,
        warning_concept_ratio: float = 35.0,
        max_top5_ratio: float = 50.0,
        warning_top5_ratio: float = 45.0,
        *args,
        **kwargs,
    ):
        """
        Args:
            max_single_position_ratio(float): 单一股票最大持仓比例，百分比
            warning_single_position_ratio(float): 单一股票预警比例，百分比
            max_industry_ratio(float): 单一行业最大持仓比例，百分比
            warning_industry_ratio(float): 单一行业预警比例，百分比
            max_concept_ratio(float): 单一概念最大持仓比例，百分比
            warning_concept_ratio(float): 单一概念预警比例，百分比
            max_top5_ratio(float): 前5大持仓最大比例，百分比
            warning_top5_ratio(float): 前5大持仓预警比例，百分比
        """
        super(ConcentrationRisk, self).__init__(name, *args, **kwargs)
        self._max_single_position_ratio = float(max_single_position_ratio)
        self._warning_single_position_ratio = float(warning_single_position_ratio)
        self._max_industry_ratio = float(max_industry_ratio)
        self._warning_industry_ratio = float(warning_industry_ratio)
        self._max_concept_ratio = float(max_concept_ratio)
        self._warning_concept_ratio = float(warning_concept_ratio)
        self._max_top5_ratio = float(max_top5_ratio)
        self._warning_top5_ratio = float(warning_top5_ratio)

        # 存储股票的行业和概念信息
        self._stock_industry_map = {}  # code: industry_name
        self._stock_concept_map = {}   # code: [concept_list]

        self.set_name(f"{name}_single{self._max_single_position_ratio}%_industry{self._max_industry_ratio}%_concept{self._max_concept_ratio}%")

    @property
    def max_single_position_ratio(self) -> float:
        return self._max_single_position_ratio

    @property
    def warning_single_position_ratio(self) -> float:
        return self._warning_single_position_ratio

    @property
    def max_industry_ratio(self) -> float:
        return self._max_industry_ratio

    @property
    def warning_industry_ratio(self) -> float:
        return self._warning_industry_ratio

    def cal(self, portfolio_info: Dict, order: Order) -> Order:
        """
        订单风控检查

        当投资过于集中时，限制新订单或减少订单规模。

        Args:
            portfolio_info(Dict): 投资组合信息
            order(Order): 待处理的订单

        Returns:
            Order: 处理后的订单
        """
        current_concentrations = self._calculate_concentrations(portfolio_info)

        # 检查单一股票集中度
        if order.direction == DIRECTION_TYPES.LONG:
            # 计算当前该股票的持仓比例
            current_ratio = self._get_current_position_ratio(portfolio_info, order.code)
            projected_ratio = self._calculate_projected_ratio(portfolio_info, order)

            if projected_ratio > self._max_single_position_ratio:
                # 超过最大单一持仓比例，大幅减少订单
                reduction_factor = self._max_single_position_ratio / projected_ratio
                original_volume = order.volume
                order.volume = int(order.volume * reduction_factor)

                min_volume = max(1, int(original_volume * 0.1))
                order.volume = max(order.volume, min_volume)

                self.log("WARNING", f"ConcentrationRisk: Single position {order.code} would be {projected_ratio:.1f}% > {self._max_single_position_ratio}%, "
                         f"reducing order {original_volume} → {order.volume}")

            # 检查行业集中度
            stock_industry = self._stock_industry_map.get(order.code, "未知行业")
            industry_ratio = self._calculate_projected_industry_ratio(portfolio_info, order, stock_industry)

            if industry_ratio > self._max_industry_ratio:
                reduction_factor = self._max_industry_ratio / industry_ratio
                order.volume = int(order.volume * reduction_factor)

                self.log("WARNING", f"ConcentrationRisk: Industry {stock_industry} would be {industry_ratio:.1f}% > {self._max_industry_ratio}%, "
                         f"adjusting order to {order.volume}")

        return order

    def generate_signals(self, portfolio_info: Dict, event) -> List[Signal]:
        """
        生成集中度风控信号

        当集中度超过不同阈值时生成相应的风控信号。

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

        current_concentrations = self._calculate_concentrations(portfolio_info)

        # 检查单一股票集中度
        if current_concentrations.get('max_single_position', 0) > self._max_single_position_ratio:
            worst_position = current_concentrations.get('worst_single_position', '')
            if worst_position:
                signal = Signal(
                    portfolio_id=portfolio_info["uuid"],
                    engine_id=self.engine_id,
                    timestamp=portfolio_info["now"],
                    code=worst_position,
                    direction=DIRECTION_TYPES.SHORT,
                    reason=f"CRITICAL: Single position concentration {current_concentrations['max_single_position']:.1f}% exceeded {self._max_single_position_ratio}%",
                    source=SOURCE_TYPES.STRATEGY,
                )
                signal.strength = 0.85  # 高强度信号
                signals.append(signal)

        # 检查行业集中度
        if current_concentrations.get('max_industry', 0) > self._max_industry_ratio:
            worst_industry = current_concentrations.get('worst_industry', '')
            if worst_industry:
                # 选择该行业中最大的持仓进行减仓
                industry_positions = current_concentrations.get('industry_positions', {}).get(worst_industry, [])
                if industry_positions:
                    signal = Signal(
                        portfolio_id=portfolio_info["uuid"],
                        engine_id=self.engine_id,
                        timestamp=portfolio_info["now"],
                        code=industry_positions[0],  # 选择最大持仓
                        direction=DIRECTION_TYPES.SHORT,
                        reason=f"WARNING: Industry concentration {current_concentrations['max_industry']:.1f}% exceeded {self._max_industry_ratio}% for {worst_industry}",
                        source=SOURCE_TYPES.STRATEGY,
                    )
                    signal.strength = 0.7  # 中等强度信号
                    signals.append(signal)

        # 检查前5大持仓集中度
        if current_concentrations.get('top5_ratio', 0) > self._max_top5_ratio:
            self.log("WARNING", f"ConcentrationRisk: Top 5 positions concentration {current_concentrations['top5_ratio']:.1f}% > {self._max_top5_ratio}%")

        return signals

    def _calculate_concentrations(self, portfolio_info: Dict) -> Dict:
        """计算各种集中度指标"""
        positions = portfolio_info.get("positions", {})
        if not positions:
            return {}

        total_value = sum(pos.market_value for pos in positions.values() if pos and pos.market_value)
        if total_value <= 0:
            return {}

        # 单一股票集中度
        max_single_position = 0.0
        worst_single_position = ""
        position_ratios = {}

        # 行业集中度
        industry_values = {}
        industry_positions = {}

        # 前N大持仓
        position_values = []

        for code, position in positions.items():
            if position and position.market_value > 0:
                ratio = (position.market_value / total_value) * 100
                position_ratios[code] = ratio
                position_values.append((code, position.market_value))

                # 最大单一持仓
                if ratio > max_single_position:
                    max_single_position = ratio
                    worst_single_position = code

                # 行业集中度
                industry = self._stock_industry_map.get(code, "未知行业")
                if industry not in industry_values:
                    industry_values[industry] = 0
                    industry_positions[industry] = []

                industry_values[industry] += position.market_value
                industry_positions[industry].append(code)

        # 计算行业集中度
        max_industry = 0.0
        worst_industry = ""
        for industry, industry_value in industry_values.items():
            industry_ratio = (industry_value / total_value) * 100
            if industry_ratio > max_industry:
                max_industry = industry_ratio
                worst_industry = industry

        # 计算前5大持仓集中度
        position_values.sort(key=lambda x: x[1], reverse=True)
        top5_value = sum(value for _, value in position_values[:5])
        top5_ratio = (top5_value / total_value) * 100

        return {
            'max_single_position': max_single_position,
            'worst_single_position': worst_single_position,
            'position_ratios': position_ratios,
            'max_industry': max_industry,
            'worst_industry': worst_industry,
            'industry_positions': industry_positions,
            'top5_ratio': top5_ratio,
            'total_value': total_value
        }

    def _get_current_position_ratio(self, portfolio_info: Dict, code: str) -> float:
        """获取指定股票的当前持仓比例"""
        positions = portfolio_info.get("positions", {})
        position = positions.get(code)

        if not position or position.market_value <= 0:
            return 0.0

        total_value = sum(pos.market_value for pos in positions.values() if pos and pos.market_value)
        if total_value <= 0:
            return 0.0

        return (position.market_value / total_value) * 100

    def _calculate_projected_ratio(self, portfolio_info: Dict, order: Order) -> float:
        """计算下单后的预计持仓比例"""
        current_ratio = self._get_current_position_ratio(portfolio_info, order.code)

        if order.direction != DIRECTION_TYPES.LONG:
            return current_ratio

        # 简化计算：假设订单金额按当前价格计算
        # 在实际实现中，需要考虑订单的实际价格
        order_value = order.volume * 100  # 假设每股100元
        positions = portfolio_info.get("positions", {})
        total_value = sum(pos.market_value for pos in positions.values() if pos and pos.market_value)

        if total_value <= 0:
            return 100.0  # 第一笔订单

        projected_total = total_value + order_value
        projected_position_value = positions.get(order.code).market_value if positions.get(order.code) else 0
        projected_position_value += order_value

        return (projected_position_value / projected_total) * 100

    def _calculate_projected_industry_ratio(self, portfolio_info: Dict, order: Order, industry: str) -> float:
        """计算下单后的预计行业持仓比例"""
        positions = portfolio_info.get("positions", {})
        total_value = sum(pos.market_value for pos in positions.values() if pos and pos.market_value)

        if total_value <= 0:
            return 100.0

        # 计算当前行业价值
        current_industry_value = 0.0
        for code, position in positions.items():
            if position and position.market_value > 0:
                stock_industry = self._stock_industry_map.get(code, "未知行业")
                if stock_industry == industry:
                    current_industry_value += position.market_value

        # 计算订单价值
        order_value = order.volume * 100  # 假设每股100元

        projected_industry_value = current_industry_value + order_value
        projected_total = total_value + order_value

        return (projected_industry_value / projected_total) * 100

    def update_stock_classification(self, code: str, industry: str = None, concepts: List[str] = None):
        """
        更新股票的行业和概念分类

        Args:
            code: 股票代码
            industry: 行业名称
            concepts: 概念列表
        """
        if industry:
            self._stock_industry_map[code] = industry

        if concepts:
            self._stock_concept_map[code] = concepts

    def get_concentration_report(self, portfolio_info: Dict) -> Dict:
        """
        生成集中度报告

        Args:
            portfolio_info: 投资组合信息

        Returns:
            Dict: 集中度分析报告
        """
        concentrations = self._calculate_concentrations(portfolio_info)

        report = {
            'single_position_analysis': {
                'max_ratio': concentrations.get('max_single_position', 0),
                'warning_threshold': self._warning_single_position_ratio,
                'max_threshold': self._max_single_position_ratio,
                'status': 'critical' if concentrations.get('max_single_position', 0) > self._max_single_position_ratio
                         else 'warning' if concentrations.get('max_single_position', 0) > self._warning_single_position_ratio
                         else 'normal'
            },
            'industry_analysis': {
                'max_ratio': concentrations.get('max_industry', 0),
                'warning_threshold': self._warning_industry_ratio,
                'max_threshold': self._max_industry_ratio,
                'status': 'critical' if concentrations.get('max_industry', 0) > self._max_industry_ratio
                         else 'warning' if concentrations.get('max_industry', 0) > self._warning_industry_ratio
                         else 'normal'
            },
            'top_positions_analysis': {
                'top5_ratio': concentrations.get('top5_ratio', 0),
                'warning_threshold': self._warning_top5_ratio,
                'max_threshold': self._max_top5_ratio,
                'status': 'critical' if concentrations.get('top5_ratio', 0) > self._max_top5_ratio
                         else 'warning' if concentrations.get('top5_ratio', 0) > self._warning_top5_ratio
                         else 'normal'
            }
        }

        return report