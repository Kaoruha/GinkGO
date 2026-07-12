# Upstream: 核心模块(core.__init__)、适配器模块、工厂模块、各业务模块
# Downstream: BaseStrategy, BaseModel, BasePortfolio
# Role: 接口定义包入口，导出策略/模型/组合三类核心接口协议，定义组件标准契约
# Note: 死抽象引擎接口层已删（ADR-022 原则 2，0 生产消费者）；真实引擎基类见 trading/engines/base_engine.py






"""
统一接口定义模块

定义系统中所有组件的统一接口，确保不同模块间的兼容性。
"""

from ginkgo.core.interfaces.strategy_interface import BaseStrategy
from ginkgo.core.interfaces.model_interface import BaseModel
from ginkgo.core.interfaces.portfolio_interface import BasePortfolio

__all__ = [
    'BaseStrategy',
    'BaseModel',
    'BasePortfolio'
]
