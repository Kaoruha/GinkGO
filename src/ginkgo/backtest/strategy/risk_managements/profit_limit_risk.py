from typing import List, Dict
from decimal import Decimal
from ginkgo.backtest.risk_managements.base_risk import BaseRiskManagement
from ginkgo.backtest.entities.signal import Signal
from ginkgo.backtest.entities.order import Order
from ginkgo.backtest.execution.events import EventPriceUpdate
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES, EVENT_TYPES


class ProfitLimitRisk(BaseRiskManagement):
    """
    止盈风控模块
    当持仓盈利超过设定阈值时，主动生成平仓信号
    """
    
    __abstract__ = False

    def __init__(
        self,
        name: str = "ProfitLimitRisk",
        profit_limit: float = 10.0,
        *args,
        **kwargs,
    ):
        """
        Args:
            profit_limit(float): 止盈阈值，百分比（例如：10.0表示10%）
        """
        super(ProfitLimitRisk, self).__init__(name, *args, **kwargs)
        self._profit_limit = float(profit_limit)
        self.set_name(f"{name}_{self._profit_limit}%")

    @property
    def profit_limit(self) -> float:
        return self._profit_limit

    def cal(self, portfolio_info: Dict, order: Order) -> Order:
        """
        订单风控检查（保持原有订单不变）
        Args:
            portfolio_info(Dict): 投资组合信息
            order(Order): 待处理的订单
        Returns:
            Order: 处理后的订单
        """
        # 止盈风控不干预新订单，只负责生成平仓信号
        return order

    def generate_signals(self, portfolio_info: Dict, event) -> List[Signal]:
        """
        生成止盈信号
        只处理价格更新事件，监控持仓盈利情况，超过阈值时生成平仓信号
        
        Args:
            portfolio_info(Dict): 投资组合信息
            event: 事件对象
        Returns:
            List[Signal]: 止盈信号列表
        """
        signals = []
        
        # 只处理价格更新事件
        if not isinstance(event, EventPriceUpdate) and event.event_type != EVENT_TYPES.PRICEUPDATE:
            return signals
        
        code = event.code
        
        # 检查是否有该股票的持仓
        if code not in portfolio_info["positions"]:
            return signals
            
        position = portfolio_info["positions"][code]
        if position is None or position.volume <= 0:
            return signals
        
        # 计算盈利比例
        cost = position.cost
        current_price = getattr(event, 'close', None) or getattr(event, 'price', None)
        
        if current_price is None or cost <= 0:
            self.log("WARN", f"ProfitLimitRisk: Invalid price data for {code}")
            return signals
            
        profit_ratio = (current_price / cost - 1) * 100  # 转换为百分比
        
        self.log("DEBUG", f"ProfitLimitRisk: {code} profit ratio: {profit_ratio:.2f}%, limit: {self._profit_limit}%")
        
        # 如果盈利超过阈值，生成平仓信号
        if profit_ratio > self._profit_limit:
            self.log("INFO", f"ProfitLimitRisk: Profit limit triggered for {code}, ratio: {profit_ratio:.2f}%")
            
            signal = Signal(
                portfolio_id=portfolio_info["uuid"],
                engine_id=self.engine_id,  # 使用self获取engine_id
                timestamp=portfolio_info["now"],
                code=code,
                direction=DIRECTION_TYPES.SHORT,  # 平仓
                reason=f"Profit Limit ({profit_ratio:.2f}% > {self._profit_limit}%)",
                source=SOURCE_TYPES.STRATEGY,  # 风控生成的信号也标记为策略来源
            )
            signals.append(signal)
        
        return signals