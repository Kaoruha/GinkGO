"""规则层抽象类跳过契约（#6471）。

锁定 ``_is_abstract_class`` 6 处统一为 ``ast_helpers.is_abstract_class`` 后，
两条规则链路的 skip 行为经公开 ``check_ast`` 接口仍然正确：

- 具体策略（``__abstract__ = False``）→ 参与检查（可命中 issue）
- 抽象类（继承 ABC）→ 被跳过（不报 issue）

两个规则文件此前无直接测试，本文件作为重构的安全网。
"""

from pathlib import Path

from ginkgo.trading.evaluation.rules.best_practice_rules import DecoratorUsageRule
from ginkgo.trading.evaluation.rules.structural_rules import AbstractMarkerRule


def _check(rule, source: str):
    """对给定源码跑规则，返回 EvaluationIssue 或 None。"""
    import ast

    tree = ast.parse(source)
    return rule.check_ast(tree, Path("fake_strategy.py"), source)


CONCRETE_NO_MARKER = '''
class FooStrategy(BaseStrategy):
    def cal(self, portfolio_info, event):
        return []
'''


CONCRETE_WITH_MARKER_NO_DECORATOR = '''
class FooStrategy(BaseStrategy):
    __abstract__ = False

    def cal(self, portfolio_info, event):
        return []
'''


ABSTRACT_ABC_STRATEGY = '''
class FooStrategy(BaseStrategy, ABC):
    def cal(self, portfolio_info, event):
        return []
'''


# ---------------------------------------------------------------------------
# structural_rules.AbstractMarkerRule
# ---------------------------------------------------------------------------


def test_abstract_marker_rule_concrete_without_marker_flagged() -> None:
    """具体策略未标 __abstract__ = False → 报 ABSTRACT_MARKER issue。"""
    issue = _check(AbstractMarkerRule(), CONCRETE_NO_MARKER)
    assert issue is not None
    assert "__abstract__" in issue.message


def test_abstract_marker_rule_abc_class_skipped() -> None:
    """继承 ABC 的抽象类 → 被跳过，不报 issue（三重语义之一）。"""
    issue = _check(AbstractMarkerRule(), ABSTRACT_ABC_STRATEGY)
    assert issue is None


def test_abstract_marker_rule_concrete_with_marker_not_flagged() -> None:
    """具体策略已标 __abstract__ = False → 不报 issue。"""
    issue = _check(AbstractMarkerRule(), CONCRETE_WITH_MARKER_NO_DECORATOR)
    assert issue is None


# ---------------------------------------------------------------------------
# best_practice_rules.DecoratorUsageRule
# ---------------------------------------------------------------------------


def test_decorator_rule_concrete_cal_without_decorator_flagged() -> None:
    """具体策略 cal() 无 @time_logger/@retry → 报 DECORATOR_USAGE issue。"""
    issue = _check(DecoratorUsageRule(), CONCRETE_WITH_MARKER_NO_DECORATOR)
    assert issue is not None
    assert "decorator" in issue.message.lower()


def test_decorator_rule_abc_class_skipped() -> None:
    """继承 ABC 的抽象类 → 被跳过（三重语义统一后，best_practice 也跳过 ABC）。"""
    issue = _check(DecoratorUsageRule(), ABSTRACT_ABC_STRATEGY)
    assert issue is None
