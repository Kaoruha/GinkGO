"""
测试工具类 - Pytest重构版本

提供Protocol接口和Mixin功能测试的专用工具：
1. 接口验证工具
2. 混入类测试工具
3. 类型安全检查工具
4. 模拟数据生成工具

重构要点：
- 使用pytest fixtures共享测试资源
- 使用parametrize进行参数化测试
- 使用pytest.mark.unit标记
- 清晰的测试类分组
"""

import pytest
from typing import Any, Dict, List, Type, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
from unittest.mock import Mock

# Ginkgo imports
from ginkgo.trading.entities.order import Order
from ginkgo.trading.entities.position import Position
from ginkgo.trading.entities.signal import Signal
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES

# 导入要测试的工具
from test.fixtures.trading_factories import (
    TradingDataFactory, ProtocolTestHelper, MixinTestHelper,
    TypeSafetyValidator, TestScenarioBuilder, AssertionHelper
)


# ===== Fixtures =====

@pytest.fixture
def mock_data_config():
    """模拟数据配置fixture"""
    return MockDataConfig(
        count=10,
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 12, 31),
        symbols=["000001.SZ", "000002.SZ"],
        initial_price=Decimal("10.0"),
        volatility=Decimal("0.02")
    )


@pytest.fixture
def trading_data_factory(mock_data_config):
    """交易数据工厂fixture"""
    return TradingDataFactory(mock_data_config)


@pytest.fixture
def protocol_test_helper():
    """Protocol测试辅助类fixture"""
    return ProtocolTestHelper()


@pytest.fixture
def mixin_test_helper():
    """Mixin测试辅助类fixture"""
    return MixinTestHelper()


@pytest.fixture
def type_safety_validator():
    """类型安全验证器fixture"""
    return TypeSafetyValidator()


@pytest.fixture
def test_scenario_builder():
    """测试场景构建器fixture"""
    return TestScenarioBuilder()


@pytest.fixture
def assertion_helper():
    """断言辅助类fixture"""
    return AssertionHelper()


# ===== MockDataConfig测试 =====

