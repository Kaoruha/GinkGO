"""
执行确认事件模块

该模块定义了信号执行确认相关的事件类型，支持确认、拒绝、超时等执行状态变更事件。
"""

from typing import Optional
from decimal import Decimal
from datetime import datetime

from ginkgo.trading.events.base_event import EventBase
from ginkgo.enums import EVENT_TYPES, EXECUTION_STATUS, DIRECTION_TYPES


class EventExecutionConfirmed(EventBase):
    """
    执行确认事件
    
    当用户确认信号执行时触发，包含实际执行参数和偏差信息
    """
    
    def __init__(
        self,
        signal_id: str,
        tracking_id: str,
        code: str,
        direction: DIRECTION_TYPES,
        expected_price: Decimal,
        actual_price: Decimal,
        expected_volume: int,
        actual_volume: int,
        execution_time: datetime,
        slippage: Optional[Decimal] = None,
        delay_seconds: Optional[int] = None,
        commission: Optional[Decimal] = None,
        **kwargs
    ):
        """
        初始化执行确认事件
        
        Args:
            signal_id: 信号ID
            tracking_id: 追踪记录ID
            code: 股票代码
            direction: 交易方向
            expected_price: 预期价格
            actual_price: 实际执行价格
            expected_volume: 预期数量
            actual_volume: 实际执行数量
            execution_time: 执行时间
            slippage: 滑点（可选）
            delay_seconds: 延迟秒数（可选）
            commission: 手续费（可选）
        """
        super().__init__(name="ExecutionConfirmed", **kwargs)
        self.set_type(EVENT_TYPES.EXECUTION_CONFIRMATION)
        
        self.signal_id = signal_id
        self.tracking_id = tracking_id
        self.code = code
        self.direction = direction
        self.expected_price = expected_price
        self.actual_price = actual_price
        self.expected_volume = expected_volume
        self.actual_volume = actual_volume
        self.execution_time = execution_time
        self.slippage = slippage or Decimal('0')
        self.delay_seconds = delay_seconds or 0
        self.commission = commission or Decimal('0')
        
        # 计算偏差指标
        self.price_deviation = self._calculate_price_deviation()
        self.volume_deviation = self._calculate_volume_deviation()
        
    def _calculate_price_deviation(self) -> Decimal:
        """计算价格偏差百分比"""
        if self.expected_price == 0:
            return Decimal('0')
        return (self.actual_price - self.expected_price) / self.expected_price * 100
    
    def _calculate_volume_deviation(self) -> Decimal:
        """计算数量偏差百分比"""
        if self.expected_volume == 0:
            return Decimal('0')
        return Decimal((self.actual_volume - self.expected_volume) / self.expected_volume * 100)
    
    @property
    def transaction_value(self) -> Decimal:
        """计算实际成交金额"""
        return self.actual_price * self.actual_volume
    
    def __repr__(self) -> str:
        return (f"EventExecutionConfirmed(signal_id={self.signal_id[:8]}, "
                f"code={self.code}, direction={self.direction}, "
                f"price={self.actual_price}, volume={self.actual_volume})")


class EventExecutionRejected(EventBase):
    """
    执行拒绝事件
    
    当用户拒绝信号执行时触发
    """
    
    def __init__(
        self,
        signal_id: str,
        tracking_id: str,
        code: str,
        direction: DIRECTION_TYPES,
        reject_reason: str,
        reject_time: datetime,
        **kwargs
    ):
        """
        初始化执行拒绝事件
        
        Args:
            signal_id: 信号ID
            tracking_id: 追踪记录ID
            code: 股票代码
            direction: 交易方向
            reject_reason: 拒绝原因
            reject_time: 拒绝时间
        """
        super().__init__(name="ExecutionRejected", **kwargs)
        self.set_type(EVENT_TYPES.EXECUTION_REJECTION)
        
        self.signal_id = signal_id
        self.tracking_id = tracking_id
        self.code = code
        self.direction = direction
        self.reject_reason = reject_reason
        self.reject_time = reject_time
    
    def __repr__(self) -> str:
        return (f"EventExecutionRejected(signal_id={self.signal_id[:8]}, "
                f"code={self.code}, reason={self.reject_reason})")


class EventExecutionTimeout(EventBase):
    """
    执行超时事件
    
    当信号执行超时时触发
    """
    
    def __init__(
        self,
        signal_id: str,
        tracking_id: str,
        code: str,
        direction: DIRECTION_TYPES,
        timeout_duration: int,
        timeout_time: datetime,
        **kwargs
    ):
        """
        初始化执行超时事件
        
        Args:
            signal_id: 信号ID
            tracking_id: 追踪记录ID
            code: 股票代码
            direction: 交易方向
            timeout_duration: 超时时长（秒）
            timeout_time: 超时时间
        """
        super().__init__(name="ExecutionTimeout", **kwargs)
        self.set_type(EVENT_TYPES.EXECUTION_TIMEOUT)
        
        self.signal_id = signal_id
        self.tracking_id = tracking_id
        self.code = code
        self.direction = direction
        self.timeout_duration = timeout_duration
        self.timeout_time = timeout_time
    
    def __repr__(self) -> str:
        return (f"EventExecutionTimeout(signal_id={self.signal_id[:8]}, "
                f"code={self.code}, timeout={self.timeout_duration}s)")


class EventExecutionCanceled(EventBase):
    """
    执行取消事件
    
    当信号执行被系统取消时触发（如策略停止、系统错误等）
    """
    
    def __init__(
        self,
        signal_id: str,
        tracking_id: str,
        code: str,
        direction: DIRECTION_TYPES,
        cancel_reason: str,
        cancel_time: datetime,
        **kwargs
    ):
        """
        初始化执行取消事件
        
        Args:
            signal_id: 信号ID
            tracking_id: 追踪记录ID
            code: 股票代码
            direction: 交易方向
            cancel_reason: 取消原因
            cancel_time: 取消时间
        """
        super().__init__(name="ExecutionCanceled", **kwargs)
        self.set_type(EVENT_TYPES.EXECUTION_CANCELLATION)
        
        self.signal_id = signal_id
        self.tracking_id = tracking_id
        self.code = code
        self.direction = direction
        self.cancel_reason = cancel_reason
        self.cancel_time = cancel_time
    
    def __repr__(self) -> str:
        return (f"EventExecutionCanceled(signal_id={self.signal_id[:8]}, "
                f"code={self.code}, reason={self.cancel_reason})")