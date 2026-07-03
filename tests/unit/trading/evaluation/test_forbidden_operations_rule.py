"""ForbiddenOperationsRule 行为测试。

验证规则对 StrategyDataMixin 合规方法与真正违规操作的判定边界。
Issue #4896: 之前 self.get_bars_cached() 因子串命中 get_bars 黑名单被误报 database。
"""

import ast
from pathlib import Path

from ginkgo.trading.evaluation.rules.logical_rules import ForbiddenOperationsRule


def _check(source: str):
    """对给定策略源码跑 ForbiddenOperationsRule，返回 EvaluationIssue 或 None。"""
    tree = ast.parse(source)
    rule = ForbiddenOperationsRule()
    return rule.check_ast(tree, Path("fake_strategy.py"), source)


STRATEGY_USING_MIXIN = '''
class FooStrategy:
    def cal(self, portfolio_info, event):
        bars = self.get_bars_cached(symbol="000001", count=50, frequency="1d", use_cache=True)
        return []
'''

STRATEGY_USING_DATA_FEEDER = '''
class FooStrategy:
    def cal(self, portfolio_info, event):
        bars = self.data_feeder.get_bars(code="000001")
        return []
'''

STRATEGY_USING_CRUD = '''
class FooStrategy:
    def cal(self, portfolio_info, event):
        rows = self.crud.get_bar(code="000001")
        return []
'''

STRATEGY_USING_REQUESTS = '''
class FooStrategy:
    def cal(self, portfolio_info, event):
        resp = requests.get("http://example.com")
        return []
'''


def test_mixin_get_bars_cached_not_flagged():
    """self.get_bars_cached(...) 是 StrategyDataMixin 合规方法，不应报 database。"""
    issue = _check(STRATEGY_USING_MIXIN)
    assert issue is None, f"期望不报，但得到: {issue}"


def test_data_feeder_direct_access_still_allowed():
    """self.data_feeder.get_bars() 是合规直接访问，不应报（原有豁免保持）。"""
    issue = _check(STRATEGY_USING_DATA_FEEDER)
    assert issue is None, f"期望不报，但得到: {issue}"


def test_crud_access_still_flagged():
    """self.crud.xxx 仍应报 database（回归：白名单未放宽 crud. 拦截）。"""
    issue = _check(STRATEGY_USING_CRUD)
    assert issue is not None, "期望报 database，但未报"
    assert "database" in issue.message


def test_requests_still_flagged():
    """requests.get(...) 仍应报 network（回归：白名单未放宽 network 拦截）。"""
    issue = _check(STRATEGY_USING_REQUESTS)
    assert issue is not None, "期望报 network，但未报"
    assert "network" in issue.message

