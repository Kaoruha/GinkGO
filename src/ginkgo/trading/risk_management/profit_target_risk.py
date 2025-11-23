"""
止盈风控管理器 - Green阶段最小实现

TDD Green阶段：实现让测试通过的最小可用代码
只实现测试要求的功能，不过度设计

Author: TDD Green Implementation
Created: 2024-01-15
"""

from decimal import Decimal
from typing import Dict, List, Any
from datetime import datetime

from ginkgo.trading.bases.risk_base import RiskBase as BaseRiskManagement
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.entities.order import Order
from ginkgo.trading.events.base_event import EventBase
from ginkgo.enums import DIRECTION_TYPES


class ProfitTargetRisk(BaseRiskManagement):
    """
    止盈风控管理器 - Green阶段最小实现

    当持仓盈利达到设定阈值时生成卖出信号
    """

    def __init__(self, profit_target: float,
                 partial_take_profit: bool = False,
                 partial_ratio: float = 1.0,
                 dynamic_adjustment: bool = False,
                 volatility_multiplier: float = 1.0,
                 trailing_stop: bool = False,
                 trailing_percentage: float = 0.0):
        """
        初始化止盈风控管理器

        Args:
            profit_target: 止盈目标比例（如0.15表示15%）
            partial_take_profit: 是否分批止盈
            partial_ratio: 部分止盈比例
            dynamic_adjustment: 是否动态调整
            volatility_multiplier: 波动性调整乘数
            trailing_stop: 是否使用移动止盈
            trailing_percentage: 移动止盈回撤比例
        """
        super().__init__()

        # 参数验证（满足测试要求）
        if profit_target <= 0:
            raise ValueError("止盈目标必须为正数")
        if profit_target > 1:
            raise ValueError("止盈目标不能超过100%")

        self.profit_target = profit_target
        self.partial_take_profit = partial_take_profit
        self.partial_ratio = partial_ratio
        self.dynamic_adjustment = dynamic_adjustment
        self.volatility_multiplier = volatility_multiplier
        self.trailing_stop = trailing_stop
        self.trailing_percentage = trailing_percentage

        # 移动止盈跟踪
        self.trailing_highs = {}  # 记录每只股票的最高价

        self.set_name("ProfitTargetRisk")

    def generate_signals(self, portfolio_info: Dict, event: EventBase) -> List[Signal]:
        """
        生成止盈信号

        Args:
            portfolio_info: 投资组合信息
            event: 价格更新事件

        Returns:
            止盈信号列表
        """
        signals = []

        # 检查是否有该股票的持仓
        if not hasattr(event, 'code') or event.code not in portfolio_info.get('positions', {}):
            return signals

        position = portfolio_info['positions'][event.code]

        # 计算当前盈利比例
        current_profit_ratio = position.get('profit_loss_ratio', 0)

        # 检查是否达到止盈目标
        if current_profit_ratio >= self.profit_target:
            # 正确初始化Signal，提供必需参数
            portfolio_id = portfolio_info.get('uuid', 'default')
            reason = f"Partial profit target reached: {current_profit_ratio:.1%}" if self.partial_take_profit else f"Profit target reached: {current_profit_ratio:.1%}"

            signal = Signal(
                portfolio_id=portfolio_id,
                engine_id="profit_target_risk",
                run_id="",
                timestamp=datetime.now(),
                code=event.code,
                direction=DIRECTION_TYPES.SHORT,
                reason=reason,
                source="ProfitTargetRisk"
            )
            signal.strength = 0.9  # 高强度信号

            if self.partial_take_profit:
                signal.volume_ratio = self.partial_ratio

            signals.append(signal)

        # 检查移动止盈
        if self.trailing_stop and hasattr(event, 'close'):
            if self.check_trailing_stop(event.code, event.close):
                signal = Signal()
                signal.code = event.code
                signal.direction = DIRECTION_TYPES.SHORT
                signal.timestamp = datetime.now()
                signal.strength = 0.95
                signal.reason = f"Trailing stop triggered at {event.close}"
                signals.append(signal)

        return signals

    def cal(self, portfolio_info: Dict, order: Order) -> Order:
        """
        处理订单（止盈风控主要是信号生成，订单处理较简单）

        Args:
            portfolio_info: 投资组合信息
            order: 待处理订单

        Returns:
            处理后的订单
        """
        # 买入订单直接通过
        if order.direction == DIRECTION_TYPES.LONG:
            return order

        # 卖出订单验证数量
        if order.direction == DIRECTION_TYPES.SHORT:
            position = portfolio_info.get('positions', {}).get(order.code)
            if position:
                max_sellable = position.get('volume', 0)
                if order.volume > max_sellable:
                    order.volume = max_sellable

        return order

    def calculate_dynamic_target(self, code: str, market_volatility: float) -> float:
        """
        根据市场波动性动态调整止盈目标

        Args:
            code: 股票代码
            market_volatility: 市场波动率

        Returns:
            调整后的止盈目标
        """
        if not self.dynamic_adjustment:
            return self.profit_target

        # 简单的动态调整逻辑：波动性低时降低止盈目标
        adjustment_factor = 1 - (market_volatility * self.volatility_multiplier)
        adjusted_target = self.profit_target * adjustment_factor

        # 确保调整后的目标在合理范围内
        return max(0.10, min(adjusted_target, self.profit_target))

    def update_trailing_high(self, code: str, price: Decimal) -> None:
        """
        更新移动止盈的最高价记录

        Args:
            code: 股票代码
            price: 当前价格
        """
        if code not in self.trailing_highs:
            self.trailing_highs[code] = price
        else:
            self.trailing_highs[code] = max(self.trailing_highs[code], price)

    def check_trailing_stop(self, code: str, current_price: Decimal) -> bool:
        """
        检查是否触发移动止盈

        Args:
            code: 股票代码
            current_price: 当前价格

        Returns:
            是否应该止盈
        """
        if not self.trailing_stop or code not in self.trailing_highs:
            return False

        high_price = self.trailing_highs[code]
        decline_ratio = (high_price - current_price) / high_price

        return decline_ratio >= self.trailing_percentage