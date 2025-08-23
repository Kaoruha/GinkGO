from typing import Dict, List, Optional
from decimal import Decimal
import datetime

from ginkgo.backtest.entities.signal import Signal


class ExecutionConstraints:
    """
    执行约束类
    
    定义自动化交易的安全机制和限制条件
    """
    
    def __init__(self):
        # 金额限制
        self.max_single_order_value: Decimal = Decimal('10000')      # 单笔最大金额
        self.max_daily_volume: Decimal = Decimal('100000')           # 日最大交易量
        
        # 时间限制
        self.allowed_time_windows: List[tuple] = [
            (datetime.time(9, 30), datetime.time(11, 30)),   # 上午交易时间
            (datetime.time(13, 0), datetime.time(15, 0))     # 下午交易时间
        ]
        
        # 持仓限制
        self.max_single_position_ratio: float = 0.05         # 单股最大持仓比例
        self.max_total_position_ratio: float = 0.95          # 总持仓比例
        
        # 风险限制
        self.volatility_threshold: float = 0.05              # 波动率阈值
        self.max_daily_loss: float = 0.02                    # 日最大亏损
        
        # 流动性要求
        self.min_avg_volume: int = 100000                    # 最小平均成交量
        
        # 策略白名单
        self.auto_execution_enabled: bool = False
        self.whitelist_strategies: List[str] = []
        
        # 确认阈值（超过此值需要人工确认）
        self.confirmation_thresholds: Dict[str, Decimal] = {}
    
    def can_auto_execute(self, signal: Signal, current_positions: Optional[Dict] = None) -> bool:
        """
        判断信号是否可以自动执行
        
        Args:
            signal: 交易信号
            current_positions: 当前持仓情况
            
        Returns:
            bool: 是否可以自动执行
        """
        if not self.auto_execution_enabled:
            return False
        
        # 检查策略白名单
        if signal.strategy_id not in self.whitelist_strategies:
            return False
        
        # 检查订单金额
        order_value = signal.price * signal.volume
        if order_value > self.max_single_order_value:
            return False
        
        # 检查确认阈值
        threshold = self.confirmation_thresholds.get(signal.strategy_id, Decimal('0'))
        if order_value > threshold:
            return False
        
        # 检查交易时间窗口
        if not self._in_allowed_time_window():
            return False
        
        # 检查持仓限制（如果提供了当前持仓）
        if current_positions and self._exceeds_position_limits(signal, current_positions):
            return False
        
        return True
    
    def _in_allowed_time_window(self) -> bool:
        """检查是否在允许的交易时间窗口内"""
        current_time = datetime.datetime.now().time()
        
        for start_time, end_time in self.allowed_time_windows:
            if start_time <= current_time <= end_time:
                return True
        
        return False
    
    def _exceeds_position_limits(self, signal: Signal, current_positions: Dict) -> bool:
        """检查是否超过持仓限制"""
        # 这里需要具体的持仓计算逻辑
        # 暂时返回False，后续根据实际需求实现
        return False
    
    def update_constraints(self, **kwargs):
        """动态更新约束条件"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)