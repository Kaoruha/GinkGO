# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: 交易核心模块导出引擎基类/回测基类/装配器/身份标识/状态管理等核心组件支持交易系统功能和组件集成提供完整业务支持






"""
Core Module - 核心基础设施

提供 Ginkgo Backtest 框架的核心基础设施，包括：
- 基础类和抽象基类
- 依赖注入容器
- 文件信息管理
- 公共工具和配置
"""

from ginkgo.trading.core.base import Base
from ginkgo.trading.core.backtest_base import BacktestBase
from ginkgo.trading.core.file_info import FileInfo
from ginkgo.trading.core.containers import Container

__all__ = [
    "Base",
    "BacktestBase", 
    "FileInfo",
    "Container",
]

__version__ = "3.0.0"
__description__ = "Ginkgo Backtest 核心基础设施模块"