"""
性能: 271MB RSS, 2.56s, 20 tests [PASS]
默认分析器功能测试

测试Portfolio的默认分析器初始化机制，使用真实的PortfolioT1Backtest和PortfolioBase。
"""

import pytest
from unittest.mock import Mock

from ginkgo.enums import DEFAULT_ANALYZER_SET
from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest
from ginkgo.trading.bases.portfolio_base import PortfolioBase


def _make_portfolio(**kwargs):
    """创建一个PortfolioT1Backtest实例用于测试，Mock掉notification_service。"""
    return PortfolioT1Backtest(
        notification_service=Mock(),
        **kwargs,
    )


class TestDefaultAnalyzerSet:
    """测试DEFAULT_ANALYZER_SET枚举"""

    def test_minimal_set_exists(self):
        assert DEFAULT_ANALYZER_SET.MINIMAL is not None
        assert DEFAULT_ANALYZER_SET.MINIMAL.value == 1

    def test_standard_set_exists(self):
        assert DEFAULT_ANALYZER_SET.STANDARD is not None
        assert DEFAULT_ANALYZER_SET.STANDARD.value == 2

    def test_full_set_exists(self):
        assert DEFAULT_ANALYZER_SET.FULL is not None
        assert DEFAULT_ANALYZER_SET.FULL.value == 3


class TestMinimalAnalyzerSet:
    """测试MINIMAL分析器集合"""

    def test_minimal_set_initialization(self):
        portfolio = _make_portfolio(
            use_default_analyzers=True,
            default_analyzer_set=DEFAULT_ANALYZER_SET.MINIMAL,
        )
        assert len(portfolio._analyzers) == 2
        assert 'net_value' in portfolio._analyzers
        assert 'profit' in portfolio._analyzers

    def test_minimal_set_not_include_others(self):
        portfolio = _make_portfolio(
            use_default_analyzers=True,
            default_analyzer_set=DEFAULT_ANALYZER_SET.MINIMAL,
        )
        assert 'max_drawdown' not in portfolio._analyzers
        assert 'sharpe_ratio' not in portfolio._analyzers
        assert 'win_rate' not in portfolio._analyzers


class TestStandardAnalyzerSet:
    """测试STANDARD分析器集合"""

    def test_standard_set_initialization(self):
        portfolio = _make_portfolio(
            use_default_analyzers=True,
            default_analyzer_set=DEFAULT_ANALYZER_SET.STANDARD,
        )
        assert len(portfolio._analyzers) == 5
        assert 'net_value' in portfolio._analyzers
        assert 'profit' in portfolio._analyzers
        assert 'max_drawdown' in portfolio._analyzers
        assert 'sharpe_ratio' in portfolio._analyzers
        assert 'win_rate' in portfolio._analyzers

    def test_standard_is_default(self):
        portfolio = _make_portfolio(use_default_analyzers=True)
        assert portfolio._default_analyzer_set == DEFAULT_ANALYZER_SET.STANDARD


class TestFullAnalyzerSet:
    """测试FULL分析器集合"""

    def test_full_set_initialization(self):
        portfolio = _make_portfolio(
            use_default_analyzers=True,
            default_analyzer_set=DEFAULT_ANALYZER_SET.FULL,
        )
        assert len(portfolio._analyzers) == 10

        expected = [
            'net_value', 'profit', 'max_drawdown', 'sharpe_ratio',
            'win_rate', 'volatility', 'sortino_ratio', 'calmar_ratio',
            'hold_pct', 'signal_count',
        ]
        for name in expected:
            assert name in portfolio._analyzers, f"Missing analyzer: {name}"


class TestDisableDefaultAnalyzers:
    """测试禁用默认分析器"""

    def test_disable_default_analyzers(self):
        portfolio = _make_portfolio(use_default_analyzers=False)
        assert len(portfolio._analyzers) == 0

    def test_disable_with_set_parameter_ignored(self):
        portfolio = _make_portfolio(
            use_default_analyzers=False,
            default_analyzer_set=DEFAULT_ANALYZER_SET.FULL,
        )
        assert len(portfolio._analyzers) == 0


