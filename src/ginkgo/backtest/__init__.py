"""
Ginkgo Backtest Module - 量化回测框架

重组后的模块化架构：
- core/: 核心基础设施
- entities/: 业务实体对象
- execution/: 执行引擎层  
- strategy/: 策略层
- computation/: 计算层（技术指标）
- analysis/: 分析评估层
- trading/: 交易层
- services/: 服务层
"""

# === 核心基础设施 ===
from .core.base import Base
from .core.backtest_base import BacktestBase
from .core.file_info import FileInfo
from .core.containers import Container

# === 业务实体对象 ===
from .entities.bar import Bar
from .entities.order import Order
from .entities.position import Position
from .entities.signal import Signal
from .entities.stockinfo import StockInfo
from .entities.tick import Tick
from .entities.tradeday import TradeDay
from .entities.transfer import Transfer
from .entities.adjustfactor import Adjustfactor
from .entities.time_related import TimeRelated

# === 计算模块（向后兼容） ===
# 从computation模块导入所有技术指标
from .computation import *

# === 向后兼容的别名 ===
# 为了保持与旧代码的兼容性，提供常用类的直接访问
# 暂时注释掉，等测试通过后再启用
# from .execution.engines.historic_engine import HistoricEngine
# from .execution.engines.live_engine import LiveEngine
# from .execution.portfolios.base_portfolio import BasePortfolio  
# from .strategy.strategies.base_strategy import BaseStrategy
# from .analysis.analyzers.base_analyzer import BaseAnalyzer

# === 公共接口导出 ===
__all__ = [
    # 核心基础设施
    "Base", "BacktestBase", "FileInfo", "Container",
    
    # 业务实体
    "Bar", "Order", "Position", "Signal", "StockInfo", 
    "Tick", "TradeDay", "Transfer", "Adjustfactor", "TimeRelated",
    
    # 引擎和核心组件（暂时注释，等修复后启用）
    # "HistoricEngine", "LiveEngine", "BasePortfolio", 
    # "BaseStrategy", "BaseAnalyzer",
    
    # 技术指标（从computation导入）
    "BaseIndicator", "SimpleMovingAverage", "ExponentialMovingAverage",
    "AverageTrueRange", "BollingerBands", "RelativeStrengthIndex",
    
    # Alpha158因子
    "Alpha158Factory", "KMID", "KLEN", "KLOW", "KHIGH",
    "MA", "STD", "BETA", "ROC", "MAX", "MIN",
]

# === 向后兼容性处理 ===
import warnings
import sys
from types import ModuleType

def _create_compatibility_warning(old_path: str, new_path: str):
    """创建兼容性警告的辅助函数"""
    warnings.warn(
        f"从 '{old_path}' 导入已弃用。请使用 '{new_path}'。"
        f"此兼容性层将在未来版本中移除。",
        DeprecationWarning,
        stacklevel=3
    )

# 创建兼容性模块映射
class _CompatibilityModule(ModuleType):
    """兼容性模块，用于处理旧的导入路径"""
    
    def __init__(self, name, new_module):
        super().__init__(name)
        self._new_module = new_module
        self._old_path = name
        self._new_path = new_module.__name__
    
    def __getattr__(self, name):
        _create_compatibility_warning(self._old_path, self._new_path)
        return getattr(self._new_module, name)

# 注册兼容性模块
try:
    # 为旧的 indicators 模块创建兼容性层
    from . import computation as computation_module
    indicators_compat = _CompatibilityModule('ginkgo.backtest.indicators', computation_module)
    sys.modules['ginkgo.backtest.indicators'] = indicators_compat
    
    # 为旧的 indices 模块创建兼容性层（指向同样的 computation 模块）
    indices_compat = _CompatibilityModule('ginkgo.backtest.indices', computation_module)  
    sys.modules['ginkgo.backtest.indices'] = indices_compat
    
except ImportError:
    # 如果导入失败，跳过兼容性层设置
    pass

# 添加常见的别名映射，用于向后兼容
try:
    # 技术指标的别名
    from .computation.technical.base_indicator import BaseIndicator
    BaseIndex = BaseIndicator  # 常用的别名
    
    # 将别名添加到 __all__ 中（如果还没有的话）
    if 'BaseIndex' not in __all__:
        __all__.append('BaseIndex')
        
except ImportError:
    pass

# === 模块元数据 ===
__version__ = "3.0.0"
__author__ = "Ginkgo Team"
__description__ = "重组后的量化回测框架 - 模块化架构"

# 兼容性信息
__compatibility_notes__ = """
重构说明 (v3.0.0):
- indicators/ → computation/
- indices/ → computation/ (已删除重复)
- 数据容器类 → entities/
- 引擎类 → execution/engines/
- 策略类 → strategy/strategies/
- 分析器 → analysis/analyzers/

旧的导入路径仍然支持，但会显示弃用警告。
"""
