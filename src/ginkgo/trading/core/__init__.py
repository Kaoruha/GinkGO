# Upstream: 全系统（所有trading子模块和外部调用者）
# Downstream: entities.base, entities.identity, entities.file_info, trading.core.backtest_base, trading.core.containers
# Role: 交易核心基础设施模块包入口，导出Base基础类、BacktestBase回测基类、FileInfo文件信息、Container依赖注入容器






"""
Core Module - 核心基础设施

提供 Ginkgo Backtest 框架的核心基础设施，包括：
- 基础类和抽象基类
- 依赖注入容器
- 文件信息管理
- 公共工具和配置
"""

from ginkgo.entities.base import Base
from ginkgo.entities.identity import IdentityUtils
from ginkgo.entities.file_info import FileInfo
from ginkgo.trading.core.backtest_base import BacktestBase
from ginkgo.trading.core.containers import Container

__all__ = [
    "Base",
    "BacktestBase", 
    "FileInfo",
    "Container",
]

__version__ = "3.0.0"
__description__ = "Ginkgo Backtest 核心基础设施模块"
