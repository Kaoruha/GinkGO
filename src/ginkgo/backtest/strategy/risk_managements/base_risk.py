from typing import List, Dict, Any
from ginkgo.backtest.entities.order import Order
from ginkgo.backtest.entities.signal import Signal
from ginkgo.backtest.core.backtest_base import BacktestBase
from ginkgo.backtest.execution.events.base_event import EventBase


class BaseRiskManagement(BacktestBase):
    def __init__(self, name: str = "baseriskmanagement", *args, **kwargs):
        super(BaseRiskManagement, self).__init__(name, *args, **kwargs)
        self._data_feeder = None

    def bind_data_feeder(self, feeder, *args, **kwargs):
        self._data_feeder = feeder

    def cal(self, portfolio_info: Dict, order: Order):
        """
        风控订单处理
        接收投资组合信息和订单，返回处理后的订单
        
        Args:
            portfolio_info(Dict): 投资组合信息
            order(Order): 待处理的订单
            
        Returns:
            Order: 处理后的订单，如果拒绝订单则返回None
        """
        return order

    def generate_signals(self, portfolio_info: Dict, event: EventBase) -> List[Signal]:
        """
        风控信号生成
        接收到Event后主动生成风控信号来控制仓位
        
        Args:
            portfolio_info(Dict): 投资组合信息
            event(EventBase): 收到的事件
            
        Returns:
            List[Signal]: 风控信号列表
        """
        return []
