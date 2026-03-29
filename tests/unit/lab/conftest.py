"""
Pytest配置和共享fixtures for lab tests.
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock
from datetime import datetime


@pytest.fixture
def mock_portfolio():
    """Mock Portfolio实例."""
    portfolio = Mock()
    portfolio.uuid = "test_portfolio_uuid"
    portfolio.name = "Test Portfolio"
    portfolio.cash = 100000.0
    portfolio.frozen = 0.0
    portfolio.worth = 100000.0
    portfolio.positions = {}
    return portfolio


@pytest.fixture
def mock_strategy():
    """Mock Strategy实例."""
    strategy = Mock()
    strategy.uuid = "test_strategy_uuid"
    strategy.name = "Test Strategy"
    return strategy


@pytest.fixture
def mock_engine():
    """Mock Engine实例."""
    engine = Mock()
    engine.uuid = "test_engine_uuid"
    engine.name = "Test Engine"
    return engine


@pytest.fixture
def mock_signal():
    """Mock Signal实例."""
    from decimal import Decimal

    signal = Mock()
    signal.uuid = "test_signal_uuid"
    signal.code = "000001.SZ"
    signal.direction = "LONG"
    signal.timestamp = datetime(2024, 1, 1, 9, 30, 0)
    signal.price = Decimal("10.0")
    signal.volume = 1000
    return signal


@pytest.fixture
def sample_stock_codes() -> List[str]:
    """示例股票代码列表."""
    return ["000001.SZ", "000002.SZ", "600000.SH", "600594.SH"]


@pytest.fixture
def sample_bar_data():
    """示例K线数据."""
    return {
        "code": "000001.SZ",
        "timestamp": datetime(2024, 1, 1, 9, 30, 0),
        "open": 10.0,
        "high": 10.5,
        "low": 9.8,
        "close": 10.2,
        "volume": 1000000,
    }


@pytest.fixture
def sample_portfolio_info() -> Dict[str, Any]:
    """示例组合信息."""
    return {
        "cash": 100000.0,
        "frozen": 0.0,
        "worth": 100000.0,
        "positions": {},
        "total_value": 100000.0,
    }


def pytest_configure(config):
    """Pytest配置钩子."""
    # 注册自定义标记
    config.addinivalue_line("markers", "unit: 单元测试标记")
    config.addinivalue_line("markers", "integration: 集成测试标记")
    config.addinivalue_line("markers", "lab: 实验性测试标记")
    config.addinivalue_line("markers", "strategy: 策略测试标记")
    config.addinivalue_line("markers", "sizer: 仓位管理测试标记")
    config.addinivalue_line("markers", "selector: 选择器测试标记")
