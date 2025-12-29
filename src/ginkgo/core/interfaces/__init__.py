# Upstream: All Modules
# Downstream: Standard Library
# Role: 核心接口模块导出引擎/组合/策略/模型等核心接口协议定义组件的标准契约支持交易系统功能和组件集成提供完整业务支持






"""
统一接口定义模块

定义系统中所有组件的统一接口，确保不同模块间的兼容性。
"""

from ginkgo.core.interfaces.strategy_interface import IStrategy
from ginkgo.core.interfaces.model_interface import IModel  
from ginkgo.core.interfaces.engine_interface import IEngine
from ginkgo.core.interfaces.portfolio_interface import IPortfolio

__all__ = [
    'IStrategy',
    'IModel', 
    'IEngine',
    'IPortfolio'
]