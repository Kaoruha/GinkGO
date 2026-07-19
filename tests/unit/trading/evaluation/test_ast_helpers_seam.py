"""ast_helpers 新增 seam 函数契约（#6471）。

锁定上提的两个查找 helper 的语义，作为 9+7 处私有副本统一的依据：

- ``get_node_name``：保留 ``_get_name`` 的 **attr 取名语义**——
  ``Name`` → ``id``、``Attribute`` → ``attr``（不是 ``ast.unparse``）。
  这是 ``find_strategy_classes`` 能命中 ``module.BaseStrategy`` 形式的关键，
  也是它与已有 ``inherits_from``（走 ``get_base_classes`` 返回 ``"module.BaseStrategy"``）
  的本质区别——故不能直接复用 ``inherits_from``。
- ``find_strategy_classes``：遍历树收集指定基类的 ClassDef，返回 ``(node, name)`` 元组列表，
  保持原 ``_find_strategy_classes`` 的返回形状（调用方按 ``for class_node, class_name in ...`` 解包）。
"""

import ast

from ginkgo.trading.evaluation.utils.ast_helpers import (
    find_strategy_classes,
    get_node_name,
)


# ---------------------------------------------------------------------------
# get_node_name —— attr 取名语义（_get_name 上提）
# ---------------------------------------------------------------------------


def test_get_node_name_name_node_returns_id() -> None:
    """Name 节点取 id（class Foo(BaseStrategy) 的 BaseStrategy）。"""
    tree = ast.parse("class Foo(BaseStrategy):\n    pass\n")
    base = tree.body[0].bases[0]  # type: ignore[attr-defined]
    assert isinstance(base, ast.Name)
    assert get_node_name(base) == "BaseStrategy"


def test_get_node_name_attribute_node_returns_attr() -> None:
    """Attribute 节点取 attr（class Foo(mod.BaseStrategy) → 'BaseStrategy'）。

    关键：不是 ast.unparse 的 'mod.BaseStrategy'。这是上提不能复用 inherits_from 的根因。
    """
    tree = ast.parse("class Foo(mod.BaseStrategy):\n    pass\n")
    base = tree.body[0].bases[0]  # type: ignore[attr-defined]
    assert isinstance(base, ast.Attribute)
    assert get_node_name(base) == "BaseStrategy"


def test_get_node_name_other_node_returns_none() -> None:
    """非 Name/Attribute 节点返回 None。"""
    tree = ast.parse("x = 1\n")
    assert get_node_name(tree.body[0]) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# find_strategy_classes —— _find_strategy_classes 上提
# ---------------------------------------------------------------------------


def test_find_strategy_classes_name_base() -> None:
    """class Foo(BaseStrategy) 被收集，返回 (node, 'Foo')。"""
    tree = ast.parse("class Foo(BaseStrategy):\n    pass\n")
    result = find_strategy_classes(tree)
    assert len(result) == 1
    node, name = result[0]
    assert isinstance(node, ast.ClassDef)
    assert name == "Foo"


def test_find_strategy_classes_attribute_base() -> None:
    """class Foo(mod.BaseStrategy) 也被收集（attr 语义，非 unparse）。

    这是保留 _get_name 语义、不复用 inherits_from 的回归守护。
    """
    tree = ast.parse("class Foo(mod.BaseStrategy):\n    pass\n")
    result = find_strategy_classes(tree)
    assert len(result) == 1
    assert result[0][1] == "Foo"


def test_find_strategy_classes_ignores_unrelated() -> None:
    """非策略类不被收集。"""
    tree = ast.parse("class Foo(OtherBase):\n    pass\n")
    assert find_strategy_classes(tree) == []


def test_find_strategy_classes_custom_base_name() -> None:
    """支持自定义基类名（如 BaseSelector）。"""
    tree = ast.parse("class Foo(BaseSelector):\n    pass\n")
    result = find_strategy_classes(tree, base_name="BaseSelector")
    assert len(result) == 1
    assert result[0][1] == "Foo"


def test_find_strategy_classes_multiple() -> None:
    """多个策略类全部收集，顺序按树遍历。"""
    tree = ast.parse(
        "class A(BaseStrategy):\n    pass\n"
        "class B(BaseStrategy):\n    pass\n"
    )
    result = find_strategy_classes(tree)
    assert [name for _, name in result] == ["A", "B"]
