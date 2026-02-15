"""
IPortfolio Protocol接口测试

测试IPortfolio Protocol接口的类型安全性和运行时验证。
遵循pytest最佳实践，使用fixtures和参数化测试。
"""

import pytest
from typing import Dict, Any, List
from datetime import datetime
from decimal import Decimal


# ===== Protocol测试类 =====

@pytest.mark.unit
class TestIPortfolioProtocolBasic:
    """IPortfolio Protocol基础功能测试"""

    def test_portfolio_required_methods(self):
        """测试投资组合必需方法"""
        # 创建模拟投资组合
        portfolio = self._create_mock_portfolio()

        # 验证必需方法存在
        required_methods = [
            'get_portfolio_info', 'add_strategy', 'remove_strategy',
            'add_risk_manager', 'remove_risk_manager', 'get_positions',
            'get_position', 'update_position', 'remove_position',
            'get_orders', 'put_order', 'get_cash', 'get_frozen',
            'freeze_capital', 'unfreeze_capital', 'get_frozen_capital',
            'calculate_available_cash', 'calculate_available_positions',
            'process_event', 'publish_event', 'add_component',
            'remove_component', 'get_components', 'validate_state'
        ]

        for method in required_methods:
            assert hasattr(portfolio, method), f"投资组合必须有{method}方法"

    def test_portfolio_required_properties(self):
        """测试投资组合必需属性"""
        portfolio = self._create_mock_portfolio()

        # 验证必需属性
        assert hasattr(portfolio, 'name'), "投资组合必须有name属性"
        assert hasattr(portfolio, 'uuid'), "投资组合必须有uuid属性"

        # 验证属性类型
        assert isinstance(portfolio.name, str), "name应该是字符串"
        assert isinstance(portfolio.uuid, str), "uuid应该是字符串"

    def test_get_portfolio_info_structure(self, sample_portfolio_data):
        """测试get_portfolio_info返回结构"""
        portfolio = self._create_mock_portfolio()

        # 调用方法
        info = portfolio.get_portfolio_info()

        # 验证返回结构
        assert isinstance(info, dict), "get_portfolio_info应该返回字典"
        required_fields = ['uuid', 'name', 'cash', 'total_value', 'positions']
        for field in required_fields:
            assert field in info, f"返回信息应该包含{field}字段"

    def test_portfolio_strategy_management(self, sample_portfolio_data):
        """测试策略管理方法"""
        portfolio = self._create_mock_portfolio()
        strategy = Mock(name="TestStrategy")

        # 测试添加策略
        portfolio.add_strategy(strategy)
        strategies = portfolio.get_components("strategy")
        assert len(strategies) == 1

        # 测试移除策略
        portfolio.remove_strategy(strategy)
        strategies = portfolio.get_components("strategy")
        assert len(strategies) == 0

    def test_portfolio_risk_manager_management(self, sample_portfolio_data):
        """测试风控管理器管理方法"""
        portfolio = self._create_mock_portfolio()
        risk_manager = Mock(name="TestRiskManager")

        # 测试添加风控管理器
        portfolio.add_risk_manager(risk_manager)
        risk_managers = portfolio.get_components("risk_manager")
        assert len(risk_managers) == 1

        # 测试移除风控管理器
        portfolio.remove_risk_manager(risk_manager)
        risk_managers = portfolio.get_components("risk_manager")
        assert len(risk_managers) == 0

    def _create_mock_portfolio(self):
        """创建模拟投资组合"""
        class MockPortfolio:
            def __init__(self):
                self.name = "TestPortfolio"
                self.uuid = "portfolio_123"
                self.cash = Decimal('100000.0')
                self.frozen = Decimal('0.0')
                self.positions = {}
                self.strategies = []
                self.risk_managers = []
                self.orders = []

            def get_portfolio_info(self):
                return {
                    "uuid": self.uuid,
                    "name": self.name,
                    "cash": self.cash,
                    "frozen": self.frozen,
                    "total_value": self.calculate_total_value(),
                    "positions": self.positions
                }

            def calculate_total_value(self):
                return self.cash + sum(
                    pos.get('market_value', 0) for pos in self.positions.values()
                )

            def add_strategy(self, strategy):
                self.strategies.append(strategy)

            def remove_strategy(self, strategy):
                if strategy in self.strategies:
                    self.strategies.remove(strategy)

            def add_risk_manager(self, risk_manager):
                self.risk_managers.append(risk_manager)

            def remove_risk_manager(self, risk_manager):
                if risk_manager in self.risk_managers:
                    self.risk_managers.remove(risk_manager)

            def get_positions(self):
                return list(self.positions.values())

            def get_position(self, code):
                return self.positions.get(code)

            def update_position(self, position):
                self.positions[position.code] = position

            def remove_position(self, code):
                self.positions.pop(code, None)

            def get_orders(self):
                return self.orders.copy()

            def put_order(self, order):
                self.orders.append(order)

            def get_cash(self):
                return self.cash

            def get_frozen(self):
                return self.frozen

            def freeze_capital(self, amount):
                if amount <= self.cash:
                    self.cash -= amount
                    self.frozen += amount
                    return True
                return False

            def unfreeze_capital(self, amount):
                if amount <= self.frozen:
                    self.frozen -= amount
                    self.cash += amount
                    return True
                return False

            def get_frozen_capital(self):
                return self.frozen

            def calculate_available_cash(self):
                return self.cash - self.frozen

            def calculate_available_positions(self):
                return {
                    code: pos for code, pos in self.positions.items()
                    if pos.get('available_volume', pos.get('volume', 0)) > 0
                }

            def process_event(self, event):
                pass

            def publish_event(self, event):
                pass

            def add_component(self, component_type, component):
                if component_type == "strategy":
                    self.add_strategy(component)
                elif component_type == "risk_manager":
                    self.add_risk_manager(component)

            def remove_component(self, component_type, component):
                if component_type == "strategy":
                    self.remove_strategy(component)
                elif component_type == "risk_manager":
                    self.remove_risk_manager(component)

            def get_components(self, component_type=None):
                if component_type == "strategy":
                    return self.strategies.copy()
                elif component_type == "risk_manager":
                    return self.risk_managers.copy()
                else:
                    return {
                        "strategies": self.strategies.copy(),
                        "risk_managers": self.risk_managers.copy()
                    }

            def validate_state(self):
                errors = []
                if self.cash < 0:
                    errors.append("现金不能为负数")
                if self.frozen < 0:
                    errors.append("冻结资金不能为负数")
                if self.frozen > self.cash:
                    errors.append("冻结资金不能超过现金")
                return errors

        return MockPortfolio()


