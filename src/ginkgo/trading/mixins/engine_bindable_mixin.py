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
        # 保存引擎引用和事件发布函数
        self._bound_engine = engine
        self._engine_put = engine.put

        # 设置TimeProvider - 这是关键的修复！
        if hasattr(engine, '_time_provider'):
            self.set_time_provider(engine._time_provider)

    def set_event_publisher(self, publisher) -> None:
        """
        设置事件发布器（通常是引擎的put函数）

        Args:
            publisher: 事件发布函数
        """
        self._engine_put = publisher

    def publish_event(self, event) -> None:
        """
        发布事件到绑定的引擎

        Args:
            event: 要发布的事件
        """
        if self._engine_put is None:
            # 使用log方法（如果继承者有的话）
            if hasattr(self, 'log'):
                self.log("ERROR", "Engine put not bind. Events can not put back to the engine.")
            else:
                print(f"ERROR: Engine put not bind in {self.__class__.__name__}. Events can not put back to the engine.")
            return
        self._engine_put(event)

    @property
    def engine_put(self):
        """获取引擎的事件发布函数"""
        return self._engine_put

    @property
    def bound_engine(self):
        """获取绑定的引擎实例"""
        return self._bound_engine