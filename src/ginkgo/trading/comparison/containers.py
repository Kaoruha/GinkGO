# Upstream: ginkgo.trading.engines, ginkgo.service_hub
# Downstream: ginkgo.client
# Role: 回测对比模块依赖注入容器 - 提供回测对比服务的依赖注入

"""
Comparison Module Container

回测对比模块的依赖注入容器，提供：
- BacktestComparator: 回测对比器

Usage:
    from ginkgo.trading.comparison.containers import comparison_container

    # 获取回测对比器
    comparator = comparison_container.backtest_comparator()
"""

from dependency_injector import containers, providers


class ComparisonContainer(containers.DeclarativeContainer):
    """
    回测对比模块容器

    提供回测对比相关服务的依赖注入。
    """

    # 占位符 - 后续实现具体服务时添加
    # backtest_comparator = providers.Factory(BacktestComparator)

    pass


# 全局容器实例
comparison_container = ComparisonContainer()
