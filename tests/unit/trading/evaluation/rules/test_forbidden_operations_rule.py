"""Tests for ForbiddenOperationsRule — AST-based detection of forbidden ops in cal().

Covers issue #4722: get_bars_cached 误报 database 操作（子串匹配命中），
data_feeder.* 走白名单放行。验证合法调用不报、违规调用命中。
"""
import ast
from pathlib import Path

import pytest

from ginkgo.trading.evaluation.rules.logical_rules import ForbiddenOperationsRule


def _check_cal(source: str):
    """Parse source, run ForbiddenOperationsRule.check_ast, return issue or None."""
    tree = ast.parse(source)
    rule = ForbiddenOperationsRule()
    return rule.check_ast(tree, Path("dummy_strategy.py"), source)


class TestForbiddenOperationsAllowedCalls:
    """合法调用模式不应触发 forbidden 告警（issue #4722 误报修复）。"""

    @pytest.mark.tdd
    def test_get_bars_cached_not_flagged_as_database(self):
        """self.get_bars_cached() 是 StrategyDataMixin 合法缓存取数方法。

        历史问题：forbidden_patterns 含 ('get_bars','database')，子串匹配
        命中 'self.get_bars_cached'，误报为 database 操作。
        """
        source = (
            "class MyStrategy:\n"
            "    def cal(self, bar):\n"
            "        bars = self.get_bars_cached('000001', 100)\n"
            "        return []\n"
        )
        issue = _check_cal(source)
        assert issue is None, (
            f"get_bars_cached 不应被误报为 forbidden database 操作，got: {issue}"
        )

    @pytest.mark.tdd
    def test_data_feeder_get_bars_allowed(self):
        """self.data_feeder.get_bars() 受 BacktestFeeder 时间边界保护，合法。"""
        source = (
            "class MyStrategy:\n"
            "    def cal(self, bar):\n"
            "        bars = self.data_feeder.get_bars('000001', 100)\n"
            "        return []\n"
        )
        assert _check_cal(source) is None

    @pytest.mark.tdd
    def test_data_feeder_get_historical_data_allowed(self):
        """self.data_feeder.get_historical_data() 走 datafeeder 白名单放行。

        BacktestFeeder.get_historical_data (backtest_feeder.py:166) 实际有实现，
        回测取数能力由数据源决定（#6488 修 trade_day 日历），非 forbidden 操作。
        """
        source = (
            "class MyStrategy:\n"
            "    def cal(self, bar):\n"
            "        df = self.data_feeder.get_historical_data(['000001'], s, e)\n"
            "        return []\n"
        )
        assert _check_cal(source) is None


class TestForbiddenOperationsViolations:
    """违规调用必须命中（确保修误报时不漏掉真违规）。"""

    @pytest.mark.tdd
    def test_bare_get_bars_flagged_as_database(self):
        """裸 get_bars(...) 是模块级 CRUD 函数调用，必须报 database。

        与 self.get_bars_cached 区分：裸调用（无 self./obj. 前缀）= 直接
        import 的 CRUD 函数，绕过 datafeeder 时间边界。
        """
        source = (
            "class MyStrategy:\n"
            "    def cal(self, bar):\n"
            "        bars = get_bars('000001', 100)\n"
            "        return []\n"
        )
        issue = _check_cal(source)
        assert issue is not None
        assert "database" in issue.message

    @pytest.mark.tdd
    def test_cruds_access_flagged_as_database(self):
        """cruds.xxx 直接 CRUD 访问必须报 database（前缀子串匹配）。"""
        source = (
            "class MyStrategy:\n"
            "    def cal(self, bar):\n"
            "        stock = cruds.stock.get('000001')\n"
            "        return []\n"
        )
        issue = _check_cal(source)
        assert issue is not None
        assert "database" in issue.message

    @pytest.mark.tdd
    def test_requests_flagged_as_network(self):
        """requests.get 网络调用必须报 network。"""
        source = (
            "class MyStrategy:\n"
            "    def cal(self, bar):\n"
            "        r = requests.get('http://example.com')\n"
            "        return []\n"
        )
        issue = _check_cal(source)
        assert issue is not None
        assert "network" in issue.message

    @pytest.mark.tdd
    def test_bare_open_flagged_as_file_io(self):
        """裸 open(...) 文件 IO 必须报 file I/O。"""
        source = (
            "class MyStrategy:\n"
            "    def cal(self, bar):\n"
            "        f = open('/tmp/x')\n"
            "        return []\n"
        )
        issue = _check_cal(source)
        assert issue is not None
        assert "file I/O" in issue.message

