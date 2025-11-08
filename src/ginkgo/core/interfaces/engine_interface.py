"""
引擎统一接口定义

定义所有回测引擎必须实现的统一接口，
支持事件驱动、矩阵和混合等不同回测模式。
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum

from ginkgo.trading.bases.portfolio_base import PortfolioBase


class EngineMode(Enum):
    """引擎模式枚举"""
    EVENT_DRIVEN = "event_driven"
    MATRIX = "matrix" 
    HYBRID = "hybrid"
    AUTO = "auto"


class EngineStatus(Enum):
    """引擎状态枚举"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


class IEngine(ABC):
    """回测引擎统一接口"""
    
    def __init__(self, name: str = "UnknownEngine", mode: EngineMode = EngineMode.AUTO):
        self.name = name
        self.mode = mode
        self.status = EngineStatus.IDLE
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        
        # 引擎配置
        self._config = {}
        
        # 性能统计
        self._performance_stats = {
            'events_processed': 0,
            'execution_time': 0.0,
            'memory_usage_mb': 0.0,
            'error_count': 0
        }
        
        # 回调函数
        self._on_start_callbacks = []
        self._on_complete_callbacks = []
        self._on_error_callbacks = []
        
    @property
    def config(self) -> Dict[str, Any]:
        """引擎配置"""
        return self._config
    
    @property
    def performance_stats(self) -> Dict[str, Any]:
        """性能统计"""
        return self._performance_stats
    
    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self.status == EngineStatus.RUNNING
    
    @property
    def is_completed(self) -> bool:
        """是否已完成"""
        return self.status == EngineStatus.COMPLETED
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any] = None) -> None:
        """
        初始化引擎
        
        Args:
            config: 引擎配置参数
        """
        pass
    
    @abstractmethod
    def run(self, portfolio: PortfolioBase) -> Dict[str, Any]:
        """
        运行回测
        
        Args:
            portfolio: 投资组合
            
        Returns:
            Dict[str, Any]: 回测结果
        """
        pass
    
    def start(self) -> None:
        """开始运行"""
        if self.status not in [EngineStatus.IDLE, EngineStatus.PAUSED]:
            raise RuntimeError(f"引擎当前状态 {self.status.value} 不允许启动")
            
        self.status = EngineStatus.RUNNING
        self.started_at = datetime.now()
        
        # 执行启动回调
        for callback in self._on_start_callbacks:
            try:
                callback(self)
            except Exception as e:
                print(f"启动回调执行失败: {e}")
    
    def stop(self) -> None:
        """停止运行"""
        if self.status == EngineStatus.RUNNING:
            self.status = EngineStatus.COMPLETED
            self.completed_at = datetime.now()
            
            # 计算执行时间
            if self.started_at:
                self._performance_stats['execution_time'] = (
                    self.completed_at - self.started_at
                ).total_seconds()
            
            # 执行完成回调
            for callback in self._on_complete_callbacks:
                try:
                    callback(self)
                except Exception as e:
                    print(f"完成回调执行失败: {e}")
    
    def pause(self) -> None:
        """暂停运行"""
        if self.status == EngineStatus.RUNNING:
            self.status = EngineStatus.PAUSED
    
    def resume(self) -> None:
        """恢复运行"""
        if self.status == EngineStatus.PAUSED:
            self.status = EngineStatus.RUNNING
    
    def reset(self) -> None:
        """重置引擎状态"""
        self.status = EngineStatus.IDLE
        self.started_at = None
        self.completed_at = None
        self._performance_stats = {
            'events_processed': 0,
            'execution_time': 0.0,
            'memory_usage_mb': 0.0,
            'error_count': 0
        }
    
    def set_config(self, config: Dict[str, Any]) -> None:
        """设置引擎配置"""
        self._config.update(config)
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self._config.get(key, default)
    
    def validate_config(self) -> bool:
        """验证配置有效性"""
        return True
    
    def get_supported_modes(self) -> List[EngineMode]:
        """获取支持的引擎模式"""
        return [EngineMode.AUTO]
    
    def can_switch_mode(self, target_mode: EngineMode) -> bool:
        """检查是否可以切换到目标模式"""
        return target_mode in self.get_supported_modes()
    
    def switch_mode(self, target_mode: EngineMode) -> bool:
        """切换引擎模式"""
        if not self.can_switch_mode(target_mode):
            return False
            
        if self.status == EngineStatus.RUNNING:
            return False  # 运行中不允许切换
            
        self.mode = target_mode
        return True
    
    def add_callback(self, event: str, callback) -> None:
        """添加回调函数"""
        if event == 'on_start':
            self._on_start_callbacks.append(callback)
        elif event == 'on_complete':
            self._on_complete_callbacks.append(callback)
        elif event == 'on_error':
            self._on_error_callbacks.append(callback)
        else:
            raise ValueError(f"不支持的回调事件: {event}")
    
    def remove_callback(self, event: str, callback) -> None:
        """移除回调函数"""
        if event == 'on_start' and callback in self._on_start_callbacks:
            self._on_start_callbacks.remove(callback)
        elif event == 'on_complete' and callback in self._on_complete_callbacks:
            self._on_complete_callbacks.remove(callback)
        elif event == 'on_error' and callback in self._on_error_callbacks:
            self._on_error_callbacks.remove(callback)
    
    def update_performance_stats(self, stats: Dict[str, Any]) -> None:
        """更新性能统计"""
        self._performance_stats.update(stats)
    
    def get_memory_usage(self) -> float:
        """获取内存使用量(MB)"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0
    
    def log_error(self, error: Exception) -> None:
        """记录错误"""
        self._performance_stats['error_count'] += 1
        self.status = EngineStatus.ERROR
        
        # 执行错误回调
        for callback in self._on_error_callbacks:
            try:
                callback(self, error)
            except Exception as e:
                print(f"错误回调执行失败: {e}")
    
    def get_status_report(self) -> Dict[str, Any]:
        """获取状态报告"""
        return {
            'name': self.name,
            'mode': self.mode.value,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'performance_stats': self._performance_stats.copy(),
            'config': self._config.copy()
        }
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, mode={self.mode.value}, status={self.status.value})"
    
    def __repr__(self) -> str:
        return self.__str__()


class IEventDrivenEngine(IEngine):
    """事件驱动引擎接口"""
    
    def __init__(self, name: str = "EventDrivenEngine"):
        super().__init__(name, EngineMode.EVENT_DRIVEN)
        self._event_queue = None
        self._event_handlers = {}
        
    @abstractmethod
    def process_event(self, event: Any) -> None:
        """
        处理单个事件
        
        Args:
            event: 事件对象
        """
        pass
    
    @abstractmethod
    def main_loop(self, stop_flag) -> None:
        """
        主事件循环
        
        Args:
            stop_flag: 停止标志
        """
        pass
    
    def register_event_handler(self, event_type: str, handler) -> None:
        """注册事件处理器"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
    
    def unregister_event_handler(self, event_type: str, handler) -> None:
        """注销事件处理器"""
        if event_type in self._event_handlers:
            if handler in self._event_handlers[event_type]:
                self._event_handlers[event_type].remove(handler)
    
    def get_supported_modes(self) -> List[EngineMode]:
        return [EngineMode.EVENT_DRIVEN, EngineMode.HYBRID]


