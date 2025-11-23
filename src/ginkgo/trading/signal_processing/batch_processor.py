"""
时间窗口批处理器核心实现

该模块定义了批处理系统的核心抽象类和枚举类型，提供信号批量处理的基础框架。
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple, Callable, Any
from datetime import datetime, timedelta
from ginkgo.trading.time.clock import now as clock_now
from enum import Enum
from collections import defaultdict

from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.entities.order import Order
from ginkgo.libs import GLOG


class WindowType(Enum):
    """时间窗口类型枚举"""
    DAILY = "daily"          # 日线窗口
    HOURLY = "hourly"        # 小时窗口  
    MINUTELY = "minutely"    # 分钟窗口
    IMMEDIATE = "immediate"  # 立即处理（兼容模式）


class ProcessingMode(Enum):
    """处理模式枚举"""
    BACKTEST = "backtest"    # 回测模式：严格时间窗口
    LIVE = "live"           # 实盘模式：即时响应优先
    HYBRID = "hybrid"       # 混合模式：可配置延迟


class TimeWindowBatchProcessor(ABC):
    """
    时间窗口批处理器基类
    
    该类实现了信号批量处理的核心逻辑，解决了传统逐个处理信号导致的
    资源竞争不真实问题。支持多种时间粒度和处理模式。
    """
    
    def __init__(self,
                 window_type: WindowType = WindowType.DAILY,
                 processing_mode: ProcessingMode = ProcessingMode.BACKTEST,
                 max_batch_delay: timedelta = timedelta(seconds=30),
                 min_batch_size: int = 1,
                 resource_optimization: bool = True,
                 priority_weighting: bool = False,
                 portfolio_info_getter: Optional[Callable] = None,
                 logger=None):
        """
        初始化批处理器
        
        Args:
            window_type: 时间窗口类型
            processing_mode: 处理模式
            max_batch_delay: 最大批处理延迟（实盘模式使用）
            min_batch_size: 最小批处理大小
            resource_optimization: 是否启用资源优化
            priority_weighting: 是否考虑信号优先级
            portfolio_info_getter: 组合信息获取函数
            logger: 日志记录器
        """
        # 配置属性
        self.window_type = window_type
        self.processing_mode = processing_mode
        self.max_batch_delay = max_batch_delay
        self.min_batch_size = min_batch_size
        self.resource_optimization = resource_optimization
        self.priority_weighting = priority_weighting
        
        # 功能组件
        self.get_portfolio_info = portfolio_info_getter
        self.logger = logger or GLOG
        
        # 内部状态
        self._signal_batches: Dict[datetime, List[Signal]] = defaultdict(list)
        self._batch_timestamps: Dict[datetime, datetime] = {}  # 记录批次创建时间
        self._processing_queue: List[Tuple[datetime, List[Signal]]] = []
        
        # 统计信息
        self._processed_batches = 0
        self._total_signals_processed = 0
        
    @abstractmethod
    def get_window_start(self, timestamp: datetime) -> datetime:
        """
        获取给定时间戳对应的窗口起始时间
        
        Args:
            timestamp: 信号时间戳
            
        Returns:
            窗口起始时间
        """
        pass
        
    @abstractmethod 
    def should_process_batch(self, window_start: datetime, signals: List[Signal]) -> bool:
        """
        判断是否应该处理该批次
        
        Args:
            window_start: 窗口起始时间
            signals: 该窗口内的信号列表
            
        Returns:
            是否应该处理
        """
        pass
        
    def add_signal(self, signal: Signal) -> Optional[List[Order]]:
        """
        添加信号到批处理队列
        
        Args:
            signal: 待处理信号
            
        Returns:
            如果触发批处理，返回生成的订单列表；否则返回None
        """
        try:
            window_start = self.get_window_start(signal.timestamp)
            
            # 记录信号到对应窗口
            if window_start not in self._signal_batches:
                self._batch_timestamps[window_start] = clock_now()
                
            self._signal_batches[window_start].append(signal)
            
            self.logger.DEBUG(f"Added signal {signal.code} to window {window_start}, "
                            f"batch size: {len(self._signal_batches[window_start])}")
            
            # 检查是否需要处理该批次
            if self.should_process_batch(window_start, self._signal_batches[window_start]):
                return self.process_batch(window_start)
                
        except Exception as e:
            self.logger.ERROR(f"Error adding signal to batch processor: {e}")
            
        return None
        
    def process_batch(self, window_start: datetime) -> List[Order]:
        """
        处理单个批次的信号
        
        Args:
            window_start: 窗口起始时间
            
        Returns:
            生成的订单列表
        """
        if window_start not in self._signal_batches:
            return []
            
        signals = self._signal_batches[window_start]
        del self._signal_batches[window_start]
        if window_start in self._batch_timestamps:
            del self._batch_timestamps[window_start]
            
        if not signals:
            return []
            
        try:
            self.logger.INFO(f"Processing batch with {len(signals)} signals from window {window_start}")
            
            # 根据配置选择处理策略
            if self.resource_optimization:
                orders = self._optimize_resource_allocation(signals)
            else:
                orders = self._simple_sequential_processing(signals)
                
            # 更新统计信息
            self._processed_batches += 1
            self._total_signals_processed += len(signals)
            
            self.logger.INFO(f"Batch processing completed: {len(orders)} orders generated from {len(signals)} signals")
            return orders
            
        except Exception as e:
            self.logger.ERROR(f"Error processing batch: {e}")
            return []
            
    def _optimize_resource_allocation(self, signals: List[Signal]) -> List[Order]:
        """
        资源优化分配算法
        
        Args:
            signals: 信号列表
            
        Returns:
            优化后的订单列表
        """
        if not self.get_portfolio_info:
            self.logger.WARN("No portfolio info getter provided, falling back to sequential processing")
            return self._simple_sequential_processing(signals)
            
        try:
            portfolio_info = self.get_portfolio_info()
            available_capital = portfolio_info.get('available_cash', 0)
            
            if available_capital <= 0:
                self.logger.WARN("No available capital for signal processing")
                return []
                
            # 信号优先级排序
            prioritized_signals = self._prioritize_signals(signals)
            
            # 资本分配优化
            orders = self._allocate_capital_optimally(prioritized_signals, available_capital, portfolio_info)
            
            return orders
            
        except Exception as e:
            self.logger.ERROR(f"Error in resource optimization: {e}")
            return self._simple_sequential_processing(signals)
            
    def _prioritize_signals(self, signals: List[Signal]) -> List[Signal]:
        """
        信号优先级排序
        
        Args:
            signals: 原始信号列表
            
        Returns:
            排序后的信号列表
        """
        if not self.priority_weighting:
            return signals
            
        # 按优先级、置信度等排序
        return sorted(signals, key=lambda s: (
            getattr(s, 'priority', 50),      # 优先级（默认50）
            getattr(s, 'confidence', 0.5),   # 置信度（默认0.5）
            -getattr(s, 'urgency', 0)        # 紧急度（负号表示高紧急度排前面）
        ), reverse=True)
        
    def _allocate_capital_optimally(self, signals: List[Signal], 
                                  available_capital: float, 
                                  portfolio_info: Dict[str, Any]) -> List[Order]:
        """
        最优资本分配算法
        
        Args:
            signals: 排序后的信号列表
            available_capital: 可用资金
            portfolio_info: 组合信息
            
        Returns:
            生成的订单列表
        """
        orders = []
        remaining_capital = available_capital
        
        for signal in signals:
            if remaining_capital <= 0:
                break
                
            try:
                # 计算建议仓位大小
                suggested_position_size = self._calculate_position_size(
                    signal, remaining_capital, portfolio_info
                )
                
                if suggested_position_size > 0:
                    order = self._create_order_from_signal(signal, suggested_position_size)
                    if order and order.frozen <= remaining_capital:
                        orders.append(order)
                        remaining_capital -= order.frozen
                        
            except Exception as e:
                self.logger.ERROR(f"Error processing signal {signal.code}: {e}")
                continue
                
        return orders
        
    def _simple_sequential_processing(self, signals: List[Signal]) -> List[Order]:
        """
        简单顺序处理（兼容模式）
        
        Args:
            signals: 信号列表
            
        Returns:
            订单列表
        """
        orders = []
        
        for signal in signals:
            try:
                # 这里需要调用现有的Sizer逻辑
                # 由于我们在基类中，这部分留给子类或Portfolio来实现
                pass
            except Exception as e:
                self.logger.ERROR(f"Error in sequential processing for signal {signal.code}: {e}")
                
        return orders
        
    def _calculate_position_size(self, signal: Signal, available_capital: float, 
                               portfolio_info: Dict[str, Any]) -> int:
        """
        计算建议仓位大小
        
        Args:
            signal: 交易信号
            available_capital: 可用资金  
            portfolio_info: 组合信息
            
        Returns:
            建议仓位大小
        """
        # 这是一个基础实现，实际应该根据风险控制和仓位管理策略来计算
        # 简单按资金的固定比例分配
        allocation_ratio = 0.1  # 默认每个信号分配10%资金
        estimated_price = getattr(signal, 'price', 10.0)  # 估算价格
        
        max_volume_by_capital = int((available_capital * allocation_ratio) / estimated_price)
        return max(0, max_volume_by_capital)
        
    def _create_order_from_signal(self, signal: Signal, volume: int) -> Optional[Order]:
        """
        从信号创建订单
        
        Args:
            signal: 交易信号
            volume: 交易数量
            
        Returns:
            创建的订单
        """
        if volume <= 0:
            return None
            
        try:
            estimated_price = getattr(signal, 'price', 10.0)
            
            order = Order(
                code=signal.code,
                direction=signal.direction,
                volume=volume,
                limit_price=estimated_price,
                frozen=estimated_price * volume,  # 简化的冻结金额计算
                timestamp=signal.timestamp,
                portfolio_id=signal.portfolio_id,
                engine_id=signal.engine_id
            )
            
            return order
            
        except Exception as e:
            self.logger.ERROR(f"Error creating order from signal {signal.code}: {e}")
            return None
            
    def force_process_all_batches(self) -> List[Order]:
        """
        强制处理所有待处理批次（回测结束时调用）
        
        Returns:
            所有生成的订单列表
        """
        all_orders = []
        
        for window_start in list(self._signal_batches.keys()):
            orders = self.process_batch(window_start)
            all_orders.extend(orders)
            
        self.logger.INFO(f"Force processed all batches: {len(all_orders)} total orders generated")
        return all_orders
        
    def get_stats(self) -> Dict[str, Any]:
        """
        获取处理统计信息
        
        Returns:
            统计信息字典
        """
        return {
            'processed_batches': self._processed_batches,
            'total_signals_processed': self._total_signals_processed,
            'pending_batches': len(self._signal_batches),
            'pending_signals': sum(len(signals) for signals in self._signal_batches.values()),
            'window_type': self.window_type.value,
            'processing_mode': self.processing_mode.value,
            'resource_optimization': self.resource_optimization,
        }
        
    def clear_batches(self) -> None:
        """清理所有待处理批次"""
        cleared_signals = sum(len(signals) for signals in self._signal_batches.values())
        self._signal_batches.clear()
        self._batch_timestamps.clear()
        self.logger.INFO(f"Cleared {cleared_signals} pending signals from {len(self._signal_batches)} batches")