@pytest.mark.unit
class TestIPortfolioProtocolValidation:
    """IPortfolio Protocol验证测试"""

    def test_portfolio_state_validation(self):
        """测试投资组合状态验证"""
        portfolio = self._create_mock_portfolio()

        # 正常状态应该通过验证
        errors = portfolio.validate_state()
        assert len(errors) == 0

        # 异常状态应该检测错误
        portfolio.cash = Decimal('-1000.0')
        errors = portfolio.validate_state()
        assert len(errors) > 0
        assert any("现金" in error for error in errors)

    @pytest.mark.parametrize("cash,frozen,should_error", [
        (Decimal('100000.0'), Decimal('0.0'), False),
        (Decimal('50000.0'), Decimal('50000.0'), False),
        (Decimal('10000.0'), Decimal('0.0'), False),
        (Decimal('-1000.0'), Decimal('0.0'), True),
        (Decimal('100000.0'), Decimal('100000.0'), True),
        (Decimal('100000.0'), Decimal('-1000.0'), True),
    ])
    def test_portfolio_cash_validation(self, cash, frozen, should_error):
        """测试现金验证 - 参数化"""
        portfolio = self._create_mock_portfolio()
        portfolio.cash = cash
        portfolio.frozen = frozen

        errors = portfolio.validate_state()
        has_errors = len(errors) > 0
        assert has_errors == should_error

    def _create_mock_portfolio(self):
        """创建模拟投资组合"""
        class MockPortfolio:
            def __init__(self):
                self.name = "TestPortfolio"
                self.uuid = "portfolio_123"
                self.cash = Decimal('100000.0')
                self.frozen = Decimal('0.0')
                self.positions = {}
                self.strategies = []
                self.risk_managers = []
                self.orders = []

            def get_portfolio_info(self):
                return {"uuid": self.uuid, "name": self.name, "cash": self.cash,
                       "frozen": self.frozen, "total_value": self.cash, "positions": self.positions}

            def add_strategy(self, strategy):
                self.strategies.append(strategy)

            def remove_strategy(self, strategy):
                if strategy in self.strategies:
                    self.strategies.remove(strategy)

            def add_risk_manager(self, risk_manager):
                self.risk_managers.append(risk_manager)

            def remove_risk_manager(self, risk_manager):
                if risk_manager in self.risk_managers:
                    self.risk_managers.remove(risk_manager)

            def get_positions(self):
                return list(self.positions.values())

            def get_position(self, code):
                return self.positions.get(code)

            def update_position(self, position):
                self.positions[position.code] = position

            def remove_position(self, code):
                self.positions.pop(code, None)

            def get_orders(self):
                return self.orders.copy()

            def put_order(self, order):
                self.orders.append(order)

            def get_cash(self):
                return self.cash

            def get_frozen(self):
                return self.frozen

            def freeze_capital(self, amount):
                if amount <= self.cash:
                    self.cash -= amount
                    self.frozen += amount
                    return True
                return False

            def unfreeze_capital(self, amount):
                if amount <= self.frozen:
                    self.frozen -= amount
                    self.cash += amount
                    return True
                return False

            def get_frozen_capital(self):
                return self.frozen

            def calculate_available_cash(self):
                return self.cash - self.frozen

            def calculate_available_positions(self):
                return {code: pos for code, pos in self.positions.items()
                       if pos.get('available_volume', pos.get('volume', 0)) > 0}

            def process_event(self, event):
                pass

            def publish_event(self, event):
                pass

            def add_component(self, component_type, component):
                if component_type == "strategy":
                    self.add_strategy(component)
                elif component_type == "risk_manager":
                    self.add_risk_manager(component)

            def remove_component(self, component_type, component):
                if component_type == "strategy":
                    self.remove_strategy(component)
                elif component_type == "risk_manager":
                    self.remove_risk_manager(component)

            def get_components(self, component_type=None):
                if component_type == "strategy":
                    return self.strategies.copy()
                elif component_type == "risk_manager":
                    return self.risk_managers.copy()
                else:
                    return {"strategies": self.strategies.copy(),
                           "risk_managers": self.risk_managers.copy()}

            def validate_state(self):
                errors = []
                if self.cash < 0:
                    errors.append("现金不能为负数")
                if self.frozen < 0:
                    errors.append("冻结资金不能为负数")
                if self.frozen > self.cash:
                    errors.append("冻结资金不能超过现金")
                return errors

        return MockPortfolio()


