"""
Interfaces测试共享配置和fixtures

提供pytest fixtures和测试工具函数。
"""

import pytest
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, List
from unittest.mock import Mock

# 导入Ginkgo核心模块
from ginkgo.enums import ENGINESTATUS_TYPES, EXECUTION_MODE
from ginkgo.trading.entities.bar import Bar
from ginkgo.trading.events.price_update import EventPriceUpdate


# ===== Fixtures =====

@pytest.fixture
def sample_bar_data():
    """基础K线数据"""
    return {
        "code": "000001.SZ",
        "open": Decimal('10.0'),
        "high": Decimal('10.8'),
        "low": Decimal('9.8'),
        "close": Decimal('10.5'),
        "volume": 100000,
        "amount": Decimal('1050000.0'),
        "frequency": "DAY",
        "timestamp": datetime(2024, 1, 1, tzinfo=timezone.utc)
    }


@pytest.fixture
def sample_portfolio_data():
    """基础投资组合数据"""
    return {
        "uuid": f"portfolio_{uuid.uuid4().hex[:12]}",
        "name": "TestPortfolio",
        "cash": Decimal('50000.0'),
        "frozen": Decimal('0.0'),
        "total_value": Decimal('100000.0'),
        "positions": {},
        "strategies": [],
        "risk_managers": []
    }


@pytest.fixture
def high_risk_portfolio_data():
    """高风险投资组合数据"""
    return {
        "uuid": f"portfolio_{uuid.uuid4().hex[:12]}",
        "name": "HighRiskPortfolio",
        "cash": Decimal('10000.0'),
        "frozen": Decimal('0.0'),
        "total_value": Decimal('100000.0'),
        "positions": {
            "000001.SZ": {
                "code": "000001.SZ",
                "volume": 9000,
                "cost": Decimal('10.0'),
                "current_price": Decimal('10.0'),
                "market_value": Decimal('90000.0')
            }
        }
    }


@pytest.fixture
def event_factory(sample_bar_data):
    """事件工厂fixture"""
    class EventFactory:
        @staticmethod
        def create_price_update_event(code="000001.SZ", **kwargs):
            """创建价格更新事件"""
            data = sample_bar_data.copy()
            data.update(kwargs)
            bar = Bar(**data)
            return EventPriceUpdate(bar)

    return EventFactory


@pytest.fixture
def portfolio_factory():
    """投资组合工厂fixture"""
    class PortfolioFactory:
        @staticmethod
        def create_basic_portfolio(**kwargs):
            """创建基础投资组合"""
            defaults = {
                "uuid": f"portfolio_{uuid.uuid4().hex[:12]}",
                "cash": Decimal('50000.0'),
                "total_value": Decimal('100000.0'),
                "positions": {}
            }
            defaults.update(kwargs)
            return defaults

        @staticmethod
        def create_high_risk_portfolio(**kwargs):
            """创建高风险投资组合"""
            defaults = {
                "uuid": f"portfolio_{uuid.uuid4().hex[:12]}",
                "cash": Decimal('10000.0'),
                "total_value": Decimal('100000.0'),
                "positions": {
                    "000001.SZ": {
                        "code": "000001.SZ",
                        "volume": 9000,
                        "cost": Decimal('10.0'),
                        "current_price": Decimal('10.0'),
                        "market_value": Decimal('90000.0')
                    }
                }
            }
            defaults.update(kwargs)
            return defaults

        @staticmethod
        def create_conservative_portfolio(**kwargs):
            """创建保守型投资组合"""
            defaults = {
                "uuid": f"portfolio_{uuid.uuid4().hex[:12]}",
                "cash": Decimal('90000.0'),
                "total_value": Decimal('100000.0'),
                "positions": {
                    "000001.SZ": {
                        "code": "000001.SZ",
                        "volume": 1000,
                        "cost": Decimal('10.0'),
                        "current_price": Decimal('10.0'),
                        "market_value": Decimal('10000.0')
                    }
                }
            }
            defaults.update(kwargs)
            return defaults

    return PortfolioFactory


@pytest.fixture
def protocol_factory():
    """协议测试工厂fixture"""
    class ProtocolTestFactory:
        @staticmethod
        def create_strategy_implementation(name: str, strategy_type: str):
            """创建策略实现"""
            strategy = Mock()
            strategy.name = name
            strategy.signals_generated = []

            def cal(portfolio_info, event):
                return []

            def get_strategy_info():
                return {'name': name, 'type': strategy_type}

            strategy.cal = cal
            strategy.get_strategy_info = get_strategy_info
            return strategy

        @staticmethod
        def create_risk_manager_implementation(name: str, risk_type: str):
            """创建风控管理器实现"""
            risk_manager = Mock()
            risk_manager.name = name

            def validate_order(portfolio_info, order):
                return order

            def generate_risk_signals(portfolio_info, event):
                return []

            def check_risk_limits(portfolio_info):
                return []

            def update_risk_parameters(params):
                pass

            def get_risk_metrics(portfolio_info):
                return {
                    "total_value": portfolio_info.get("total_value", 0),
                    "positions_count": len(portfolio_info.get("positions", {}))
                }

            risk_manager.validate_order = validate_order
            risk_manager.generate_risk_signals = generate_risk_signals
            risk_manager.check_risk_limits = check_risk_limits
            risk_manager.update_risk_parameters = update_risk_parameters
            risk_manager.get_risk_metrics = get_risk_metrics

            if risk_type == "stop_loss":
                risk_manager.loss_limit = 0.1
            elif risk_type == "position_ratio":
                risk_manager.max_position_ratio = 0.2
                risk_manager.max_total_position_ratio = 0.8

            return risk_manager

    return ProtocolTestFactory


