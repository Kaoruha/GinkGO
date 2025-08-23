import datetime
from typing import Optional
from decimal import Decimal

from ginkgo.enums import EXECUTION_STATUS


class ExecutionResult:
    """
    执行结果类
    
    统一的执行结果格式，支持所有执行模式
    """
    
    def __init__(
        self,
        signal_id: str,
        status: EXECUTION_STATUS,
        executed_price: Optional[Decimal] = None,
        executed_volume: Optional[int] = None,
        execution_time: Optional[datetime.datetime] = None,
        tracking_id: Optional[str] = None,
        reject_reason: Optional[str] = None,
        slippage: Optional[Decimal] = None,
        delay_seconds: Optional[int] = None,
        **kwargs
    ):
        self.signal_id = signal_id
        self.status = status
        self.executed_price = executed_price
        self.executed_volume = executed_volume
        self.execution_time = execution_time or datetime.datetime.now()
        self.tracking_id = tracking_id
        self.reject_reason = reject_reason
        self.slippage = slippage or Decimal('0')
        self.delay_seconds = delay_seconds or 0
        
        # 扩展字段
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    @property
    def is_successful(self) -> bool:
        """判断执行是否成功"""
        return self.status in [EXECUTION_STATUS.FILLED, EXECUTION_STATUS.PARTIAL_FILLED]
    
    @property
    def is_pending(self) -> bool:
        """判断是否等待确认"""
        return self.status == EXECUTION_STATUS.PENDING_CONFIRMATION
    
    @property
    def is_rejected(self) -> bool:
        """判断是否被拒绝"""
        return self.status in [EXECUTION_STATUS.REJECTED, EXECUTION_STATUS.ERROR]
    
    def __repr__(self) -> str:
        return f"ExecutionResult(signal_id={self.signal_id}, status={self.status}, executed_price={self.executed_price})"