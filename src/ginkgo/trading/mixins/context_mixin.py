"""
Engine相关Mixin

提供engine_id, run_id, portfolio_id等引擎相关标识的统一管理
"""

from typing import Optional


class ContextMixin:
    """引擎相关的Mixin，管理engine_id、run_id、portfolio_id等标识"""

    def __init__(self, engine_id: str = None, run_id: str = None, portfolio_id: str = None, *args, **kwargs):
        """
        初始化引擎相关标识

        Args:
            engine_id: 引擎ID
            run_id: 运行会话ID
            portfolio_id: 投资组合ID
        """
        self._engine_id: Optional[str] = engine_id
        self._run_id: Optional[str] = run_id
        self._portfolio_id: Optional[str] = portfolio_id
        self._bound_engine = None  # 确保属性存在
        self._bound_portfolio = None  # 确保属性存在
        super().__init__(*args, **kwargs)

    def _set_bound_engine(self, engine) -> None:
        """内部方法：设置绑定的引擎引用"""
        self._bound_engine = engine

    def _set_bound_portfolio(self, portfolio) -> None:
        """内部方法：设置绑定的投资组合引用"""
        self._bound_portfolio = portfolio

    def bind_engine(self, engine) -> None:
        """绑定引擎实例（公共接口）"""
        self._bound_engine = engine

    def bind_portfolio(self, portfolio) -> None:
        """绑定投资组合实例（公共接口）"""
        self._bound_portfolio = portfolio

        # 如果portfolio已绑定engine，自动绑定engine以实现灵活的上下文传播
        if hasattr(portfolio, '_bound_engine') and portfolio._bound_engine is not None:
            self.bind_engine(portfolio._bound_engine)

    @property
    def engine_id(self) -> Optional[str]:
        """获取引擎ID - 从绑定引擎获取，未绑定时返回None"""
        if self._bound_engine is not None:
            return self._bound_engine.engine_id
        return None

    @engine_id.setter
    def engine_id(self, value: str) -> None:
        """设置引擎ID"""
        self._engine_id = value

    @property
    def run_id(self) -> Optional[str]:
        """获取运行会话ID - 从绑定引擎获取，未绑定时返回None"""
        if self._bound_engine is not None:
            return self._bound_engine.run_id
        return None

    @run_id.setter
    def run_id(self, value: str) -> None:
        """设置运行会话ID"""
        self._run_id = value

    @property
    def portfolio_id(self) -> Optional[str]:
        """获取投资组合ID - 从绑定portfolio获取，未绑定时返回None"""
        if self._bound_portfolio is not None:
            return self._bound_portfolio.uuid
        return None

    @portfolio_id.setter
    def portfolio_id(self, value: str) -> None:
        """设置投资组合ID"""
        self._portfolio_id = value

    def set_engine_context(self, engine_id: str = None, run_id: str = None, portfolio_id: str = None) -> None:
        """
        批量设置引擎上下文

        Args:
            engine_id: 引擎ID
            run_id: 运行会话ID
            portfolio_id: 投资组合ID
        """
        if engine_id is not None:
            self.engine_id = engine_id
        if run_id is not None:
            self.run_id = run_id
        if portfolio_id is not None:
            self.portfolio_id = portfolio_id

    def sync_engine_context(self, engine) -> None:
        """
        从引擎同步上下文ID信息，不涉及事件发布

        Args:
            engine: 引擎实例
        """
        if hasattr(engine, "engine_id") and engine.engine_id:
            self.engine_id = engine.engine_id
        if hasattr(engine, "run_id") and engine.run_id:
            self.run_id = engine.run_id