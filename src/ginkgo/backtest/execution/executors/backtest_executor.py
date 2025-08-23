from typing import Optional
from datetime import datetime
from decimal import Decimal

from .base_executor import BaseExecutor
from .execution_result import ExecutionResult
from .execution_constraints import ExecutionConstraints
from ....enums import EXECUTION_MODE, EXECUTION_STATUS, ACCOUNT_TYPE
from ....backtest.entities.signal import Signal
from ....libs import GLOG, time_logger


class BacktestExecutor(BaseExecutor):
    """
    回测执行器
    
    用于历史回测的自动化执行，直接模拟成交，无需人工干预
    """
    
    def __init__(self, slippage: float = 0.0, commission_rate: float = 0.0):
        """
        初始化回测执行器
        
        Args:
            slippage: 滑点率（默认0）
            commission_rate: 手续费率（默认0）
        """
        super().__init__(EXECUTION_MODE.BACKTEST)
        self.slippage = slippage
        self.commission_rate = commission_rate
    
    @time_logger(threshold=0.01)  # 信号执行，10ms阈值
    def execute_signal(self, signal: Signal) -> ExecutionResult:
        """
        执行信号 - 直接模拟成交
        
        Args:
            signal: 需要执行的交易信号
            
        Returns:
            ExecutionResult: 执行结果
        """
        try:
            # 计算执行价格（考虑滑点）
            expected_price = float(getattr(signal, 'price', 0))
            executed_price = self._calculate_executed_price(signal, expected_price)
            
            # 计算执行数量（回测中通常全部成交）
            expected_volume = getattr(signal, 'volume', 0)
            executed_volume = expected_volume
            
            # 计算手续费
            commission = self._calculate_commission(executed_price, executed_volume)
            
            # 返回成交结果
            return ExecutionResult(
                signal_id=signal.uuid,
                status=EXECUTION_STATUS.FILLED,
                executed_price=Decimal(str(executed_price)),
                executed_volume=executed_volume,
                execution_time=signal.timestamp,  # 回测中使用信号时间
                slippage=Decimal(str(abs(executed_price - expected_price) / expected_price)) if expected_price != 0 else Decimal('0'),
                delay_seconds=0,  # 回测中无延迟
                commission=commission
            )
            
        except Exception as e:
            GLOG.ERROR(f"BacktestExecutor failed to execute signal: {e}")
            return self.create_error_result(signal, f"Execution error: {e}")
    
    
    def can_auto_execute(self) -> bool:
        """
        是否支持自动执行
        
        Returns:
            bool: True，回测模式支持自动执行
        """
        return True
    
    def requires_confirmation(self) -> bool:
        """
        是否需要人工确认
        
        Returns:
            bool: False，回测模式不需要人工确认
        """
        return False
    
    def _validate_mode_specific(self, signal: Signal) -> bool:
        """
        回测模式特定的验证逻辑
        
        Args:
            signal: 交易信号
            
        Returns:
            bool: 模式特定验证是否通过
        """
        try:
            # 回测特有验证 - 基础验证已在父类完成
            # 这里只需要添加回测特有的验证逻辑
            return True
            
        except Exception as e:
            GLOG.ERROR(f"Backtest mode specific validation error: {e}")
            return False
    
    def _create_execution_constraints(self) -> Optional[ExecutionConstraints]:
        """
        创建回测模式的执行约束条件
        
        Returns:
            ExecutionConstraints: 回测模式通常没有约束
        """
        # 回测模式通常没有执行约束
        return None
    
    def _prepare_mode_specific(self, signal: Signal) -> bool:
        """
        回测模式特定的准备工作
        
        Args:
            signal: 交易信号
            
        Returns:
            bool: 准备是否成功
        """
        try:
            # 回测模式的准备工作很简单
            GLOG.DEBUG(f"Preparing backtest execution for signal: {signal.uuid}")
            return True
            
        except Exception as e:
            GLOG.ERROR(f"Backtest execution preparation failed: {e}")
            return False
    
    def _cleanup_mode_specific(self, signal: Signal, result: ExecutionResult) -> None:
        """
        回测模式特定的清理工作
        
        Args:
            signal: 已执行的信号
            result: 执行结果
        """
        try:
            GLOG.DEBUG(f"Cleaning up backtest execution for signal: {signal.uuid}")
            # 回测模式通常不需要特殊清理
            
        except Exception as e:
            GLOG.ERROR(f"Backtest cleanup execution failed: {e}")
    
    def _calculate_executed_price(self, signal: Signal, expected_price: float) -> float:
        """
        计算实际执行价格（考虑滑点）
        
        Args:
            signal: 交易信号
            expected_price: 预期价格
            
        Returns:
            float: 实际执行价格
        """
        if self.slippage == 0:
            return expected_price
        
        # 根据交易方向计算滑点
        # 买入时价格向上滑点，卖出时价格向下滑点
        direction_multiplier = 1 if signal.direction.value == 1 else -1
        slippage_amount = expected_price * self.slippage * direction_multiplier
        
        executed_price = expected_price + slippage_amount
        
        # 确保价格为正
        return max(executed_price, 0.01)
    
    def _calculate_commission(self, price: float, volume: int) -> Decimal:
        """
        计算手续费
        
        Args:
            price: 成交价格
            volume: 成交数量
            
        Returns:
            Decimal: 手续费金额
        """
        if self.commission_rate == 0:
            return Decimal('0')
        
        transaction_value = price * volume
        commission = transaction_value * self.commission_rate
        
        return Decimal(str(commission))
    
    def set_slippage(self, slippage: float) -> None:
        """
        设置滑点率
        
        Args:
            slippage: 滑点率
        """
        self.slippage = max(0, slippage)  # 确保滑点率非负
    
    def set_commission_rate(self, commission_rate: float) -> None:
        """
        设置手续费率
        
        Args:
            commission_rate: 手续费率
        """
        self.commission_rate = max(0, commission_rate)  # 确保手续费率非负
    
    def get_slippage(self) -> float:
        """
        获取当前滑点率
        
        Returns:
            float: 滑点率
        """
        return self.slippage
    
    def get_commission_rate(self) -> float:
        """
        获取当前手续费率
        
        Returns:
            float: 手续费率
        """
        return self.commission_rate