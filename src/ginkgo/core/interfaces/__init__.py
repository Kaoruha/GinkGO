# Upstream: 核心模块(core.__init__)、适配器模块、工厂模块、各业务模块
# Downstream: BaseStrategy, BaseModel, BaseEngine, BasePortfolio
# Role: 接口定义包入口，导出策略/模型/引擎/组合四类核心接口协议，定义组件标准契约






"""
统一接口定义模块

定义系统中所有组件的统一接口，确保不同模块间的兼容性。
"""

from ginkgo.core.interfaces.strategy_interface import BaseStrategy
from ginkgo.core.interfaces.model_interface import BaseModel
from ginkgo.core.interfaces.engine_interface import BaseEngine
from ginkgo.core.interfaces.portfolio_interface import BasePortfolio

__all__ = [
    'BaseStrategy',
    'BaseModel',
    'BaseEngine',
    'BasePortfolio'
]
