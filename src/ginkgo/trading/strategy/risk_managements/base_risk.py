from typing import List, Dict, Any
from ginkgo.trading.entities.order import Order
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.core.backtest_base import BacktestBase
from ginkgo.trading.entities.time_related import TimeRelated
from ginkgo.trading.events.base_event import EventBase


class BaseRiskManagement(BacktestBase, TimeRelated):
    def __init__(self, name: str = "baseriskmanagement", timestamp=None, *args, **kwargs):
        BacktestBase.__init__(self, name=name, *args, **kwargs)
        TimeRelated.__init__(self, timestamp=timestamp, *args, **kwargs)
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
