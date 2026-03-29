# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: 引擎装配子模块包，将 EngineAssemblyService 拆分为多个职责单一的子模块


"""
引擎装配子模块包

将原 engine_assembly_service.py (2182行) 拆分为以下子模块：
- ComponentLoader: 组件实例化和绑定
- InfrastructureFactory: 引擎基础设施创建（无状态工具类）
- TaskEngineBuilder: 从 BacktestTask 构建引擎
- DataPreparer: 数据准备和 YAML 配置驱动装配
"""

from ginkgo.trading.services._assembly.component_loader import ComponentLoader
from ginkgo.trading.services._assembly.infrastructure_factory import InfrastructureFactory
from ginkgo.trading.services._assembly.task_engine_builder import TaskEngineBuilder
from ginkgo.trading.services._assembly.data_preparer import DataPreparer

__all__ = [
    "ComponentLoader",
    "InfrastructureFactory",
    "TaskEngineBuilder",
    "DataPreparer",
]
