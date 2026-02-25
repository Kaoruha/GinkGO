# Upstream: ginkgo.data.cruds, ginkgo.trading.engines, ginkgo.service_hub
# Downstream: ginkgo.client, ginkgo.trading.comparison
# Role: Paper Trading模块依赖注入容器 - 提供Paper Trading引擎和滑点模型的依赖注入

"""
Paper Trading Module Container

Paper Trading模块的依赖注入容器，提供：
- PaperTradingEngine: Paper Trading 引擎
- SlippageModel: 滑点模型

Usage:
    from ginkgo.trading.paper.containers import paper_container

    # 获取 Paper Trading 引擎
    engine = paper_container.paper_trading_engine()

    # 获取固定滑点模型
    slippage = paper_container.fixed_slippage(slippage=0.02)
"""

from dependency_injector import containers, providers


class PaperContainer(containers.DeclarativeContainer):
    """
    Paper Trading模块容器

    提供Paper Trading相关服务的依赖注入。
    """

    # 占位符 - 后续实现具体服务时添加
    # paper_trading_engine = providers.Factory(PaperTradingEngine)
    # fixed_slippage = providers.Factory(FixedSlippage)
    # percentage_slippage = providers.Factory(PercentageSlippage)

    pass


# 全局容器实例
paper_container = PaperContainer()
