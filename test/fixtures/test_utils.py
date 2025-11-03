"""
测试工具类 - Trading Framework Enhancement

提供Protocol接口和Mixin功能测试的专用工具：
1. 接口验证工具
2. 混入类测试工具
3. 类型安全检查工具
4. 模拟数据生成工具
"""

from typing import Any, Dict, List, Type, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
import inspect
import uuid
from unittest.mock import Mock, MagicMock

# Ginkgo imports
from ginkgo.trading.entities.order import Order
from ginkgo.trading.entities.position import Position
from ginkgo.trading.entities.signal import Signal
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES

# Protocol imports
from ginkgo.trading.interfaces.protocols.strategy import IStrategy
from ginkgo.trading.interfaces.protocols.risk_management import IRiskManagement
from ginkgo.trading.interfaces.protocols.portfolio import IPortfolio
from ginkgo.trading.interfaces.protocols.engine import IEngine


def generate_test_uuid(prefix: str = "TEST") -> str:
    """
    生成测试用的UUID，带前缀标识

    Args:
        prefix: UUID前缀，用于标识测试数据

    Returns:
        str: 带前缀的UUID字符串，格式: PREFIX_xxxx-xxxx-xxxx-xxxx
    """
    return f"{prefix}_{uuid.uuid4()}"


@dataclass
class MockDataConfig:
    """模拟数据配置"""
    count: int = 10
    start_date: datetime = field(default_factory=lambda: datetime(2024, 1, 1))
    end_date: datetime = field(default_factory=lambda: datetime(2024, 12, 31))
    symbols: List[str] = field(default_factory=lambda: ["000001.SZ", "000002.SZ"])
    initial_price: Decimal = field(default_factory=lambda: Decimal("10.0"))
    volatility: Decimal = field(default_factory=lambda: Decimal("0.02"))


class TradingDataFactory:
    """量化交易数据工厂"""

    def __init__(self, config: MockDataConfig = None):
        self.config = config or MockDataConfig()

    def create_orders(self, portfolio_id: str = "test_portfolio") -> List[Order]:
        """创建模拟订单数据"""
        orders = []
        for i in range(self.config.count):
            order = Order(
                portfolio_id=portfolio_id,
                engine_id=f"test_engine_{i}",
                run_id=f"test_run_{i}",
                code=self.config.symbols[i % len(self.config.symbols)],
                direction=DIRECTION_TYPES.LONG if i % 2 == 0 else DIRECTION_TYPES.SHORT,
                order_type=ORDER_TYPES.LIMITORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=1000 * (i + 1),
                limit_price=float(self.config.initial_price + Decimal(i) * Decimal("0.1")),
                frozen_money=1000 * (i + 1) * float(self.config.initial_price + Decimal(i) * Decimal("0.1")),
                timestamp=self.config.start_date + timedelta(days=i)
            )
            orders.append(order)
        return orders

    def create_positions(self) -> List[Position]:
        """创建模拟持仓数据"""
        positions = []
        for i in range(self.config.count):
            position = Position()
            position.code = self.config.symbols[i % len(self.config.symbols)]
            position.volume = 1000 * (i + 1)
            position.average_cost = self.config.initial_price + Decimal(i) * Decimal("0.05")
            position.current_price = self.config.initial_price + Decimal(i) * Decimal("0.1")
            positions.append(position)
        return positions

    def create_signals(self) -> List[Signal]:
        """创建模拟信号数据"""
        signals = []
        for i in range(self.config.count):
            signal = Signal()
            signal.code = self.config.symbols[i % len(self.config.symbols)]
            signal.direction = DIRECTION_TYPES.LONG if i % 2 == 0 else DIRECTION_TYPES.SHORT
            signal.timestamp = self.config.start_date + timedelta(days=i)
            signal.strength = 0.5 + (i % 5) * 0.1
            signal.reason = f"测试信号_{i}"
            signals.append(signal)
        return signals

    def create_portfolio_info(self, total_value: Decimal = None) -> Dict[str, Any]:
        """创建投资组合信息"""
        positions = self.create_positions()
        total_market_value = sum(p.current_price * p.volume for p in positions)
        cash = (total_value or Decimal("100000.0")) - total_market_value

        return {
            "uuid": "test_portfolio",
            "cash": cash,
            "total_value": total_value or Decimal("100000.0"),
            "positions": {
                pos.code: {
                    "code": pos.code,
                    "volume": pos.volume,
                    "cost": pos.average_cost,
                    "current_price": pos.current_price,
                    "market_value": pos.current_price * pos.volume,
                    "profit_loss": (pos.current_price - pos.average_cost) * pos.volume,
                    "profit_loss_ratio": float((pos.current_price - pos.average_cost) / pos.average_cost)
                }
                for pos in positions
            },
            "risk_metrics": {
                "var": Decimal("0.025"),
                "max_drawdown": Decimal("0.08"),
                "sharpe_ratio": Decimal("1.2"),
                "beta": Decimal("1.1"),
                "leverage": Decimal("1.0")
            }
        }


