# Upstream: ginkgo.data.cruds, ginkgo.service_hub
# Downstream: ginkgo.trading.strategies, ginkgo.validation
# Role: 因子研究模块依赖注入容器 - 提供IC分析、分层、正交化等服务的依赖注入

"""
Research Module Container

因子研究模块的依赖注入容器，提供：
- ICAnalyzer: IC 分析服务
- FactorLayering: 因子分层服务
- FactorOrthogonalizer: 因子正交化服务
- 其他因子分析服务

Usage:
    from ginkgo.research.containers import research_container

    # 获取 IC 分析器
    ic_analyzer = research_container.ic_analyzer()

    # 获取因子分层器
    layering = research_container.factor_layering()
"""

from dependency_injector import containers, providers


class ResearchContainer(containers.DeclarativeContainer):
    """
    因子研究模块容器

    提供因子研究相关服务的依赖注入。
    """

    # 占位符 - 后续实现具体服务时添加
    # ic_analyzer = providers.Factory(ICAnalyzer)
    # factor_layering = providers.Factory(FactorLayering)
    # factor_orthogonalizer = providers.Factory(FactorOrthogonalizer)

    pass


# 全局容器实例
research_container = ResearchContainer()
