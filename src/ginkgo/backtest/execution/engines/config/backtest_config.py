"""
回测配置类

统一管理所有回测相关的配置参数，支持不同引擎模式的配置。
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, date
from enum import Enum

from ginkgo.core.interfaces.engine_interface import EngineMode


class DataFrequency(Enum):
    """数据频率"""
    DAILY = "daily"
    HOURLY = "hourly"
    MINUTE_30 = "30min"
    MINUTE_15 = "15min"
    MINUTE_5 = "5min"
    MINUTE_1 = "1min"
    SECOND = "second"
    TICK = "tick"


class TradingSession(Enum):
    """交易时段"""
    FULL_DAY = "full_day"
    MORNING = "morning"
    AFTERNOON = "afternoon"
    NIGHT = "night"
    CUSTOM = "custom"


@dataclass
class BacktestConfig:
    """回测配置类"""
    
    # 基础配置
    name: str = "DefaultBacktest"
    description: str = ""
    start_date: Union[str, date, datetime] = "2020-01-01"
    end_date: Union[str, date, datetime] = "2023-12-31"
    initial_capital: float = 1000000.0
    
    # 引擎配置
    engine_mode: EngineMode = EngineMode.AUTO
    data_frequency: DataFrequency = DataFrequency.DAILY
    trading_session: TradingSession = TradingSession.FULL_DAY
    
    # 数据配置
    enable_tick_data: bool = False
    enable_level2_data: bool = False
    adjust_type: str = "fore"  # fore, back, none
    include_suspended: bool = False
    min_trading_days: int = 60
    
    # 交易配置
    transaction_cost: float = 0.0003  # 万分之3
    slippage: float = 0.001  # 千分之1
    min_order_amount: float = 100.0  # 最小下单金额
    max_single_position: float = 0.2  # 单只股票最大仓位
    cash_reserve_ratio: float = 0.05  # 现金保留比例
    
    # 风险控制
    enable_stop_loss: bool = False
    stop_loss_ratio: float = -0.1  # -10%止损
    enable_stop_profit: bool = False
    stop_profit_ratio: float = 0.2  # 20%止盈
    max_drawdown_limit: float = -0.3  # 最大回撤限制
    
    # 事件驱动引擎配置
    event_engine_config: Dict[str, Any] = field(default_factory=lambda: {
        'sleep_interval': 0.001,  # 主循环休眠间隔(秒)
        'max_queue_size': 10000,  # 事件队列最大大小
        'enable_priority_queue': True,  # 启用优先队列
        'enable_event_cache': True,  # 启用事件缓存
        'cache_size': 1000,  # 缓存大小
        'enable_batch_processing': True,  # 启用批处理
        'batch_size': 100,  # 批处理大小
        'timeout': 10.0,  # 超时时间(秒)
        'max_retries': 3,  # 最大重试次数
    })
    
    # 矩阵引擎配置
    matrix_engine_config: Dict[str, Any] = field(default_factory=lambda: {
        'chunk_size': 1000,  # 数据分块大小
        'parallel_workers': 4,  # 并行工作进程数
        'memory_limit_mb': 1000,  # 内存限制(MB)
        'enable_gpu': False,  # 启用GPU加速
        'gpu_memory_fraction': 0.8,  # GPU内存使用比例
        'enable_cache': True,  # 启用结果缓存
        'cache_dir': "./cache",  # 缓存目录
        'optimize_memory': True,  # 内存优化
        'enable_progress_bar': True,  # 进度条
    })
    
    # 混合引擎配置
    hybrid_engine_config: Dict[str, Any] = field(default_factory=lambda: {
        'auto_switch_threshold': 10000,  # 自动切换阈值
        'prefer_matrix_for_large_data': True,  # 大数据优先矩阵模式
        'enable_performance_monitor': True,  # 性能监控
        'monitor_interval': 60,  # 监控间隔(秒)
        'switch_cooldown': 300,  # 切换冷却时间(秒)
    })
    
    # 输出配置
    output_config: Dict[str, Any] = field(default_factory=lambda: {
        'save_results': True,  # 保存结果
        'result_dir': "./results",  # 结果目录
        'save_trades': True,  # 保存交易记录
        'save_positions': True,  # 保存持仓记录
        'save_signals': False,  # 保存信号记录
        'export_format': ['csv', 'json'],  # 导出格式
        'plot_results': True,  # 生成图表
        'plot_format': 'png',  # 图表格式
    })
    
    # 扩展配置
    custom_config: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后处理"""
        # 标准化日期格式
        self.start_date = self._normalize_date(self.start_date)
        self.end_date = self._normalize_date(self.end_date)
        
        # 验证配置
        self._validate_config()
    
    def _normalize_date(self, date_input: Union[str, date, datetime]) -> str:
        """标准化日期格式"""
        if isinstance(date_input, str):
            return date_input
        elif isinstance(date_input, (date, datetime)):
            return date_input.strftime("%Y-%m-%d")
        else:
            raise ValueError(f"不支持的日期格式: {type(date_input)}")
    
    def _validate_config(self) -> None:
        """验证配置参数"""
        errors = []
        
        # 验证日期
        try:
            start = datetime.strptime(self.start_date, "%Y-%m-%d")
            end = datetime.strptime(self.end_date, "%Y-%m-%d")
            if start >= end:
                errors.append("开始日期必须早于结束日期")
        except ValueError as e:
            errors.append(f"日期格式错误: {e}")
        
        # 验证资金
        if self.initial_capital <= 0:
            errors.append("初始资金必须大于0")
        
        # 验证比例参数
        if not (0 <= self.transaction_cost <= 0.1):
            errors.append("交易成本应在0-10%之间")
        
        if not (0 <= self.slippage <= 0.1):
            errors.append("滑点应在0-10%之间")
        
        if not (0 <= self.max_single_position <= 1):
            errors.append("单只股票最大仓位应在0-100%之间")
        
        if not (0 <= self.cash_reserve_ratio <= 1):
            errors.append("现金保留比例应在0-100%之间")
        
        # 验证止损止盈
        if self.enable_stop_loss and self.stop_loss_ratio >= 0:
            errors.append("止损比例应为负数")
        
        if self.enable_stop_profit and self.stop_profit_ratio <= 0:
            errors.append("止盈比例应为正数")
        
        if errors:
            raise ValueError(f"配置验证失败: {'; '.join(errors)}")
    
    def get_engine_config(self, engine_mode: EngineMode = None) -> Dict[str, Any]:
        """获取特定引擎的配置"""
        mode = engine_mode or self.engine_mode
        
        if mode == EngineMode.EVENT_DRIVEN:
            return self.event_engine_config
        elif mode == EngineMode.MATRIX:
            return self.matrix_engine_config
        elif mode == EngineMode.HYBRID:
            return self.hybrid_engine_config
        else:
            return {}
    
    def set_engine_config(self, engine_mode: EngineMode, config: Dict[str, Any]) -> None:
        """设置特定引擎的配置"""
        if engine_mode == EngineMode.EVENT_DRIVEN:
            self.event_engine_config.update(config)
        elif engine_mode == EngineMode.MATRIX:
            self.matrix_engine_config.update(config)
        elif engine_mode == EngineMode.HYBRID:
            self.hybrid_engine_config.update(config)
    
    def enable_debug_mode(self) -> None:
        """启用调试模式"""
        self.event_engine_config['enable_event_cache'] = False
        self.matrix_engine_config['enable_cache'] = False
        self.output_config['save_signals'] = True
        self.custom_config['debug_mode'] = True
    
    def enable_performance_mode(self) -> None:
        """启用性能模式"""
        self.event_engine_config['enable_batch_processing'] = True
        self.event_engine_config['batch_size'] = 200
        self.matrix_engine_config['parallel_workers'] = 8
        self.matrix_engine_config['optimize_memory'] = True
        self.custom_config['performance_mode'] = True
    
    def optimize_for_large_dataset(self) -> None:
        """为大数据集优化"""
        self.engine_mode = EngineMode.MATRIX
        self.matrix_engine_config.update({
            'chunk_size': 2000,
            'parallel_workers': 8,
            'memory_limit_mb': 2000,
            'optimize_memory': True,
        })
        self.custom_config['large_dataset_mode'] = True
    
    def optimize_for_realtime(self) -> None:
        """为实时交易优化"""
        self.engine_mode = EngineMode.EVENT_DRIVEN
        self.event_engine_config.update({
            'sleep_interval': 0.0001,
            'enable_batch_processing': False,
            'enable_event_cache': False,
            'timeout': 1.0,
        })
        self.custom_config['realtime_mode'] = True
    
    def get_trading_period_days(self) -> int:
        """获取交易期间天数"""
        start = datetime.strptime(self.start_date, "%Y-%m-%d")
        end = datetime.strptime(self.end_date, "%Y-%m-%d")
        return (end - start).days
    
    def estimate_memory_usage(self) -> float:
        """估算内存使用量(MB)"""
        days = self.get_trading_period_days()
        
        # 基础估算：每天每只股票约1KB数据
        estimated_stocks = 4000  # A股约4000只股票
        base_memory = days * estimated_stocks * 0.001  # MB
        
        # 根据数据频率调整
        frequency_multiplier = {
            DataFrequency.DAILY: 1,
            DataFrequency.HOURLY: 4,
            DataFrequency.MINUTE_30: 8,
            DataFrequency.MINUTE_15: 16,
            DataFrequency.MINUTE_5: 48,
            DataFrequency.MINUTE_1: 240,
            DataFrequency.TICK: 1000,
        }
        
        multiplier = frequency_multiplier.get(self.data_frequency, 1)
        estimated_memory = base_memory * multiplier
        
        # 考虑缓存和临时数据
        if self.event_engine_config.get('enable_event_cache', False):
            estimated_memory *= 1.5
        
        if self.matrix_engine_config.get('enable_cache', False):
            estimated_memory *= 2.0
        
        return estimated_memory
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'name': self.name,
            'description': self.description,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'initial_capital': self.initial_capital,
            'engine_mode': self.engine_mode.value,
            'data_frequency': self.data_frequency.value,
            'trading_session': self.trading_session.value,
            'transaction_cost': self.transaction_cost,
            'slippage': self.slippage,
            'max_single_position': self.max_single_position,
            'cash_reserve_ratio': self.cash_reserve_ratio,
            'event_engine_config': self.event_engine_config,
            'matrix_engine_config': self.matrix_engine_config,
            'hybrid_engine_config': self.hybrid_engine_config,
            'output_config': self.output_config,
            'custom_config': self.custom_config,
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'BacktestConfig':
        """从字典创建配置对象"""
        # 转换枚举值
        if 'engine_mode' in config_dict:
            config_dict['engine_mode'] = EngineMode(config_dict['engine_mode'])
        if 'data_frequency' in config_dict:
            config_dict['data_frequency'] = DataFrequency(config_dict['data_frequency'])
        if 'trading_session' in config_dict:
            config_dict['trading_session'] = TradingSession(config_dict['trading_session'])
        
        return cls(**config_dict)
    
    def save_to_file(self, filepath: str) -> None:
        """保存配置到文件"""
        import json
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'BacktestConfig':
        """从文件加载配置"""
        import json
        
        with open(filepath, 'r', encoding='utf-8') as f:
            config_dict = json.load(f)
        
        return cls.from_dict(config_dict)
    
    def copy(self) -> 'BacktestConfig':
        """创建配置副本"""
        return self.from_dict(self.to_dict())
    
    def __str__(self) -> str:
        return f"BacktestConfig(name={self.name}, period={self.start_date}~{self.end_date}, mode={self.engine_mode.value})"
    
    def __repr__(self) -> str:
        return self.__str__()


