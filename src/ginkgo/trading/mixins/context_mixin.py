# Upstream: 所有需要引擎绑定的组件(Strategy/Portfolio/Broker/Analyzer等)
# Downstream: BaseEngine(引擎实例绑定)、EngineContext(引擎上下文)、PortfolioContext(投资组合上下文)
# Role: ContextMixin上下文混入类提供portfolio_id/engine_id/run_id等上下文属性和方法，用于组件访问上下文信息






"""
统一上下文管理Mixin

整合引擎绑定和上下文信息管理，提供完整的引擎集成功能：
- 引擎实例绑定和管理
- 上下文ID信息的存储和访问（engine_id, run_id, portfolio_id）
- 事件发布功能
- 动态获取引擎状态

设计原则：
- 统一管理所有与引擎相关的交互
- 确保组件能够动态访问引擎的最新状态
- 避免Mixin之间的复杂协调问题
- 支持 EngineContext/PortfolioContext 分级上下文架构
"""

from typing import Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from ginkgo.trading.engines.base_engine import BaseEngine
    from ginkgo.trading.context.engine_context import EngineContext
    from ginkgo.trading.context.portfolio_context import PortfolioContext


class ContextMixin:
    """统一的上下文管理Mixin，整合引擎绑定和上下文信息"""

    def __init__(self, engine=None, *args, **kwargs):
        """
        初始化上下文管理

        Args:
            engine: 引擎实例（可选）
        """
        # 引擎绑定相关
        self._bound_engine: Optional["BaseEngine"] = None
        self._engine_put = None
        self._bound_portfolio = None

        # 上下文对象（新架构）
        self._context: Optional[Union["EngineContext", "PortfolioContext"]] = None

        # 如果提供了engine，直接绑定
        if engine is not None:
            self.bind_engine(engine)
        super().__init__(*args, **kwargs)

    def bind_engine(self, engine: "BaseEngine") -> None:
        """
        统一的引擎绑定方法，整合引擎绑定和上下文设置

        对于 Portfolio 组件：创建 PortfolioContext（隔离不同 portfolio）
        对于其他组件：优先使用 PortfolioContext（如果已通过 bind_portfolio 设置）

        Args:
            engine: 要绑定的引擎实例
        """
        # 保存引擎引用和事件发布函数
        self._bound_engine = engine
        self._engine_put = engine.put

        # 如果已经有 PortfolioContext（通过 bind_portfolio 设置），不要覆盖
        if self._context is not None:
            return

        # 获取 EngineContext（所有组件共享）
        engine_context = engine.get_engine_context()

        # 判断是否为 Portfolio 组件（通过 uuid 属性判断）
        if hasattr(self, 'uuid') and hasattr(self, '_is_portfolio'):
            # Portfolio 组件创建独立的 PortfolioContext
            from ..context.portfolio_context import PortfolioContext
            self._context = PortfolioContext(
                portfolio_id=self.uuid,  # Portfolio 使用自己的 uuid
                engine_context=engine_context
            )
        else:
            # 其他组件直接使用 EngineContext
            self._context = engine_context

    def _set_bound_portfolio(self, portfolio) -> None:
        """内部方法：设置绑定的投资组合引用"""
        self._bound_portfolio = portfolio

        # 如果 portfolio 有 _context，传播给子组件
        if hasattr(portfolio, '_context') and portfolio._context is not None:
            self._context = portfolio._context

    def bind_portfolio(self, portfolio) -> None:
        """绑定投资组合实例（公共接口）"""
        self._bound_portfolio = portfolio

        # 如果portfolio已绑定引擎，自动绑定当前组件
        if hasattr(portfolio, '_bound_engine') and portfolio._bound_engine is not None:
            self.bind_engine(portfolio._bound_engine)

        # 传播 portfolio 的上下文给子组件
        if hasattr(portfolio, '_context') and portfolio._context is not None:
            self._context = portfolio._context

    @property
    def engine_put(self):
        """获取引擎的事件发布函数"""
        return self._engine_put

    @property
    def bound_engine(self):
        """获取绑定的引擎实例"""
        return self._bound_engine

    @property
    def engine_id(self) -> Optional[str]:
        """获取引擎ID - 从上下文动态获取，支持延迟查找"""
        # 优先从自身 context 获取
        if self._context:
            return self._context.engine_id

        # 延迟查找：尝试从绑定的 portfolio 获取
        if self._bound_portfolio and hasattr(self._bound_portfolio, '_context') and self._bound_portfolio._context:
            return self._bound_portfolio._context.engine_id

        return None

    @property
    def run_id(self) -> Optional[str]:
        """获取运行会话ID - 从上下文动态获取，支持延迟查找"""
        # 优先从自身 context 获取
        if self._context:
            return self._context.run_id

        # 延迟查找：如果自身没有 context，尝试从绑定的 portfolio 获取
        # 这样即使装配时 Portfolio 还没有 context，在调用时也能动态获取
        if self._bound_portfolio and hasattr(self._bound_portfolio, '_context') and self._bound_portfolio._context:
            return self._bound_portfolio._context.run_id

        # 后备：使用 TimeMixin 的 _validation_run_id（当 set_run_id 被调用时设置）
        if hasattr(self, '_validation_run_id') and self._validation_run_id is not None:
            return self._validation_run_id

        return None

    @property
    def portfolio_id(self) -> Optional[str]:
        """获取投资组合ID - 从上下文动态获取，支持延迟查找"""
        # 优先从自身 context 获取
        if self._context and hasattr(self._context, 'portfolio_id'):
            return self._context.portfolio_id

        # 延迟查找：尝试从绑定的 portfolio 获取
        if self._bound_portfolio and hasattr(self._bound_portfolio, 'uuid'):
            return self._bound_portfolio.uuid

        return None

