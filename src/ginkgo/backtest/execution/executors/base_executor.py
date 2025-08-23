from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime

from .execution_result import ExecutionResult
from .execution_constraints import ExecutionConstraints
from ....enums import EXECUTION_MODE, EXECUTION_STATUS
from ....backtest.entities.signal import Signal
from ....libs import GLOG, time_logger


class BaseExecutor(ABC):
    """
    执行器基类
    
    提供所有执行器的公共功能和默认实现，具体执行器只需实现核心的execute_signal方法
    """
    
    def __init__(self, execution_mode: EXECUTION_MODE):
        """
        初始化执行器基类
        
        Args:
            execution_mode: 执行模式
        """
        self.execution_mode = execution_mode
        self._constraints: Optional[ExecutionConstraints] = None
    
    def get_execution_mode(self) -> EXECUTION_MODE:
        """
        获取执行模式
        
        Returns:
            EXECUTION_MODE: 当前执行模式
        """
        return self.execution_mode
    
    @abstractmethod
    def execute_signal(self, signal: Signal) -> ExecutionResult:
        """
        执行信号的统一接口 - 子类必须实现
        
        Args:
            signal: 需要执行的交易信号
            
        Returns:
            ExecutionResult: 执行结果
        """
        pass
    
    @abstractmethod
    def can_auto_execute(self) -> bool:
        """
        是否支持自动执行 - 子类必须实现
        
        Returns:
            bool: 是否支持自动执行
        """
        pass
    
    @abstractmethod
    def requires_confirmation(self) -> bool:
        """
        是否需要人工确认 - 子类必须实现
        
        Returns:
            bool: 是否需要人工确认
        """
        pass
    
    def validate_signal(self, signal: Signal) -> bool:
        """
        验证信号有效性 - 提供通用的信号验证逻辑
        
        Args:
            signal: 需要验证的信号
            
        Returns:
            bool: 信号是否有效
        """
        try:
            # 基础字段验证
            if not self._validate_basic_fields(signal):
                return False
            
            # 业务逻辑验证
            if not self._validate_business_rules(signal):
                return False
            
            # 执行模式特定验证
            if not self._validate_mode_specific(signal):
                return False
            
            return True
            
        except Exception as e:
            GLOG.ERROR(f"Signal validation error: {e}")
            return False
    
    def _validate_basic_fields(self, signal: Signal) -> bool:
        """
        验证信号的基础字段
        
        Args:
            signal: 交易信号
            
        Returns:
            bool: 基础字段是否有效
        """
        if not signal.uuid:
            GLOG.WARN("Signal missing uuid")
            return False
        
        if not signal.code:
            GLOG.WARN("Signal missing code")
            return False
        
        if not signal.direction:
            GLOG.WARN("Signal missing direction")
            return False
        
        if not hasattr(signal, 'price') or not signal.price:
            GLOG.WARN("Signal missing price")
            return False
        
        if not hasattr(signal, 'volume') or signal.volume <= 0:
            GLOG.WARN("Signal missing or invalid volume")
            return False
        
        if not signal.timestamp:
            GLOG.WARN("Signal missing timestamp")
            return False
        
        return True
    
    def _validate_business_rules(self, signal: Signal) -> bool:
        """
        验证信号的业务规则
        
        Args:
            signal: 交易信号
            
        Returns:
            bool: 业务规则是否通过
        """
        # 价格必须为正
        if float(signal.price) <= 0:
            GLOG.WARN("Signal price must be positive")
            return False
        
        # 数量必须为正整数
        if signal.volume <= 0 or not isinstance(signal.volume, int):
            GLOG.WARN("Signal volume must be positive integer")
            return False
        
        # 时间戳不能是未来时间（对于回测和模拟盘）
        if signal.timestamp > datetime.now():
            GLOG.WARN("Signal timestamp cannot be in the future")
            return False
        
        return True
    
    def _validate_mode_specific(self, signal: Signal) -> bool:
        """
        执行模式特定的验证逻辑 - 子类可以重写
        
        Args:
            signal: 交易信号
            
        Returns:
            bool: 模式特定验证是否通过
        """
        # 默认通过，子类可以重写添加特定验证
        return True
    
    def get_execution_constraints(self) -> Optional[ExecutionConstraints]:
        """
        获取执行约束条件 - 提供缓存机制
        
        Returns:
            ExecutionConstraints: 执行约束条件，如果不需要约束则返回None
        """
        if self._constraints is None:
            self._constraints = self._create_execution_constraints()
        return self._constraints
    
    def _create_execution_constraints(self) -> Optional[ExecutionConstraints]:
        """
        创建执行约束条件 - 子类可以重写
        
        Returns:
            ExecutionConstraints: 执行约束条件
        """
        # 默认无约束，子类可以重写
        return None
    
    def prepare_execution(self, signal: Signal) -> bool:
        """
        执行前准备工作 - 提供通用的准备逻辑
        
        Args:
            signal: 准备执行的信号
            
        Returns:
            bool: 准备是否成功
        """
        try:
            GLOG.DEBUG(f"Preparing execution for signal: {signal.uuid} in mode: {self.execution_mode}")
            
            # 通用准备工作
            if not self._prepare_common(signal):
                return False
            
            # 模式特定准备工作
            if not self._prepare_mode_specific(signal):
                return False
            
            return True
            
        except Exception as e:
            GLOG.ERROR(f"Prepare execution failed: {e}")
            return False
    
    def _prepare_common(self, signal: Signal) -> bool:
        """
        通用准备工作
        
        Args:
            signal: 交易信号
            
        Returns:
            bool: 准备是否成功
        """
        # 检查约束条件
        constraints = self.get_execution_constraints()
        if constraints and not constraints.can_auto_execute(signal):
            GLOG.WARN(f"Signal {signal.uuid} violates execution constraints")
            return False
        
        return True
    
    def _prepare_mode_specific(self, signal: Signal) -> bool:
        """
        模式特定准备工作 - 子类可以重写
        
        Args:
            signal: 交易信号
            
        Returns:
            bool: 准备是否成功
        """
        # 默认成功，子类可以重写
        return True
    
    def cleanup_execution(self, signal: Signal, result: ExecutionResult) -> None:
        """
        执行后清理工作 - 提供通用的清理逻辑
        
        Args:
            signal: 已执行的信号
            result: 执行结果
        """
        try:
            GLOG.DEBUG(f"Cleaning up execution for signal: {signal.uuid}")
            
            # 通用清理工作
            self._cleanup_common(signal, result)
            
            # 模式特定清理工作
            self._cleanup_mode_specific(signal, result)
            
        except Exception as e:
            GLOG.ERROR(f"Cleanup execution failed: {e}")
    
    def _cleanup_common(self, signal: Signal, result: ExecutionResult) -> None:
        """
        通用清理工作
        
        Args:
            signal: 已执行的信号
            result: 执行结果
        """
        # 记录执行统计
        self._record_execution_stats(signal, result)
    
    def _cleanup_mode_specific(self, signal: Signal, result: ExecutionResult) -> None:
        """
        模式特定清理工作 - 子类可以重写
        
        Args:
            signal: 已执行的信号
            result: 执行结果
        """
        # 默认无操作，子类可以重写
        pass
    
    def _record_execution_stats(self, signal: Signal, result: ExecutionResult) -> None:
        """
        记录执行统计信息
        
        Args:
            signal: 交易信号
            result: 执行结果
        """
        try:
            # 记录基础统计信息
            GLOG.DEBUG(f"Execution stats - Signal: {signal.uuid}, Status: {result.status}, "
                      f"Mode: {self.execution_mode}")
            
            # 如果执行成功，记录更详细的信息
            if result.is_successful:
                GLOG.DEBUG(f"Successful execution - Price: {result.executed_price}, "
                          f"Volume: {result.executed_volume}, Slippage: {result.slippage}")
            
        except Exception as e:
            GLOG.ERROR(f"Failed to record execution stats: {e}")
    
    def create_error_result(self, signal: Signal, reason: str) -> ExecutionResult:
        """
        创建错误执行结果 - 统一的错误结果创建方法
        
        Args:
            signal: 交易信号
            reason: 错误原因
            
        Returns:
            ExecutionResult: 错误执行结果
        """
        return ExecutionResult(
            signal_id=signal.uuid,
            status=EXECUTION_STATUS.ERROR,
            reject_reason=reason,
            execution_time=datetime.now()
        )
    
    def create_rejected_result(self, signal: Signal, reason: str) -> ExecutionResult:
        """
        创建拒绝执行结果 - 统一的拒绝结果创建方法
        
        Args:
            signal: 交易信号
            reason: 拒绝原因
            
        Returns:
            ExecutionResult: 拒绝执行结果
        """
        return ExecutionResult(
            signal_id=signal.uuid,
            status=EXECUTION_STATUS.REJECTED,
            reject_reason=reason,
            execution_time=datetime.now()
        )
    
    @time_logger
    def execute_signal_with_lifecycle(self, signal: Signal) -> ExecutionResult:
        """
        带完整生命周期的信号执行 - 模板方法模式
        
        Args:
            signal: 需要执行的交易信号
            
        Returns:
            ExecutionResult: 执行结果
        """
        try:
            # 1. 验证信号
            if not self.validate_signal(signal):
                return self.create_rejected_result(signal, "Signal validation failed")
            
            # 2. 准备执行
            if not self.prepare_execution(signal):
                return self.create_error_result(signal, "Execution preparation failed")
            
            # 3. 执行信号（由子类实现）
            result = self.execute_signal(signal)
            
            # 4. 清理工作
            self.cleanup_execution(signal, result)
            
            return result
            
        except Exception as e:
            GLOG.ERROR(f"Signal execution lifecycle failed: {e}")
            return self.create_error_result(signal, f"Execution lifecycle error: {e}")
    
    def __str__(self) -> str:
        """
        字符串表示
        
        Returns:
            str: 执行器描述
        """
        return f"{self.__class__.__name__}(mode={self.execution_mode})"
    
    def __repr__(self) -> str:
        """
        对象表示
        
        Returns:
            str: 执行器详细描述
        """
        return (f"{self.__class__.__name__}("
                f"mode={self.execution_mode}, "
                f"auto_execute={self.can_auto_execute()}, "
                f"requires_confirmation={self.requires_confirmation()})")