@pytest.fixture
def mock_engine():
    """模拟引擎fixture"""
    class SimpleMockEngine:
        def __init__(self):
            import time
            self._name = "MockEngine"
            self._engine_id = f"engine_{uuid.uuid4().hex[:12]}"
            self._run_id = None
            self._status = ENGINESTATUS_TYPES.VOID
            self._state = ENGINESTATUS_TYPES.VOID
            self._is_active_flag = False
            self._mode = EXECUTION_MODE.BACKTEST
            self._run_sequence = 1
            self._portfolios = []
            self._event_timeout = 30.0
            self._is_resizing_queue = False
            self.component_type = "ENGINE"
            self.uuid = self._engine_id

        @property
        def name(self):
            return self._name

        @property
        def engine_id(self):
            return self._engine_id

        @property
        def run_id(self):
            return self._run_id

        @property
        def status(self):
            return self._status.value

        @property
        def state(self):
            return self._state

        @property
        def is_active(self):
            return self._is_active_flag

        @property
        def mode(self):
            return self._mode

        @mode.setter
        def mode(self, value):
            self._mode = value

        @property
        def run_sequence(self):
            return self._run_sequence

        @property
        def portfolios(self):
            return self._portfolios.copy()

        @property
        def event_timeout(self):
            return self._event_timeout

        @property
        def is_resizing_queue(self):
            return self._is_resizing_queue

        def start(self):
            if self._state != ENGINESTATUS_TYPES.VOID:
                return False
            self._state = ENGINESTATUS_TYPES.RUNNING
            self._is_active_flag = True
            import time
            self._run_id = f"run_{int(time.time())}"
            return True

        def pause(self):
            if self._state != ENGINESTATUS_TYPES.RUNNING:
                return False
            self._state = ENGINESTATUS_TYPES.PAUSED
            self._is_active_flag = False
            return True

        def stop(self):
            if self._state not in [ENGINESTATUS_TYPES.RUNNING, ENGINESTATUS_TYPES.PAUSED]:
                return False
            self._state = ENGINESTATUS_TYPES.STOPPED
            self._is_active_flag = False
            self._run_id = None
            return True

        def put(self, event):
            pass

        def get_event(self, timeout=None):
            return None

        def handle_event(self, event):
            pass

        def run(self):
            return {"status": "completed"}

        def add_portfolio(self, portfolio):
            if portfolio not in self._portfolios:
                self._portfolios.append(portfolio)

        def remove_portfolio(self, portfolio):
            if portfolio in self._portfolios:
                self._portfolios.remove(portfolio)

        def set_event_timeout(self, timeout):
            self._event_timeout = max(0.1, timeout)

        def set_event_queue_size(self, size):
            return size > 0

        def get_engine_summary(self):
            return {
                "name": self.name,
                "engine_id": self.engine_id,
                "run_id": self.run_id,
                "status": self.status,
                "is_active": self.is_active,
                "run_sequence": self.run_sequence,
                "mode": self.mode.value,
                "portfolios_count": len(self._portfolios)
            }

    return SimpleMockEngine()


@pytest.fixture
def mock_event_base():
    """模拟事件基类fixture"""
    class MockBaseEvent:
        def __init__(self, **kwargs):
            self._uuid = f"event_{uuid.uuid4().hex[:12]}"
            self.event_type = kwargs.get('event_type', 'MockEvent')
            self.timestamp = kwargs.get('timestamp', datetime.now())
            self.code = kwargs.get('code', 'DEFAULT')
            self.run_id = kwargs.get('run_id', 'test_run')

    return MockBaseEvent


# ===== 参数化测试数据 =====

@pytest.mark.parametrize("portfolio_type", ["basic", "high_risk", "conservative"])
def test_portfolio_scenarios(portfolio_type, portfolio_factory):
    """参数化测试不同投资组合场景"""
    if portfolio_type == "basic":
        portfolio = portfolio_factory.create_basic_portfolio()
    elif portfolio_type == "high_risk":
        portfolio = portfolio_factory.create_high_risk_portfolio()
    else:
        portfolio = portfolio_factory.create_conservative_portfolio()

    assert isinstance(portfolio, dict)
    assert "total_value" in portfolio
    assert "cash" in portfolio
    assert "positions" in portfolio


@pytest.mark.parametrize("cash_ratio,expected_cash", [
    (0.0, Decimal('0.0')),
    (0.5, Decimal('50000.0')),
    (1.0, Decimal('100000.0'))
])
def test_portfolio_cash_ratios(cash_ratio, expected_cash, portfolio_factory):
    """参数化测试投资组合现金比例"""
    portfolio = portfolio_factory.create_basic_portfolio(
        total_value=Decimal('100000.0'),
        cash_ratio=cash_ratio,
        positions=[]
    )
    assert portfolio["cash"] == expected_cash


# ===== 辅助函数 =====

def create_mock_portfolio(**kwargs):
    """创建模拟投资组合的辅助函数"""
    defaults = {
        "uuid": f"portfolio_{uuid.uuid4().hex[:12]}",
        "name": "MockPortfolio",
        "cash": Decimal('50000.0'),
        "frozen": Decimal('0.0'),
        "total_value": Decimal('100000.0'),
        "positions": {},
        "strategies": [],
        "risk_managers": []
    }
    defaults.update(kwargs)
    return defaults


def create_mock_order(**kwargs):
    """创建模拟订单的辅助函数"""
    from ginkgo.trading.entities.order import Order
    from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES

    defaults = {
        "code": "000001.SZ",
        "volume": 100,
        "direction": DIRECTION_TYPES.LONG,
        "order_type": ORDER_TYPES.LIMIT,
        "limit_price": Decimal('10.5')
    }
    defaults.update(kwargs)
    return Order(**defaults)
