"""
SubscribableMixin + @subscribes 单元测试

验证 ADR-017（事件订阅契约归组件）的 6 项契约：
  ① append 默认继承父类 _subscriptions
  ② 子类声明覆盖父类同 event → 换映射免费（无需 unsubscribe）
  ③ 一方法多 event（@subscribes(E1, E2) → 多键同值）
  ④ 装饰器叠加累积（@subscribes(E1) @subscribes(E2)）
  ⑤ __subscriptions_reset__=True 清空父类仅留本类
  ⑥ reset 用 vars 读取不沿 MRO（孙类默认 append，不继承祖先 reset）— 关键 bug 防护
  ⑦ register_handlers 遍历 registry 调 engine.register(E, bound_method)
  ⑧ register_handlers 经 getattr 解析返回子类 override 版本（MRO bound method）

测试隔离：每个 test 内重新定义类族，__init_subclass__ 每次重新触发，无跨测试状态污染。
事件键用模块级 object() sentinel —— mixin 契约是 Dict[Any, str]，键类型泛型，零真实 Event 耦合。
"""

import pytest
from unittest.mock import Mock

from ginkgo.trading.mixins.subscribable_mixin import SubscribableMixin, subscribes

# 事件 sentinel —— 不关心键类型，只关心映射
E1, E2, E3 = object(), object(), object()


# ============================================================================
# @subscribes 装饰器
# ============================================================================


class TestSubscribesDecorator:
    """装饰器本身：标记函数 + 累积 + 原样返回"""

    def test_decorator_marks_function(self):
        @subscribes(E1)
        def handler(self):
            pass

        assert handler.__subscribes__ == (E1,)

    def test_decorator_stacks_across_multiple_decorators(self):
        @subscribes(E1)
        @subscribes(E2)
        def handler(self):
            pass

        # 顺序无关，集合相等即可
        assert set(handler.__subscribes__) == {E1, E2}

    def test_decorator_multi_events_in_one_call(self):
        @subscribes(E1, E2, E3)
        def handler(self):
            pass

        assert set(handler.__subscribes__) == {E1, E2, E3}

    def test_decorator_preserves_function_identity(self):
        def handler(self):
            pass

        wrapped = subscribes(E1)(handler)
        assert wrapped is handler  # 原函数对象，非 wrapper


# ============================================================================
# __init_subclass__ 合并规则
# ============================================================================


class TestSubscriptionMerge:
    """类创建期把声明合并进 _subscriptions"""

    def test_append_inherits_parent_subscriptions(self):
        """① 默认 append：子类不声明 → 继承父类全部"""

        class Parent(SubscribableMixin):
            @subscribes(E1)
            def on_e1(self):
                return "parent"

        class Child(Parent):
            pass

        assert Parent._subscriptions == {E1: "on_e1"}
        assert Child._subscriptions == {E1: "on_e1"}

    def test_child_override_remaps_for_free(self):
        """② 子类声明覆盖父类同 event → 换映射免费（不需 unsubscribe）"""

        class Parent(SubscribableMixin):
            @subscribes(E1)
            def on_e1(self):
                return "parent"

        class Child(Parent):
            @subscribes(E1)  # 同 event，不同方法名
            def on_e1_v2(self):
                return "child"

        assert Parent._subscriptions[E1] == "on_e1"
        assert Child._subscriptions[E1] == "on_e1_v2"  # 映射换到子类实现

    def test_one_method_many_events(self):
        """③ @subscribes(E1, E2) 标同一方法 → 多键同值"""

        class Component(SubscribableMixin):
            @subscribes(E1, E2)
            def on_multi(self):
                return "shared"

        assert Component._subscriptions == {E1: "on_multi", E2: "on_multi"}

    def test_grandchild_accumulates_across_chain(self):
        """链式 append：三级各自声明 → 孙类含全部三个 event"""

        class L1(SubscribableMixin):
            @subscribes(E1)
            def on_e1(self):
                pass

        class L2(L1):
            @subscribes(E2)
            def on_e2(self):
                pass

        class L3(L2):
            @subscribes(E3)
            def on_e3(self):
                pass

        assert set(L3._subscriptions.keys()) == {E1, E2, E3}


# ============================================================================
# __subscriptions_reset__ 全量清空 + MRO 隔离（关键 bug 防护）
# ============================================================================


