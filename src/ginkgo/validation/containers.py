# Upstream: ginkgo.trading.engines, ginkgo.service_hub
# Downstream: ginkgo.trading.strategies
# Role: 策略验证模块依赖注入容器 - 提供走步验证、蒙特卡洛、敏感性分析等服务的依赖注入

"""
Validation Module Container

策略验证模块的依赖注入容器，提供：
- WalkForwardValidator: 走步验证服务
- MonteCarloSimulator: 蒙特卡洛模拟服务
- SensitivityAnalyzer: 敏感性分析服务

Usage:
    from ginkgo.validation.containers import validation_container

    # 获取走步验证器
    walk_forward = validation_container.walk_forward_validator()

    # 获取蒙特卡洛模拟器
    monte_carlo = validation_container.monte_carlo_simulator()
"""

from dependency_injector import containers, providers


class ValidationContainer(containers.DeclarativeContainer):
    """
    策略验证模块容器

    提供策略验证相关服务的依赖注入。
    """

    # 占位符 - 后续实现具体服务时添加
    # walk_forward_validator = providers.Factory(WalkForwardValidator)
    # monte_carlo_simulator = providers.Factory(MonteCarloSimulator)
    # sensitivity_analyzer = providers.Factory(SensitivityAnalyzer)

    pass


# 全局容器实例
validation_container = ValidationContainer()
