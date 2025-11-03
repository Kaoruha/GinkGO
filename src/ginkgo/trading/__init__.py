"""
Ginkgo Backtest Module - 量化回测框架

统一的T5事件驱动架构：
- core/: 核心基础设施
- entities/: 业务实体对象
- engines/: 事件驱动引擎层 (原execution/engines)
- events/: 事件体系 (原execution/events)
- feeders/: 数据供给层 (原execution/feeders)
- portfolios/: 投资组合管理 (原execution/portfolios)
- brokers/: 统一交易执行层
- routing/: 订单路由中心 (原matchmakings)
- strategy/: 策略层
- computation/: 计算层（技术指标）
- analysis/: 分析评估层
- services/: 服务层
"""

# === 核心基础设施 ===
from ginkgo.trading.core.base import Base
from ginkgo.trading.core.backtest_base import BacktestBase
from ginkgo.trading.core.file_info import FileInfo
from ginkgo.trading.core.containers import Container

# === 业务实体对象 ===
from ginkgo.trading.entities.bar import Bar
from ginkgo.trading.entities.order import Order
from ginkgo.trading.entities.position import Position
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.entities.stockinfo import StockInfo
from ginkgo.trading.entities.tick import Tick
from ginkgo.trading.entities.tradeday import TradeDay
from ginkgo.trading.entities.transfer import Transfer
from ginkgo.trading.entities.adjustfactor import Adjustfactor
from ginkgo.trading.entities.time_related import TimeRelated

# === 计算模块（向后兼容） ===
# 从computation模块导入所有技术指标
from ginkgo.trading.computation import *

# === 向后兼容的别名 ===
# 为了保持与旧代码的兼容性，提供常用类的直接访问
# 已迁移到新的架构，旧的execution路径已废弃

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
    """创建兼容性警告的辅助函数 - 仅在首次使用时警告"""
    if not hasattr(_create_compatibility_warning, 'warned'):
        _create_compatibility_warning.warned = set()
    
    if old_path not in _create_compatibility_warning.warned:
        warnings.warn(
            f"从 '{old_path}' 导入已弃用。请使用 '{new_path}'。"
            f"此兼容性层将在未来版本中移除。",
            DeprecationWarning,
            stacklevel=4
        )
        _create_compatibility_warning.warned.add(old_path)

# 创建兼容性模块映射
class _CompatibilityModule(ModuleType):
    """兼容性模块，用于处理旧的导入路径"""
    
    def __init__(self, name, new_module):
        super().__init__(name)
        self._new_module = new_module
        self._old_path = name
        self._new_path = new_module.__name__
        self._warned = False  # 添加单次警告标志
    
    def __getattr__(self, name):
        if not self._warned:
            _create_compatibility_warning(self._old_path, self._new_path)
            self._warned = True
        return getattr(self._new_module, name)

# 注册兼容性模块
try:
    # 为旧的 indicators 模块创建兼容性层
    from ginkgo.trading import computation as computation_module
    indicators_compat = _CompatibilityModule('ginkgo.trading.indicators', computation_module)
    sys.modules['ginkgo.trading.indicators'] = indicators_compat
    
    # 为旧的 indices 模块创建兼容性层（指向同样的 computation 模块）
    indices_compat = _CompatibilityModule('ginkgo.trading.indices', computation_module)  
    sys.modules['ginkgo.trading.indices'] = indices_compat
    
except ImportError:
    # 如果导入失败，跳过兼容性层设置
    pass

# 添加常见的别名映射，用于向后兼容
try:
    # 技术指标的别名
    from ginkgo.trading.computation.technical.base_indicator import BaseIndicator
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
- indicators/ → computation/ (兼容性支持，首次使用时警告)
- indices/ → computation/ (兼容性支持，首次使用时警告) 
- 数据容器类 → entities/
- 引擎类 → engines/ (原execution/engines已迁移)
- 策略类 → strategy/strategies/
- 分析器 → analysis/analyzers/

兼容性层经过优化，减少了重复警告。
"""