class ProtocolTestHelper:
    """Protocol接口测试辅助类"""

    @staticmethod
    def create_mock_strategy() -> Mock:
        """创建模拟策略对象"""
        mock_strategy = Mock(spec=IStrategy)
        mock_strategy.name = "MockStrategy"
        mock_strategy.cal.return_value = []
        mock_strategy.get_strategy_info.return_value = {
            "name": "MockStrategy",
            "version": "1.0.0",
            "description": "模拟策略用于测试"
        }
        mock_strategy.validate_parameters.return_value = True
        return mock_strategy

    @staticmethod
    def create_mock_risk_manager() -> Mock:
        """创建模拟风控管理器"""
        mock_risk = Mock(spec=IRiskManagement)
        mock_risk.name = "MockRiskManager"
        mock_risk.validate_order.return_value = None  # 不修改订单
        mock_risk.generate_risk_signals.return_value = []  # 无风控信号
        mock_risk.check_risk_limits.return_value = []
        mock_risk.get_risk_metrics.return_value = {
            "portfolio_var_95": 0.025,
            "max_drawdown": 0.08,
            "volatility": 0.15
        }
        return mock_risk

    @staticmethod
    def create_mock_portfolio() -> Mock:
        """创建模拟投资组合"""
        mock_portfolio = Mock(spec=IPortfolio)
        mock_portfolio.name = "MockPortfolio"
        mock_portfolio.add_strategy.return_value = None
        mock_portfolio.remove_strategy.return_value = True
        mock_portfolio.process_signals.return_value = []
        mock_portfolio.get_portfolio_info.return_value = {
            "name": "MockPortfolio",
            "total_value": 100000.0,
            "available_cash": 50000.0
        }
        mock_portfolio.get_total_value.return_value = 100000.0
        mock_portfolio.get_available_cash.return_value = 50000.0
        return mock_portfolio

    @staticmethod
    def create_mock_engine() -> Mock:
        """创建模拟引擎"""
        mock_engine = Mock(spec=IEngine)
        mock_engine.name = "MockEngine"
        mock_engine.engine_id = "mock_engine_001"
        mock_engine.start.return_value = True
        mock_engine.pause.return_value = True
        mock_engine.stop.return_value = True
        mock_engine.run.return_value = {"status": "completed", "result": "success"}
        mock_engine.handle_event.return_value = None
        mock_engine.status = "Idle"
        mock_engine.is_active = False
        return mock_engine

    @staticmethod
    def validate_protocol_interface(obj: Any, protocol_class: Type) -> Tuple[bool, List[str]]:
        """验证对象是否实现了Protocol接口"""
        errors = []

        # 获取Protocol的所有公共方法
        protocol_methods = {}
        for name, method in inspect.getmembers(protocol_class, predicate=inspect.isfunction):
            if not name.startswith('_'):
                protocol_methods[name] = method

        # 检查每个方法是否存在
        for method_name in protocol_methods:
            if not hasattr(obj, method_name):
                errors.append(f"缺少方法: {method_name}")
                continue

            # 检查方法是否可调用
            obj_method = getattr(obj, method_name)
            if not callable(obj_method):
                errors.append(f"方法不可调用: {method_name}")

        return len(errors) == 0, errors


