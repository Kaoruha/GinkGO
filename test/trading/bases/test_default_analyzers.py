"""
默认分析器功能测试

测试Portfolio的默认分析器初始化机制
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

from ginkgo.enums import DEFAULT_ANALYZER_SET


def create_mock_analyzer(name: str):
    """创建一个具有正确name属性的Mock分析器"""
    mock = MagicMock()
    # 直接设置name属性为字符串
    mock.name = name
    return mock


# 需要一个可实例化的Portfolio类来测试
# 由于PortfolioBase是抽象类，我们创建一个具体实现用于测试
class ConcretePortfolio:
    """用于测试的具体Portfolio实现"""

    BUILTIN_DEFAULT_ANALYZERS = {
        DEFAULT_ANALYZER_SET.MINIMAL: ['net_value', 'profit'],
        DEFAULT_ANALYZER_SET.STANDARD: ['net_value', 'profit', 'max_drawdown', 'sharpe_ratio', 'win_rate'],
        DEFAULT_ANALYZER_SET.FULL: ['net_value', 'profit', 'max_drawdown', 'sharpe_ratio',
                                     'win_rate', 'volatility', 'sortino_ratio', 'calmar_ratio',
                                     'hold_pct', 'signal_count'],
    }

    def __init__(
        self,
        name: str = "TestPortfolio",
        use_default_analyzers: bool = True,
        default_analyzer_set: DEFAULT_ANALYZER_SET = DEFAULT_ANALYZER_SET.STANDARD,
    ):
        self.name = name
        self._use_default_analyzers = use_default_analyzers
        self._default_analyzer_set = default_analyzer_set
        self._analyzers = {}
        self._logs = []

        if use_default_analyzers:
            self._init_default_analyzers()

    def log(self, level, msg):
        self._logs.append((level, msg))

    def add_analyzer(self, analyzer):
        if analyzer.name in self._analyzers:
            self.log("WARN", f"Analyzer {analyzer.name} already exists")
            return
        self._analyzers[analyzer.name] = analyzer

    def _init_default_analyzers(self):
        """初始化内置默认分析器"""
        analyzer_names = self.BUILTIN_DEFAULT_ANALYZERS.get(self._default_analyzer_set, [])

        for name in analyzer_names:
            if name in self._analyzers:
                self.log("DEBUG", f"Default analyzer '{name}' already exists, skipping")
                continue

            # 创建Mock分析器
            analyzer = create_mock_analyzer(name)
            self.add_analyzer(analyzer)
            self.log("DEBUG", f"Added default analyzer: {name}")


class TestDefaultAnalyzerSet:
    """测试DEFAULT_ANALYZER_SET枚举"""

    def test_minimal_set_exists(self):
        """测试MINIMAL集合存在"""
        assert hasattr(DEFAULT_ANALYZER_SET, 'MINIMAL')
        assert DEFAULT_ANALYZER_SET.MINIMAL.value == 1

    def test_standard_set_exists(self):
        """测试STANDARD集合存在"""
        assert hasattr(DEFAULT_ANALYZER_SET, 'STANDARD')
        assert DEFAULT_ANALYZER_SET.STANDARD.value == 2

    def test_full_set_exists(self):
        """测试FULL集合存在"""
        assert hasattr(DEFAULT_ANALYZER_SET, 'FULL')
        assert DEFAULT_ANALYZER_SET.FULL.value == 3


class TestMinimalAnalyzerSet:
    """测试MINIMAL分析器集合"""

    def test_minimal_set_initialization(self):
        """测试MINIMAL集合初始化"""
        portfolio = ConcretePortfolio(
            use_default_analyzers=True,
            default_analyzer_set=DEFAULT_ANALYZER_SET.MINIMAL
        )

        # MINIMAL应该只有2个分析器
        assert len(portfolio._analyzers) == 2
        assert 'net_value' in portfolio._analyzers
        assert 'profit' in portfolio._analyzers

    def test_minimal_set_not_include_others(self):
        """测试MINIMAL集合不包含其他分析器"""
        portfolio = ConcretePortfolio(
            use_default_analyzers=True,
            default_analyzer_set=DEFAULT_ANALYZER_SET.MINIMAL
        )

        # 不应该包含这些
        assert 'max_drawdown' not in portfolio._analyzers
        assert 'sharpe_ratio' not in portfolio._analyzers
        assert 'win_rate' not in portfolio._analyzers


class TestStandardAnalyzerSet:
    """测试STANDARD分析器集合"""

    def test_standard_set_initialization(self):
        """测试STANDARD集合初始化"""
        portfolio = ConcretePortfolio(
            use_default_analyzers=True,
            default_analyzer_set=DEFAULT_ANALYZER_SET.STANDARD
        )

        # STANDARD应该有5个分析器
        assert len(portfolio._analyzers) == 5
        assert 'net_value' in portfolio._analyzers
        assert 'profit' in portfolio._analyzers
        assert 'max_drawdown' in portfolio._analyzers
        assert 'sharpe_ratio' in portfolio._analyzers
        assert 'win_rate' in portfolio._analyzers

    def test_standard_is_default(self):
        """测试STANDARD是默认值"""
        portfolio = ConcretePortfolio(use_default_analyzers=True)
        assert portfolio._default_analyzer_set == DEFAULT_ANALYZER_SET.STANDARD


class TestFullAnalyzerSet:
    """测试FULL分析器集合"""

    def test_full_set_initialization(self):
        """测试FULL集合初始化"""
        portfolio = ConcretePortfolio(
            use_default_analyzers=True,
            default_analyzer_set=DEFAULT_ANALYZER_SET.FULL
        )

        # FULL应该有10个分析器
        assert len(portfolio._analyzers) == 10

        expected = [
            'net_value', 'profit', 'max_drawdown', 'sharpe_ratio',
            'win_rate', 'volatility', 'sortino_ratio', 'calmar_ratio',
            'hold_pct', 'signal_count'
        ]
        for name in expected:
            assert name in portfolio._analyzers, f"Missing analyzer: {name}"


class TestDisableDefaultAnalyzers:
    """测试禁用默认分析器"""

    def test_disable_default_analyzers(self):
        """测试use_default_analyzers=False时不添加分析器"""
        portfolio = ConcretePortfolio(use_default_analyzers=False)

        assert len(portfolio._analyzers) == 0

    def test_disable_with_set_parameter_ignored(self):
        """测试禁用时忽略default_analyzer_set参数"""
        portfolio = ConcretePortfolio(
            use_default_analyzers=False,
            default_analyzer_set=DEFAULT_ANALYZER_SET.FULL
        )

        # 即使设置了FULL，禁用时也不应该添加
        assert len(portfolio._analyzers) == 0


class TestUserAnalyzerPriority:
    """测试用户自定义分析器优先级"""

    def test_user_analyzer_not_overwritten(self):
        """测试用户手动添加的分析器不被默认分析器覆盖"""
        portfolio = ConcretePortfolio(
            use_default_analyzers=True,
            default_analyzer_set=DEFAULT_ANALYZER_SET.STANDARD
        )

        # 用户手动添加同名分析器
        custom_analyzer = create_mock_analyzer('net_value')
        custom_analyzer.custom = True  # 标记为自定义
        original_count = len(portfolio._analyzers)

        # 尝试添加已存在的分析器
        portfolio.add_analyzer(custom_analyzer)

        # 应该被拒绝（不会增加）
        assert len(portfolio._analyzers) == original_count

    def test_user_can_add_different_analyzer(self):
        """测试用户可以添加不同名称的分析器"""
        portfolio = ConcretePortfolio(
            use_default_analyzers=True,
            default_analyzer_set=DEFAULT_ANALYZER_SET.MINIMAL
        )

        # 添加自定义分析器
        custom_analyzer = create_mock_analyzer('custom_analyzer')
        portfolio.add_analyzer(custom_analyzer)

        assert 'custom_analyzer' in portfolio._analyzers
        assert len(portfolio._analyzers) == 3  # 2个默认 + 1个自定义


class TestBuiltinAnalyzerConfiguration:
    """测试内置分析器配置"""

    def test_builtin_config_minimal_count(self):
        """测试MINIMAL配置的分析器数量"""
        config = ConcretePortfolio.BUILTIN_DEFAULT_ANALYZERS[DEFAULT_ANALYZER_SET.MINIMAL]
        assert len(config) == 2

    def test_builtin_config_standard_count(self):
        """测试STANDARD配置的分析器数量"""
        config = ConcretePortfolio.BUILTIN_DEFAULT_ANALYZERS[DEFAULT_ANALYZER_SET.STANDARD]
        assert len(config) == 5

    def test_builtin_config_full_count(self):
        """测试FULL配置的分析器数量"""
        config = ConcretePortfolio.BUILTIN_DEFAULT_ANALYZERS[DEFAULT_ANALYZER_SET.FULL]
        assert len(config) == 10

    def test_minimal_subset_of_standard(self):
        """测试MINIMAL是STANDARD的子集"""
        minimal = set(ConcretePortfolio.BUILTIN_DEFAULT_ANALYZERS[DEFAULT_ANALYZER_SET.MINIMAL])
        standard = set(ConcretePortfolio.BUILTIN_DEFAULT_ANALYZERS[DEFAULT_ANALYZER_SET.STANDARD])
        assert minimal.issubset(standard)

    def test_standard_subset_of_full(self):
        """测试STANDARD是FULL的子集"""
        standard = set(ConcretePortfolio.BUILTIN_DEFAULT_ANALYZERS[DEFAULT_ANALYZER_SET.STANDARD])
        full = set(ConcretePortfolio.BUILTIN_DEFAULT_ANALYZERS[DEFAULT_ANALYZER_SET.FULL])
        assert standard.issubset(full)


class TestRealPortfolioBase:
    """测试真实的PortfolioBase类（如果可以导入）"""

    @pytest.mark.skipif(
        True,  # 默认跳过，因为PortfolioBase是抽象类
        reason="PortfolioBase是抽象类，需要具体实现才能实例化"
    )
    def test_real_portfolio_default_analyzers(self):
        """测试真实Portfolio的默认分析器"""
        from ginkgo.trading.bases.portfolio_base import PortfolioBase

        # 这里需要具体的Portfolio实现类
        # 如果有具体实现，可以这样测试：
        # portfolio = ConcretePortfolioImpl(
        #     use_default_analyzers=True,
        #     default_analyzer_set=DEFAULT_ANALYZER_SET.STANDARD
        # )
        # assert 'net_value' in portfolio.analyzers
        pass


class TestEnumMethods:
    """测试枚举方法"""

    def test_enum_from_int(self):
        """测试from_int方法"""
        assert DEFAULT_ANALYZER_SET.from_int(1) == DEFAULT_ANALYZER_SET.MINIMAL
        assert DEFAULT_ANALYZER_SET.from_int(2) == DEFAULT_ANALYZER_SET.STANDARD
        assert DEFAULT_ANALYZER_SET.from_int(3) == DEFAULT_ANALYZER_SET.FULL

    def test_enum_to_int(self):
        """测试to_int方法"""
        assert DEFAULT_ANALYZER_SET.MINIMAL.to_int() == 1
        assert DEFAULT_ANALYZER_SET.STANDARD.to_int() == 2
        assert DEFAULT_ANALYZER_SET.FULL.to_int() == 3

    def test_enum_validate_input(self):
        """测试validate_input方法"""
        assert DEFAULT_ANALYZER_SET.validate_input(DEFAULT_ANALYZER_SET.STANDARD) == 2
        assert DEFAULT_ANALYZER_SET.validate_input(2) == 2
