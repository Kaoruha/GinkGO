"""
引擎绑定Mixin

提供完整引擎绑定功能，包括ID同步和事件发布
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ginkgo.trading.engines.base_engine import BaseEngine


class EngineBindableMixin:
    """引擎绑定Mixin，提供完整引擎绑定功能"""

    def __init__(self, engine=None, **kwargs):
        self._engine_put = None
        self._bound_engine = None
        # 如果提供了engine，直接绑定
        if engine is not None:
            self.bind_engine(engine)
        super().__init__(**kwargs)

    def bind_engine(self, engine: "BaseEngine") -> None:
        """
        绑定到引擎，包括ID同步和事件发布功能

        Args:
            engine (BaseEngine): 要绑定的引擎实例

        Raises:
            ValueError: 如果引擎无效或缺少必要属性
        """
        # 验证引擎必要属性
        if not hasattr(engine, "put"):
            raise ValueError("Invalid engine: missing required attribute 'put'.")

        # 1. 保存引擎引用和事件发布函数
        self._bound_engine = engine
        self._engine_put = engine.put

    @property
    def engine_put(self):
        """获取引擎的事件发布函数"""
        return self._engine_put

    @property
    def bound_engine(self):
        """获取绑定的引擎实例"""
        return self._bound_engine