class MixinTestHelper:
    """Mixin功能测试辅助类"""

    @staticmethod
    def create_test_class_with_mixin(base_class: Type, mixin_class: Type) -> Type:
        """创建包含Mixin的测试类"""
        class TestClass(base_class, mixin_class):
            pass
        TestClass.__name__ = f"Test{base_class.__name__}With{mixin_class.__name__}"
        return TestClass

    @staticmethod
    def validate_mixin_integration(obj: Any, mixin_class: Type, base_class: Type = None) -> Tuple[bool, List[str]]:
        """验证Mixin集成是否正确"""
        errors = []

        # 检查继承关系
        if base_class and not isinstance(obj, base_class):
            errors.append(f"未正确继承基类: {base_class.__name__}")

        if not isinstance(obj, mixin_class):
            errors.append(f"未正确继承Mixin: {mixin_class.__name__}")

        # 检查Mixin方法是否可用
        mixin_methods = {}
        for name, method in inspect.getmembers(mixin_class, predicate=inspect.isfunction):
            if not name.startswith('_'):
                mixin_methods[name] = method

        for method_name in mixin_methods:
            if not hasattr(obj, method_name):
                errors.append(f"Mixin方法未添加: {method_name}")
            else:
                # 尝试访问方法
                try:
                    obj_method = getattr(obj, method_name)
                    if not callable(obj_method):
                        errors.append(f"Mixin方法不可调用: {method_name}")
                except Exception as e:
                    errors.append(f"Mixin方法访问失败: {method_name} - {str(e)}")

        return len(errors) == 0, errors

    @staticmethod
    def test_method_override(base_class: Type, mixin_class: Type, method_name: str) -> bool:
        """测试方法是否被正确覆盖"""
        if not hasattr(base_class, method_name) or not hasattr(mixin_class, method_name):
            return False

        base_method = getattr(base_class, method_name)
        mixin_method = getattr(mixin_class, method_name)

        # 检查方法是否不同
        return base_method != mixin_method


class TypeSafetyValidator:
    """类型安全验证器"""

    @staticmethod
    def validate_method_signatures(obj: Any, expected_methods: Dict[str, inspect.Signature]) -> Tuple[bool, List[str]]:
        """验证方法签名是否符合预期"""
        errors = []

        for method_name, expected_signature in expected_methods.items():
            if not hasattr(obj, method_name):
                errors.append(f"缺少方法: {method_name}")
                continue

            try:
                actual_signature = inspect.signature(getattr(obj, method_name))
                if not TypeSafetyValidator._signatures_compatible(actual_signature, expected_signature):
                    errors.append(f"方法签名不匹配: {method_name}")
            except (ValueError, TypeError):
                errors.append(f"无法解析方法签名: {method_name}")

        return len(errors) == 0, errors

    @staticmethod
    def _signatures_compatible(sig1: inspect.Signature, sig2: inspect.Signature) -> bool:
        """检查两个签名是否兼容"""
        params1 = list(sig1.parameters.values())
        params2 = list(sig2.parameters.values())

        if len(params1) != len(params2):
            return False

        for p1, p2 in zip(params1, params2):
            if p1.kind != p2.kind:
                return False
            if p1.default != p2.default:
                return False

        return True

    @staticmethod
    def validate_return_types(obj: Any, method_name: str, expected_return_type: Type, test_args: tuple = (), test_kwargs: dict = None) -> bool:
        """验证方法返回类型"""
        if not hasattr(obj, method_name):
            return False

        method = getattr(obj, method_name)
        if not callable(method):
            return False

        try:
            result = method(*test_args, **(test_kwargs or {}))
            return isinstance(result, expected_return_type) or (
                hasattr(expected_return_type, '__origin__') and
                isinstance(result, expected_return_type.__origin__)
            )
        except Exception:
            return False


