# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: 计算模块公共接口，导出Alpha158因子、Technical技术指标、BollingerBands布林带、RSI相对强弱等计算器和指标






"""
Computation Module - 计算层

统一的技术指标、模式识别和量化计算模块。
整合了原来的 indicators 和 indices 模块，消除重复代码。
"""

import warnings

# 从技术指标子模块导入所有内容
from ginkgo.trading.computation.technical import *
from ginkgo.trading.computation.technical.base_indicator import BaseIndicator

# 向后兼容性：提供旧的 BaseIndex 别名
BaseIndex = BaseIndicator

# 弃用警告配置
def _warn_deprecated_import(old_module: str):
    """发出弃用警告的辅助函数"""
    warnings.warn(
        f"从 '{old_module}' 导入已弃用。请使用 'from ginkgo.trading.computation import ...' "
        f"此兼容性层将在未来版本中移除。",
        DeprecationWarning,
        stacklevel=3
    )

# 提供向后兼容的导入钩子
class _CompatibilityLayer:
    """兼容性层，用于处理旧的导入路径"""
    
    @staticmethod
    def indicators_import():
        _warn_deprecated_import("ginkgo.trading.indicators")
        return True
    
    @staticmethod  
    def indices_import():
        _warn_deprecated_import("ginkgo.trading.indices")
        return True

# 导出的公共接口
__all__ = [
    # 基类
    'BaseIndicator', 'BaseIndex',  # BaseIndex 是向后兼容别名
    
    # 基础移动平均类
    'SimpleMovingAverage', 'WeightedMovingAverage', 'ExponentialMovingAverage',
    
    # 技术指标
    'AverageTrueRange', 'PinBar', 'InflectionPoint', 'Gap',
    'BollingerBands', 'BollingerBandsSignal',
    'RelativeStrengthIndex', 'RSISignal',
    
    # Alpha158因子
    'KMID', 'KLEN', 'KLOW', 'KHIGH',
    'MA', 'STD', 'BETA', 'ROC',
    'MAX', 'MIN', 'QTLU', 'QTLD',
    'RANK', 'RSV', 'IMAX', 'IMIN', 'IMXD',
    'Alpha158Factory',
]

# 模块级元数据
__version__ = "2.0.0"
__author__ = "Ginkgo Team"
__description__ = "统一的计算和技术指标模块"