@pytest.mark.unit
class TestIPortfolioProtocolComponents:
    """IPortfolio Protocol组件管理测试"""

    def test_component_management(self):
        """测试组件管理"""
        portfolio = self._create_mock_portfolio()
        strategy = Mock(name="TestStrategy")
        risk_manager = Mock(name="TestRiskManager")

        # 测试添加组件
        portfolio.add_component("strategy", strategy)
        portfolio.add_component("risk_manager", risk_manager)

        # 验证组件
        components = portfolio.get_components()
        assert len(components["strategies"]) == 1
        assert len(components["risk_managers"]) == 1

        # 测试移除组件
        portfolio.remove_component("strategy", strategy)
        components = portfolio.get_components()
        assert len(components["strategies"]) == 0

    @pytest.mark.parametrize("component_type", ["strategy", "risk_manager"])
    def test_component_by_type(self, component_type):
        """测试按类型获取组件 - 参数化"""
        portfolio = self._create_mock_portfolio()

        # 添加组件
        for i in range(3):
            component = Mock(name=f"{component_type}_{i}")
            portfolio.add_component(component_type, component)

        # 获取指定类型组件
        components = portfolio.get_components(component_type)
        assert len(components) == 3

    def _create_mock_portfolio(self):
        """创建模拟投资组合"""
        class MockPortfolio:
            def __init__(self):
                self.name = "TestPortfolio"
                self.uuid = "portfolio_123"
                self.strategies = []
                self.risk_managers = []

            def get_portfolio_info(self):
                return {"uuid": self.uuid, "name": self.name, "cash": 100000,
                       "frozen": 0, "total_value": 100000, "positions": {}}

            def add_strategy(self, strategy):
                self.strategies.append(strategy)

            def remove_strategy(self, strategy):
                if strategy in self.strategies:
                    self.strategies.remove(strategy)

            def add_risk_manager(self, risk_manager):
                self.risk_managers.append(risk_manager)

            def remove_risk_manager(self, risk_manager):
                if risk_manager in self.risk_managers:
                    self.risk_managers.remove(risk_manager)

            def get_positions(self):
                return []

            def get_position(self, code):
                return None

            def update_position(self, position):
                pass

            def remove_position(self, code):
                pass

            def get_orders(self):
                return []

            def put_order(self, order):
                pass

            def get_cash(self):
                return 100000

            def get_frozen(self):
                return 0

            def freeze_capital(self, amount):
                return True

            def unfreeze_capital(self, amount):
                return True

            def get_frozen_capital(self):
                return 0

            def calculate_available_cash(self):
                return 100000

            def calculate_available_positions(self):
                return {}

            def process_event(self, event):
                pass

            def publish_event(self, event):
                pass

            def add_component(self, component_type, component):
                if component_type == "strategy":
                    self.strategies.append(component)
                elif component_type == "risk_manager":
                    self.risk_managers.append(component)

            def remove_component(self, component_type, component):
                if component_type == "strategy":
                    if component in self.strategies:
                        self.strategies.remove(component)
                elif component_type == "risk_manager":
                    if component in self.risk_managers:
                        self.risk_managers.remove(component)

            def get_components(self, component_type=None):
                if component_type == "strategy":
                    return self.strategies.copy()
                elif component_type == "risk_manager":
                    return self.risk_managers.copy()
                else:
                    return {"strategies": self.strategies.copy(),
                           "risk_managers": self.risk_managers.copy()}

            def validate_state(self):
                return []

        return MockPortfolio()