class IMatrixEngine(IEngine):
    """矩阵引擎接口"""
    
    def __init__(self, name: str = "MatrixEngine"):
        super().__init__(name, EngineMode.MATRIX)
        self._data_loader = None
        self._vectorized_processors = []
    
    @abstractmethod
    def load_data(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        加载数据
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            Dict[str, Any]: 加载的数据
        """
        pass
    
    @abstractmethod
    def process_vectorized(self, data: Dict[str, Any], portfolio: PortfolioBase) -> Dict[str, Any]:
        """
        向量化处理
        
        Args:
            data: 数据
            portfolio: 投资组合
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        pass
    
    def add_vectorized_processor(self, processor) -> None:
        """添加向量化处理器"""
        self._vectorized_processors.append(processor)
    
    def remove_vectorized_processor(self, processor) -> None:
        """移除向量化处理器"""
        if processor in self._vectorized_processors:
            self._vectorized_processors.remove(processor)
    
    def get_supported_modes(self) -> List[EngineMode]:
        return [EngineMode.MATRIX, EngineMode.HYBRID]


class IHybridEngine(IEngine):
    """混合引擎接口"""
    
    def __init__(self, name: str = "HybridEngine"):
        super().__init__(name, EngineMode.HYBRID)
        self._event_engine = None
        self._matrix_engine = None
        self._mode_selector = None
    
    @abstractmethod
    def select_optimal_mode(self, context: Dict[str, Any]) -> EngineMode:
        """
        选择最优模式
        
        Args:
            context: 上下文信息
            
        Returns:
            EngineMode: 选择的模式
        """
        pass
    
    @abstractmethod
    def switch_engine_mode(self, target_mode: EngineMode) -> bool:
        """
        切换引擎模式
        
        Args:
            target_mode: 目标模式
            
        Returns:
            bool: 是否切换成功
        """
        pass
    
    def get_supported_modes(self) -> List[EngineMode]:
        return [EngineMode.EVENT_DRIVEN, EngineMode.MATRIX, EngineMode.HYBRID, EngineMode.AUTO]