@pytest.mark.unit
class TestMockDataConfig:
    """模拟数据配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = MockDataConfig()

        assert config.count == 10
        assert config.symbols == ["000001.SZ", "000002.SZ"]
        assert config.initial_price == Decimal("10.0")
        assert config.volatility == Decimal("0.02")

    @pytest.mark.parametrize("count,symbols,initial_price", [
        (5, ["000001.SZ"], Decimal("5.0")),
        (20, ["000001.SZ", "000002.SZ", "000003.SZ"], Decimal("15.0")),
    ])
    def test_custom_config(self, count, symbols, initial_price):
        """测试自定义配置"""
        config = MockDataConfig(
            count=count,
            symbols=symbols,
            initial_price=initial_price
        )

        assert config.count == count
        assert config.symbols == symbols
        assert config.initial_price == initial_price


# ===== TradingDataFactory测试 =====

@pytest.mark.unit
class TestTradingDataFactory:
    """量化交易数据工厂测试"""

    def test_create_orders(self, trading_data_factory):
        """测试创建订单数据"""
        portfolio_id = "test_portfolio"
        orders = trading_data_factory.create_orders(portfolio_id)

        assert len(orders) == 10
        assert all(o.portfolio_id == portfolio_id for o in orders)
        assert all(isinstance(o, Order) for o in orders)

    def test_create_positions(self, trading_data_factory):
        """测试创建持仓数据"""
        positions = trading_data_factory.create_positions()

        assert len(positions) == 10
        assert all(isinstance(p, Position) for p in positions)

    def test_create_signals(self, trading_data_factory):
        """测试创建信号数据"""
        signals = trading_data_factory.create_signals()

        assert len(signals) == 10
        assert all(isinstance(s, Signal) for s in signals)

    def test_create_portfolio_info(self, trading_data_factory):
        """测试创建投资组合信息"""
        portfolio_info = trading_data_factory.create_portfolio_info()

        assert "uuid" in portfolio_info
        assert "cash" in portfolio_info
        assert "total_value" in portfolio_info
        assert "positions" in portfolio_info
        assert "risk_metrics" in portfolio_info


# ===== ProtocolTestHelper测试 =====

@pytest.mark.unit
class TestProtocolTestHelper:
    """Protocol接口测试辅助类测试"""

    def test_create_mock_strategy(self, protocol_test_helper):
        """测试创建模拟策略"""
        strategy = protocol_test_helper.create_mock_strategy()

        assert strategy is not None
        assert strategy.name == "MockStrategy"
        assert strategy.cal.return_value == []
        assert strategy.validate_parameters.return_value is True

    def test_create_mock_risk_manager(self, protocol_test_helper):
        """测试创建模拟风控管理器"""
        risk_manager = protocol_test_helper.create_mock_risk_manager()

        assert risk_manager is not None
        assert risk_manager.name == "MockRiskManager"
        assert risk_manager.validate_order.return_value is None
        assert risk_manager.generate_risk_signals.return_value == []

    def test_create_mock_portfolio(self, protocol_test_helper):
        """测试创建模拟投资组合"""
        portfolio = protocol_test_helper.create_mock_portfolio()

        assert portfolio is not None
        assert portfolio.name == "MockPortfolio"
        assert portfolio.add_strategy.return_value is None
        assert portfolio.get_portfolio_info.return_value["total_value"] == 100000.0

    def test_create_mock_engine(self, protocol_test_helper):
        """测试创建模拟引擎"""
        engine = protocol_test_helper.create_mock_engine()

        assert engine is not None
        assert engine.name == "MockEngine"
        assert engine.start.return_value is True
        assert engine.run.return_value["status"] == "completed"


# ===== MixinTestHelper测试 =====

@pytest.mark.unit
class TestMixinTestHelper:
    """Mixin功能测试辅助类测试"""

    def test_create_test_class_with_mixin(self, mixin_test_helper):
        """测试创建包含Mixin的测试类"""
        class BaseClass:
            pass

        class TestMixin:
            def mixin_method(self):
                return "mixin"

        TestClass = mixin_test_helper.create_test_class_with_mixin(BaseClass, TestMixin)

        assert TestClass is not None
        assert "BaseClass" in TestClass.__name__
        assert "Mixin" in TestClass.__name__

    def test_validate_mixin_integration_success(self, mixin_test_helper):
        """测试成功的Mixin集成验证"""
        class BaseClass:
            pass

        class TestMixin:
            def mixin_method(self):
                return "mixin"

        class CombinedClass(BaseClass, TestMixin):
            pass

        is_valid, errors = mixin_test_helper.validate_mixin_integration(
            CombinedClass(), TestMixin, BaseClass
        )

        assert is_valid
        assert len(errors) == 0


# ===== TypeSafetyValidator测试 =====

@pytest.mark.unit
class TestTypeSafetyValidator:
    """类型安全验证器测试"""

    def test_validate_method_signatures_success(self, type_safety_validator):
        """测试成功的方法签名验证"""
        class TestClass:
            def method1(self, arg1: int) -> str:
                return str(arg1)

            def method2(self, arg1: int, arg2: str) -> None:
                pass

        import inspect
        expected_methods = {
            "method1": inspect.signature(TestClass.method1),
            "method2": inspect.signature(TestClass.method2),
        }

        is_valid, errors = type_safety_validator.validate_method_signatures(
            TestClass(), expected_methods
        )

        assert is_valid
        assert len(errors) == 0

    def test_validate_return_types_success(self, type_safety_validator):
        """测试成功的返回类型验证"""
        class TestClass:
            def method_returns_int(self) -> int:
                return 42

            def method_returns_string(self) -> str:
                return "test"

        test_obj = TestClass()

        assert type_safety_validator.validate_return_types(
            test_obj, "method_returns_int", int
        )

        assert type_safety_validator.validate_return_types(
            test_obj, "method_returns_string", str
        )


# ===== TestScenarioBuilder测试 =====

@pytest.mark.unit
class TestTestScenarioBuilder:
    """测试场景构建器测试"""

    def test_build_strategy_test_scenario(self, test_scenario_builder):
        """测试构建策略测试场景"""
        scenario = test_scenario_builder.build_strategy_test_scenario("bull_market")

        assert "portfolio_info" in scenario
        assert "market_event" in scenario
        assert "expected_signals" in scenario

    def test_build_risk_test_scenario(self, test_scenario_builder):
        """测试构建风控测试场景"""
        scenario = test_scenario_builder.build_risk_test_scenario("position_limit")

        assert "portfolio_info" in scenario
        assert "order" in scenario
        assert "risk_type" in scenario
        assert scenario["risk_type"] == "position_limit"

    def test_build_portfolio_test_scenario(self, test_scenario_builder):
        """测试构建投资组合测试场景"""
        scenario = test_scenario_builder.build_portfolio_test_scenario("cash_insufficient")

        assert "portfolio_info" in scenario
        assert "signals" in scenario
        assert "state" in scenario
        assert scenario["state"] == "cash_insufficient"


# ===== AssertionHelper测试 =====

@pytest.mark.unit
class TestAssertionHelper:
    """断言辅助类测试"""

    def test_assert_financial_precision_success(self, assertion_helper):
        """测试成功的金融精度断言"""
        # 应该不抛出异常
        assertion_helper.assert_financial_precision(
            Decimal("10.1234"),
            Decimal("10.1235"),
            places=3
        )

    def test_assert_financial_precision_failure(self, assertion_helper):
        """测试失败的金融精度断言"""
        with pytest.raises(AssertionError):
            assertion_helper.assert_financial_precision(
                Decimal("10.1234"),
                Decimal("10.5678"),
                places=3
            )

    def test_assert_list_not_empty_success(self, assertion_helper):
        """测试成功的非空列表断言"""
        test_list = [1, 2, 3]
        # 应该不抛出异常
        assertion_helper.assert_list_not_empty(test_list)

    def test_assert_list_not_empty_failure(self, assertion_helper):
        """测试失败的非空列表断言"""
        with pytest.raises(AssertionError):
            assertion_helper.assert_list_not_empty([])

    def test_assert_dict_contains_keys_success(self, assertion_helper):
        """测试成功的字典键断言"""
        test_dict = {"key1": "value1", "key2": "value2"}
        # 应该不抛出异常
        assertion_helper.assert_dict_contains_keys(test_dict, ["key1", "key2"])

    def test_assert_dict_contains_keys_failure(self, assertion_helper):
        """测试失败的字典键断言"""
        test_dict = {"key1": "value1"}
        with pytest.raises(AssertionError):
            assertion_helper.assert_dict_contains_keys(test_dict, ["key1", "key2"])

    def test_assert_datetime_range_success(self, assertion_helper):
        """测试成功的时间范围断言"""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)
        test_dt = datetime(2024, 6, 15)
        # 应该不抛出异常
        assertion_helper.assert_datetime_range(test_dt, start, end)

    def test_assert_datetime_range_failure(self, assertion_helper):
        """测试失败的时间范围断言"""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)
        test_dt = datetime(2025, 6, 15)
        with pytest.raises(AssertionError):
            assertion_helper.assert_datetime_range(test_dt, start, end)


# ===== 参数化测试 =====

@pytest.mark.unit
@pytest.mark.parametrize("test_uuid,prefix", [
    ("TEST_12345678-1234-1234-1234-123456789abc", "TEST"),
    ("DATA_12345678-1234-1234-1234-123456789def", "DATA"),
    ("SIM_12345678-1234-1234-1234-123456789012", "SIM"),
])
def test_generate_test_uuid(test_uuid, prefix):
    """测试UUID生成"""
    # 生成UUID并验证前缀
    from test.fixtures.trading_factories import generate_test_uuid
    result = generate_test_uuid(prefix)

    assert result.startswith(f"{prefix}_")
    assert len(result) == len(prefix) + 37  # prefix + '_' + uuid长度


@pytest.mark.unit
@pytest.mark.parametrize("portfolio_value,expected_cash,cash_ratio", [
    (Decimal('100000.0'), Decimal('50000.0'), 0.5),
    (Decimal('200000.0'), Decimal('40000.0'), 0.2),
    (Decimal('150000.0'), Decimal('120000.0'), 0.8),
])
def test_portfolio_cash_calculation(portfolio_value, expected_cash, cash_ratio):
    """测试投资组合现金计算"""
    cash = portfolio_value * Decimal(str(cash_ratio))
    assert cash == expected_cash


# ===== Mock类定义 =====

@dataclass
class MockDataConfig:
    """模拟数据配置"""
    count: int = 10
    start_date: datetime = field(default_factory=lambda: datetime(2024, 1, 1))
    end_date: datetime = field(default_factory=lambda: datetime(2024, 12, 31))
    symbols: List[str] = field(default_factory=lambda: ["000001.SZ", "000002.SZ"])
    initial_price: Decimal = field(default_factory=lambda: Decimal("10.0"))
    volatility: Decimal = field(default_factory=lambda: Decimal("0.02"))


# ===== 测试辅助函数 =====

def test_generate_test_uuid_helper():
    """测试UUID生成辅助函数"""
    from test.fixtures.trading_factories import generate_test_uuid

    # 测试不同前缀
    test_prefix = "TEST"
    result = generate_test_uuid(test_prefix)

    assert result.startswith(f"{test_prefix}_")
    assert len(result.split("_")) == 2  # 前缀和UUID部分

    # 测试UUID部分有效性
    uuid_part = result.split("_")[1]
    # 验证UUID格式 (简化检查)
    assert len(uuid_part) == 36  # 标准UUID长度
    assert uuid_part.count('-') == 4  # UUID有4个连字符


@pytest.mark.unit
class TestTradingDataFactoryEdgeCases:
    """交易数据工厂边界情况测试"""

    @pytest.mark.parametrize("count", [
        0,      # 零个对象
        1,      # 单个对象
        100,    # 大量对象
    ])
    def test_create_varying_counts(self, count):
        """测试创建不同数量的对象"""
        config = MockDataConfig(count=count)
        factory = TradingDataFactory(config)

        orders = factory.create_orders()
        assert len(orders) == count

    @pytest.mark.parametrize("invalid_symbol", [
        "",          # 空字符串
        "INVALID",   # 无效格式
        None,        # None值
    ])
    def test_handle_invalid_symbols(self, invalid_symbol):
        """测试处理无效股票代码"""
        config = MockDataConfig(symbols=[invalid_symbol])
        factory = TradingDataFactory(config)

        # 应该能处理无效代码
        try:
            orders = factory.create_orders()
            assert len(orders) == 10
        except (ValueError, AttributeError, TypeError):
            # 某些情况下可能抛出异常
            pass


# ===== 集成测试辅助 =====

@pytest.mark.unit
class TestIntegrationHelpers:
    """集成测试辅助类"""

    def test_complete_workflow_with_helpers(self, trading_data_factory, assertion_helper):
        """测试完整的工作流程"""
        # 创建数据
        orders = trading_data_factory.create_orders()
        positions = trading_data_factory.create_positions()
        signals = trading_data_factory.create_signals()

        # 验证数据
        assertion_helper.assert_list_not_empty(orders)
        assertion_helper.assert_list_not_empty(positions)
        assertion_helper.assert_list_not_empty(signals)

        # 验证数据完整性
        for order in orders:
            assert isinstance(order, Order)

        for position in positions:
            assert isinstance(position, Position)

        for signal in signals:
            assert isinstance(signal, Signal)

    def test_scenario_builder_with_data_factory(self, test_scenario_builder, trading_data_factory):
        """测试场景构建器与数据工厂的集成"""
        # 构建场景
        scenario = test_scenario_builder.build_strategy_test_scenario()

        # 添加额外数据
        scenario['additional_orders'] = trading_data_factory.create_orders()
        scenario['additional_positions'] = trading_data_factory.create_positions()

        # 验证场景
        assert 'portfolio_info' in scenario
        assert 'additional_orders' in scenario
        assert 'additional_positions' in scenario
        assert len(scenario['additional_orders']) == 10
        assert len(scenario['additional_positions']) == 10
