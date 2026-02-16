# Upstream: ginkgo.trading.strategies, ginkgo.service_hub
# Downstream: ginkgo.client
# Role: 参数优化模块依赖注入容器 - 提供网格搜索、遗传算法、贝叶斯优化等服务的依赖注入

"""
Optimization Module Container

参数优化模块的依赖注入容器，提供：
- GridSearchOptimizer: 网格搜索优化器
- GeneticOptimizer: 遗传算法优化器
- BayesianOptimizer: 贝叶斯优化器

Usage:
    from ginkgo.trading.optimization.containers import optimization_container

    # 获取网格搜索优化器
    grid_optimizer = optimization_container.grid_search_optimizer()
"""

from dependency_injector import containers, providers


class OptimizationContainer(containers.DeclarativeContainer):
    """
    参数优化模块容器

    提供参数优化相关服务的依赖注入。
    """

    # 占位符 - 后续实现具体服务时添加
    # grid_search_optimizer = providers.Factory(GridSearchOptimizer)
    # genetic_optimizer = providers.Factory(GeneticOptimizer)
    # bayesian_optimizer = providers.Factory(BayesianOptimizer)

    pass


# 全局容器实例
optimization_container = OptimizationContainer()