# 预定义配置模板
class ConfigTemplates:
    """配置模板"""
    
    @staticmethod
    def day_trading_config() -> BacktestConfig:
        """日内交易配置"""
        config = BacktestConfig(
            name="DayTradingBacktest",
            data_frequency=DataFrequency.MINUTE_5,
            engine_mode=EngineMode.EVENT_DRIVEN,
            transaction_cost=0.0005,  # 日内交易成本更高
            slippage=0.002,
            max_single_position=0.1,  # 分散持仓
            cash_reserve_ratio=0.1,  # 保留更多现金
        )
        config.optimize_for_realtime()
        return config
    
    @staticmethod
    def swing_trading_config() -> BacktestConfig:
        """波段交易配置"""
        config = BacktestConfig(
            name="SwingTradingBacktest",
            data_frequency=DataFrequency.DAILY,
            engine_mode=EngineMode.MATRIX,
            transaction_cost=0.0003,
            max_single_position=0.2,
            enable_stop_loss=True,
            stop_loss_ratio=-0.08,
            enable_stop_profit=True,
            stop_profit_ratio=0.15,
        )
        return config
    
    @staticmethod
    def long_term_config() -> BacktestConfig:
        """长期投资配置"""
        config = BacktestConfig(
            name="LongTermBacktest",
            data_frequency=DataFrequency.DAILY,
            engine_mode=EngineMode.MATRIX,
            transaction_cost=0.0002,
            max_single_position=0.3,
            cash_reserve_ratio=0.02,  # 长期投资现金保留较少
            min_trading_days=252,  # 至少一年数据
        )
        config.optimize_for_large_dataset()
        return config
    
    @staticmethod
    def ml_research_config() -> BacktestConfig:
        """ML研究配置"""
        config = BacktestConfig(
            name="MLResearchBacktest", 
            data_frequency=DataFrequency.DAILY,
            engine_mode=EngineMode.AUTO,
            initial_capital=10000000,  # 更大的资金池
            min_trading_days=500,  # 更长的历史数据
        )
        config.enable_debug_mode()
        config.matrix_engine_config.update({
            'parallel_workers': 8,
            'memory_limit_mb': 4000,
            'enable_cache': True,
        })
        return config