@pytest.mark.unit
class TestIPortfolioProtocolEdgeCases:
    """IPortfolio Protocol边界情况测试"""

    def test_empty_portfolio(self):
        """测试空投资组合"""
        portfolio = self._create_mock_portfolio()

        # 验证空投资组合状态
        info = portfolio.get_portfolio_info()
        assert len(info.get('positions', {})) == 0
        assert len(portfolio.get_positions()) == 0
        assert len(portfolio.get_orders()) == 0

        # 验证状态检查
        errors = portfolio.validate_state()
        assert len(errors) == 0

    def test_portfolio_with_positions(self):
        """测试带持仓的投资组合"""
        portfolio = self._create_mock_portfolio()

        # 添加持仓
        position = Mock(code="000001.SZ", volume=1000, market_value=10000)
        portfolio.update_position(position)

        # 验证持仓
        positions = portfolio.get_positions()
        assert len(positions) == 1

        # 验证获取特定持仓
        position = portfolio.get_position("000001.SZ")
        assert position is not None
        assert position.code == "000001.SZ"

    @pytest.mark.parametrize("component_count", [1, 5, 10, 100])
    def test_large_number_of_components(self, component_count):
        """测试大量组件 - 参数化"""
        portfolio = self._create_mock_portfolio()

        # 添加大量策略
        for i in range(component_count):
            strategy = Mock(name=f"Strategy_{i}")
            portfolio.add_strategy(strategy)

        # 验证策略数量
        strategies = portfolio.get_components("strategy")
        assert len(strategies) == component_count

    def _create_mock_portfolio(self):
        """创建模拟投资组合"""
        class MockPortfolio:
            def __init__(self):
                self.name = "TestPortfolio"
                self.uuid = "portfolio_123"
                self.cash = Decimal('100000.0')
                self.frozen = Decimal('0.0')
                self.positions = {}
                self.strategies = []
                self.risk_managers = []
                self.orders = []

            def get_portfolio_info(self):
                return {"uuid": self.uuid, "name": self.name, "cash": self.cash,
                       "frozen": self.frozen, "total_value": self.cash, "positions": self.positions}

            def add_strategy(self, strategy):
                self.strategies.append(strategy)

            def remove_strategy(self, strategy):
                if strategy in self.strategies:
                    self.strategies.remove(strategy)

            def add_risk_manager(self, risk_manager):
                self.risk_managers.append(risk_manager)

            def remove_risk_manager(self, risk_manager):
                if risk_manager in self.risk_managers:
                    self.risk_managers.remove(risk_manager)

            def get_positions(self):
                return list(self.positions.values())

            def get_position(self, code):
                return self.positions.get(code)

            def update_position(self, position):
                self.positions[position.code] = position

            def remove_position(self, code):
                self.positions.pop(code, None)

            def get_orders(self):
                return self.orders.copy()

            def put_order(self, order):
                self.orders.append(order)

            def get_cash(self):
                return self.cash

            def get_frozen(self):
                return self.frozen

            def freeze_capital(self, amount):
                if amount <= self.cash:
                    self.cash -= amount
                    self.frozen += amount
                    return True
                return False

            def unfreeze_capital(self, amount):
                if amount <= self.frozen:
                    self.frozen -= amount
                    self.cash += amount
                    return True
                return False

            def get_frozen_capital(self):
                return self.frozen

            def calculate_available_cash(self):
                return self.cash - self.frozen

            def calculate_available_positions(self):
                return {code: pos for code, pos in self.positions.items()
                       if pos.get('available_volume', pos.get('volume', 0)) > 0}

            def process_event(self, event):
                pass

            def publish_event(self, event):
                pass

            def add_component(self, component_type, component):
                if component_type == "strategy":
                    self.add_strategy(component)
                elif component_type == "risk_manager":
                    self.add_risk_manager(component)

            def remove_component(self, component_type, component):
                if component_type == "strategy":
                    self.remove_strategy(component)
                elif component_type == "risk_manager":
                    self.remove_risk_manager(component)

            def get_components(self, component_type=None):
                if component_type == "strategy":
                    return self.strategies.copy()
                elif component_type == "risk_manager":
                    return self.risk_managers.copy()
                else:
                    return {"strategies": self.strategies.copy(),
                           "risk_managers": self.risk_managers.copy()}

            def validate_state(self):
                errors = []
                if self.cash < 0:
                    errors.append("现金不能为负数")
                if self.frozen < 0:
                    errors.append("冻结资金不能为负数")
                if self.frozen > self.cash:
                    errors.append("冻结资金不能超过现金")
                return errors

        return MockPortfolio()


# ===== 导入 =====

from unittest.mock import Mock
from test.interfaces.conftest import sample_portfolio_data
