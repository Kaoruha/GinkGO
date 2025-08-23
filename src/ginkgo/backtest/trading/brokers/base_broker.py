"""
BaseBroker - 统一的Broker接口基类

定义了所有Broker必须实现的标准接口，确保不同类型的Broker
（模拟、OKX、IBKR等）都有一致的调用方式。
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from ginkgo.backtest.entities import Order
from ginkgo.enums import DIRECTION_TYPES, ORDERSTATUS_TYPES


class ExecutionStatus(Enum):
    """执行状态枚举"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass
class ExecutionResult:
    """订单执行结果"""
    order_id: str
    status: ExecutionStatus
    filled_volume: float = 0.0
    filled_price: float = 0.0
    commission: float = 0.0
    message: str = ""
    timestamp: Optional[str] = None
    broker_order_id: Optional[str] = None  # 券商返回的订单ID
    
    @property
    def is_success(self) -> bool:
        """判断是否执行成功"""
        return self.status in [ExecutionStatus.FILLED, ExecutionStatus.PARTIALLY_FILLED]
    
    @property
    def is_final_status(self) -> bool:
        """判断是否为最终状态"""
        return self.status in [
            ExecutionStatus.FILLED, 
            ExecutionStatus.CANCELLED, 
            ExecutionStatus.REJECTED, 
            ExecutionStatus.FAILED
        ]


@dataclass
class Position:
    """持仓信息"""
    code: str
    volume: float
    available_volume: float  # 可用数量
    avg_price: float
    market_value: float
    unrealized_pnl: float
    direction: DIRECTION_TYPES


@dataclass
class AccountInfo:
    """账户信息"""
    total_asset: float  # 总资产
    available_cash: float  # 可用现金
    frozen_cash: float  # 冻结资金
    market_value: float  # 持仓市值
    total_pnl: float  # 总盈亏


class BaseBroker(ABC):
    """
    Broker基类 - 定义统一的交易接口
    
    所有具体的Broker实现都应该继承此类并实现抽象方法。
    这样可以确保MatchMaking层能够以统一的方式调用不同的Broker。
    """
    
    def __init__(self, broker_config: Dict[str, Any]):
        """
        初始化Broker
        
        Args:
            broker_config: Broker配置字典
        """
        self.config = broker_config
        self.name = self.__class__.__name__
        self._connected = False
    
    @abstractmethod
    def connect(self) -> bool:
        """
        建立连接
        
        Returns:
            bool: 连接是否成功
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """
        断开连接
        
        Returns:
            bool: 断开是否成功
        """
        pass
    
    @property
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected
    
    @abstractmethod
    def submit_order(self, order: Order) -> ExecutionResult:
        """
        提交订单
        
        Args:
            order: 订单对象
            
        Returns:
            ExecutionResult: 执行结果
        """
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> ExecutionResult:
        """
        撤销订单
        
        Args:
            order_id: 订单ID
            
        Returns:
            ExecutionResult: 执行结果
        """
        pass
    
    @abstractmethod
    def query_order(self, order_id: str) -> ExecutionResult:
        """
        查询订单状态
        
        Args:
            order_id: 订单ID
            
        Returns:
            ExecutionResult: 订单状态
        """
        pass
    
    @abstractmethod
    def get_positions(self) -> List[Position]:
        """
        获取持仓信息
        
        Returns:
            List[Position]: 持仓列表
        """
        pass
    
    @abstractmethod
    def get_account_info(self) -> AccountInfo:
        """
        获取账户信息
        
        Returns:
            AccountInfo: 账户信息
        """
        pass
    
    def validate_order(self, order: Order) -> bool:
        """
        订单验证（基础验证，子类可覆盖）
        
        Args:
            order: 订单对象
            
        Returns:
            bool: 是否通过验证
        """
        if not order.code:
            return False
        if order.volume <= 0:
            return False
        if order.direction not in [DIRECTION_TYPES.LONG, DIRECTION_TYPES.SHORT]:
            return False
        return True
    
    def __str__(self) -> str:
        return f"{self.name}(connected={self.is_connected})"
    
    def __repr__(self) -> str:
        return self.__str__()