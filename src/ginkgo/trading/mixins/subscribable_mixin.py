# Upstream: 任何需向引擎订阅事件的组件（Portfolio / Feeder / Gateway / Analyzer）
# Downstream: BaseEngine.register（事件入方向落点）
# Role: 声明式事件订阅契约，类创建期合并 @subscribes 声明进 _subscriptions，
#       register_handlers 遍历该映射完成入方向绑定。详见 ADR-017。

"""
事件订阅契约归组件（ADR-017）

引擎绑定分两个方向：
  - 出方向：组件 → 引擎（publish_event，由 EngineBindableMixin.bind_engine 设 _engine_put）
  - 入方向：引擎 → 组件（事件回调，本 Mixin 负责）

本 Mixin 补入方向落点：组件在类创建期用 @subscribes 声明订阅，__init_subclass__
合并进类属性 _subscriptions: Dict[Event, str]，register_handlers 遍历该映射注册。

合并规则（见 ADR-017 Decision）：
  - 默认 append：继承最近父类的 _subscriptions
  - 子类声明覆盖父类同 event 的方法名 → 换映射免费（无需 unsubscribe）
  - __subscriptions_reset__ = True → 丢弃父类全部，仅本类声明为唯一真相
    （reset 标志用 vars(cls) 读取，不沿 MRO 继承，否则后代意外继承祖先的 reset）
  - 一方法多 event：@subscribes(E1, E2) → 多键同方法名
"""

from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from ginkgo.trading.engines.base_engine import BaseEngine


def subscribes(*events: Any):
    """声明被装饰方法订阅哪些事件。

    可叠加（多个 @subscribes 装饰器）也可单次多事件（@subscribes(E1, E2)）。
    在函数对象上累积 ``__subscribes__`` 元组，由 SubscribableMixin.__init_subclass__
    在类创建期读取合并。返回原函数，非 wrapper。

    Args:
        *events: 订阅的事件键（通常是 Event 枚举值）。
    """

    def decorator(func):
        func.__subscribes__ = (*getattr(func, "__subscribes__", ()), *events)
        return func

    return decorator


class SubscribableMixin:
    """事件订阅契约归组件（ADR-017）。

    子类在类创建期经 @subscribes 声明订阅，合并规则把声明并入 ``_subscriptions``。
    bind_engine 时调用 register_handlers 完成入方向绑定。

    类属性:
        _subscriptions: Dict[Event, str] —— 事件键 → 处理方法名（由 __init_subclass__ 维护）。
        __subscriptions_reset__: bool —— 子类设 True 表示丢弃父类全部订阅，仅留本类。
            用 vars(cls) 读取，不沿 MRO 继承。
    """

    _subscriptions: Dict[Any, str] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        own = vars(cls)
        # reset 用 vars(cls) 读取：仅当前类命名空间，不沿 MRO 继承。
        # 若用 getattr，孙类会沿 MRO 命中祖先的 reset=True，意外清空继承链。
        if own.get("__subscriptions_reset__", False):
            merged: Dict[Any, str] = {}
        else:
            # append：继承最近父类的 _subscriptions（getattr 沿 MRO 取最近定义）
            merged = dict(getattr(cls, "_subscriptions", {}))
        for name, member in own.items():
            for ev in getattr(member, "__subscribes__", ()):
                merged[ev] = name
        cls._subscriptions = merged

    def register_handlers(self, engine: "BaseEngine") -> None:
        """遍历 _subscriptions，按方法名解析 bound method 注册到引擎。

        getattr(self, method_name) 经 MRO 解析，子类 override 同名方法自然返回子类版本。
        与 EngineBindableMixin.bind_engine（出方向）对称，构成本 Mixin 的入方向落点。

        Args:
            engine: 目标引擎，需提供 register(event, handler) 接口。
        """
        for event, method_name in self._subscriptions.items():
            engine.register(event, getattr(self, method_name))
