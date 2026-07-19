"""ASTBasedRule 体系与 ast_helpers 的契约测试。

锁住 #6471 重构的关键行为：
- ``is_abstract_class`` 三重语义（ABC 继承 ∨ @abstractmethod ∨ __abstract__=True），
  作为 6 处私有 ``_is_abstract_class`` 统一的目标语义。
- ``ASTBasedRule.check`` 的解析 / 缓存命中 / 异常兜底契约（验收标准要求）。
- ``find_strategy_classes`` 保持 ``_get_name`` 的 attr 取名语义（不因上提而漂移）。
"""

import ast
from pathlib import Path
from textwrap import dedent
from typing import List, Optional, Tuple

from ginkgo.trading.evaluation.rules.base_rule import ASTBasedRule
from ginkgo.trading.evaluation.utils.ast_helpers import is_abstract_class


class _SpyRule(ASTBasedRule):
    """记录 check_ast 调用的最小子类，用于测 ASTBasedRule.check 契约。

    不耦合任何具体规则业务，只验证基类 check() 的解析/缓存/异常行为。
    """

    rule_id = "TEST_SPY"

    def __init__(self, *, raise_on_check: Optional[Exception] = None) -> None:
        self.calls: List[Tuple[object, Path, str]] = []
        self._raise = raise_on_check

    def check_ast(self, tree, file_path, source_code):  # type: ignore[override]
        self.calls.append((tree, file_path, source_code))
        if self._raise is not None:
            raise self._raise
        return None


def _class_node(source: str, name: str = "Foo") -> ast.ClassDef:
    """从源码片段解析出指定类的 ClassDef 节点。"""
    tree = ast.parse(dedent(source))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise AssertionError(f"class {name} not found in source")


# ---------------------------------------------------------------------------
# is_abstract_class 三重语义契约（#6471 统一目标语义）
# ---------------------------------------------------------------------------


def test_is_abstract_class_abc_inheritance() -> None:
    """直接继承 ABC 的类判为抽象（三重之一）。"""
    node = _class_node("class Foo(ABC):\n    pass")
    assert is_abstract_class(node) is True


def test_is_abstract_class_abstractmethod_decorator() -> None:
    """含 @abstractmethod 装饰方法的类判为抽象（三重之二）。"""
    source = """
    class Foo:
        @abstractmethod
        def cal(self):
            pass
    """
    assert is_abstract_class(_class_node(source)) is True


def test_is_abstract_class_ginkgo_marker_true() -> None:
    """标 __abstract__ = True 的类判为抽象（三重之三，Ginkgo 惯例）。"""
    source = """
    class Foo:
        __abstract__ = True
    """
    assert is_abstract_class(_class_node(source)) is True


def test_is_abstract_class_concrete_strategy() -> None:
    """具体策略类（__abstract__ = False）判为非抽象——检查的目标对象。"""
    source = """
    class Foo:
        __abstract__ = False
    """
    assert is_abstract_class(_class_node(source)) is False


def test_is_abstract_class_plain_class() -> None:
    """无任何抽象标记的普通类判为非抽象。"""
    assert is_abstract_class(_class_node("class Foo:\n    pass")) is False


# ---------------------------------------------------------------------------
# ASTBasedRule.check 契约（解析 / 缓存命中 / 异常兜底）—— 验收标准要求
# ---------------------------------------------------------------------------


def test_check_parses_file_calls_check_ast(tmp_path) -> None:
    """正常文件：check 读文件 parse 后调 check_ast，传入 tree 与完整源码。"""
    src = "class Foo:\n    pass\n"
    f = tmp_path / "s.py"
    f.write_text(src, encoding="utf-8")
    rule = _SpyRule()
    issue = rule.check(f)
    assert issue is None
    assert len(rule.calls) == 1
    tree, file_path, source_code = rule.calls[0]
    assert isinstance(tree, ast.Module)
    assert file_path == f
    assert source_code == src


def test_check_uses_cached_ast_context(tmp_path) -> None:
    """component_class 含 ast_context：用缓存 tree，不读磁盘。"""
    cached_tree = ast.parse("class Foo:\n    pass\n")
    cached_src = "class Foo:\n    pass\n"
    # 用不存在的路径，证明没走磁盘读取
    fake_path = tmp_path / "does_not_exist.py"
    rule = _SpyRule()
    rule.check(
        fake_path,
        component_class={"ast_context": cached_tree, "source_code": cached_src},
    )
    assert len(rule.calls) == 1
    tree, _file_path, source_code = rule.calls[0]
    assert tree is cached_tree
    assert source_code == cached_src


def test_check_syntax_error_returns_issue(tmp_path) -> None:
    """语法错误文件：check 捕获 SyntaxError 返回 issue，不调 check_ast。"""
    f = tmp_path / "bad.py"
    f.write_text("def (\n", encoding="utf-8")
    rule = _SpyRule()
    issue = rule.check(f)
    assert issue is not None
    assert rule.calls == []
    assert "syntax" in issue.message.lower()


def test_check_exception_in_check_ast_returns_issue(tmp_path) -> None:
    """check_ast 抛异常：check 兜底捕获并返回 issue。"""
    src = "class Foo:\n    pass\n"
    f = tmp_path / "s.py"
    f.write_text(src, encoding="utf-8")
    rule = _SpyRule(raise_on_check=RuntimeError("boom"))
    issue = rule.check(f)
    assert issue is not None
    assert len(rule.calls) == 1  # check_ast 被调到（调用后抛异常）
