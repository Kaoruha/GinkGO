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
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ginkgo.trading.engines.base_engine import BaseEngine


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

        # 如果提供了engine，直接绑定
        if engine is not None:
            self.bind_engine(engine)
        super().__init__(*args, **kwargs)

    def bind_engine(self, engine: "BaseEngine") -> None:
        """
        统一的引擎绑定方法，整合引擎绑定和上下文设置

        Args:
            engine: 要绑定的引擎实例
        """
        # 保存引擎引用和事件发布函数
        self._bound_engine = engine
        self._engine_put = engine.put

    def _set_bound_portfolio(self, portfolio) -> None:
        """内部方法：设置绑定的投资组合引用"""
        self._bound_portfolio = portfolio

    def bind_portfolio(self, portfolio) -> None:
        """绑定投资组合实例（公共接口）"""
        self._bound_portfolio = portfolio

        # 如果portfolio已绑定引擎，自动绑定当前组件
        if hasattr(portfolio, '_bound_engine') and portfolio._bound_engine is not None:
            self.bind_engine(portfolio._bound_engine)

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
        """获取引擎ID - 从绑定的引擎动态获取"""
        return self._bound_engine.engine_id if self._bound_engine else None

    @property
    def run_id(self) -> Optional[str]:
        """获取运行会话ID - 从绑定的引擎动态获取"""
        return self._bound_engine.run_id if self._bound_engine else None

    @property
    def portfolio_id(self) -> Optional[str]:
        """获取投资组合ID - 从绑定的portfolio动态获取"""
        return self._bound_portfolio.uuid if self._bound_portfolio else None

    