class TestResetSemantics:
    """reset：全量清空父类 + vars 读取不沿 MRO"""

    def test_reset_clears_parent_subscriptions(self):
        """⑤ __subscriptions_reset__=True → 丢弃父类全部，仅留本类声明"""

        class Parent(SubscribableMixin):
            @subscribes(E1)
            def on_e1(self):
                pass

            @subscribes(E2)
            def on_e2(self):
                pass

        class Child(Parent):
            __subscriptions_reset__ = True

            @subscribes(E3)
            def on_e3(self):
                pass

        assert Parent._subscriptions == {E1: "on_e1", E2: "on_e2"}
        # Child 清空父类 E1/E2，仅留本类 E3
        assert Child._subscriptions == {E3: "on_e3"}

    def test_reset_mro_isolation_grandchild_does_not_inherit_reset(self):
        """⑥ 关键：reset 用 vars 读取，孙类不继承祖先 reset

        链：Parent(声明 E1) → Child(reset=True, 声明 E2) → GrandChild(无声明)

        正确（vars 实现）：
          Child reset → {E2}
          GrandChild own 无 reset → append，继承 Child 的 {E2}

        Bug（getattr 实现）：
          GrandChild getattr 沿 MRO 找到 Child 的 reset=True
          → merged 从 {} 开始 → GrandChild._subscriptions == {}（丢失 E2）
        """

        class Parent(SubscribableMixin):
            @subscribes(E1)
            def on_e1(self):
                pass

        class Child(Parent):
            __subscriptions_reset__ = True

            @subscribes(E2)
            def on_e2(self):
                pass

        class GrandChild(Child):
            pass  # 无 reset 声明，应 append 继承 Child

        assert Child._subscriptions == {E2: "on_e2"}
        # GrandChild 必须继承 Child 的 E2，而非被祖先 reset 清空
        assert GrandChild._subscriptions == {E2: "on_e2"}

    def test_reset_only_affects_own_class_not_siblings(self):
        """reset 只影响该类自身命名空间，不影响兄弟类"""

        class Parent(SubscribableMixin):
            @subscribes(E1)
            def on_e1(self):
                pass

        class ResettingChild(Parent):
            __subscriptions_reset__ = True

            @subscribes(E2)
            def on_e2(self):
                pass

        class AppendingChild(Parent):
            @subscribes(E3)
            def on_e3(self):
                pass

        assert ResettingChild._subscriptions == {E2: "on_e2"}
        # 兄弟类不受 reset 影响，正常 append 父类 E1
        assert AppendingChild._subscriptions == {E1: "on_e1", E3: "on_e3"}


# ============================================================================
# register_handlers —— bind_engine 入方向落点
# ============================================================================


class TestRegisterHandlers:
    """register_handlers 遍历 _subscriptions 调 engine.register"""

    def test_register_calls_engine_for_each_subscription(self):
        """⑦ 每个 (event, 方法名) → engine.register(event, bound_method)"""

        class Component(SubscribableMixin):
            @subscribes(E1)
            def on_e1(self):
                return "e1"

            @subscribes(E2)
            def on_e2(self):
                return "e2"

        engine = Mock()
        component = Component()
        component.register_handlers(engine)

        # 断言注册了两个 event
        registered_events = {call.args[0] for call in engine.register.call_args_list}
        assert registered_events == {E1, E2}

        # 第二参数是 bound method（getattr(self, mname)），可调用且绑定到实例
        for call in engine.register.call_args_list:
            bound_method = call.args[1]
            assert callable(bound_method)

    def test_register_resolves_subclass_override_via_getattr(self):
        """⑧ register 传 getattr(self, mname) → 子类 override 版本（MRO bound method）

        Parent 声明 @subscribes(E1) on handle；Child override handle 不重标。
        register_handlers 传的应是 Child 的 bound method，调用返回 'child'。
        """

        class Parent(SubscribableMixin):
            @subscribes(E1)
            def handle(self):
                return "parent"

        class Child(Parent):
            def handle(self):  # override，不标装饰器
                return "child"

        engine = Mock()
        child = Child()
        child.register_handlers(engine)

        assert engine.register.call_count == 1
        event_arg, method_arg = engine.register.call_args.args
        assert event_arg is E1
        # 传的是 child 的 bound method，调用得 'child' 而非 'parent'
        assert method_arg() == "child"

    def test_register_handles_empty_subscriptions(self):
        """无声明组件 register_handlers 不报错、不调 register"""

        class Bare(SubscribableMixin):
            pass

        engine = Mock()
        Bare().register_handlers(engine)
        engine.register.assert_not_called()