class TestUserAnalyzerPriority:
    """测试用户自定义分析器优先级"""

    def test_user_analyzer_not_overwritten(self):
        from ginkgo.trading.analysis.analyzers.net_value import NetValue

        portfolio = _make_portfolio(
            use_default_analyzers=False,
            default_analyzer_set=DEFAULT_ANALYZER_SET.STANDARD,
        )

        # 手动添加一个同名的真实分析器
        custom = NetValue(name='net_value')
        portfolio.add_analyzer(custom)
        assert len(portfolio._analyzers) == 1

        # 现在开启默认分析器——已有的不应被覆盖
        portfolio._init_default_analyzers()
        # STANDARD有5个，但net_value已存在，所以只添加4个新的
        assert len(portfolio._analyzers) == 5
        assert portfolio._analyzers['net_value'] is custom

    def test_user_can_add_different_analyzer(self):
        from ginkgo.trading.analysis.analyzers.net_value import NetValue

        portfolio = _make_portfolio(
            use_default_analyzers=True,
            default_analyzer_set=DEFAULT_ANALYZER_SET.MINIMAL,
        )
        custom = NetValue(name='custom_analyzer')
        portfolio.add_analyzer(custom)

        assert 'custom_analyzer' in portfolio._analyzers
        assert len(portfolio._analyzers) == 3  # 2 default + 1 custom


class TestBuiltinAnalyzerConfiguration:
    """测试内置分析器配置（直接从PortfolioBase读取真实常量）"""

    def test_builtin_config_minimal_count(self):
        config = PortfolioBase.BUILTIN_DEFAULT_ANALYZERS[DEFAULT_ANALYZER_SET.MINIMAL]
        assert len(config) == 2

    def test_builtin_config_standard_count(self):
        config = PortfolioBase.BUILTIN_DEFAULT_ANALYZERS[DEFAULT_ANALYZER_SET.STANDARD]
        assert len(config) == 5

    def test_builtin_config_full_count(self):
        config = PortfolioBase.BUILTIN_DEFAULT_ANALYZERS[DEFAULT_ANALYZER_SET.FULL]
        assert len(config) == 10

    def test_minimal_subset_of_standard(self):
        minimal = set(PortfolioBase.BUILTIN_DEFAULT_ANALYZERS[DEFAULT_ANALYZER_SET.MINIMAL])
        standard = set(PortfolioBase.BUILTIN_DEFAULT_ANALYZERS[DEFAULT_ANALYZER_SET.STANDARD])
        assert minimal.issubset(standard)

    def test_standard_subset_of_full(self):
        standard = set(PortfolioBase.BUILTIN_DEFAULT_ANALYZERS[DEFAULT_ANALYZER_SET.STANDARD])
        full = set(PortfolioBase.BUILTIN_DEFAULT_ANALYZERS[DEFAULT_ANALYZER_SET.FULL])
        assert standard.issubset(full)


class TestEnumMethods:
    """测试枚举方法"""

    def test_enum_from_int(self):
        assert DEFAULT_ANALYZER_SET.from_int(1) == DEFAULT_ANALYZER_SET.MINIMAL
        assert DEFAULT_ANALYZER_SET.from_int(2) == DEFAULT_ANALYZER_SET.STANDARD
        assert DEFAULT_ANALYZER_SET.from_int(3) == DEFAULT_ANALYZER_SET.FULL

    def test_enum_to_int(self):
        assert DEFAULT_ANALYZER_SET.MINIMAL.to_int() == 1
        assert DEFAULT_ANALYZER_SET.STANDARD.to_int() == 2
        assert DEFAULT_ANALYZER_SET.FULL.to_int() == 3

    def test_enum_validate_input(self):
        assert DEFAULT_ANALYZER_SET.validate_input(DEFAULT_ANALYZER_SET.STANDARD) == 2
        assert DEFAULT_ANALYZER_SET.validate_input(2) == 2