class TestScenarioBuilder:
    """测试场景构建器"""

    def __init__(self):
        self.data_factory = TradingDataFactory()

    def build_strategy_test_scenario(self, scenario_type: str = "normal") -> Dict[str, Any]:
        """构建策略测试场景"""
        base_scenario = {
            "portfolio_info": self.data_factory.create_portfolio_info(),
            "market_event": self._create_price_update_event("000001.SZ", Decimal("10.5")),
            "expected_signals": []
        }

        if scenario_type == "bull_market":
            base_scenario["market_event"].price = Decimal("12.0")
            base_scenario["expected_signals"] = [
                Signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG, reason="牛市买入信号")
            ]
        elif scenario_type == "bear_market":
            base_scenario["market_event"].price = Decimal("8.5")
            base_scenario["expected_signals"] = [
                Signal(code="000001.SZ", direction=DIRECTION_TYPES.SHORT, reason="熊市卖出信号")
            ]

        return base_scenario

    def build_risk_test_scenario(self, risk_type: str = "normal") -> Dict[str, Any]:
        """构建风控测试场景"""
        portfolio_info = self.data_factory.create_portfolio_info()
        order = self.data_factory.create_orders()[0]

        if risk_type == "position_limit":
            # 创建超出仓位限制的订单
            order.volume = 100000  # 超大订单
        elif risk_type == "loss_limit":
            # 创建亏损的投资组合
            position = list(portfolio_info["positions"].values())[0]
            position["current_price"] = Decimal("8.0")
            position["profit_loss_ratio"] = -0.2

        return {
            "portfolio_info": portfolio_info,
            "order": order,
            "risk_type": risk_type
        }

    def build_portfolio_test_scenario(self, state: str = "normal") -> Dict[str, Any]:
        """构建投资组合测试场景"""
        portfolio_info = self.data_factory.create_portfolio_info()
        signals = self.data_factory.create_signals()

        if state == "cash_insufficient":
            portfolio_info["available_cash"] = Decimal("100.0")  # 现金不足
        elif state == "max_positions":
            # 添加更多持仓直到达到上限
            for i in range(10):
                new_symbol = f"60000{i}.SH"
                portfolio_info["positions"][new_symbol] = {
                    "code": new_symbol,
                    "volume": 1000,
                    "cost": Decimal("10.0"),
                    "current_price": Decimal("10.5"),
                    "market_value": Decimal("10500.0"),
                    "profit_loss": Decimal("500.0"),
                    "profit_loss_ratio": 0.05
                }

        return {
            "portfolio_info": portfolio_info,
            "signals": signals[:3],  # 取前3个信号
            "state": state
        }

    def _create_price_update_event(self, symbol: str, price: Decimal):
        """创建价格更新事件"""
        # 简化的事件对象
        event = Mock()
        event.code = symbol
        event.price = price
        event.timestamp = datetime.now()
        event.volume = 100000
        return event


class AssertionHelper:
    """断言辅助类"""

    @staticmethod
    def assert_financial_precision(actual: Decimal, expected: Decimal, places: int = 4):
        """断言金融精度"""
        if not isinstance(actual, Decimal):
            raise AssertionError(f"实际值不是Decimal类型: {type(actual)}")
        if not isinstance(expected, Decimal):
            raise AssertionError(f"期望值不是Decimal类型: {type(expected)}")

        tolerance = Decimal(10) ** (-places)
        diff = abs(actual - expected)
        if diff > tolerance:
            raise AssertionError(
                f"金融精度不匹配: 实际值 {actual}, 期望值 {expected}, "
                f"差值 {diff}, 容差 {tolerance} (精度: {places}位小数)"
            )

    @staticmethod
    def assert_protocol_compliance(obj: Any, protocol_class: Type):
        """断言Protocol接口符合性"""
        is_compliant, errors = ProtocolTestHelper.validate_protocol_interface(obj, protocol_class)
        if not is_compliant:
            error_msg = "; ".join(errors)
            raise AssertionError(f"对象不符合 {protocol_class.__name__} 接口要求: {error_msg}")

    @staticmethod
    def assert_mixin_functionality(obj: Any, mixin_class: Type, base_class: Type = None):
        """断言Mixin功能"""
        is_functional, errors = MixinTestHelper.validate_mixin_integration(obj, mixin_class, base_class)
        if not is_functional:
            error_msg = "; ".join(errors)
            raise AssertionError(f"Mixin功能验证失败: {error_msg}")

    @staticmethod
    def assert_list_not_empty(lst: List[Any], message: str = "列表不应为空"):
        """断言列表非空"""
        if not lst:
            raise AssertionError(message)

    @staticmethod
    def assert_dict_contains_keys(d: Dict[str, Any], required_keys: List[str]):
        """断言字典包含必需键"""
        missing_keys = [key for key in required_keys if key not in d]
        if missing_keys:
            raise AssertionError(f"字典缺少必需键: {missing_keys}")

    @staticmethod
    def assert_datetime_range(dt: datetime, start: datetime, end: datetime):
        """断言日期时间在指定范围内"""
        if not (start <= dt <= end):
            raise AssertionError(f"日期时间 {dt} 不在范围 [{start}, {end}] 内")